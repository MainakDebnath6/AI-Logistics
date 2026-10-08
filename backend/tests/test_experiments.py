from __future__ import annotations

import numpy as np
import pytest

from experiments.common import (
    ExperimentConfig,
    calculate_metrics,
    chronological_split,
    make_dataset,
)
from experiments.forecasting import run_forecasting_experiments
from experiments.routing import run_paired_routing_experiment


def test_synthetic_dataset_is_seeded_and_chronological_split_is_preserved():
    config = ExperimentConfig(seed=77, observations=40, training_days=30, holdout_days=10)

    first = make_dataset(config)
    second = make_dataset(config)
    training, holdout = chronological_split(first, config.training_days)

    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(training, first[:30])
    np.testing.assert_array_equal(holdout, first[30:])


def test_metrics_are_computed_from_provided_values():
    metrics = calculate_metrics(np.array([10.0, 20.0]), np.array([12.0, 18.0]))

    assert metrics["mae"] == 2.0
    assert metrics["rmse"] == 2.0
    assert metrics["mape_percent"] == pytest.approx(15.0)


def test_forecasting_experiment_generates_all_models_ablations_and_horizons(tmp_path, monkeypatch):
    from experiments import forecasting

    config = ExperimentConfig(observations=730, training_days=670, holdout_days=60)
    monkeypatch.setattr(forecasting, "OUTPUT_DIR", tmp_path)

    results = run_forecasting_experiments(config)

    assert {row["model"] for row in results["forecast_models"]} == {
        "naive_last_value",
        "holt_winters_weekly",
        "seasonal_linear_regression",
    }
    assert len(results["feature_ablation"]) == 6
    assert {row["horizon_days"] for row in results["horizon_sensitivity"]} == {7, 14, 30, 60}
    assert (tmp_path / "forecast_models.csv").exists()
    assert (tmp_path / "forecast_models.json").exists()


def test_paired_routing_arms_keep_operational_metrics_identical(tmp_path, monkeypatch):
    from experiments import routing

    config = ExperimentConfig(observations=730, training_days=670, holdout_days=60)
    monkeypatch.setattr(routing, "OUTPUT_DIR", tmp_path)

    rows = run_paired_routing_experiment(config)

    assert len(rows) == 6
    for row in rows:
        for metric in (
            "feasible",
            "service_level_percent",
            "fleet_utilization_percent",
            "route_distance_km",
            "capacity_shortfall",
            "route_count",
        ):
            assert row[f"reactive_{metric}"] == row[f"hgfc_{metric}"]
    assert (tmp_path / "reactive_vs_hgfc.csv").exists()
    assert (tmp_path / "reactive_vs_hgfc.json").exists()
