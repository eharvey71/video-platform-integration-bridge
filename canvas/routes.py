from flask import Blueprint, request, redirect, session, jsonify, abort
from flask_login import login_required
from src.models import CanvasOauthConfig, CanvasAuthorizedUsers, db
import src.logger as logger
import requests, secrets, time

canvas_bp = Blueprint('canvas', __name__, template_folder='templates')

# Canvas is the only party that should ever see the client secret, so every call
# out to it is server-side and nothing from those responses is echoed back to the
# browser.
CANVAS_HTTP_TIMEOUT = 30


def _oauth_config_or_404():
    oauth_config = CanvasOauthConfig.query.get(1)
    if not oauth_config:
        abort(404, description="Canvas OAuth configuration has not been set up")
    return oauth_config


# Redirect URI route
@canvas_bp.route("/oauth2response", methods=["GET"])
def oauth2response():

    # The state we minted in canvas_config must come back untouched. Without this
    # check an attacker can feed us their own authorization code and bind their
    # Canvas account to this install.
    expected_state = session.pop('canvas_oauth_state', None)
    received_state = request.args.get("state")
    if not expected_state or not received_state or not secrets.compare_digest(
        expected_state, received_state
    ):
        logger.log("Canvas OAuth callback rejected: state mismatch")
        return redirect('/canvas?error=invalid_state')

    code = request.args.get("code")
    if not code:
        return redirect('/canvas?error=no_code')

    oauth_config = _oauth_config_or_404()

    # Exchange the code for an access token
    token_url = f"{oauth_config.canvas_base_url}/login/oauth2/token"
    response = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "client_id": oauth_config.canvas_client_id,
            "client_secret": oauth_config.canvas_client_secret,
            "redirect_uri": oauth_config.redirect_uri,
            "code": code,
        },
        timeout=CANVAS_HTTP_TIMEOUT,
    )

    if response.status_code != 200:
        logger.log(f"Canvas token exchange failed with status {response.status_code}")
        return redirect('/canvas?error=exchange_failed')

    payload = response.json()
    user_id = payload.get("user", {}).get("id")
    full_name = payload.get("user", {}).get("name")

    existing_user = CanvasAuthorizedUsers.query.filter_by(user_id=user_id).first()
    if existing_user:
        return redirect('/canvas?status=already_authorized')

    authorized_user = CanvasAuthorizedUsers(
        primary_email='email_not_stored',
        user_id=user_id,
        full_name=full_name,
        canvas_access_token=payload["access_token"],
        canvas_refresh_token=payload["refresh_token"],
        # expires_in is a duration; store the absolute epoch so callers can tell
        # whether the token is still valid
        canvas_token_expiry=int(time.time()) + int(payload.get("expires_in", 0)),
    )
    db.session.add(authorized_user)
    db.session.commit()
    logger.log(f"Canvas authorization stored for user_id {user_id}")

    return redirect('/canvas?status=authorized')


@canvas_bp.route("/refreshtoken", methods=["POST"])
@login_required
def refreshtoken():
    """Refresh a stored Canvas authorization.

    Takes the Canvas user_id and uses the refresh token already on record; the
    token itself is never accepted from, or returned to, the caller.
    """
    user_id = request.form.get("user_id") or (request.get_json(silent=True) or {}).get("user_id")
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    authorized_user = CanvasAuthorizedUsers.query.filter_by(user_id=user_id).first()
    if not authorized_user:
        return jsonify({"error": "No stored authorization for that user"}), 404

    oauth_config = _oauth_config_or_404()

    token_url = f"{oauth_config.canvas_base_url}/login/oauth2/token"
    response = requests.post(
        token_url,
        data={
            "grant_type": "refresh_token",
            "client_id": oauth_config.canvas_client_id,
            "client_secret": oauth_config.canvas_client_secret,
            "refresh_token": authorized_user.canvas_refresh_token,
        },
        timeout=CANVAS_HTTP_TIMEOUT,
    )

    if response.status_code != 200:
        logger.log(f"Canvas token refresh failed for user_id {user_id} with status {response.status_code}")
        return jsonify({"error": "Failed to refresh token"}), 502

    payload = response.json()
    authorized_user.canvas_access_token = payload["access_token"]
    # Canvas only returns a new refresh token when it rotates one
    if payload.get("refresh_token"):
        authorized_user.canvas_refresh_token = payload["refresh_token"]
    authorized_user.canvas_token_expiry = int(time.time()) + int(payload.get("expires_in", 0))
    db.session.commit()
    logger.log(f"Canvas token refreshed for user_id {user_id}")

    return jsonify({
        "user_id": authorized_user.user_id,
        "expires_at": authorized_user.canvas_token_expiry,
    })
