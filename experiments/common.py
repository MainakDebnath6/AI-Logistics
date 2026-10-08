"""Shared deterministic data generation and metric utilities for experiments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 20261008
    observations: int = 730
    training_days: int = 670
    holdout_days: int = 60
    base_demand: float = 100.0
    linear_growth_per_day: float = 0.04
    weekly_amplitude: float = 18.0
    annual_amplitude: float = 25.0
    noise_standard_deviation: float = 7.0
    horizons: tuple[int, ...] = (7, 14, 30, 60)


def make_dataset(config: ExperimentConfig) -> np.ndarray:
    """Generate the specified synthetic daily series deterministically."""
    rng = np.random.default_rng(config.seed)
    day = np.arange(config.observations, dtype=float)
    weekly = config.weekly_amplitude * np.sin(2.0 * np.pi * day / 7.0)
    annual = config.annual_amplitude * np.sin(2.0 * np.pi * day / 365.0)
    trend = config.linear_growth_per_day * day
    noise = rng.normal(0.0, config.noise_standard_deviation, config.observations)
    return np.maximum(config.base_demand + trend + weekly + annual + noise, 0.0)


def chronological_split(values: np.ndarray, training_days: int) -> tuple[np.ndarray, np.ndarray]:
    """Split a daily series chronologically without shuffling."""
    if training_days <= 0 or training_days >= len(values):
        raise ValueError("training_days must be within the series length.")
    return values[:training_days].copy(), values[training_days:].copy()


def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    """Calculate MAE, RMSE, and MAPE; exclude zero actuals from MAPE."""
    if actual.shape != predicted.shape or actual.size == 0:
        raise ValueError("actual and predicted must have the same non-empty shape.")
    errors = predicted - actual
    nonzero = actual != 0
    mape = float(np.mean(np.abs(errors[nonzero] / actual[nonzero])) * 100.0) if np.any(nonzero) else 0.0
    return {
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(np.square(errors)))),
        "mape_percent": mape,
    }


def write_results(
    output_dir: Path,
    stem: str,
    rows: list[dict[str, Any]],
    config: ExperimentConfig,
    methodology: dict[str, Any] | None = None,
) -> None:
    """Write raw rows and configuration as CSV and JSON."""
    import csv

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (output_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        if fields:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    payload = {
        "configuration": asdict(config),
        "methodology": methodology or {},
        "results": rows,
    }
    with (output_dir / f"{stem}.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
