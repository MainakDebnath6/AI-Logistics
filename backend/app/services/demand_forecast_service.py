"""Demand forecasting business logic."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol


class DemandForecastModelProtocol(Protocol):
    """Protocol for sklearn-compatible demand forecasting models."""

    def predict(self, X: list[list[float]]) -> list[float]:
        """Predict demand values for the provided feature matrix."""


class DemandForecastService:
    """Service for demand forecast predictions."""

    def __init__(
        self,
        model: DemandForecastModelProtocol | None = None,
        window_size: int = 7,
    ) -> None:
        """Initialize the service with optional model and feature window size."""

        self._model = model
        self._window_size = max(window_size, 1)

    def forecast_demand(self, historical_demand: Sequence[float]) -> float:
        """Return predicted demand from historical demand observations."""
        normalized = self._normalize_history(historical_demand)
        if self._model is not None:
            return self._forecast_with_model(normalized)
        return self._forecast_with_smoothing(normalized)

    def forecast_demand_values(self, historical_demand_values: Sequence[float]) -> float:
        """Backward-compatible facade using explicit values naming."""
        return self.forecast_demand(historical_demand_values)

    @staticmethod
    def _normalize_history(historical_demand: Sequence[float]) -> list[float]:
        """Validate and normalize historical demand values."""
        if not historical_demand:
            raise ValueError("Historical demand cannot be empty.")

        normalized: list[float] = []
        for value in historical_demand:
            if value < 0:
                raise ValueError("Historical demand values cannot be negative.")
            normalized.append(float(value))

        return normalized

    def _forecast_with_model(self, history: list[float]) -> float:
        """Forecast demand using an injected sklearn-compatible model."""
        features = self._build_feature_row(history)
        predictions = self._model.predict([features])
        if not predictions:
            raise ValueError("Prediction model returned no demand value.")

        forecast = float(predictions[0])
        return round(max(forecast, 0.0), 2)

    def _build_feature_row(self, history: list[float]) -> list[float]:
        """Build a fixed-size feature row from historical demand."""
        if len(history) >= self._window_size:
            return history[-self._window_size :]

        padding = [history[0]] * (self._window_size - len(history))
        return [*padding, *history]

    @staticmethod
    def _forecast_with_smoothing(history: list[float], alpha: float = 0.35) -> float:
        """Forecast demand using exponential smoothing fallback."""
        smoothed = history[0]
        for value in history[1:]:
            smoothed = alpha * value + (1.0 - alpha) * smoothed
        return round(max(smoothed, 0.0), 2)
