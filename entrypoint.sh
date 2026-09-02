#!/bin/sh
set -e

# Generate per-container secrets when none were supplied. Baking these into the
# image at build time would give every container the same session-signing key.
if [ -z "$FLASK_SECRET_KEY" ]; then
    FLASK_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    export FLASK_SECRET_KEY
    echo "entrypoint: generated an ephemeral FLASK_SECRET_KEY; sessions will not survive a restart" >&2
fi

if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    export JWT_SECRET
    echo "entrypoint: generated an ephemeral JWT_SECRET; issued tokens will not survive a restart" >&2
fi

exec "$@"
