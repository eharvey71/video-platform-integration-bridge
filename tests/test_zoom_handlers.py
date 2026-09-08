import pytest

from src.zoom_handlers import validate_zoom_url, validate_access_key
from src.models import ZoomClientConfig, db


@pytest.mark.parametrize("url", [
    "https://zoom.us/rec/download/abc",
    "https://us02web.zoom.us/rec/download/abc",
    "https://company.us02web.zoom.us/rec/download/abc",
])
def test_validate_zoom_url_accepts_zoom_hosts(url):
    assert validate_zoom_url(url) is True


@pytest.mark.parametrize("url", [
    # The old regex left the dot in "zoom.us" unescaped, so this host was accepted
    # and get_recording_transcript_by_url would send a Zoom bearer token to it.
    "https://zoomxus/rec/download/abc",
    "https://zoom.us.evil.com/rec/download/abc",
    "https://evil.com/https://zoom.us/rec",
    "https://notzoom.us.attacker.net/",
    "http://zoom.us/rec/download/abc",
    "ftp://zoom.us/rec",
    "",
    "not a url",
])
def test_validate_zoom_url_rejects_non_zoom_hosts(url):
    assert validate_zoom_url(url) is False


def test_access_key_not_required_when_toggle_is_off(app_ctx):
    db.session.add(ZoomClientConfig(
        id=1, zoom_client_id="i", zoom_client_secret="s", zoom_account_id="a",
        access_key="correct-key", require_access_key=False,
    ))
    db.session.commit()
    assert validate_access_key("correct-key") is None


def test_access_key_accepts_only_the_configured_key(app_ctx):
    db.session.add(ZoomClientConfig(
        id=1, zoom_client_id="i", zoom_client_secret="s", zoom_account_id="a",
        access_key="correct-key", require_access_key=True,
    ))
    db.session.commit()

    assert validate_access_key("correct-key") == {"sub": "zoom_api_user"}
    assert validate_access_key("wrong-key") is None
    assert validate_access_key("") is None
    assert validate_access_key(None) is None
    # a prefix must not pass -- compare_digest is length-aware
    assert validate_access_key("correct") is None
