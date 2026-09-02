"""Shared test setup.

config.py reads its secrets and database URI at import time, so both have to be
set in the environment before anything under test is imported. DATABASE_URL in
particular: Flask-SQLAlchemy binds an engine at init, so reassigning
app.config afterwards would leave create_all()/drop_all() aimed at the
developer's real database/epib.db.

A temp file rather than sqlite:///:memory: -- an in-memory database is scoped to
its connection, so the schema would vanish as soon as an app context closed.
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

_TMP_DB = pathlib.Path(tempfile.mkdtemp(prefix="vpib-tests-")) / "test.db"

os.environ.setdefault("FLASK_SECRET_KEY", "test-flask-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("DEBUG", "False")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"

import pytest  # noqa: E402

from config import app as flask_app, db  # noqa: E402

# Importing the models is what populates db.metadata; without it create_all()
# silently creates nothing.
import src.models  # noqa: E402,F401

# app.py queries VendorProxies at import time to decide which vendor API specs to
# mount, so the schema has to exist before it is imported. Importing it is also
# what registers the blueprints the API tests exercise.
with flask_app.app_context():
    db.create_all()

import app as app_module  # noqa: E402,F401


@pytest.fixture
def app_ctx():
    """An app context over a database reset between tests."""
    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        yield flask_app
        db.session.remove()


@pytest.fixture
def client(app_ctx):
    """Flask test client sharing the app_ctx database."""
    app_ctx.config["TESTING"] = True
    with app_ctx.test_client() as c:
        yield c
