import pytest
from pydantic import ValidationError

from rag_system.config import Settings


def test_runtime_settings_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.log_level == "info"


def test_runtime_settings_support_plain_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("LOG_LEVEL", "debug")

    settings = Settings(_env_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.log_level == "debug"


def test_runtime_settings_support_rag_prefixed_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RAG_HOST", "0.0.0.0")
    monkeypatch.setenv("RAG_PORT", "7001")
    monkeypatch.setenv("RAG_LOG_LEVEL", "warning")

    settings = Settings(_env_file=None)

    assert settings.host == "0.0.0.0"
    assert settings.port == 7001
    assert settings.log_level == "warning"


def test_runtime_settings_reject_invalid_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "70000")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)