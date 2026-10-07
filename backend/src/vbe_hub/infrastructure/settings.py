from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_environment: str = Field(default="development", validation_alias="APP_ENVIRONMENT")
    database_url: SecretStr = Field(validation_alias="DATABASE_URL")
    redis_url: SecretStr = Field(validation_alias="REDIS_URL")
    dependency_timeout_seconds: float = Field(
        default=2.0,
        gt=0,
        le=30,
        validation_alias="DEPENDENCY_TIMEOUT_SECONDS",
    )
    review_actor_id: str = Field(
        default="synthetic-analyst",
        validation_alias="REVIEW_ACTOR_ID",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._@:-]+$",
    )
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite", validation_alias="GEMINI_MODEL", min_length=1
    )
    gemini_embedding_model: str = Field(
        default="gemini-embedding-001", validation_alias="GEMINI_EMBEDDING_MODEL", min_length=1
    )
    gemini_timeout_seconds: float = Field(
        default=15, gt=0, le=60, validation_alias="GEMINI_TIMEOUT_SECONDS"
    )
    gemini_max_attempts: int = Field(
        default=3, ge=1, le=4, validation_alias="GEMINI_MAX_ATTEMPTS"
    )
    gemini_max_input_chars: int = Field(
        default=12_000, ge=1_000, le=50_000, validation_alias="GEMINI_MAX_INPUT_CHARS"
    )
    gemini_max_output_tokens: int = Field(
        default=2_048, ge=256, le=8_192, validation_alias="GEMINI_MAX_OUTPUT_TOKENS"
    )
    gemini_input_usd_per_million: float | None = Field(
        default=None, ge=0, validation_alias="GEMINI_INPUT_USD_PER_MILLION"
    )
    gemini_output_usd_per_million: float | None = Field(
        default=None, ge=0, validation_alias="GEMINI_OUTPUT_USD_PER_MILLION"
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        url = self.database_url.get_secret_value()
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
