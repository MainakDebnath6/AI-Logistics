"""Prediction API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies.auth import get_current_dispatcher
from app.models.user import User
from app.services.demand_forecast_service import DemandForecastService
from app.services.eta_service import ETAService


class ETAPredictionRequest(BaseModel):
    """Request payload for ETA prediction."""

    route_distance_km: float = Field(gt=0)
    average_speed_kmph: float = Field(gt=0)
    traffic_factor: float = Field(default=1.0, gt=0)


class ETAPredictionResponse(BaseModel):
    """Response payload for ETA prediction."""

    predicted_eta_minutes: float


class DemandForecastRequest(BaseModel):
    """Request payload for demand forecasting."""

    historical_demand: list[float] = Field(min_length=1)


class DemandForecastResponse(BaseModel):
    """Response payload for demand forecasting."""

    predicted_demand: float


router = APIRouter(
    prefix="/predictions",
    tags=["Predictions"],
)


def get_eta_service() -> ETAService:
    """Create an ETA service instance."""

    return ETAService()


def get_demand_forecast_service() -> DemandForecastService:
    """Create a demand forecast service instance."""

    return DemandForecastService()


def _is_dispatcher_or_admin(user: User) -> bool:
    """Return whether the authenticated user can access prediction endpoints."""

    role = getattr(user, "role", None)
    if role is None:
        return False

    role_value = getattr(role, "value", role)
    return isinstance(role_value, str) and role_value.lower() in {"dispatcher", "admin"}


def _authorize_prediction_access(user: User) -> None:
    """Raise an HTTP error when prediction access is not allowed."""

    if _is_dispatcher_or_admin(user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only dispatcher or admin users can access predictions.",
    )


@router.post("/eta", response_model=ETAPredictionResponse)
def predict_eta(
    payload: ETAPredictionRequest,
    current_dispatcher: User = Depends(get_current_dispatcher),
    eta_service: ETAService = Depends(get_eta_service),
) -> ETAPredictionResponse:
    """Return ETA prediction for route parameters."""

    _authorize_prediction_access(current_dispatcher)

    try:
        predicted_eta = eta_service.predict_eta(
            route_distance_km=payload.route_distance_km,
            average_speed_kmph=payload.average_speed_kmph,
            traffic_factor=payload.traffic_factor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ETAPredictionResponse(predicted_eta_minutes=predicted_eta)


@router.post("/demand", response_model=DemandForecastResponse)
def forecast_demand(
    payload: DemandForecastRequest,
    current_dispatcher: User = Depends(get_current_dispatcher),
    demand_forecast_service: DemandForecastService = Depends(get_demand_forecast_service),
) -> DemandForecastResponse:
    """Return demand forecast from historical demand observations."""

    _authorize_prediction_access(current_dispatcher)

    try:
        predicted_demand = demand_forecast_service.forecast_demand(payload.historical_demand)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return DemandForecastResponse(predicted_demand=predicted_demand)
