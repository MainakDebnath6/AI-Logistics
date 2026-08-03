"""Application settings loaded from environment variables via Pydantic Settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the FastAPI application."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_logistics")
    secret_key: str = Field(default="change-me")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for application-wide reuse."""

    return Settings()
