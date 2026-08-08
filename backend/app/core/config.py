"""Environment-backed application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = "postgresql+asyncpg://lending_v2:lending_v2@127.0.0.1:5432/lending_nelson_v2"


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or a local `.env` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Lending Nelson V2 API"
    api_v1_prefix: str = "/api/v1"
    database_url: PostgresDsn = PostgresDsn(LOCAL_DATABASE_URL)
    log_level: str = "INFO"

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("/") or normalized == "":
            raise ValueError("API_V1_PREFIX must be a non-root absolute path")
        return normalized

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
            raise ValueError("LOG_LEVEL must be a supported Python logging level")
        return normalized

    @model_validator(mode="after")
    def reject_local_database_in_deployed_environments(self) -> "Settings":
        if (
            self.app_env in {"staging", "production"}
            and str(self.database_url) == LOCAL_DATABASE_URL
        ):
            raise ValueError("DATABASE_URL must be explicitly configured outside local development")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings object per process."""

    return Settings()
