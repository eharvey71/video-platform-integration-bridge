"""Tests for the vendor-facing Kaltura app token handlers (src/tokens.py)."""
import pytest
from werkzeug.exceptions import HTTPException

import src.tokens as tokens
from src.models import KalturaAppToken, db


@pytest.fixture
def seeded(app_ctx):
    db.session.add(KalturaAppToken(
        kaltura_token_id="1_abc",
        token="original-secret",
        partner_id=111,
        session_privileges="privacycontext:one",
        description="original description",
        expiry=1767157200,
        session_duration=86400,
        label="ANTH-201",
    ))
    db.session.commit()


def test_update_actually_persists(seeded):
    """The bug: the payload was loaded into a throwaway object and discarded,
    so the commit wrote nothing and the caller got back the unchanged token."""
    body, status = tokens.update_existing({
        "kaltura_token_id": "1_abc",
        "description": "updated description",
        "session_privileges": "privacycontext:two",
    })

    assert status == 200
    assert body["description"] == "updated description"

    db.session.expire_all()
    stored = db.session.get(KalturaAppToken, "1_abc")
    assert stored.description == "updated description"
    assert stored.session_privileges == "privacycontext:two"
    # Untouched fields survive a partial update.
    assert stored.token == "original-secret"
    assert stored.label == "ANTH-201"


def test_update_with_the_documented_body_does_not_raise(seeded):
    """The spec's own PUT body has no 'id' key. Reading payload['id'] made every
    documented request a KeyError before anything else ran."""
    _, status = tokens.update_existing({"kaltura_token_id": "1_abc", "token": "rotated"})
    assert status == 200
    db.session.expire_all()
    assert db.session.get(KalturaAppToken, "1_abc").token == "rotated"


def test_update_accepts_a_kaltura_shaped_payload(seeded):
    body, status = tokens.update_existing({
        "id": "1_abc",
        "token": "from-kaltura",
        "partnerId": 4526213,
        "sessionPrivileges": "enableentitlement",
        "objectType": "KalturaAppToken",
    })

    assert status == 200
    db.session.expire_all()
    stored = db.session.get(KalturaAppToken, "1_abc")
    assert stored.token == "from-kaltura"
    assert stored.partner_id == 4526213
    assert stored.session_privileges == "enableentitlement"


def test_partial_kaltura_payload_does_not_raise(seeded):
    """Every camelCase field used to be read unconditionally, so a response
    missing any one of them raised KeyError."""
    _, status = tokens.update_existing({"id": "1_abc", "token": "partial"})
    assert status == 200


def test_update_of_a_missing_token_is_404(app_ctx):
    with pytest.raises(HTTPException) as exc:
        tokens.update_existing({"kaltura_token_id": "1_nope", "token": "x"})
    assert exc.value.code == 404


def test_update_without_an_id_is_400(seeded):
    with pytest.raises(HTTPException) as exc:
        tokens.update_existing({"token": "x"})
    assert exc.value.code == 400


def test_update_to_a_taken_label_is_409_not_a_500(seeded):
    db.session.add(KalturaAppToken(
        kaltura_token_id="1_other", token="t", label="CIS-101",
        expiry=0, session_duration=86400,
    ))
    db.session.commit()

    with pytest.raises(HTTPException) as exc:
        tokens.update_existing({"kaltura_token_id": "1_abc", "label": "CIS-101"})
    assert exc.value.code == 409


def test_unknown_fields_are_ignored(seeded):
    """Only known columns are assigned, so stray keys cannot reach the model."""
    _, status = tokens.update_existing({
        "kaltura_token_id": "1_abc",
        "objectType": "KalturaAppToken",
        "hashType": "SHA256",
    })
    assert status == 200


def test_add_existing_creates_a_token(app_ctx):
    body, status = tokens.add_existing({"kaltura_token_id": "1_new", "token": "secret"})
    assert status == 201
    stored = db.session.get(KalturaAppToken, "1_new")
    assert stored.token == "secret"
    assert stored.session_duration == 86400
    assert body["kaltura_token_id"] == "1_new"


def test_add_existing_keeps_caller_supplied_values(app_ctx):
    tokens.add_existing({
        "kaltura_token_id": "1_new", "token": "secret",
        "expiry": 1767157200, "session_duration": 3600, "label": "NEW-101",
    })
    stored = db.session.get(KalturaAppToken, "1_new")
    # These were previously overwritten with hardcoded defaults.
    assert stored.expiry == 1767157200
    assert stored.session_duration == 3600
    assert stored.label == "NEW-101"


def test_add_existing_does_not_mutate_the_caller_payload(app_ctx):
    payload = {"kaltura_token_id": "1_new", "token": "secret"}
    tokens.add_existing(payload)
    assert payload == {"kaltura_token_id": "1_new", "token": "secret"}


def test_add_existing_rejects_a_duplicate_id(seeded):
    with pytest.raises(HTTPException) as exc:
        tokens.add_existing({"kaltura_token_id": "1_abc", "token": "other"})
    assert exc.value.code == 409


def test_add_existing_requires_both_fields(app_ctx):
    for payload in [{}, {"kaltura_token_id": "1_x"}, {"token": "t"}, {"kaltura_token_id": " ", "token": "t"}]:
        with pytest.raises(HTTPException) as exc:
            tokens.add_existing(payload)
        assert exc.value.code == 400


def test_read_one_and_delete(seeded):
    assert tokens.read_one("1_abc")["kaltura_token_id"] == "1_abc"
    assert tokens.delete("1_abc").status_code == 200
    assert db.session.get(KalturaAppToken, "1_abc") is None

    with pytest.raises(HTTPException) as exc:
        tokens.read_one("1_abc")
    assert exc.value.code == 404
