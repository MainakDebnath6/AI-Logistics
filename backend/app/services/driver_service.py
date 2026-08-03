"""Business logic for driver operations."""

from uuid import UUID

from app.models.driver import Driver
from app.repositories.driver_repository import DriverRepository
from app.schemas.driver import DriverCreate, DriverUpdate
from fastapi import HTTPException, status

DRIVER_NOT_FOUND = "Driver not found."
INVALID_CAPACITY = "max_capacity must be greater than 0."
DUPLICATE_DRIVER = "A driver profile already exists for this user."
DUPLICATE_LICENSE = "License number already exists."


class DriverService:
    """Coordinate driver persistence and business rules."""

    def __init__(self, repository: DriverRepository) -> None:
        """Initialize the service with a driver repository."""

        self.repository = repository

    def create_driver(self, driver_data: DriverCreate) -> Driver:
        """Create a new driver profile."""

        if driver_data.max_capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_CAPACITY,
            )

        existing_driver = self.repository.get_by_user_id(driver_data.user_id)
        if existing_driver is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=DUPLICATE_DRIVER,
            )

        existing_license = self.repository.get_by_license_number(
            driver_data.license_number
        )
        if existing_license is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=DUPLICATE_LICENSE,
            )

        driver = Driver(
            user_id=driver_data.user_id,
            license_number=driver_data.license_number,
            phone=driver_data.phone,
            vehicle_id=driver_data.vehicle_id,
            max_capacity=driver_data.max_capacity,
        )

        return self.repository.create(driver)

    def get_driver(self, driver_id: UUID) -> Driver:
        """Return a driver by identifier."""

        driver = self.repository.get_by_id(driver_id)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=DRIVER_NOT_FOUND,
            )

        return driver

    def get_driver_by_user(self, user_id: UUID) -> Driver:
        """Return a driver by linked user identifier."""

        driver = self.repository.get_by_user_id(user_id)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=DRIVER_NOT_FOUND,
            )

        return driver

    def list_drivers(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Driver]:
        """Return drivers with pagination."""

        return self.repository.get_all(skip=skip, limit=limit)

    def list_available_drivers(self) -> list[Driver]:
        """Return drivers available for assignment."""

        return self.repository.get_available_drivers()

    def update_driver(
        self,
        driver_id: UUID,
        driver_data: DriverUpdate,
    ) -> Driver:
        """Update the mutable fields for a driver."""

        if driver_data.max_capacity is not None and driver_data.max_capacity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_CAPACITY,
            )

        driver = self.repository.get_by_id(driver_id)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=DRIVER_NOT_FOUND,
            )

        if (
            driver_data.license_number is not None
            and driver_data.license_number != driver.license_number
        ):
            existing = self.repository.get_by_license_number(driver_data.license_number)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=DUPLICATE_LICENSE,
                )

        data = driver_data.model_dump(exclude_unset=True)
        return self.repository.update(driver, data)

    def delete_driver(self, driver_id: UUID) -> None:
        """Delete a driver by identifier."""

        driver = self.repository.get_by_id(driver_id)
        if driver is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=DRIVER_NOT_FOUND,
            )

        self.repository.delete(driver)
