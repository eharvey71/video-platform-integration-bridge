from flask import abort, make_response
from sqlalchemy.exc import IntegrityError

from config import db
from src.models import KalturaAppToken, kapptoken_schema, kapptokens_schema

# Columns a caller may change through the API. kaltura_token_id is the primary
# key and identifies the row, so it is matched on rather than assigned.
UPDATABLE_FIELDS = (
    "token",
    "partner_id",
    "created_at",
    "updated_at",
    "status",
    "session_type",
    "expiry",
    "session_duration",
    "session_user_id",
    "session_privileges",
    "description",
    "label",
)

# Kaltura returns its own camelCase field names. A payload copied straight from a
# Kaltura response is accepted by translating those to our column names.
KALTURA_FIELD_MAP = {
    "id": "kaltura_token_id",
    "token": "token",
    "partnerId": "partner_id",
    "createdAt": "created_at",
    "updatedAt": "updated_at",
    "status": "status",
    "sessionType": "session_type",
    "expiry": "expiry",
    "sessionDuration": "session_duration",
    "sessionUserId": "session_user_id",
    "sessionPrivileges": "session_privileges",
    "description": "description",
}


def read_all():
    tokens = KalturaAppToken.query.all()
    return kapptokens_schema.dump(tokens)


def read_one(kaltura_token_id):
    token = db.session.get(KalturaAppToken, kaltura_token_id)

    if token is not None:
        return kapptoken_schema.dump(token)
    else:
        abort(
            404, f"Token with ID {kaltura_token_id} not found"
        )


def add_existing(payload):
    kaltura_token_id = (payload.get("kaltura_token_id") or "").strip()
    token = (payload.get("token") or "").strip()

    if not kaltura_token_id or not token:
        abort(400, "kaltura_token_id and token are required")

    if db.session.get(KalturaAppToken, kaltura_token_id) is not None:
        abort(409, f"Token with ID {kaltura_token_id} already exists")

    # Defaults for a token whose details have not been pulled from Kaltura;
    # anything the caller supplied wins.
    values = {"expiry": 0, "session_duration": 86400}
    values.update({f: payload[f] for f in UPDATABLE_FIELDS if f in payload})
    values["token"] = token

    new_token = KalturaAppToken(kaltura_token_id=kaltura_token_id, **values)
    db.session.add(new_token)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "That label is already in use by another token")

    return kapptoken_schema.dump(new_token), 201


def _normalize(payload):
    """Accept either our column names or a payload lifted from a Kaltura response."""
    if "id" not in payload:
        return payload

    return {
        column: payload[kaltura_field]
        for kaltura_field, column in KALTURA_FIELD_MAP.items()
        if kaltura_field in payload
    }


def update_existing(payload):
    payload = _normalize(payload)

    kaltura_token_id = payload.get("kaltura_token_id")
    if not kaltura_token_id:
        abort(400, "kaltura_token_id is required")

    existing_token = db.session.get(KalturaAppToken, kaltura_token_id)
    if existing_token is None:
        abort(404, f"Token with ID {kaltura_token_id} not found")

    # Assign onto the loaded row. The previous implementation deserialized the
    # payload into a throwaway object and discarded it, so the commit that
    # followed had nothing to write and the endpoint silently changed nothing.
    for field in UPDATABLE_FIELDS:
        if field in payload:
            setattr(existing_token, field, payload[field])

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(409, "That label is already in use by another token")

    return kapptoken_schema.dump(existing_token), 200


def delete(kaltura_token_id):
    existing_token = db.session.get(KalturaAppToken, kaltura_token_id)

    if existing_token:
        db.session.delete(existing_token)
        db.session.commit()
        return make_response(f"Token with ID {kaltura_token_id} successfully deleted", 200)
    else:
        abort(404, f"Token with ID {kaltura_token_id} not found")
