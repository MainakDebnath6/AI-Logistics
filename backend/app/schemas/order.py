"""Pydantic schemas for delivery orders."""

from datetime import datetime
from uuid import UUID

from app.models.order import OrderStatus
from pydantic import BaseModel, ConfigDict, Field, model_validator


class OrderCreate(BaseModel):
    """Input used to create a delivery order."""

    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str = Field(min_length=1, max_length=32)
    pickup_address: str = Field(min_length=1)
    delivery_address: str = Field(min_length=1)
    pickup_latitude: float = Field(ge=-90.0, le=90.0)
    pickup_longitude: float = Field(ge=-180.0, le=180.0)
    delivery_latitude: float = Field(ge=-90.0, le=90.0)
    delivery_longitude: float = Field(ge=-180.0, le=180.0)
    demand: int = Field(gt=0)
    priority: int = Field(default=1, ge=1)
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "OrderCreate":
        """Ensure the delivery time window is chronologically valid."""

        if self.time_window_start is not None and self.time_window_end is not None:
            if self.time_window_start >= self.time_window_end:
                raise ValueError("time_window_start must be before time_window_end")

        return self


class OrderUpdate(BaseModel):
    """Input used to update a delivery order."""

    customer_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    customer_phone: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
    )
    pickup_address: str | None = Field(
        default=None,
        min_length=1,
    )
    delivery_address: str | None = Field(
        default=None,
        min_length=1,
    )
    pickup_latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )
    pickup_longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )
    delivery_latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )
    delivery_longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )
    demand: int | None = Field(
        default=None,
        gt=0,
    )
    priority: int | None = Field(
        default=None,
        ge=1,
    )
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    status: OrderStatus | None = None
    assigned_driver_id: UUID | None = None
    assigned_vehicle_id: UUID | None = None

    @model_validator(mode="after")
    def validate_time_window(self) -> "OrderUpdate":
        """Ensure the delivery time window is chronologically valid."""

        if self.time_window_start is not None and self.time_window_end is not None:
            if self.time_window_start >= self.time_window_end:
                raise ValueError("time_window_start must be before time_window_end")

        return self


class OrderResponse(BaseModel):
    """Public order representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_name: str
    customer_phone: str
    pickup_address: str
    delivery_address: str
    pickup_latitude: float
    pickup_longitude: float
    delivery_latitude: float
    delivery_longitude: float
    demand: int
    priority: int
    time_window_start: datetime | None
    time_window_end: datetime | None
    status: OrderStatus
    assigned_driver_id: UUID | None
    assigned_vehicle_id: UUID | None
    created_at: datetime
    updated_at: datetime
