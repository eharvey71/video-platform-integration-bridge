"""Double-submit CSRF protection for the admin JSON API.

Same-origin plus SameSite=Lax already keeps the session cookie off cross-site
form posts. This is the second layer: a token minted into the session and echoed
back in a header the browser will not attach automatically.
"""
import secrets

from flask import session, request

CSRF_SESSION_KEY = "_csrf_token"
CSRF_HEADER = "X-CSRF-Token"
CSRF_COOKIE = "csrf_token"
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def get_csrf_token():
    """Return this session's CSRF token, minting one on first use."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token():
    """Issue a fresh token. Called on login and logout so a token minted before
    authentication cannot be replayed against the new session."""
    session[CSRF_SESSION_KEY] = secrets.token_urlsafe(32)
    return session[CSRF_SESSION_KEY]


def csrf_is_valid():
    if request.method in SAFE_METHODS:
        return True
    expected = session.get(CSRF_SESSION_KEY)
    provided = request.headers.get(CSRF_HEADER)
    if not expected or not provided:
        return False
    return secrets.compare_digest(expected, provided)


def attach_csrf_cookie(response):
    """Expose the token to the SPA.

    Readable by JavaScript on purpose -- that is the half of the double submit
    the page has to send back. It is not the session cookie and grants nothing
    on its own.
    """
    if CSRF_SESSION_KEY in session:
        response.set_cookie(
            CSRF_COOKIE,
            session[CSRF_SESSION_KEY],
            samesite="Lax",
            secure=request.is_secure,
            httponly=False,
        )
    return response
