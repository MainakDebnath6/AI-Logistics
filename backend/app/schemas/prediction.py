"""Pydantic schemas for prediction endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class ETARequest(BaseModel):
    """Request payload for ETA prediction."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    distance_km: float = Field(
        gt=0,
        validation_alias=AliasChoices("distance_km", "route_distance_km"),
    )
    average_speed_kmph: float = Field(gt=0)
    traffic_multiplier: float = Field(
        default=1.0,
        gt=0,
        validation_alias=AliasChoices("traffic_multiplier", "traffic_factor"),
    )


class ETAResponse(BaseModel):
    """Response payload for ETA prediction."""

    predicted_eta_minutes: float = Field(ge=0)


class DemandForecastRequest(BaseModel):
    """Request payload for demand forecasting."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    historical_demand_values: list[float] = Field(
        min_length=1,
        validation_alias=AliasChoices("historical_demand_values", "historical_demand"),
    )


class DemandForecastResponse(BaseModel):
    """Response payload for demand forecasting."""

    predicted_demand: float = Field(ge=0)
