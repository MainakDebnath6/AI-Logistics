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

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ai_logistics"
    )
    secret_key: str = Field(default="change-me")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    DEFAULT_OPTIMIZATION_TIMEOUT_SECONDS: int = Field(default=5)
    DEFAULT_LOCAL_SEARCH: str = Field(default="GUIDED_LOCAL_SEARCH")
    DEFAULT_LOCAL_SEARCH_METAHEURISTIC: str = Field(default="GUIDED_LOCAL_SEARCH")
    DEFAULT_FIRST_SOLUTION_STRATEGY: str = Field(default="PATH_CHEAPEST_ARC")
    DEFAULT_DEPOT_LATITUDE: float = Field(default=0.0)
    DEFAULT_DEPOT_LONGITUDE: float = Field(default=0.0)

    optimization_timeout_seconds: int = Field(default=5)
    optimization_default_depot_latitude: float = Field(default=0.0)
    optimization_default_depot_longitude: float = Field(default=0.0)
    optimization_default_strategy: str = Field(default="GUIDED_LOCAL_SEARCH")

    analytics_default_average_eta: float = Field(default=0.0)
    analytics_default_total_distance: float = Field(default=0.0)
    analytics_default_route_efficiency: float = Field(default=0.0)
    analytics_default_on_time_delivery_percentage: float = Field(default=0.0)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for application-wide reuse."""

    return Settings()
