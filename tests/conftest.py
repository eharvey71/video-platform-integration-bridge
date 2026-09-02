"""Shared test setup.

config.py reads secrets at import time and refuses to start without them, so
these have to be in the environment before anything under test is imported.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.environ.setdefault("FLASK_SECRET_KEY", "test-flask-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("DEBUG", "False")

import pytest  # noqa: E402

from config import app as flask_app, db  # noqa: E402


@pytest.fixture
def app_ctx():
    """An app context backed by a throwaway in-memory database."""
    flask_app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite://"
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()
