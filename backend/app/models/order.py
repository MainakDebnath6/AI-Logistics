"""Order ORM model and status enumeration."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.db.base import Base
from sqlalchemy import CheckConstraint, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.driver import Driver
    from app.models.vehicle import Vehicle


class OrderStatus(str, Enum):
    """Supported order states."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class Order(Base):
    """Persisted delivery order for dispatch operations."""

    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint(
            "demand > 0",
            name="ck_orders_demand_positive",
        ),
        CheckConstraint(
            "priority >= 1",
            name="ck_orders_priority_minimum",
        ),
        CheckConstraint(
            "pickup_latitude >= -90 AND pickup_latitude <= 90",
            name="ck_pickup_latitude",
        ),
        CheckConstraint(
            "pickup_longitude >= -180 AND pickup_longitude <= 180",
            name="ck_pickup_longitude",
        ),
        CheckConstraint(
            "delivery_latitude >= -90 AND delivery_latitude <= 90",
            name="ck_delivery_latitude",
        ),
        CheckConstraint(
            "delivery_longitude >= -180 AND delivery_longitude <= 180",
            name="ck_delivery_longitude",
        ),
        Index("ix_orders_status", "status"),
        Index("ix_orders_priority", "priority"),
        Index("ix_orders_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    customer_phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    pickup_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    delivery_address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    pickup_latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    pickup_longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    delivery_latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    delivery_longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    demand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    time_window_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    time_window_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status"),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )

    assigned_driver_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="SET NULL"),
        nullable=True,
    )

    assigned_vehicle_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assigned_driver: Mapped["Driver | None"] = relationship(
        "Driver",
        back_populates="orders",
        foreign_keys=[assigned_driver_id],
        lazy="selectin",
    )

    assigned_vehicle: Mapped["Vehicle | None"] = relationship(
        "Vehicle",
        back_populates="orders",
        foreign_keys=[assigned_vehicle_id],
        lazy="selectin",
    )
