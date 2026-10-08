"""Pydantic schemas for analytics endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FleetAnalyticsResponse(BaseModel):
    """Aggregated fleet analytics metrics for dashboard consumption."""

    model_config = ConfigDict(from_attributes=True)

    vehicle_utilization_percentage: float
    driver_utilization_percentage: float
    average_route_distance_km: float
    average_eta_minutes: float
    completed_orders: int
    pending_orders: int
    total_orders: int
    route_efficiency_percentage: float
    on_time_delivery_percentage: float
    generated_at: datetime
