"""Application settings loaded from environment variables via Pydantic Settings."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_FRONTEND_ORIGIN = "https://ai-logistics-umber.vercel.app"
PROJECT_PREVIEW_ORIGIN_REGEX = (
    r"^https://ai-logistics-[a-z0-9-]+-mainak-d\.vercel\.app$"
)


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
    environment: str = Field(default="development")
    secret_key: str = Field(default="change-me")
    backend_cors_origins: str = Field(
        default="http://localhost:4173,http://localhost:5173,http://127.0.0.1:4173,http://127.0.0.1:5173"
    )
    backend_cors_origin_regex: str | None = Field(default=PROJECT_PREVIEW_ORIGIN_REGEX)
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    hgfc_max_horizon_days: int = Field(default=14, ge=1)

    DEFAULT_OPTIMIZATION_TIMEOUT_SECONDS: int = Field(default=5)
    DEFAULT_LOCAL_SEARCH: str = Field(default="GUIDED_LOCAL_SEARCH")
    DEFAULT_LOCAL_SEARCH_METAHEURISTIC: str = Field(default="GUIDED_LOCAL_SEARCH")
    DEFAULT_FIRST_SOLUTION_STRATEGY: str = Field(default="PATH_CHEAPEST_ARC")
    DEFAULT_DEPOT_LATITUDE: float | None = Field(default=None, ge=-90.0, le=90.0)
    DEFAULT_DEPOT_LONGITUDE: float | None = Field(default=None, ge=-180.0, le=180.0)
    OSRM_BASE_URL: str = Field(default="https://router.project-osrm.org")
    OSRM_TIMEOUT_SECONDS: float = Field(default=4.0, gt=0.0, le=30.0)

    optimization_timeout_seconds: int = Field(default=5)
    optimization_default_depot_latitude: float = Field(default=0.0)
    optimization_default_depot_longitude: float = Field(default=0.0)
    optimization_default_strategy: str = Field(default="GUIDED_LOCAL_SEARCH")

    analytics_default_average_eta: float = Field(default=0.0)
    analytics_default_total_distance: float = Field(default=0.0)
    analytics_default_route_efficiency: float = Field(default=0.0)
    analytics_default_on_time_delivery_percentage: float = Field(default=0.0)

    @property
    def cors_origins(self) -> list[str]:
        """Return configured CORS origins as a normalized list."""
        origins = [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]
        if PRODUCTION_FRONTEND_ORIGIN not in origins:
            origins.append(PRODUCTION_FRONTEND_ORIGIN)
        return origins

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Fail closed for insecure production secrets and credentialed wildcard CORS."""
        if self.environment.strip().lower() == "production":
            if self.secret_key.strip().lower() in {
                "",
                "change-me",
                "change-me-with-a-long-random-secret",
            }:
                raise ValueError("SECRET_KEY must be explicitly configured in production.")
            if "*" in self.cors_origins:
                raise ValueError("Credentialed CORS cannot use a wildcard origin in production.")
            if self.backend_cors_origin_regex != PROJECT_PREVIEW_ORIGIN_REGEX:
                raise ValueError(
                    "Credentialed CORS preview regex must match only this project's Vercel previews."
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object for application-wide reuse."""

    return Settings()
