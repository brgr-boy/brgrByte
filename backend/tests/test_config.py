from app.config import Settings


def set_config_values(monkeypatch, prefix):
    values = {
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JWT_SECRET_KEY": "test-signing-key-that-is-at-least-32-characters",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "test-password-long-enough",
        "CORS_ORIGINS": "http://localhost:8080",
    }
    for key, value in values.items():
        monkeypatch.setenv(f"{prefix}_{key}", value)


def clear_config_values(monkeypatch):
    for prefix in ("BRGRBYTE", "NETWORKPATH"):
        for key in (
            "DATABASE_URL",
            "JWT_SECRET_KEY",
            "ADMIN_USERNAME",
            "ADMIN_PASSWORD",
            "CORS_ORIGINS",
        ):
            monkeypatch.delenv(f"{prefix}_{key}", raising=False)


def test_settings_accept_current_environment_names(monkeypatch):
    clear_config_values(monkeypatch)
    set_config_values(monkeypatch, "BRGRBYTE")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert (
        settings.jwt_secret_key.get_secret_value()
        == "test-signing-key-that-is-at-least-32-characters"
    )
    assert settings.cors_origins == "http://localhost:8080"


def test_settings_accept_previous_environment_names(monkeypatch):
    clear_config_values(monkeypatch)
    set_config_values(monkeypatch, "NETWORKPATH")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert settings.admin_username == "admin"


def test_current_environment_names_take_precedence(monkeypatch):
    clear_config_values(monkeypatch)
    set_config_values(monkeypatch, "NETWORKPATH")
    set_config_values(monkeypatch, "BRGRBYTE")
    monkeypatch.setenv("BRGRBYTE_ADMIN_USERNAME", "current-admin")

    assert Settings(_env_file=None).admin_username == "current-admin"
