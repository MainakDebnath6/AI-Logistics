"""Database access helpers for order persistence."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order, OrderStatus


class OrderRepository:
    """Encapsulate SQLAlchemy operations for order records."""

    def __init__(self, db: Session) -> None:
        """Initialize the repository with a database session."""

        self.db = db

    def create(self, order: Order) -> Order:
        """Persist a new order and return the stored object."""

        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_by_id(self, order_id: UUID) -> Order | None:
        """Return an order by primary key if it exists."""

        statement = select(Order).where(Order.id == order_id)
        return self.db.scalar(statement)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Order]:
        """Return orders ordered by newest first with pagination."""

        statement = (
            select(Order)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        """Return orders matching the given status."""

        statement = (
            select(Order)
            .where(Order.status == status)
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_driver(self, driver_id: UUID) -> list[Order]:
        """Return orders assigned to the given driver."""

        statement = (
            select(Order)
            .where(Order.assigned_driver_id == driver_id)
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_by_vehicle(self, vehicle_id: UUID) -> list[Order]:
        """Return orders assigned to the given vehicle."""

        statement = (
            select(Order)
            .where(Order.assigned_vehicle_id == vehicle_id)
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def get_unassigned_orders(self) -> list[Order]:
        """Return orders that are not assigned to a driver or vehicle."""

        statement = (
            select(Order)
            .where(
                Order.assigned_driver_id.is_(None),
                Order.assigned_vehicle_id.is_(None),
            )
            .order_by(Order.created_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def update(
        self,
        order: Order,
        data: dict[str, Any],
    ) -> Order:
        """Update existing order attributes and return the stored object."""

        for key, value in data.items():
            if hasattr(order, key):
                setattr(order, key, value)

        self.db.commit()
        self.db.refresh(order)
        return order

    def delete(self, order: Order) -> None:
        """Delete an order from the database."""

        self.db.delete(order)
        self.db.commit()