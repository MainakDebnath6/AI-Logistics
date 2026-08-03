"""Pydantic schemas for driver profiles."""

from datetime import datetime
from uuid import UUID

from app.models.driver import DriverStatus
from pydantic import BaseModel, ConfigDict, Field


class DriverCreate(BaseModel):
    """Input used to create a driver profile."""

    user_id: UUID
    license_number: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=1, max_length=32)
    vehicle_id: UUID | None = None
    max_capacity: int = Field(gt=0)


class DriverUpdate(BaseModel):
    """Input used to update a driver profile."""

    license_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    phone: str | None = Field(
        default=None,
        min_length=1,
        max_length=32,
    )
    vehicle_id: UUID | None = None
    status: DriverStatus | None = None
    current_latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
    )
    current_longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
    )
    max_capacity: int | None = Field(
        default=None,
        gt=0,
    )
    is_available: bool | None = None


class DriverResponse(BaseModel):
    """Public driver representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    license_number: str
    phone: str
    vehicle_id: UUID | None
    status: DriverStatus
    current_latitude: float | None
    current_longitude: float | None
    max_capacity: int
    is_available: bool
    created_at: datetime
    updated_at: datetime
