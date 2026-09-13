"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the FinSight API.

    Values are read from environment variables (and an optional `.env` file).
    Add new fields here as the platform grows (database URL, auth secrets, etc.).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "FinSight"
    app_env: str = "development"
    debug: bool = True

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Comma-separated list in env, e.g. "http://localhost:3000,http://127.0.0.1:3000"
    cors_origins: str = "http://localhost:3000"

    # SQLAlchemy / PostgreSQL connection string (psycopg v3 driver)
    database_url: str = "postgresql+psycopg://gigiguan@localhost:5432/finsight"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (safe to call from dependencies)."""
    return Settings()
