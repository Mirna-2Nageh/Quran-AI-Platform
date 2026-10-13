from app.config import Settings


def test_settings_read_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("QURAN_AI_APP_NAME", "Test API")
    monkeypatch.setenv("QURAN_AI_DEBUG", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test API"
    assert settings.debug is True
