"""Contract tests for the admin JSON API: the auth gate, CSRF, and secret handling."""
import time

import pytest
from werkzeug.security import generate_password_hash

from src.models import User, ZoomClientConfig, VendorProxies, db

PASSWORD = "correct-horse-battery"


@pytest.fixture
def admin(app_ctx):
    user = User(
        username="admin", email="admin@example.edu", role="admin",
        password=generate_password_hash(PASSWORD, method="pbkdf2"),
    )
    db.session.add(user)
    db.session.add(VendorProxies(
        id=1, kaltura_proxy_enabled=True,
        canvas_proxy_enabled=False, zoom_proxy_enabled=True,
    ))
    db.session.commit()
    return user


def _login(client):
    """Sign in and return the CSRF token for subsequent mutating calls."""
    token = client.get("/adminapi/session").get_json()["csrfToken"]
    resp = client.post(
        "/adminapi/session",
        json={"username": "admin", "password": PASSWORD},
        headers={"X-CSRF-Token": token},
    )
    assert resp.status_code == 200
    return resp.get_json()["csrfToken"]


def test_session_probe_is_anonymous_and_reports_unauthenticated(client, admin):
    body = client.get("/adminapi/session").get_json()
    assert body["authenticated"] is False
    assert "user" not in body
    assert body["csrfToken"]


def test_protected_routes_require_authentication(client, admin):
    for path in ["/adminapi/settings", "/adminapi/kaltura/tokens",
                 "/adminapi/zoom/config", "/adminapi/logs"]:
        assert client.get(path).status_code == 401


def test_login_and_logout_round_trip(client, admin):
    csrf = _login(client)
    body = client.get("/adminapi/session").get_json()
    assert body["authenticated"] is True
    assert body["user"]["username"] == "admin"
    assert body["features"] == {"kaltura": True, "canvas": False, "zoom": True}

    assert client.delete("/adminapi/session", headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/adminapi/session").get_json()["authenticated"] is False


def test_bad_password_is_rejected(client, admin):
    csrf = client.get("/adminapi/session").get_json()["csrfToken"]
    resp = client.post("/adminapi/session",
                       json={"username": "admin", "password": "wrong"},
                       headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 401
    assert client.get("/adminapi/session").get_json()["authenticated"] is False


def test_unknown_user_and_bad_password_are_indistinguishable(client, admin):
    csrf = client.get("/adminapi/session").get_json()["csrfToken"]
    a = client.post("/adminapi/session", json={"username": "admin", "password": "wrong"},
                    headers={"X-CSRF-Token": csrf})
    b = client.post("/adminapi/session", json={"username": "nobody", "password": "wrong"},
                    headers={"X-CSRF-Token": csrf})
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json()


def test_mutating_request_without_csrf_header_is_refused(client, admin):
    _login(client)
    resp = client.put("/adminapi/settings/ui", json={"title": "Pwned"})
    assert resp.status_code == 403
    assert client.get("/adminapi/settings").get_json()["title"] != "Pwned"


def test_mutating_request_with_wrong_csrf_token_is_refused(client, admin):
    _login(client)
    resp = client.put("/adminapi/settings/ui", json={"title": "Pwned"},
                      headers={"X-CSRF-Token": "not-the-token"})
    assert resp.status_code == 403


def test_csrf_token_rotates_on_login(client, admin):
    before = client.get("/adminapi/session").get_json()["csrfToken"]
    after = _login(client)
    assert before != after


def test_settings_round_trip(client, admin):
    csrf = _login(client)
    assert client.put("/adminapi/settings/ui", json={"title": "Media Bridge"},
                      headers={"X-CSRF-Token": csrf}).status_code == 200
    assert client.get("/adminapi/settings").get_json()["title"] == "Media Bridge"

    resp = client.put("/adminapi/settings/proxies",
                      json={"kaltura": False, "canvas": True, "zoom": False},
                      headers={"X-CSRF-Token": csrf})
    assert resp.get_json()["features"] == {"kaltura": False, "canvas": True, "zoom": False}


def test_blank_title_is_rejected(client, admin):
    csrf = _login(client)
    assert client.put("/adminapi/settings/ui", json={"title": "   "},
                      headers={"X-CSRF-Token": csrf}).status_code == 400


def test_zoom_client_secret_is_never_returned(client, admin):
    db.session.add(ZoomClientConfig(
        id=1, zoom_client_id="cid", zoom_client_secret="super-secret",
        zoom_account_id="aid", access_key="ak", require_access_key=True,
    ))
    db.session.commit()
    csrf = _login(client)

    body = client.get("/adminapi/zoom/config").get_json()
    assert "super-secret" not in str(body)
    assert body["clientSecretSet"] is True
    assert body["clientId"] == "cid"


def test_omitting_zoom_secret_on_update_preserves_it(client, admin):
    db.session.add(ZoomClientConfig(
        id=1, zoom_client_id="cid", zoom_client_secret="super-secret",
        zoom_account_id="aid", access_key="ak", require_access_key=False,
    ))
    db.session.commit()
    csrf = _login(client)

    client.put("/adminapi/zoom/config", json={"clientId": "new-cid"},
               headers={"X-CSRF-Token": csrf})
    assert ZoomClientConfig.query.get(1).zoom_client_secret == "super-secret"
    assert ZoomClientConfig.query.get(1).zoom_client_id == "new-cid"


def test_regenerating_the_access_key_changes_it(client, admin):
    db.session.add(ZoomClientConfig(
        id=1, zoom_client_id="c", zoom_client_secret="s", zoom_account_id="a",
        access_key="original", require_access_key=True,
    ))
    db.session.commit()
    csrf = _login(client)

    new_key = client.post("/adminapi/zoom/access-key",
                          headers={"X-CSRF-Token": csrf}).get_json()["accessKey"]
    assert new_key != "original" and len(new_key) > 20


def test_kaltura_token_lifecycle(client, admin):
    csrf = _login(client)
    h = {"X-CSRF-Token": csrf}

    created = client.post("/adminapi/kaltura/tokens",
                          json={"kalturaTokenId": "1_abc", "token": "t0k3n", "label": "ANTH-201"},
                          headers=h)
    assert created.status_code == 201

    assert client.post("/adminapi/kaltura/tokens",
                       json={"kalturaTokenId": "1_abc", "token": "other"},
                       headers=h).status_code == 409
    assert client.post("/adminapi/kaltura/tokens",
                       json={"kalturaTokenId": "1_xyz", "token": "t", "label": "ANTH-201"},
                       headers=h).status_code == 409

    note = client.post("/adminapi/kaltura/tokens/1_abc/notes",
                       json={"content": "Read-only for ANTH"}, headers=h)
    assert note.status_code == 201

    tokens = client.get("/adminapi/kaltura/tokens").get_json()["tokens"]
    assert len(tokens) == 1 and len(tokens[0]["notes"]) == 1

    assert client.delete("/adminapi/kaltura/tokens/1_abc", headers=h).status_code == 204
    assert client.get("/adminapi/kaltura/tokens").get_json()["tokens"] == []


def test_allowed_categories_rejects_non_numeric_entries(client, admin):
    csrf = _login(client)
    resp = client.put("/adminapi/kaltura/config",
                      json={"allowedCategories": "594123,not-a-number"},
                      headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 400

    ok = client.put("/adminapi/kaltura/config",
                    json={"allowedCategories": "594123, 634123", "forceLabels": True},
                    headers={"X-CSRF-Token": csrf})
    assert ok.get_json()["allowedCategories"] == "594123,634123"
    assert ok.get_json()["forceLabels"] is True


def test_new_user_password_has_a_minimum_length(client, admin):
    csrf = _login(client)
    resp = client.post("/adminapi/users",
                       json={"username": "u", "password": "short",
                             "email": "u@example.edu", "role": "admin"},
                       headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 400


def test_duplicate_user_is_rejected(client, admin):
    csrf = _login(client)
    resp = client.post("/adminapi/users",
                       json={"username": "admin", "password": "a-long-enough-password",
                             "email": "new@example.edu", "role": "admin"},
                       headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 409


# --- Regressions from the PR #2 review -------------------------------------

def test_expired_session_reports_401_not_403(client, admin):
    """A dropped session takes its CSRF token with it. Answering 'bad CSRF'
    left the SPA unable to tell it simply needed to sign in again."""
    csrf = _login(client)
    client.delete("/adminapi/session", headers={"X-CSRF-Token": csrf})

    assert client.get("/adminapi/settings").status_code == 401
    resp = client.put("/adminapi/settings/ui", json={"title": "x"},
                      headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 401


def test_login_still_requires_csrf_after_the_reorder(client, admin):
    resp = client.post("/adminapi/session",
                       json={"username": "admin", "password": PASSWORD})
    assert resp.status_code == 403


def test_kaltura_config_accepts_the_nulls_its_own_get_returns(client, admin):
    """The UI round-trips the whole object, and GET reports these as null when
    no defaults row exists, so a null must not be a 400."""
    csrf = _login(client)
    current = client.get("/adminapi/kaltura/config").get_json()
    assert current["partnerId"] is None

    resp = client.put("/adminapi/kaltura/config",
                      json={**current, "allowedCategories": "594123"},
                      headers={"X-CSRF-Token": csrf})
    assert resp.status_code == 200
    assert resp.get_json()["allowedCategories"] == "594123"


def test_partial_proxy_body_leaves_omitted_flags_alone(client, admin):
    csrf = _login(client)
    resp = client.put("/adminapi/settings/proxies", json={"canvas": True},
                      headers={"X-CSRF-Token": csrf})
    # kaltura and zoom were on in the fixture and were not mentioned.
    assert resp.get_json()["features"] == {"kaltura": True, "canvas": True, "zoom": True}


def test_legacy_canvas_expiry_reports_unknown_rather_than_expired(client, admin):
    """Rows written before the value became an absolute timestamp hold the
    expires_in duration; comparing 3600 to the clock called every one expired."""
    from src.models import CanvasAuthorizedUsers

    db.session.add(CanvasAuthorizedUsers(
        primary_email="e", user_id=1, full_name="Legacy Row",
        canvas_access_token="a", canvas_refresh_token="r",
        canvas_token_expiry=3600,
    ))
    db.session.add(CanvasAuthorizedUsers(
        primary_email="e", user_id=2, full_name="Current Row",
        canvas_access_token="a", canvas_refresh_token="r",
        canvas_token_expiry=int(time.time()) + 3600,
    ))
    db.session.commit()
    _login(client)

    users = {u["fullName"]: u["expired"] for u in
             client.get("/adminapi/canvas/config").get_json()["authorizedUsers"]}
    assert users["Legacy Row"] is None
    assert users["Current Row"] is False


def test_logs_path_refuses_unauthenticated_callers(client, admin):
    """It used to answer with 200 and the SPA shell."""
    resp = client.get("/logs/log")
    assert resp.status_code == 401
    assert resp.is_json


def test_canvas_refresh_token_requires_csrf(client, admin):
    _login(client)
    assert client.post("/canvas/refreshtoken", data={"user_id": "1"}).status_code == 403


def test_remember_cookie_is_hardened(app_ctx):
    assert app_ctx.config["REMEMBER_COOKIE_HTTPONLY"] is True
    assert app_ctx.config["REMEMBER_COOKIE_SAMESITE"] == "Lax"
    assert app_ctx.config["REMEMBER_COOKIE_SECURE"] == app_ctx.config["SESSION_COOKIE_SECURE"]
    # Flask-Login's default is 365 days.
    assert app_ctx.config["REMEMBER_COOKIE_DURATION"].days <= 30
