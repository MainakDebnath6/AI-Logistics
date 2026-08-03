"""Pydantic schemas for vehicles."""

from datetime import datetime
from uuid import UUID

from app.models.vehicle import VehicleStatus
from pydantic import BaseModel, ConfigDict, Field


class VehicleCreate(BaseModel):
    """Input used to create a vehicle."""

    registration_number: str = Field(min_length=1, max_length=64)
    model: str = Field(min_length=1, max_length=255)
    manufacturer: str = Field(min_length=1, max_length=255)
    capacity: int = Field(gt=0)


class VehicleUpdate(BaseModel):
    """Input used to update a vehicle."""

    registration_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=64,
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    manufacturer: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    capacity: int | None = Field(
        default=None,
        gt=0,
    )
    status: VehicleStatus | None = None
    current_driver_id: UUID | None = None
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
    fuel_level: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
    )
    is_active: bool | None = None


class VehicleResponse(BaseModel):
    """Public vehicle representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    registration_number: str
    model: str
    manufacturer: str
    capacity: int
    status: VehicleStatus
    current_driver_id: UUID | None
    current_latitude: float | None
    current_longitude: float | None
    fuel_level: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
