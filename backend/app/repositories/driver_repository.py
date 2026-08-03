"""Database access helpers for driver persistence."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driver import Driver, DriverStatus


class DriverRepository:
    """Encapsulate SQLAlchemy operations for driver records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with a database session."""

        self.db = db

    def create(self, driver: Driver) -> Driver:
        """Persist a new driver and return the stored object."""

        self.db.add(driver)
        self.db.commit()
        self.db.refresh(driver)
        return driver

    def get_by_id(self, driver_id: UUID) -> Driver | None:
        """Return a driver by primary key if it exists."""

        statement = select(Driver).where(Driver.id == driver_id)
        return self.db.scalar(statement)

    def get_by_user_id(self, user_id: UUID) -> Driver | None:
        """Return a driver by linked user identifier if it exists."""

        statement = select(Driver).where(Driver.user_id == user_id)
        return self.db.scalar(statement)

    def get_by_license_number(self, license_number: str) -> Driver | None:
        """Return a driver by license number if it exists."""

        statement = select(Driver).where(Driver.license_number == license_number)
        return self.db.scalar(statement)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Driver]:
        """Return drivers ordered by newest first with pagination."""

        statement = (
            select(Driver)
            .order_by(Driver.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_available_drivers(self) -> list[Driver]:
        """Return drivers currently available for assignment."""

        statement = (
            select(Driver)
            .where(
                Driver.status == DriverStatus.AVAILABLE,
                Driver.is_available.is_(True),
            )
            .order_by(Driver.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_status(self, status: DriverStatus) -> list[Driver]:
        """Return drivers matching the given status."""

        statement = (
            select(Driver)
            .where(Driver.status == status)
            .order_by(Driver.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        driver: Driver,
        data: dict[str, Any],
    ) -> Driver:
        """Update existing driver attributes and return the stored object."""

        for key, value in data.items():
            if hasattr(driver, key):
                setattr(driver, key, value)

        self.db.commit()
        self.db.refresh(driver)
        return driver

    def delete(self, driver: Driver) -> None:
        """Delete a driver from the database."""

        self.db.delete(driver)
        self.db.commit()