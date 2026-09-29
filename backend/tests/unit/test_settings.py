import pytest
from pydantic import ValidationError

from vbe_hub.infrastructure.settings import Settings


def test_settings_reject_missing_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None)


def test_settings_reject_non_positive_dependency_timeout() -> None:
    with pytest.raises(ValidationError, match="DEPENDENCY_TIMEOUT_SECONDS"):
        Settings(
            DATABASE_URL="postgresql://user:password@postgres:5432/vbehub",
            REDIS_URL="redis://redis:6379/0",
            DEPENDENCY_TIMEOUT_SECONDS=0,
            _env_file=None,
        )


def test_settings_selects_asyncpg_for_sqlalchemy() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:password@postgres:5432/vbehub",
        REDIS_URL="redis://redis:6379/0",
        _env_file=None,
    )

    assert settings.sqlalchemy_database_url == (
        "postgresql+asyncpg://user:password@postgres:5432/vbehub"
    )


def test_gemini_is_optional_with_bounded_defaults() -> None:
    settings = Settings(
        DATABASE_URL="postgresql://user:password@postgres:5432/vbehub",
        REDIS_URL="redis://redis:6379/0",
        _env_file=None,
    )

    assert settings.gemini_api_key is None
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    assert settings.gemini_timeout_seconds == 15
    assert settings.gemini_max_attempts == 3
    assert settings.gemini_max_input_chars == 12_000
    assert settings.gemini_max_output_tokens == 2_048


def test_gemini_limits_reject_unbounded_configuration() -> None:
    with pytest.raises(ValidationError, match="GEMINI_MAX_ATTEMPTS"):
        Settings(
            DATABASE_URL="postgresql://user:password@postgres:5432/vbehub",
            REDIS_URL="redis://redis:6379/0",
            GEMINI_MAX_ATTEMPTS=10,
            _env_file=None,
        )
