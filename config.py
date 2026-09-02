import pathlib, os, secrets, warnings
from dotenv import load_dotenv
from datetime import timedelta
from connexion import FlaskApp #, json_schema
from connexion.options import SwaggerUIOptions
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_login import LoginManager

basedir = pathlib.Path(__file__).parent.resolve()

load_dotenv()
swagoptions = SwaggerUIOptions(
    swagger_ui=True, swagger_ui_template_dir=basedir / "swagger-ui"
)
connex_app = FlaskApp(__name__, specification_dir=basedir / "apispecs")



def _env_flag(name, default=False):
    """Read a boolean from the environment. Unset or unrecognized -> default."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


DEBUG = _env_flag("DEBUG", False)

# CORS origins are opt-in. Set CORS_ALLOWED_ORIGINS to a comma-separated list
# (e.g. "http://localhost:5173") to allow a front-end dev server to call the API.
# With no value set, no cross-origin requests are permitted.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if CORS_ALLOWED_ORIGINS:
    if "*" in CORS_ALLOWED_ORIGINS:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS may not be '*': credentialed requests require "
            "an explicit origin list."
        )
    connex_app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "api_key", "Authorization"],
        expose_headers=["Access-Control-Allow-Origin"]
    )

app = connex_app.app

app.config["DEBUG"] = DEBUG
# Overridable so tests (and non-SQLite deployments) do not have to reach into
# the module after the extension has already bound an engine to this URI.
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", f"sqlite:///{basedir / 'database/epib.db'}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


def _require_secret(env_var):
    """Return a secret from the environment.

    A missing secret is fatal outside debug: falling back to a constant would let
    anyone who has read the source forge session cookies. In debug we generate an
    ephemeral one so a fresh checkout still runs (sessions reset on restart).
    """
    value = os.getenv(env_var)
    if value:
        return value
    if not DEBUG:
        raise RuntimeError(
            f"{env_var} is not set. Generate one (e.g. `openssl rand -base64 32`) "
            f"and add it to your .env before starting the app."
        )
    warnings.warn(
        f"{env_var} is not set; using a random value for this process only. "
        f"Sessions and tokens will not survive a restart.",
        RuntimeWarning,
        stacklevel=2,
    )
    return secrets.token_urlsafe(32)


app.config["SECRET_KEY"] = _require_secret("FLASK_SECRET_KEY")
app.config["MESSAGE_FLASHING_OPTIONS"] = {"duration": 5}

# Session cookie hardening. SameSite=Lax keeps the session cookie off cross-site
# POSTs, which is what stands between the templated admin forms and CSRF until
# per-form tokens are added.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = _env_flag("SESSION_COOKIE_SECURE", not DEBUG)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
    minutes=int(os.getenv("SESSION_LIFETIME_MINUTES", "480"))
)
# OAuth2 configurations
app.config['GITHUB_CLIENT_ID'] = os.getenv('GITHUB_CLIENT_ID')
app.config['GITHUB_CLIENT_SECRET'] = os.getenv('GITHUB_CLIENT_SECRET')
app.config['OKTA_CLIENT_ID'] = os.getenv('OKTA_CLIENT_ID')
app.config['OKTA_CLIENT_SECRET'] = os.getenv('OKTA_CLIENT_SECRET')
app.config['OKTA_DOMAIN'] = os.getenv('OKTA_DOMAIN')


db = SQLAlchemy(app)
ma = Marshmallow(app)

login_manager = LoginManager()
login_manager.init_app(app)
