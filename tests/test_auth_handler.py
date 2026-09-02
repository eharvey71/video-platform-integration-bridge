import time

import pytest
from jose import jwt
from werkzeug.exceptions import Unauthorized

import src.auth_handler as ah


def test_round_trip():
    claims = ah.decode_token(ah.generate_token("alice"))
    assert claims["sub"] == "alice"
    assert claims["iss"] == ah.JWT_ISSUER


def test_token_from_another_issuer_is_rejected():
    """Same secret, different issuer -- must not be accepted here."""
    now = int(time.time())
    foreign = jwt.encode(
        {"iss": "com.example.other", "iat": now, "exp": now + 600, "sub": "alice"},
        ah.JWT_SECRET,
        algorithm=ah.JWT_ALGORITHM,
    )
    with pytest.raises(Unauthorized):
        ah.decode_token(foreign)


def test_token_signed_with_another_secret_is_rejected():
    now = int(time.time())
    forged = jwt.encode(
        {"iss": ah.JWT_ISSUER, "iat": now, "exp": now + 600, "sub": "alice"},
        "some-other-secret",
        algorithm=ah.JWT_ALGORITHM,
    )
    with pytest.raises(Unauthorized):
        ah.decode_token(forged)


def test_expired_token_is_rejected():
    now = int(time.time())
    stale = jwt.encode(
        {"iss": ah.JWT_ISSUER, "iat": now - 7200, "exp": now - 3600, "sub": "alice"},
        ah.JWT_SECRET,
        algorithm=ah.JWT_ALGORITHM,
    )
    with pytest.raises(Unauthorized):
        ah.decode_token(stale)


def test_credential_helper_that_returned_password_hashes_is_gone():
    # get_user_credentials fed /auth/get_auth_token, which handed the stored
    # password hash to the browser.
    assert not hasattr(ah, "get_user_credentials")
    assert not hasattr(ah, "get_secret")


def test_swag_auth_rejects_empty_credentials(app_ctx):
    assert ah.swag_auth("", "") is None
    assert ah.swag_auth(None, None) is None
