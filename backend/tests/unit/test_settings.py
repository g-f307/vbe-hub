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
