"""Business logic for vehicle operations."""

from uuid import UUID

from app.models.vehicle import Vehicle
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from fastapi import HTTPException, status

VEHICLE_NOT_FOUND = "Vehicle not found."
DUPLICATE_REGISTRATION_NUMBER = "Registration number already exists."
INVALID_CAPACITY = "capacity must be greater than 0."
INVALID_FUEL_LEVEL = "fuel_level must be between 0 and 100."


class VehicleService:
    """Coordinate vehicle persistence and business rules."""

    def __init__(self, repository: VehicleRepository) -> None:
        """Initialize the service with a vehicle repository."""

        self.repository = repository

    def create_vehicle(self, vehicle_data: VehicleCreate) -> Vehicle:
        """Create a new vehicle record."""

        self._validate_capacity(vehicle_data.capacity)
        self._ensure_registration_number_is_unique(vehicle_data.registration_number)

        vehicle = Vehicle(
            registration_number=vehicle_data.registration_number,
            model=vehicle_data.model,
            manufacturer=vehicle_data.manufacturer,
            capacity=vehicle_data.capacity,
        )
        return self.repository.create(vehicle)

    def get_vehicle(self, vehicle_id: UUID) -> Vehicle:
        """Return a vehicle by identifier."""

        vehicle = self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=VEHICLE_NOT_FOUND,
            )

        return vehicle

    def list_vehicles(self, skip: int = 0, limit: int = 100) -> list[Vehicle]:
        """Return vehicles with pagination."""

        return self.repository.get_all(skip=skip, limit=limit)

    def list_available_vehicles(self) -> list[Vehicle]:
        """Return vehicles available for assignment."""

        return self.repository.get_available_vehicles()

    def update_vehicle(self, vehicle_id: UUID, vehicle_data: VehicleUpdate) -> Vehicle:
        """Update the mutable fields for a vehicle."""

        vehicle = self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=VEHICLE_NOT_FOUND,
            )

        data = vehicle_data.model_dump(exclude_unset=True)

        if "capacity" in data:
            self._validate_capacity(data["capacity"])

        if "fuel_level" in data:
            self._validate_fuel_level(data["fuel_level"])

        if (
            "registration_number" in data
            and data["registration_number"] != vehicle.registration_number
        ):
            self._ensure_registration_number_is_unique(data["registration_number"])

        return self.repository.update(vehicle, data)

    def delete_vehicle(self, vehicle_id: UUID) -> None:
        """Delete a vehicle by identifier."""

        vehicle = self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=VEHICLE_NOT_FOUND,
            )

        self.repository.delete(vehicle)

    def _ensure_registration_number_is_unique(self, registration_number: str) -> None:
        """Raise an error when a registration number already exists."""

        existing_vehicle = self.repository.get_by_registration_number(
            registration_number
        )
        if existing_vehicle is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=DUPLICATE_REGISTRATION_NUMBER,
            )

    def _validate_capacity(self, capacity: int) -> None:
        """Raise an error when capacity is invalid."""

        if capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_CAPACITY,
            )

    def _validate_fuel_level(self, fuel_level: float) -> None:
        """Raise an error when fuel level is outside the allowed range."""

        if fuel_level < 0 or fuel_level > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_FUEL_LEVEL,
            )
