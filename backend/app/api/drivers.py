"""Driver API routes."""

from uuid import UUID

from app.dependencies.auth import get_current_admin, get_current_dispatcher
from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.driver_repository import DriverRepository
from app.schemas.driver import DriverCreate, DriverResponse, DriverUpdate
from app.services.driver_service import DriverService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/drivers", tags=["Drivers"])


def get_driver_service(db: Session = Depends(get_db)) -> DriverService:
    """Build the driver service for the active database session."""

    return DriverService(DriverRepository(db))


@router.get("/", response_model=list[DriverResponse])
def list_drivers(
    skip: int = 0,
    limit: int = 100,
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[DriverResponse]:
    """Return all drivers."""

    return driver_service.list_drivers(skip=skip, limit=limit)


@router.get("/available", response_model=list[DriverResponse])
def list_available_drivers(
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[DriverResponse]:
    """Return all available drivers."""

    return driver_service.list_available_drivers()


@router.get("/{driver_id}", response_model=DriverResponse)
def get_driver(
    driver_id: UUID,
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> DriverResponse:
    """Return one driver by identifier."""

    return driver_service.get_driver(driver_id)


@router.post(
    "/",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_driver(
    payload: DriverCreate,
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_admin),
) -> DriverResponse:
    """Create a new driver profile."""

    return driver_service.create_driver(payload)


@router.put("/{driver_id}", response_model=DriverResponse)
def update_driver(
    driver_id: UUID,
    payload: DriverUpdate,
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_admin),
) -> DriverResponse:
    """Update an existing driver profile."""

    return driver_service.update_driver(driver_id, payload)


@router.delete(
    "/{driver_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_driver(
    driver_id: UUID,
    driver_service: DriverService = Depends(get_driver_service),
    _current_user: User = Depends(get_current_admin),
) -> Response:
    """Delete a driver by identifier."""

    driver_service.delete_driver(driver_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
