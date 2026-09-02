from urllib.parse import parse_qs

import pytest

import src.kaltura_handlers as kh
from src.models import AccessRestrictions, db


@pytest.fixture
def restrictions(app_ctx):
    def _set(allowed_categories):
        db.session.query(AccessRestrictions).delete()
        db.session.add(AccessRestrictions(
            id=1, allowed_categories=allowed_categories, force_labels=False
        ))
        db.session.commit()
    return _set


def test_category_allowlist(restrictions):
    restrictions("594123,634123")
    assert kh.category_allowed("594123") is True
    assert kh.category_allowed(634123) is True
    assert kh.category_allowed("999999") is False


def test_empty_allowlist_permits_everything(restrictions):
    restrictions("")
    assert kh.category_allowed("999999") is True
    assert kh._allowlist_is_open() is True


def test_non_numeric_category_is_denied_not_raised(restrictions):
    restrictions("594123")
    # this used to raise ValueError out of the request handler
    assert kh.category_allowed("594123; drop") is False
    assert kh.category_allowed(None) is False
    assert kh.category_allowed("") is False


def test_full_category_name_lookup_cannot_bypass_the_allowlist(restrictions, monkeypatch):
    """The allowlist holds numeric IDs, so a full-name lookup is unverifiable.

    Previously category_allowed(category_id) was checked and then the request was
    built from full_cat_id, so an allowed ID plus any full name read anything.
    """
    restrictions("594123")
    monkeypatch.setattr(kh, "_post", lambda *a, **k: pytest.fail("request should not be sent"))

    result = kh.get_entries_by_category(category_id="594123", full_cat_id="Private>Everything")
    assert result == {"objects": []}


def test_full_category_name_lookup_allowed_when_no_allowlist(restrictions, monkeypatch):
    restrictions("")
    sent = {}

    class _Resp:
        text = '{"objects": []}'

    def _fake_post(path, params):
        sent["path"], sent["params"] = path, params
        return _Resp()

    monkeypatch.setattr(kh, "_post", _fake_post)
    monkeypatch.setattr(kh, "resolve_session", lambda label, ks, log_info: "KS")

    kh.get_entries_by_category(full_cat_id="Public>Lectures")
    assert sent["params"]["filter[categoriesFullNameIn]"] == "Public>Lectures"


def test_missing_category_arguments_return_empty(restrictions):
    restrictions("")
    # both empty used to leave `data` unbound and raise UnboundLocalError
    assert kh.get_entries_by_category() == {"objects": []}


def test_parameters_are_url_encoded(monkeypatch):
    """A value containing '&' must not become an extra Kaltura parameter."""
    captured = {}

    def _fake_requests_post(url, headers=None, data=None, timeout=None):
        captured["data"] = data
        class _R:
            text = "{}"
        return _R()

    monkeypatch.setattr(kh.requests, "post", _fake_requests_post)

    kh._post("/category/action/get", {
        "ks": "KS", "format": 1, "id": "1&filter[objectType]=KalturaInjected",
    })

    parsed = parse_qs(captured["data"])
    assert parsed["id"] == ["1&filter[objectType]=KalturaInjected"]
    assert "filter[objectType]" not in parsed
