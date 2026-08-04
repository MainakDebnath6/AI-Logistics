"""Prediction API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_dispatcher
from app.models.user import User
from app.schemas.prediction import (
    DemandForecastRequest,
    DemandForecastResponse,
    ETARequest,
    ETAResponse,
)
from app.services.demand_forecast_service import DemandForecastService
from app.services.eta_service import ETAService


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


@router.post("/eta", response_model=ETAResponse)
def predict_eta(
    payload: ETARequest,
    current_dispatcher: User = Depends(get_current_dispatcher),
    eta_service: ETAService = Depends(get_eta_service),
) -> ETAResponse:
    """Return ETA prediction for route parameters."""

    _authorize_prediction_access(current_dispatcher)

    try:
        predicted_eta = eta_service.predict_eta(
            distance_km=payload.distance_km,
            average_speed_kmph=payload.average_speed_kmph,
            traffic_multiplier=payload.traffic_multiplier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ETAResponse(predicted_eta_minutes=predicted_eta)


@router.post("/demand", response_model=DemandForecastResponse)
def forecast_demand(
    payload: DemandForecastRequest,
    current_dispatcher: User = Depends(get_current_dispatcher),
    demand_forecast_service: DemandForecastService = Depends(get_demand_forecast_service),
) -> DemandForecastResponse:
    """Return demand forecast from historical demand observations."""

    _authorize_prediction_access(current_dispatcher)

    try:
        predicted_demand = demand_forecast_service.forecast_demand(
            payload.historical_demand_values
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return DemandForecastResponse(predicted_demand=predicted_demand)
