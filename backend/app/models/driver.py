"""Driver ORM model and status enumeration."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from app.db.base import Base
from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.order import Order

DRIVER_ORDER_FK = getattr(Order, "assigned_driver_id")

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vehicle import Vehicle


class DriverStatus(str, Enum):
    """Supported driver availability states."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class Driver(Base):
    """Persisted driver profile linked to a user account."""

    __tablename__ = "drivers"

    __table_args__ = (
        Index("ix_drivers_status", "status"),
        Index("ix_drivers_is_available", "is_available"),
        Index("ix_drivers_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    license_number: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    vehicle_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[DriverStatus] = mapped_column(
        SAEnum(DriverStatus, name="driver_status"),
        nullable=False,
        default=DriverStatus.AVAILABLE,
        server_default=DriverStatus.AVAILABLE.value,
    )

    current_latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    current_longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    max_capacity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="driver",
        lazy="selectin",
    )

    vehicle: Mapped["Vehicle | None"] = relationship(
        "Vehicle",
        back_populates="driver",
        foreign_keys=[vehicle_id],
        lazy="selectin",
    )

    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="assigned_driver",
        foreign_keys=[DRIVER_ORDER_FK],
        lazy="selectin",
    )