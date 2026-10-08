"""Schemas for advisory horizon-gated forecast-to-capacity assessments."""

from enum import StrEnum

from pydantic import BaseModel, Field


class HGFCStatus(StrEnum):
    """Outcome of applying the advisory horizon gate and capacity comparison."""

    OUTSIDE_HORIZON = "outside_horizon"
    WITHIN_CAPACITY = "within_capacity"
    CAPACITY_SHORTFALL = "capacity_shortfall"


class HGFCRequest(BaseModel):
    """Inputs to an advisory assessment; none are routing constraints."""

    forecast_demand: float = Field(ge=0)
    available_capacity: float = Field(ge=0)
    horizon_days: int = Field(gt=0)


class HGFCForecastRequest(BaseModel):
    """Historical-demand inputs for the additive forecast-plus-advisory flow."""

    historical_demand_values: list[float] = Field(min_length=1)
    available_capacity: float = Field(ge=0)
    horizon_days: int = Field(gt=0)


class HGFCResponse(BaseModel):
    """Capacity-risk signal separated from confirmed-order routing inputs."""

    forecast_demand: float
    available_capacity: float
    horizon_days: int
    advisory_horizon_days: int
    gate_open: bool
    status: HGFCStatus
    capacity_delta: float | None
    rho: float | None
    capacity_risk: float | None
    recommended_additional_capacity: float
    preparation_recommended: bool