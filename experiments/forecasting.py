"""Forecast-model, ablation, and horizon sensitivity experiments."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from experiments.common import (
    ExperimentConfig,
    calculate_metrics,
    chronological_split,
    make_dataset,
    write_results,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "results"


def _naive_forecast(history: np.ndarray, horizon: int) -> np.ndarray:
    return np.full(horizon, float(history[-1]))


def _holt_winters_forecast(history: np.ndarray, horizon: int) -> np.ndarray:
    """Fit additive weekly Holt-Winters with deterministic grid-selected gains."""
    period = 7
    if len(history) <= period * 2:
        return _naive_forecast(history, horizon)

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


def _feature_row(history: list[float], time_index: int, features: frozenset[str]) -> list[float]:
    row = [1.0, time_index / 365.0]
    if "weekly" in features:
        for harmonic in (1, 2, 3):
            angle = 2.0 * np.pi * time_index * harmonic / 7.0
            row.extend((float(np.sin(angle)), float(np.cos(angle))))
    if "annual" in features:
        for harmonic in (1, 2):
            angle = 2.0 * np.pi * time_index * harmonic / 365.0
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
) -> np.ndarray:
    """Fit a deterministic feature regression and recursively forecast."""
    history = [float(value) for value in training]
    first_index = 365 if len(training) > 365 else 28
    rows = [_feature_row(history[:index], index, features) for index in range(first_index, len(training))]
    targets = training[first_index:]
    coefficients, *_ = np.linalg.lstsq(np.asarray(rows), targets, rcond=None)
    predictions: list[float] = []
    for time_index in range(len(training), len(training) + horizon):
        row = np.asarray(_feature_row(history, time_index, features))
        prediction = max(0.0, float(row @ coefficients))
        predictions.append(prediction)
        history.append(prediction)
    return np.asarray(predictions)


def run_forecasting_experiments(
    config: ExperimentConfig | None = None,
) -> dict[str, list[dict]]:
    """Run model comparison, feature ablation, and horizon sensitivity."""
    config = config or ExperimentConfig()
    series = make_dataset(config)
    training, holdout = chronological_split(series, config.training_days)
    holdout = holdout[: config.holdout_days]
    full_features = frozenset({"weekly", "annual", "lags", "rolling"})

    model_rows: list[dict] = []
    raw_rows: list[dict] = []
    for model_name, predictor in (
        ("naive_last_value", lambda size: _naive_forecast(training, size)),
        ("holt_winters_weekly", lambda size: _holt_winters_forecast(training, size)),
        ("seasonal_linear_regression", lambda size: _seasonal_regression_forecast(training, size, full_features)),
    ):
        predictions = predictor(len(holdout))
        model_rows.append({"model": model_name, "horizon_days": len(holdout), **calculate_metrics(holdout, predictions)})
        raw_rows.extend(
            {
                "experiment": "forecast_model_comparison",
                "variant": model_name,
                "holdout_day": day_index + 1,
                "actual": float(actual),
                "predicted": float(predicted),
            }
            for day_index, (actual, predicted) in enumerate(zip(holdout, predictions, strict=True))
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
    for name, features in ablations.items():
        predictions = _seasonal_regression_forecast(training, len(holdout), features)
        ablation_rows.append({"ablation": name, "horizon_days": len(holdout), **calculate_metrics(holdout, predictions)})
        raw_rows.extend(
            {
                "experiment": "feature_ablation",
                "variant": name,
                "holdout_day": day_index + 1,
                "actual": float(actual),
                "predicted": float(predicted),
            }
            for day_index, (actual, predicted) in enumerate(zip(holdout, predictions, strict=True))
        )

    horizon_rows: list[dict] = []
    for horizon in config.horizons:
        if horizon > len(holdout):
            continue
        actual = holdout[:horizon]
        for model_name, predictions in (
            ("naive_last_value", _naive_forecast(training, horizon)),
            ("holt_winters_weekly", _holt_winters_forecast(training, horizon)),
            ("seasonal_linear_regression", _seasonal_regression_forecast(training, horizon, full_features)),
        ):
            horizon_rows.append({"model": model_name, "horizon_days": horizon, **calculate_metrics(actual, predictions)})
            raw_rows.extend(
                {
                    "experiment": "horizon_sensitivity",
                    "variant": model_name,
                    "horizon_days": horizon,
                    "holdout_day": day_index + 1,
                    "actual": float(actual_value),
                    "predicted": float(predicted_value),
                }
                for day_index, (actual_value, predicted_value) in enumerate(
                    zip(actual, predictions, strict=True)
                )
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
            "models": ["last observation naive", "additive weekly Holt-Winters" , "seasonal linear regression"],
            "holt_winters_gain_grid": [0.2, 0.5, 0.8],
            "mape_zero_actual_policy": "zero observations excluded",
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
        {"full_model_features": feature_names, "baseline_features": ["intercept", "linear time trend"]},
    )
    write_results(
        OUTPUT_DIR,
        "horizon_sensitivity",
        horizon_rows,
        config,
        {"horizons_days": list(config.horizons), "forecast_origins": "single fixed origin at end of training window"},
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
