"""Forecast-model, ablation, and horizon sensitivity experiments."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np

from experiments.common import (
    ExperimentConfig,
    calculate_metrics,
    load_synthetic_dataset,
    make_dataset,
    write_results,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"
DATASET_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "synthetic_demand.csv"
ANNUAL_PERIOD_DAYS = 365.25


def _naive_previous_week(history: np.ndarray, horizon: int) -> np.ndarray:
    """Repeat the most recent observed week for each future weekday."""
    if len(history) < 7:
        raise ValueError("Previous-week naive forecasting needs at least seven observations.")
    return np.asarray([history[-7 + (offset % 7)] for offset in range(horizon)], dtype=float)


def _holt_winters_forecast(history: np.ndarray, horizon: int) -> np.ndarray:
    """Fit additive weekly Holt-Winters with deterministic grid-selected gains."""
    period = 7
    if len(history) <= period * 2:
        return _naive_previous_week(history, horizon)

    gains = (0.2, 0.5, 0.8)
    best_error = float("inf")
    best_state: tuple[float, float, np.ndarray] | None = None
    for alpha in gains:
        for beta in gains:
            for gamma in gains:
                level = float(np.mean(history[:period]))
                trend = float((np.mean(history[period : 2 * period]) - level) / period)
                seasonal = history[:period] - level
                squared_errors: list[float] = []
                for index, actual in enumerate(history):
                    season_index = index % period
                    prediction = level + trend + seasonal[season_index]
                    squared_errors.append(float((actual - prediction) ** 2))
                    previous_level = level
                    level = alpha * (actual - seasonal[season_index]) + (1.0 - alpha) * (level + trend)
                    trend = beta * (level - previous_level) + (1.0 - beta) * trend
                    seasonal[season_index] = gamma * (actual - level) + (1.0 - gamma) * seasonal[season_index]
                score = float(np.mean(squared_errors[period * 2 :]))
                if score < best_error:
                    best_error = score
                    best_state = (level, trend, seasonal.copy())

    assert best_state is not None
    level, trend, seasonal = best_state
    return np.array(
        [max(0.0, level + (step + 1) * trend + seasonal[(len(history) + step) % period]) for step in range(horizon)]
    )


def _feature_row(
    history: list[float],
    time_index: int,
    features: frozenset[str],
    annual_period_days: float = ANNUAL_PERIOD_DAYS,
) -> list[float]:
    row = [1.0, time_index / 365.0]
    if "weekly" in features:
        for harmonic in (1, 2, 3):
            angle = 2.0 * np.pi * time_index * harmonic / 7.0
            row.extend((float(np.sin(angle)), float(np.cos(angle))))
    if "annual" in features:
        for harmonic in (1, 2):
            angle = 2.0 * np.pi * time_index * harmonic / annual_period_days
            row.extend((float(np.sin(angle)), float(np.cos(angle))))
    if "lags" in features:
        for lag in (1, 7, 14, 28, 365):
            row.append(history[-lag] if len(history) >= lag else history[0])
    if "rolling" in features:
        for window in (7, 28, 365):
            row.append(float(np.mean(history[-min(window, len(history)) :])))
    return row


def _seasonal_regression_forecast(
    training: np.ndarray,
    horizon: int,
    features: frozenset[str],
    annual_period_days: float = ANNUAL_PERIOD_DAYS,
) -> np.ndarray:
    """Fit a deterministic feature regression and recursively forecast."""
    history = [float(value) for value in training]
    first_index = 365 if len(training) > 365 else max(7, len(training) // 2)
    rows = [
        _feature_row(history[:index], index, features, annual_period_days)
        for index in range(first_index, len(training))
    ]
    targets = training[first_index:]
    coefficients, *_ = np.linalg.lstsq(np.asarray(rows), targets, rcond=None)
    predictions: list[float] = []
    for time_index in range(len(training), len(training) + horizon):
        row = np.asarray(_feature_row(history, time_index, features, annual_period_days))
        prediction = max(0.0, float(row @ coefficients))
        predictions.append(prediction)
        history.append(prediction)
    return np.asarray(predictions)


def _rolling_origin_predictions(
    series: np.ndarray,
    *,
    training_days: int,
    horizon: int,
    predictor: Callable[[np.ndarray, int], np.ndarray],
) -> tuple[list[dict], np.ndarray, np.ndarray]:
    """Evaluate all valid expanding-window origins without using future targets."""
    records: list[dict] = []
    actual_values: list[float] = []
    predicted_values: list[float] = []
    last_origin = len(series) - horizon
    if training_days > last_origin:
        raise ValueError("Insufficient holdout data for the requested forecast horizon.")

    for origin in range(training_days, last_origin + 1):
        history = series[:origin]
        predictions = predictor(history, horizon)
        targets = series[origin : origin + horizon]
        for lead, (actual, predicted) in enumerate(zip(targets, predictions, strict=True), start=1):
            records.append(
                {
                    "forecast_origin_index": origin,
                    "target_index": origin + lead - 1,
                    "lead_days": lead,
                    "actual": float(actual),
                    "predicted": float(predicted),
                }
            )
            actual_values.append(float(actual))
            predicted_values.append(float(predicted))
    return records, np.asarray(actual_values), np.asarray(predicted_values)


def run_forecasting_experiments(
    config: ExperimentConfig | None = None,
    series: np.ndarray | None = None,
    dates: list[str] | None = None,
) -> dict[str, list[dict]]:
    """Run rolling-origin model comparison, ablation, and horizon sensitivity."""
    config = config or ExperimentConfig()
    if series is None:
        if DATASET_PATH.exists() and config.observations == 730:
            dates, series = load_synthetic_dataset(DATASET_PATH)
        else:
            series = make_dataset(config)
    if len(series) != config.observations:
        raise ValueError("Dataset length does not match experiment configuration.")
    if config.training_days + config.holdout_days != len(series):
        raise ValueError("Training and holdout sizes must cover the dataset exactly.")
    full_features = frozenset({"weekly", "annual", "lags", "rolling"})

    predictors: dict[str, Callable[[np.ndarray, int], np.ndarray]] = {
        "naive_previous_week": _naive_previous_week,
        "holt_winters_weekly": _holt_winters_forecast,
        "seasonal_linear_regression": lambda history, horizon: _seasonal_regression_forecast(
            history, horizon, full_features, config.annual_period_days
        ),
    }
    model_rows: list[dict] = []
    raw_rows: list[dict] = []
    horizon_rows: list[dict] = []
    for horizon in config.horizons:
        if horizon > config.holdout_days:
            continue
        for model_name, predictor in predictors.items():
            predictions, actual, predicted = _rolling_origin_predictions(
                series,
                training_days=config.training_days,
                horizon=horizon,
                predictor=predictor,
            )
            metrics = calculate_metrics(actual, predicted)
            summary = {
                "model": model_name,
                "horizon_days": horizon,
                "forecast_origins": config.holdout_days - horizon + 1,
                **metrics,
            }
            horizon_rows.append(summary)
            if horizon == config.holdout_days:
                model_rows.append(summary)
            raw_rows.extend(
                {
                    "experiment": "rolling_horizon",
                    "model": model_name,
                    "horizon_days": horizon,
                    **record,
                    "target_date": dates[record["target_index"]] if dates else record["target_index"],
                }
                for record in predictions
            )

    ablations = {
        "full": full_features,
        "remove_weekly": frozenset({"annual", "lags", "rolling"}),
        "remove_annual": frozenset({"weekly", "lags", "rolling"}),
        "remove_lags": frozenset({"weekly", "annual", "rolling"}),
        "remove_rolling": frozenset({"weekly", "annual", "lags"}),
        "remove_weekly_and_annual": frozenset({"lags", "rolling"}),
    }
    ablation_rows: list[dict] = []
    training = series[: config.training_days]
    holdout = series[config.training_days :]
    for name, features in ablations.items():
        predictions = _seasonal_regression_forecast(
            training,
            len(holdout),
            features,
            config.annual_period_days,
        )
        metrics = calculate_metrics(holdout, predictions)
        ablation_rows.append(
            {
                "ablation": name,
                "horizon_days": len(holdout),
                "forecast_origins": 1,
                "training_target_start_index": 365 if len(training) > 365 else max(7, len(training) // 2),
                **metrics,
            }
        )
        raw_rows.extend(
            {
                "experiment": "feature_ablation",
                "variant": name,
                "forecast_origin_index": config.training_days,
                "target_index": config.training_days + day_index,
                "lead_days": day_index + 1,
                "target_date": dates[config.training_days + day_index] if dates else config.training_days + day_index,
                "actual": float(actual),
                "predicted": float(predicted),
            }
            for day_index, (actual, predicted) in enumerate(zip(holdout, predictions, strict=True))
        )

    write_results(
        OUTPUT_DIR,
        "forecast_models",
        model_rows,
        config,
        {
            "split": "chronological",
            "training_days": config.training_days,
            "holdout_days": len(holdout),
            "models": ["previous-week seasonal naive", "additive weekly Holt-Winters", "seasonal linear regression"],
            "holt_winters_gain_grid": [0.2, 0.5, 0.8],
            "forecast_origin_method": "expanding-window rolling origins; past holdout observations become history only after their date",
            "mape_zero_actual_policy": "zero actual values excluded from MAPE denominator; all observations remain in MAE/RMSE",
        },
    )
    feature_names = {
        "weekly": "weekly Fourier terms, harmonics 1-3",
        "annual": "annual Fourier terms, harmonics 1-2",
        "lags": "lags 1, 7, 14, 28, and 365 days",
        "rolling": "trailing means 7, 28, and 365 days",
    }
    write_results(
        OUTPUT_DIR,
        "feature_ablation",
        ablation_rows,
        config,
        {
            "full_model_features": feature_names,
            "baseline_features": ["intercept", "linear time trend"],
            "same_training_rows_for_all_ablations": True,
            "training_target_start_index": 365 if len(training) > 365 else max(7, len(training) // 2),
        },
    )
    write_results(
        OUTPUT_DIR,
        "horizon_sensitivity",
        horizon_rows,
        config,
        {
            "horizons_days": list(config.horizons),
            "forecast_origins_by_horizon": {
                str(horizon): config.holdout_days - horizon + 1
                for horizon in config.horizons
                if horizon <= config.holdout_days
            },
            "forecast_origin_method": "expanding window; each forecast only uses observations strictly before its origin",
        },
    )
    write_results(
        OUTPUT_DIR,
        "forecast_raw_predictions",
        raw_rows,
        config,
        {"observation_unit": "daily demand", "train_test_order": "chronological; no shuffling"},
    )
    return {"forecast_models": model_rows, "feature_ablation": ablation_rows, "horizon_sensitivity": horizon_rows}


if __name__ == "__main__":
    results = run_forecasting_experiments()
    for group, rows in results.items():
        print(f"{group}: {len(rows)} rows -> {OUTPUT_DIR}")
