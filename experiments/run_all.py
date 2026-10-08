"""Run the reproducible forecast, ablation, horizon, and routing experiments."""

from __future__ import annotations

import json

from experiments.forecasting import run_forecasting_experiments
from experiments.routing import run_paired_routing_experiment


def main() -> None:
    """Run each experiment family and print concise output locations."""
    forecast_results = run_forecasting_experiments()
    routing_results = run_paired_routing_experiment()
    summary = {
        "forecast_model_rows": len(forecast_results["forecast_models"]),
        "ablation_rows": len(forecast_results["feature_ablation"]),
        "horizon_rows": len(forecast_results["horizon_sensitivity"]),
        "paired_routing_scenarios": len(routing_results),
        "result_directory": "experiments/results",
        "interpretation": (
            "Routing arms use identical confirmed inputs; any measured route-metric "
            "difference is an implementation error, while advisory interventions are reported separately."
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
