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


class SyntheticDemandObservation(BaseModel):
    """One ordered daily demand observation."""

    date: str
    demand: float


class SyntheticDemandSummary(BaseModel):
    """Summary of the synthetic demand dataset."""

    count: int
    start_date: str | None = None
    end_date: str | None = None
    average_demand: float = 0.0
    min_demand: float = 0.0
    max_demand: float = 0.0
    observations: list[SyntheticDemandObservation] = []


class ResearchAnalyticsResponse(BaseModel):
    """Read-only research analytics payload for forecast and advisory experiments."""

    synthetic_demand: SyntheticDemandSummary
    forecast_models: dict
    horizon_sensitivity: dict
    feature_ablation: dict
    cvrp_benchmark: dict
    hgfc_advisory: dict
