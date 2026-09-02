from werkzeug.security import check_password_hash
from jose import JWTError, jwt
from werkzeug.exceptions import Unauthorized
import config, time, os, src.logger as logger
from src.models import User

JWT_ISSUER = "com.enwiseweb.edtechib"
JWT_SECRET = config._require_secret("JWT_SECRET")
JWT_LIFETIME_SECONDS = 600
JWT_ALGORITHM = "HS256"

def generate_token(user_id):
    timestamp = _current_timestamp()
    payload = {
        "iss": JWT_ISSUER,
        "iat": int(timestamp),
        "exp": int(timestamp + JWT_LIFETIME_SECONDS),
        "sub": str(user_id),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token):
    try:
        # issuer is verified so a token minted by an unrelated service that happens
        # to share our secret cannot be replayed here
        return jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM], issuer=JWT_ISSUER
        )
    except JWTError as e:
        raise Unauthorized from e

def _current_timestamp() -> int:
    return int(time.time())


def swag_auth(username, password):
    if not username or not password:
        return None
    with config.connex_app.app.app_context():
        user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        logger.log("Swagger UI Auth attempt failed for user: " + username)
    else:
        logger.log("Swagger UI Auth succeeded for user: " + username)
        return {"sub": username}
    # optional: raise exception for custom error response
    return None



####
# To Do:
####
# Implement API Key Auth in swagger/openapi as a second option
# for accessing internal APIs.
# Store hashed in DB and allow to be changed in the Integration Bridge UI.
####
