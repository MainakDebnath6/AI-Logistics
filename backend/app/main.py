"""FastAPI application entrypoint for the logistics backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle hook reserved for startup and shutdown wiring."""

    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    app = FastAPI(
        title="AI Logistics Route Optimizer",
        description="Backend bootstrap for an AI-powered smart logistics route optimizer.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/")
    async def health_check() -> dict[str, str]:
        """Return a simple health response for service checks."""

        return {"status": "running", "project": "AI Logistics Route Optimizer"}

    return app


app = create_app()
