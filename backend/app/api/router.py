"""Top-level API router aggregation point."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.drivers import router as drivers_router
from app.api.users import router as users_router
from app.api.vehicles import router as vehicles_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(drivers_router)
api_router.include_router(vehicles_router)
