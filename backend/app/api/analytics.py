"""Analytics API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_dispatcher
from app.models.driver import Driver
from app.models.order import Order
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.driver_repository import DriverRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.analytics import FleetAnalyticsResponse
from app.services.analytics_service import AnalyticsService


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


def get_analytics_service() -> AnalyticsService:
    """Create an analytics service instance."""
    return AnalyticsService()


def get_driver_repository(db: Session = Depends(get_db)) -> DriverRepository:
    """Create a driver repository instance."""
    return DriverRepository(db)


def get_vehicle_repository(db: Session = Depends(get_db)) -> VehicleRepository:
    """Create a vehicle repository instance."""
    return VehicleRepository(db)


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
    """Create an order repository instance."""
    return OrderRepository(db)


def _is_dispatcher_or_admin(user: User) -> bool:
    """Return whether the authenticated user can access analytics."""
    role = getattr(user, "role", None)
    if role is None:
        return False

    role_value = getattr(role, "value", role)
    return isinstance(role_value, str) and role_value.lower() in {
        "dispatcher",
        "admin",
    }


@router.get("/dashboard", response_model=FleetAnalyticsResponse)
def get_dashboard(
    current_dispatcher: User = Depends(get_current_dispatcher),
    analytics_service: AnalyticsService = Depends(get_analytics_service),
    driver_repository: DriverRepository = Depends(get_driver_repository),
    vehicle_repository: VehicleRepository = Depends(get_vehicle_repository),
    order_repository: OrderRepository = Depends(get_order_repository),
) -> FleetAnalyticsResponse:
    """Return fleet dashboard analytics metrics."""
    if not _is_dispatcher_or_admin(current_dispatcher):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only dispatcher or admin users can access analytics.",
        )

    drivers: list[Driver] = driver_repository.get_all(skip=0, limit=10_000)
    vehicles: list[Vehicle] = vehicle_repository.get_all(skip=0, limit=10_000)
    orders: list[Order] = order_repository.get_all(skip=0, limit=10_000)

    return analytics_service.get_dashboard_metrics(
        drivers=drivers,
        vehicles=vehicles,
        orders=orders,
    )
