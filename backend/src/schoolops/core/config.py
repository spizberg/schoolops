"""Typed application settings loaded from the environment."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_DEV_JWT_SECRET = "dev-only-change-me-please-use-32-chars"  # noqa: S105


class Settings(BaseSettings):
    """Runtime configuration.

    Values come from environment variables or a local ``.env`` file. Field names are
    case-insensitive, so ``DATABASE_URL`` populates ``database_url``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Children's Bible Study Group API"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/v1"

    database_url: str = "postgresql+asyncpg://schoolops:schoolops@localhost:5433/schoolops"
    cors_origins: list[str] = ["http://localhost:4200"]

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Auth (enabled in a later slice; present so configuration is stable).
    jwt_secret: str = DEFAULT_DEV_JWT_SECRET
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_ttl_minutes: int = Field(default=480, ge=5, le=1440)
    max_request_body_bytes: int = Field(default=1_048_576, gt=0)

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """Fail closed when staging/production keeps development defaults."""
        if self.environment in {"staging", "production"}:
            if self.jwt_secret == DEFAULT_DEV_JWT_SECRET or len(self.jwt_secret) < 32:
                raise ValueError(
                    "JWT_SECRET must be replaced with at least 32 characters outside local/test."
                )
            if self.debug:
                raise ValueError("DEBUG must be disabled outside local/test.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
