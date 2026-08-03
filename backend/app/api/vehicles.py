"""Vehicle API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin, get_current_dispatcher
from app.dependencies.database import get_db
from app.models.user import User
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.vehicle_service import VehicleService


router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


def get_vehicle_service(db: Session = Depends(get_db)) -> VehicleService:
    """Build the vehicle service for the active database session."""

    return VehicleService(VehicleRepository(db))


@router.get("/", response_model=list[VehicleResponse])
def list_vehicles(
    skip: int = 0,
    limit: int = 100,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[VehicleResponse]:
    """Return all vehicles."""

    return vehicle_service.list_vehicles(skip=skip, limit=limit)


@router.get("/available", response_model=list[VehicleResponse])
def list_available_vehicles(
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[VehicleResponse]:
    """Return all available vehicles."""

    return vehicle_service.list_available_vehicles()


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(
    vehicle_id: UUID,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> VehicleResponse:
    """Return one vehicle by identifier."""

    return vehicle_service.get_vehicle(vehicle_id)


@router.post(
    "/",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    payload: VehicleCreate,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_admin),
) -> VehicleResponse:
    """Create a new vehicle."""

    return vehicle_service.create_vehicle(payload)


@router.put("/{vehicle_id}", response_model=VehicleResponse)
def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_admin),
) -> VehicleResponse:
    """Update an existing vehicle."""

    return vehicle_service.update_vehicle(vehicle_id, payload)


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vehicle(
    vehicle_id: UUID,
    vehicle_service: VehicleService = Depends(get_vehicle_service),
    _current_user: User = Depends(get_current_admin),
) -> Response:
    """Delete a vehicle by identifier."""

    vehicle_service.delete_vehicle(vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)