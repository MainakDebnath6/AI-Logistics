"""Shared deterministic data generation and metric utilities for experiments."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from itertools import pairwise
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
    annual_period_days: float = 365.25
    noise_standard_deviation: float = 5.0
    horizons: tuple[int, ...] = (7, 14, 30, 60)
    start_date: str = "2024-01-01"


def make_dataset(config: ExperimentConfig) -> np.ndarray:
    """Generate the specified synthetic daily series deterministically."""
    rng = np.random.default_rng(config.seed)
    day = np.arange(config.observations, dtype=float)
    weekly = config.weekly_amplitude * np.sin(2.0 * np.pi * day / 7.0)
    annual = config.annual_amplitude * np.sin(2.0 * np.pi * day / config.annual_period_days)
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
        "n_observations": int(actual.size),
        "mape_n_observations": int(np.count_nonzero(nonzero)),
    }


def write_synthetic_dataset(output_path: Path, config: ExperimentConfig) -> None:
    """Write the reproducible generated series with an explicit synthetic label."""
    import csv

    values = make_dataset(config)
    first_date = date.fromisoformat(config.start_date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("date", "demand", "data_type"))
        for offset, demand in enumerate(values):
            writer.writerow(
                (
                    (first_date + timedelta(days=offset)).isoformat(),
                    f"{float(demand):.10f}",
                    "synthetic",
                )
            )


def load_synthetic_dataset(path: Path) -> tuple[list[str], np.ndarray]:
    """Load and validate the checked-in synthetic date/demand dataset."""
    import csv

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"date", "demand", "data_type"}.issubset(reader.fieldnames):
            raise ValueError("Synthetic dataset must include date, demand, and data_type columns.")
        records = list(reader)

    dates = [record["date"] for record in records]
    parsed_dates = [date.fromisoformat(value) for value in dates]
    demands = np.asarray([float(record["demand"]) for record in records], dtype=float)
    if any(record["data_type"] != "synthetic" for record in records):
        raise ValueError("Dataset contains rows not marked synthetic.")
    if len(dates) != len(set(dates)):
        raise ValueError("Synthetic dataset contains duplicate dates.")
    if any((later - earlier).days != 1 for earlier, later in pairwise(parsed_dates)):
        raise ValueError("Synthetic dataset dates must be consecutive daily observations.")
    if len(demands) and np.any(demands < 0):
        raise ValueError("Synthetic demand cannot be negative.")
    return dates, demands


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
    metadata = {
        "seed": config.seed,
        "dataset_size": config.observations,
        "train_size": config.training_days,
        "test_size": config.holdout_days,
    }
    result_rows = [{**metadata, **row} for row in rows]
    fields = list(dict.fromkeys(key for row in result_rows for key in row))
    with (output_dir / f"{stem}.csv").open("w", newline="", encoding="utf-8") as handle:
        if fields:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(result_rows)
    payload = {
        "configuration": asdict(config),
        "methodology": methodology or {},
        "results": result_rows,
    }
    with (output_dir / f"{stem}.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
