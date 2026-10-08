"""Pydantic schemas for route persistence and API responses."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RouteCreate(BaseModel):
    """Payload schema used to create a persisted route record."""

    model_config = ConfigDict(from_attributes=True)

    driver_id: UUID
    vehicle_id: UUID
    total_distance_km: float
    total_load: int
    optimization_started_at: datetime | None = None
    optimization_completed_at: datetime | None = None


class RouteResponse(BaseModel):
    """Detailed route representation returned by API endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    driver_id: UUID
    vehicle_id: UUID
    total_distance_km: float
    total_load: int
    optimization_started_at: datetime | None = None
    optimization_completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class RouteSummary(BaseModel):
    """Compact route view for list responses and summary displays."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    driver_id: UUID
    vehicle_id: UUID
    total_distance_km: float
    total_load: int
    optimization_completed_at: datetime | None = None
    created_at: datetime
