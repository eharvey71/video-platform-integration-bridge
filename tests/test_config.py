import config


def test_env_flag_parses_strings_not_truthiness(monkeypatch):
    """DEBUG used to be the raw string, so "False" was truthy and debug stayed on."""
    for value in ("False", "false", "0", "no", "off", ""):
        monkeypatch.setenv("SOME_FLAG", value)
        assert config._env_flag("SOME_FLAG", default=True) is False

    for value in ("True", "true", "1", "yes", "on"):
        monkeypatch.setenv("SOME_FLAG", value)
        assert config._env_flag("SOME_FLAG", default=False) is True

    monkeypatch.delenv("SOME_FLAG", raising=False)
    assert config._env_flag("SOME_FLAG", default=True) is True


def test_session_cookie_is_hardened():
    assert config.app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert config.app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_cors_is_closed_by_default():
    # the origin list used to be a hardcoded localhost dev server
    assert config.CORS_ALLOWED_ORIGINS == []
