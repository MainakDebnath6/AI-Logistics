"""Database access helpers for vehicle persistence."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle, VehicleStatus


class VehicleRepository:
    """Encapsulate SQLAlchemy operations for vehicle records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with a database session."""

        self.db = db

    def create(self, vehicle: Vehicle) -> Vehicle:
        """Persist a new vehicle and return the stored object."""

        self.db.add(vehicle)
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def get_by_id(self, vehicle_id: UUID) -> Vehicle | None:
        """Return a vehicle by primary key if it exists."""

        statement = select(Vehicle).where(Vehicle.id == vehicle_id)
        return self.db.scalar(statement)

    def get_by_registration_number(
        self,
        registration_number: str,
    ) -> Vehicle | None:
        """Return a vehicle by registration number if it exists."""

        statement = select(Vehicle).where(
            Vehicle.registration_number == registration_number
        )
        return self.db.scalar(statement)

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Vehicle]:
        """Return vehicles ordered by newest first with pagination."""

        statement = (
            select(Vehicle)
            .order_by(Vehicle.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_available_vehicles(self) -> list[Vehicle]:
        """Return active vehicles that are currently available."""

        statement = (
            select(Vehicle)
            .where(
                Vehicle.status == VehicleStatus.AVAILABLE,
                Vehicle.is_active.is_(True),
            )
            .order_by(Vehicle.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_status(
        self,
        status: VehicleStatus,
    ) -> list[Vehicle]:
        """Return vehicles matching the given status."""

        statement = (
            select(Vehicle)
            .where(Vehicle.status == status)
            .order_by(Vehicle.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        vehicle: Vehicle,
        data: dict[str, Any],
    ) -> Vehicle:
        """Update existing vehicle attributes and return the stored object."""

        for key, value in data.items():
            if hasattr(vehicle, key):
                setattr(vehicle, key, value)

        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle

    def delete(self, vehicle: Vehicle) -> None:
        """Delete a vehicle from the database."""

        self.db.delete(vehicle)
        self.db.commit()