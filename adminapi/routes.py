"""JSON API backing the admin single-page app.

Mounted at /adminapi. The vendor-facing Connexion specs already own /api
(Kaltura) and /zoomapi, so this keeps clear of both.

Two rules hold throughout:
  * every route requires an authenticated session, except the login and session
    probe endpoints;
  * stored vendor secrets are never sent back to the browser. Reads report
    whether a secret is set; writes accept a new value.
"""
import logging
import secrets
import time
from urllib.parse import quote

from flask import Blueprint, jsonify, request, session
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

import src.logger as logger
from src.auth_handler import generate_token
from src.csrf import (
    attach_csrf_cookie,
    csrf_is_valid,
    get_csrf_token,
    rotate_csrf_token,
)
from src.models import (
    AccessRestrictions,
    AppTokenSessionDefaults,
    CanvasAuthorizedUsers,
    CanvasOauthConfig,
    KalturaAppToken,
    Note,
    UICustomizations,
    User,
    VendorProxies,
    ZoomClientConfig,
    db,
)

adminapi_bp = Blueprint("adminapi", __name__)

# Endpoints reachable without a session. Everything else is gated below.
PUBLIC_ENDPOINTS = {"adminapi.session_get", "adminapi.session_login"}


@adminapi_bp.before_request
def guard():
    if not csrf_is_valid():
        return jsonify({"error": "Invalid or missing CSRF token"}), 403
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required"}), 401
    return None


@adminapi_bp.after_request
def add_csrf_cookie(response):
    return attach_csrf_cookie(response)


def _body():
    return request.get_json(silent=True) or {}


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _as_int(value, field):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a number")


# --------------------------------------------------------------------------
# Session
# --------------------------------------------------------------------------

def _feature_flags():
    proxies = VendorProxies.query.get(1)
    return {
        "kaltura": bool(proxies and proxies.kaltura_proxy_enabled),
        "canvas": bool(proxies and proxies.canvas_proxy_enabled),
        "zoom": bool(proxies and proxies.zoom_proxy_enabled),
    }


def _app_title():
    customizations = UICustomizations.query.get(1)
    return customizations.integrator_title if customizations else "Integration Manager"


def _session_payload():
    payload = {
        "authenticated": current_user.is_authenticated,
        "csrfToken": get_csrf_token(),
        "title": _app_title(),
        "features": _feature_flags(),
    }
    if current_user.is_authenticated:
        payload["user"] = {
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
        }
    return payload


@adminapi_bp.route("/session", methods=["GET"])
def session_get():
    return jsonify(_session_payload())


@adminapi_bp.route("/session", methods=["POST"])
def session_login():
    data = _body()
    username = data.get("username") or ""
    password = data.get("password") or ""

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        logger.log("login attempt failed for user: " + str(username))
        # Deliberately identical for an unknown username and a bad password.
        return jsonify({"error": "Invalid credentials"}), 401

    logger.log("login attempt succeeded for user: " + username)
    login_user(user, remember=bool(data.get("remember")))
    # A token minted before authentication must not carry into the new session.
    rotate_csrf_token()
    return jsonify(_session_payload())


@adminapi_bp.route("/session", methods=["DELETE"])
@login_required
def session_logout():
    logout_user()
    session.pop("oauth_token", None)
    session.pop("oauth_provider", None)
    rotate_csrf_token()
    return jsonify(_session_payload())


@adminapi_bp.route("/session/token", methods=["POST"])
@login_required
def session_api_token():
    """Short-lived JWT for calling the Connexion-served vendor APIs."""
    return jsonify({"token": generate_token(current_user.username)})


# --------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------

@adminapi_bp.route("/settings", methods=["GET"])
def settings_get():
    return jsonify({"title": _app_title(), "features": _feature_flags()})


@adminapi_bp.route("/settings/ui", methods=["PUT"])
def settings_ui_put():
    title = (_body().get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    customizations = UICustomizations.query.get(1)
    if not customizations:
        customizations = UICustomizations(id=1, integrator_title=title)
        db.session.add(customizations)
    else:
        customizations.integrator_title = title
    db.session.commit()
    logger.log(f"Integrator title updated to: {title}")
    return jsonify({"title": title})


@adminapi_bp.route("/settings/proxies", methods=["PUT"])
def settings_proxies_put():
    data = _body()
    proxies = VendorProxies.query.get(1)
    if not proxies:
        proxies = VendorProxies(
            id=1, kaltura_proxy_enabled=False,
            canvas_proxy_enabled=False, zoom_proxy_enabled=False,
        )
        db.session.add(proxies)

    proxies.kaltura_proxy_enabled = _as_bool(data.get("kaltura"))
    proxies.canvas_proxy_enabled = _as_bool(data.get("canvas"))
    proxies.zoom_proxy_enabled = _as_bool(data.get("zoom"))
    db.session.commit()
    logger.log("Proxy configurations updated")
    return jsonify({"features": _feature_flags()})


@adminapi_bp.route("/users", methods=["POST"])
def users_post():
    data = _body()
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    email = (data.get("email") or "").strip()
    role = (data.get("role") or "").strip()

    if not username or not password or not email or not role:
        return jsonify({"error": "username, password, email and role are required"}), 400
    if len(password) < 12:
        return jsonify({"error": "Password must be at least 12 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "That username is already taken"}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "That email is already associated with another user"}), 409

    db.session.add(User(
        username=username,
        password=generate_password_hash(password, method="pbkdf2"),
        email=email,
        role=role,
    ))
    db.session.commit()
    logger.log(f"New user added: {username}")
    return jsonify({"username": username, "email": email, "role": role}), 201


# --------------------------------------------------------------------------
# Kaltura
# --------------------------------------------------------------------------

def _note_json(note):
    return {
        "id": note.id,
        "content": note.content,
        "timestamp": note.timestamp.isoformat() if note.timestamp else None,
    }


def _token_json(token):
    return {
        "kalturaTokenId": token.kaltura_token_id,
        "token": token.token,
        "partnerId": token.partner_id,
        "createdAt": token.created_at,
        "updatedAt": token.updated_at,
        "status": token.status,
        "sessionType": token.session_type,
        "expiry": token.expiry,
        "sessionDuration": token.session_duration,
        "sessionUserId": token.session_user_id,
        "sessionPrivileges": token.session_privileges,
        "description": token.description,
        "label": token.label,
        "notes": [_note_json(n) for n in token.notes],
    }


@adminapi_bp.route("/kaltura/config", methods=["GET"])
def kaltura_config_get():
    restrictions = AccessRestrictions.query.get(1)
    defaults = AppTokenSessionDefaults.query.get(1)
    return jsonify({
        "allowedCategories": (restrictions.allowed_categories if restrictions else "") or "",
        "forceLabels": bool(restrictions and restrictions.force_labels),
        "partnerId": defaults.partner_id if defaults else None,
        "sessionExpiry": defaults.session_expiry if defaults else None,
        "useLocalStorage": bool(defaults and defaults.use_local_storage),
    })


@adminapi_bp.route("/kaltura/config", methods=["PUT"])
def kaltura_config_put():
    data = _body()

    restrictions = AccessRestrictions.query.get(1)
    if not restrictions:
        restrictions = AccessRestrictions(id=1, force_labels=False)
        db.session.add(restrictions)

    if "allowedCategories" in data:
        raw = (data.get("allowedCategories") or "").replace(" ", "")
        entries = [e for e in raw.split(",") if e]
        for entry in entries:
            if not entry.isdigit():
                return jsonify({
                    "error": f"'{entry}' is not a category ID. Use a comma-separated list of numbers."
                }), 400
        restrictions.allowed_categories = ",".join(entries)
    if "forceLabels" in data:
        restrictions.force_labels = _as_bool(data.get("forceLabels"))

    defaults = AppTokenSessionDefaults.query.get(1)
    if not defaults:
        defaults = AppTokenSessionDefaults(id=1, partner_id=0, use_local_storage=False)
        db.session.add(defaults)

    try:
        if "partnerId" in data:
            defaults.partner_id = _as_int(data.get("partnerId"), "partnerId")
        if "sessionExpiry" in data:
            defaults.session_expiry = _as_int(data.get("sessionExpiry"), "sessionExpiry")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    if "useLocalStorage" in data:
        defaults.use_local_storage = _as_bool(data.get("useLocalStorage"))

    db.session.commit()
    logger.log("Kaltura configuration updated")
    return kaltura_config_get()


@adminapi_bp.route("/kaltura/tokens", methods=["GET"])
def kaltura_tokens_get():
    return jsonify({"tokens": [_token_json(t) for t in KalturaAppToken.query.all()]})


@adminapi_bp.route("/kaltura/tokens", methods=["POST"])
def kaltura_tokens_post():
    data = _body()
    token_id = (data.get("kalturaTokenId") or "").strip()
    token_value = (data.get("token") or "").strip()
    label = (data.get("label") or "").strip() or None

    if not token_id or not token_value:
        return jsonify({"error": "kalturaTokenId and token are required"}), 400
    if KalturaAppToken.query.get(token_id):
        return jsonify({"error": f"Token {token_id} is already registered"}), 409
    if label and KalturaAppToken.query.filter_by(label=label).first():
        return jsonify({"error": f"Label '{label}' is already in use"}), 409

    new_token = KalturaAppToken(
        kaltura_token_id=token_id,
        token=token_value,
        label=label,
        partner_id=data.get("partnerId"),
        description=data.get("description"),
        session_privileges=data.get("sessionPrivileges"),
        session_user_id=data.get("sessionUserId"),
        expiry=data.get("expiry") or 0,
        session_duration=data.get("sessionDuration") or 86400,
    )
    db.session.add(new_token)
    db.session.commit()
    logger.log(f"Kaltura app token added: {token_id}")
    return jsonify(_token_json(new_token)), 201


@adminapi_bp.route("/kaltura/tokens/<kaltura_token_id>", methods=["DELETE"])
def kaltura_tokens_delete(kaltura_token_id):
    token = KalturaAppToken.query.get(kaltura_token_id)
    if not token:
        return jsonify({"error": f"Token {kaltura_token_id} not found"}), 404
    db.session.delete(token)
    db.session.commit()
    logger.log(f"Kaltura app token deleted: {kaltura_token_id}")
    return "", 204


@adminapi_bp.route("/kaltura/tokens/<kaltura_token_id>/notes", methods=["POST"])
def kaltura_token_notes_post(kaltura_token_id):
    token = KalturaAppToken.query.get(kaltura_token_id)
    if not token:
        return jsonify({"error": f"Token {kaltura_token_id} not found"}), 404

    content = (_body().get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    note = Note(content=content)
    token.notes.append(note)
    db.session.commit()
    return jsonify(_note_json(note)), 201


@adminapi_bp.route("/notes/<int:note_id>", methods=["PUT"])
def notes_put(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": f"Note {note_id} not found"}), 404

    content = (_body().get("content") or "").strip()
    if not content:
        return jsonify({"error": "content is required"}), 400

    note.content = content
    db.session.commit()
    return jsonify(_note_json(note))


@adminapi_bp.route("/notes/<int:note_id>", methods=["DELETE"])
def notes_delete(note_id):
    note = Note.query.get(note_id)
    if not note:
        return jsonify({"error": f"Note {note_id} not found"}), 404
    db.session.delete(note)
    db.session.commit()
    return "", 204


# --------------------------------------------------------------------------
# Zoom
# --------------------------------------------------------------------------

@adminapi_bp.route("/zoom/config", methods=["GET"])
def zoom_config_get():
    config = ZoomClientConfig.query.get(1)
    if not config:
        return jsonify({
            "clientId": "", "accountId": "",
            "clientSecretSet": False, "accessKey": None, "requireAccessKey": False,
        })
    return jsonify({
        "clientId": config.zoom_client_id or "",
        "accountId": config.zoom_account_id or "",
        # the secret itself never leaves the server
        "clientSecretSet": bool(config.zoom_client_secret),
        "accessKey": config.access_key,
        "requireAccessKey": bool(config.require_access_key),
    })


def _zoom_config_row():
    config = ZoomClientConfig.query.get(1)
    if not config:
        config = ZoomClientConfig(
            id=1, zoom_client_id="", zoom_client_secret="", zoom_account_id="",
            access_key=secrets.token_urlsafe(32), require_access_key=False,
        )
        db.session.add(config)
        db.session.commit()
    return config


@adminapi_bp.route("/zoom/config", methods=["PUT"])
def zoom_config_put():
    data = _body()
    config = _zoom_config_row()

    if "clientId" in data:
        config.zoom_client_id = (data.get("clientId") or "").strip()
    if "accountId" in data:
        config.zoom_account_id = (data.get("accountId") or "").strip()
    # An omitted or blank secret leaves the stored one alone, so the UI can save
    # the rest of the form without round-tripping the secret through the browser.
    if data.get("clientSecret"):
        config.zoom_client_secret = data["clientSecret"]
    if "requireAccessKey" in data:
        config.require_access_key = _as_bool(data.get("requireAccessKey"))

    db.session.commit()
    logger.log("Zoom client config updated")
    return zoom_config_get()


@adminapi_bp.route("/zoom/access-key", methods=["POST"])
def zoom_access_key_post():
    config = _zoom_config_row()
    config.access_key = secrets.token_urlsafe(32)
    db.session.commit()
    logger.log("Zoom access key regenerated")
    return jsonify({"accessKey": config.access_key})


# --------------------------------------------------------------------------
# Canvas
# --------------------------------------------------------------------------

@adminapi_bp.route("/canvas/config", methods=["GET"])
def canvas_config_get():
    config = CanvasOauthConfig.query.get(1)
    users = [
        {
            "id": u.id,
            "userId": u.user_id,
            "fullName": u.full_name,
            "tokenExpiry": u.canvas_token_expiry,
            "expired": bool(u.canvas_token_expiry and u.canvas_token_expiry < int(time.time())),
        }
        for u in CanvasAuthorizedUsers.query.all()
    ]
    if not config:
        return jsonify({
            "baseUrl": "", "clientId": "", "redirectUri": "",
            "clientSecretSet": False, "authorizedUsers": users,
        })
    return jsonify({
        "baseUrl": config.canvas_base_url or "",
        "clientId": config.canvas_client_id,
        "redirectUri": config.redirect_uri or "",
        "clientSecretSet": bool(config.canvas_client_secret),
        "authorizedUsers": users,
    })


@adminapi_bp.route("/canvas/config", methods=["PUT"])
def canvas_config_put():
    data = _body()
    config = CanvasOauthConfig.query.get(1)
    if not config:
        config = CanvasOauthConfig(
            id=1, canvas_base_url="", canvas_client_id=0,
            canvas_client_secret="", redirect_uri="",
        )
        db.session.add(config)

    if "baseUrl" in data:
        config.canvas_base_url = (data.get("baseUrl") or "").strip().rstrip("/")
    if "redirectUri" in data:
        config.redirect_uri = (data.get("redirectUri") or "").strip()
    if "clientId" in data:
        try:
            config.canvas_client_id = _as_int(data.get("clientId"), "clientId")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    if data.get("clientSecret"):
        config.canvas_client_secret = data["clientSecret"]

    db.session.commit()
    logger.log("Canvas OAuth config updated")
    return canvas_config_get()


@adminapi_bp.route("/canvas/authorize-url", methods=["POST"])
def canvas_authorize_url():
    """Mint the Canvas authorization URL and stash the state it must return.

    A POST rather than a GET because it writes session state, and so it carries
    the CSRF header like every other mutating call.
    """
    config = CanvasOauthConfig.query.get(1)
    if not config or not config.canvas_base_url or not config.redirect_uri:
        return jsonify({"error": "Canvas OAuth is not configured yet"}), 400

    state = secrets.token_urlsafe(32)
    session["canvas_oauth_state"] = state

    return jsonify({"url": (
        f"{config.canvas_base_url}/login/oauth2/auth"
        f"?client_id={config.canvas_client_id}"
        f"&response_type=code"
        f"&state={state}"
        f"&redirect_uri={quote(config.redirect_uri, safe='')}"
    )})


@adminapi_bp.route("/canvas/users/<int:row_id>", methods=["DELETE"])
def canvas_user_delete(row_id):
    user = CanvasAuthorizedUsers.query.get(row_id)
    if not user:
        return jsonify({"error": "Authorized user not found"}), 404
    db.session.delete(user)
    db.session.commit()
    logger.log(f"Canvas authorization revoked for user_id {user.user_id}")
    return "", 204


# --------------------------------------------------------------------------
# Logs
# --------------------------------------------------------------------------

@adminapi_bp.route("/logs", methods=["GET"])
def logs_get():
    """Most recent log lines, newest first."""
    try:
        limit = min(max(int(request.args.get("limit", 500)), 1), 5000)
    except (TypeError, ValueError):
        limit = 500

    handlers = logging.getLogger("RotatingLog").handlers
    if not handlers:
        return jsonify({"lines": []})

    try:
        with open(handlers[0].baseFilename, "r") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return jsonify({"lines": []})

    return jsonify({"lines": list(reversed(lines))[:limit], "total": len(lines)})
