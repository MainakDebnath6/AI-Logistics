from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

import numpy as np
import pytest

from experiments.common import (
    ExperimentConfig,
    calculate_metrics,
    chronological_split,
    make_dataset,
)
from experiments.data_generation import generate_dataset
from experiments.forecasting import run_forecasting_experiments
from experiments.routing import (
    RoutingExperimentConfig,
    _run_cvrp,
    run_paired_routing_experiment,
)


def test_synthetic_dataset_is_seeded_and_chronological_split_is_preserved():
    config = ExperimentConfig(seed=77, observations=40, training_days=30, holdout_days=10)

    first = make_dataset(config)
    second = make_dataset(config)
    training, holdout = chronological_split(first, config.training_days)

    np.testing.assert_array_equal(first, second)
    np.testing.assert_array_equal(training, first[:30])
    np.testing.assert_array_equal(holdout, first[30:])


def test_dataset_generator_uses_weekly_annual_and_sigma_five_components():
    config = ExperimentConfig(
        seed=14,
        observations=730,
        base_demand=100.0,
        linear_growth_per_day=0.0,
        weekly_amplitude=18.0,
        annual_amplitude=0.0,
        noise_standard_deviation=0.0,
    )
    weekly_series = make_dataset(config)
    np.testing.assert_allclose(weekly_series[7:], weekly_series[:-7])

    annual_config = ExperimentConfig(
        seed=14,
        observations=730,
        base_demand=100.0,
        linear_growth_per_day=0.0,
        weekly_amplitude=0.0,
        annual_amplitude=25.0,
        noise_standard_deviation=0.0,
    )
    annual_series = make_dataset(annual_config)
    assert annual_series[90] == pytest.approx(
        100.0 + 25.0 * np.sin(2.0 * np.pi * 90 / 365.25)
    )

    noise_config = ExperimentConfig(
        seed=14,
        observations=730,
        base_demand=100.0,
        linear_growth_per_day=0.0,
        weekly_amplitude=0.0,
        annual_amplitude=0.0,
        noise_standard_deviation=5.0,
    )
    noise = make_dataset(noise_config) - noise_config.base_demand
    assert np.std(noise, ddof=1) == pytest.approx(5.0, abs=0.5)


def test_generated_csv_has_730_unique_consecutive_synthetic_days(tmp_path):
    from experiments.common import load_synthetic_dataset

    first_path = generate_dataset(tmp_path / "synthetic.csv")
    first_bytes = first_path.read_bytes()
    generate_dataset(first_path)
    dates, demand = load_synthetic_dataset(first_path)

    assert first_path.read_bytes() == first_bytes
    assert len(dates) == 730
    assert len(set(dates)) == 730
    parsed_dates = [date.fromisoformat(value) for value in dates]
    assert all((later - earlier) == timedelta(days=1) for earlier, later in pairwise(parsed_dates))
    assert len(demand) == 730
    assert np.all(demand >= 0)
    assert (tmp_path / "synthetic.csv").read_text(encoding="utf-8").splitlines()[0] == "date,demand,data_type"


def test_previous_week_naive_repeats_last_observed_week():
    from experiments.forecasting import _naive_previous_week

    np.testing.assert_array_equal(
        _naive_previous_week(np.arange(1.0, 8.0), 10),
        np.array([1, 2, 3, 4, 5, 6, 7, 1, 2, 3], dtype=float),
    )


def test_metrics_are_computed_from_provided_values():
    metrics = calculate_metrics(np.array([10.0, 20.0]), np.array([12.0, 18.0]))

    assert metrics["mae"] == 2.0
    assert metrics["rmse"] == 2.0
    assert metrics["mape_percent"] == pytest.approx(15.0)


def test_zero_actuals_are_excluded_from_mape_but_counted_for_other_metrics():
    metrics = calculate_metrics(np.array([0.0, 10.0]), np.array([5.0, 12.0]))

    assert metrics["n_observations"] == 2
    assert metrics["mape_n_observations"] == 1
    assert metrics["mape_percent"] == pytest.approx(20.0)

    all_zero_metrics = calculate_metrics(np.zeros(2), np.array([1.0, 2.0]))
    assert all_zero_metrics["mape_percent"] == 0.0
    assert all_zero_metrics["mape_n_observations"] == 0


def test_feature_ablation_removes_actual_regression_columns():
    from experiments.forecasting import _feature_row

    history = list(np.arange(1.0, 401.0))
    all_features = _feature_row(history, 400, frozenset({"weekly", "annual", "lags", "rolling"}))
    no_week_or_annual = _feature_row(history, 400, frozenset({"lags", "rolling"}))

    assert len(all_features) == 20
    assert len(no_week_or_annual) == 10
    assert no_week_or_annual == all_features[:2] + all_features[12:]


def test_forecasting_experiment_generates_all_models_ablations_and_horizons(tmp_path, monkeypatch):
    from experiments import forecasting

    config = ExperimentConfig(observations=730, training_days=670, holdout_days=60)
    monkeypatch.setattr(forecasting, "OUTPUT_DIR", tmp_path)

    results = run_forecasting_experiments(config)

    assert {row["model"] for row in results["forecast_models"]} == {
        "naive_previous_week",
        "holt_winters_weekly",
        "seasonal_linear_regression",
    }
    assert len(results["feature_ablation"]) == 6
    assert {row["horizon_days"] for row in results["horizon_sensitivity"]} == {7, 14, 30, 60}
    horizon_origins = {
        row["horizon_days"]: row["forecast_origins"]
        for row in results["horizon_sensitivity"]
        if row["model"] == "naive_previous_week"
    }
    assert horizon_origins == {7: 54, 14: 47, 30: 31, 60: 1}
    assert all("n_observations" in row for row in results["horizon_sensitivity"])
    assert {row["forecast_origins"] for row in results["horizon_sensitivity"] if row["model"] == "naive_previous_week"} == {1, 31, 47, 54}
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


def test_cvrp_benchmark_first_solution_is_repeatable():
    config = RoutingExperimentConfig(solver_solution_limit=1)

    first = _run_cvrp(3, 70.0, config)
    second = _run_cvrp(3, 70.0, config)

    assert first["feasible"] == second["feasible"]
    assert first["route_distance_km"] == second["route_distance_km"]
    assert first["route_count"] == second["route_count"]
    assert first["served_orders"] == second["served_orders"]
