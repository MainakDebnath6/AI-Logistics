"""ETA prediction business logic."""

from __future__ import annotations

from typing import Protocol


class ETARegressorProtocol(Protocol):
    """Protocol for sklearn-compatible ETA regression models."""

    def predict(self, X: list[list[float]]) -> list[float]:
        """Predict ETA values for the provided feature matrix."""


class ETAService:
    """Service for route ETA predictions."""

    def __init__(self, model: ETARegressorProtocol | None = None) -> None:
        """Initialize the service with an optional prediction model."""

        self._model = model

    def predict_eta(
        self,
        distance_km: float,
        average_speed_kmph: float,
        traffic_multiplier: float = 1.0,
        **legacy_kwargs: float,
    ) -> float:
        """Return predicted ETA in minutes for a route."""
        if "route_distance_km" in legacy_kwargs:
            distance_km = float(legacy_kwargs["route_distance_km"])
        if "traffic_factor" in legacy_kwargs:
            traffic_multiplier = float(legacy_kwargs["traffic_factor"])

        self._validate_inputs(
            distance_km=distance_km,
            average_speed_kmph=average_speed_kmph,
            traffic_multiplier=traffic_multiplier,
        )

        if self._model is not None:
            return self._predict_with_model(
                distance_km=distance_km,
                average_speed_kmph=average_speed_kmph,
                traffic_multiplier=traffic_multiplier,
            )

        return self._predict_with_formula(
            distance_km=distance_km,
            average_speed_kmph=average_speed_kmph,
            traffic_multiplier=traffic_multiplier,
        )

    @staticmethod
    def _validate_inputs(
        distance_km: float,
        average_speed_kmph: float,
        traffic_multiplier: float,
    ) -> None:
        """Validate ETA prediction inputs."""
        if distance_km <= 0:
            raise ValueError("Route distance must be greater than zero.")
        if average_speed_kmph <= 0:
            raise ValueError("Average speed must be greater than zero.")
        if traffic_multiplier <= 0:
            raise ValueError("Traffic factor must be greater than zero.")

    def _predict_with_model(
        self,
        distance_km: float,
        average_speed_kmph: float,
        traffic_multiplier: float,
    ) -> float:
        """Predict ETA using an injected sklearn-compatible model."""
        feature_row = [[distance_km, average_speed_kmph, traffic_multiplier]]
        predictions = self._model.predict(feature_row)
        if not predictions:
            raise ValueError("Prediction model returned no ETA value.")

        predicted_eta = float(predictions[0])
        return round(max(predicted_eta, 0.0), 2)

    @staticmethod
    def _predict_with_formula(
        distance_km: float,
        average_speed_kmph: float,
        traffic_multiplier: float,
    ) -> float:
        """Predict ETA with deterministic travel-time formula."""
        base_hours = distance_km / average_speed_kmph
        eta_minutes = base_hours * 60.0 * traffic_multiplier
        return round(max(eta_minutes, 0.0), 2)
