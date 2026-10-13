"""Read the frozen, paper-aligned HCCR study outputs for analytics clients."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


HCCR_CSV_ARTIFACTS = {
    "forecast_calibration": "forecast_calibration_summary.csv",
    "model_comparison": "forecast_model_ablation.csv",
    "policy_levels": "policy_levels_main.csv",
    "paired_comparisons": "paired_comparisons_main.csv",
    "paired_horizons": "paired_by_horizon_main.csv",
    "gate_rates": "gate_open_rate.csv",
    "sensitivity": "sensitivity_summary.csv",
    "routing": "routing_summary.csv",
    "routing_paired": "routing_paired_vs_reactive.csv",
    "routing_capacity_gap": "routing_capacity_vs_feasibility.csv",
    "forecast_model_paired": "forecast_model_paired.csv",
    "replication": "replication_B.csv",
    "mechanism_primary": "mechanism_confirm_primary.csv",
    "freshness_primary": "freshness_confirm_primary.csv",
    "decision_disagreement": "decision_disagreement_summary.csv",
    "decision_disagreement_primary": "decision_disagreement_primary.csv",
    "decision_disagreement_replication": "decision_disagreement_replication.csv",
    "mechanism_residual_summary": "mechanism_confirm_residual_summary.csv",
    "paired_by_horizon": "paired_by_horizon_main.csv",
    "forecast_model_ablation": "forecast_model_ablation.csv",
    "sensitivity_summary": "sensitivity_summary.csv",
    "routing_summary": "routing_summary.csv",
    "routing_paired_vs_reactive": "routing_paired_vs_reactive.csv",
    "routing_capacity_vs_feasibility": "routing_capacity_vs_feasibility.csv",
    "realdata_delta": "realdata_delta.csv",
    "realdata_forecast_calibration": "realdata_forecast_calibration.csv",
    "realdata_policies": "realdata_policies.csv",
    "comparison_table": "comparison_table.csv",
    "comparison_forecasters": "comparison_forecasters.csv",
    "real_data_policies": "realdata_policies.csv",
    "real_data_delta": "realdata_delta.csv",
    "real_data_calibration": "realdata_forecast_calibration.csv",
}

HCCR_DOWNLOADS = frozenset({
    *HCCR_CSV_ARTIFACTS.values(),
    "operational_main.csv",
    "intervals_main.csv",
    "operational_models.csv",
    "operational_sensitivity.csv",
    "replication_operational.csv",
    "mechanism_confirm_cells.csv",
    "mechanism_confirm_paired.csv",
    "freshness_confirm_cells.csv",
    "freshness_confirm_paired.csv",
    "decision_disagreement_primary.csv",
    "decision_disagreement_replication.csv",
    "routing_instances.csv",
    "config_used.json",
    "experiment_summary.json",
    "realdata_meta.json",
})


def _parse_csv_value(value: str) -> Any:
    """Convert CSV scalars without representing missing/non-finite metrics as zero."""
    stripped = value.strip()
    if not stripped:
        return None
    try:
        number = float(stripped)
    except ValueError:
        return value
    if not math.isfinite(number):
        return None
    return number


class ResearchAnalyticsService:
    """Load immutable HCCR study artifacts; never execute or mutate a study at request time."""

    def __init__(
        self,
        results_dir: Path | None = None,
        config_path: Path | None = None,
    ) -> None:
        repository_root = Path(__file__).resolve().parents[3]
        self._results_dir = results_dir or repository_root / "research_hccr" / "results"
        self._config_path = config_path or repository_root / "research_hccr" / "configs" / "study_config.json"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _read_csv(self, filename: str) -> list[dict[str, Any]] | None:
        path = self._results_dir / filename
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                return [
                    {key: _parse_csv_value(value or "") for key, value in row.items() if key is not None}
                    for row in csv.DictReader(handle)
                ]
        except (OSError, UnicodeDecodeError, csv.Error):
            return None

    def _model_horizon_accuracy(self, seed_count: int) -> list[dict[str, Any]]:
        """Aggregate matched model-ablation test rows over the same ten seeds."""
        lr_rows = self._read_csv("intervals_main.csv") or []
        ablation_rows = self._read_csv("intervals_models.csv") or []
        matched_rows = [
            row for row in lr_rows
            if isinstance(row.get("seed"), (int, float)) and row["seed"] < seed_count
        ]
        grouped: dict[tuple[str, str, float], list[dict[str, Any]]] = {}
        for row in (*matched_rows, *ablation_rows):
            if row.get("noise_scale", 1.0) != 1.0:
                continue
            key = (str(row.get("regime")), str(row.get("model")), float(row.get("h") or 0))
            grouped.setdefault(key, []).append(row)
        summary: list[dict[str, Any]] = []
        for (regime, model, horizon), rows in sorted(grouped.items()):
            output: dict[str, Any] = {
                "regime": regime,
                "model": model,
                "horizon_days": horizon,
                "seed_count": len({row.get("seed") for row in rows}),
            }
            for metric in ("mae", "wape", "cov_hspec", "cov_pooled", "width_hspec", "width_pooled"):
                values = [row[metric] for row in rows if isinstance(row.get(metric), (int, float))]
                output[metric] = sum(values) / len(values) if values else None
            summary.append(output)
        return summary

    def get_hccr_analytics(self) -> dict[str, Any]:
        """Return method, provenance and available summary results for the dashboard."""
        config = self._read_json(self._config_path)
        summary = self._read_json(self._results_dir / "experiment_summary.json")
        real_data = self._read_json(self._results_dir / "realdata_meta.json")
        artifacts: dict[str, list[dict[str, Any]] | None] = {
            key: self._read_csv(filename)
            for key, filename in HCCR_CSV_ARTIFACTS.items()
        }
        required = ("forecast_calibration", "policy_levels", "paired_comparisons", "routing")
        status = "available" if config and all(artifacts[key] is not None for key in required) else "partial"
        missing = [
            HCCR_CSV_ARTIFACTS[key]
            for key, rows in artifacts.items()
            if rows is None
        ]
        return {
            "status": status,
            "missing_artifacts": missing,
            "method_discrepancies": [
                "The latest paper specifies base capacity ceil(kappa * initial-training mean); the supplied aggregate CSVs were generated by source that used nearest-integer np.round. The recomputed single-origin decision now uses the paper's ceiling rule, but aggregate policy, cost and routing outputs have not been regenerated."
            ],
            "configuration": config,
            "summary": summary,
            "real_data_metadata": real_data,
            "provenance": {
                "simulation": "Synthetic multi-region, four-regime simulation; not operational data.",
                "real_data": "Descriptive UCI Bike Sharing check; supply-censored rentals, no routing evaluation.",
                "created_at": None,
                "created_at_note": "The archived experiment outputs do not record an execution timestamp.",
                "paper_method": "The single-origin recomputation follows the paper's ceiling rule; archived aggregates retain the supplied source's nearest-integer rounding.",
                "paper_capacity_rule": "ceil(kappa * mean demand over the initial fit period)",
                "archived_capacity_rule": "nearest-integer np.round(kappa * mean demand over the initial fit period)",
            },
            "results": artifacts,
            "model_horizon_accuracy": self._model_horizon_accuracy(
                int((config or {}).get("n_seeds_forecast_models", 0))
            ),
            "downloads": sorted(HCCR_DOWNLOADS),
        }

    def get_hccr_decision(
        self,
        *,
        regime: str,
        seed: int,
        region: int,
        horizon_days: int,
        origin: int,
    ) -> dict[str, Any]:
        """Recompute one frozen test-origin reservation decision from the supplied simulator."""
        import numpy as np

        from research_hccr.calibrate import residuals, window_h, window_pooled
        from research_hccr.policies import MIN_RESIDUALS
        from research_hccr.study import load_config, make_pool, run_sim

        config = load_config(str(self._config_path))
        if regime not in config["regimes"]:
            raise ValueError("Unsupported simulation regime.")
        if horizon_days not in config["horizons"]:
            raise ValueError("Unsupported research horizon.")
        if not 0 <= seed < config["n_seeds_main"]:
            raise ValueError("Seed is outside the frozen primary study range.")
        if not 0 <= region < config["n_regions"]:
            raise ValueError("Region index is outside the frozen simulation.")
        test_start = config["t_test_start"]
        last_origin = config["t_test_last_origin"]
        if not test_start <= origin <= last_origin or origin + horizon_days >= config["T"]:
            raise ValueError("Origin is outside the frozen test period for this horizon.")

        simulation, demand, forecasts = run_sim(
            regime,
            seed,
            config,
            model="lr",
            keep_decisions=True,
        )
        decisions = simulation[2]
        if forecasts is None or decisions is None:
            raise ValueError("The frozen simulation did not produce reservation decisions.")

        residual_by_horizon = residuals(demand, forecasts)
        calibration_start = config["t_calibration_start"]
        window_size = config["calibration_window"]
        horizon_residuals = window_h(
            residual_by_horizon[horizon_days][region],
            horizon_days,
            origin,
            window_size,
            calibration_start,
        )
        pooled_residuals = window_pooled(
            residual_by_horizon,
            region,
            config["horizons"],
            origin,
            window_size,
            calibration_start,
        )
        pool = make_pool(config)
        base_capacity = float(decisions["A"][region])
        point_forecast = float(forecasts[horizon_days][region, origin])
        actual_demand = float(demand[region, origin + horizon_days])
        shortage_penalty = float(config["shortage_penalty"])
        decisions_by_policy: dict[str, dict[str, Any]] = {}

        for policy, residual_window in (
            ("hspec", horizon_residuals),
            ("pooled", pooled_residuals),
        ):
            selected_index = int(decisions["S"][policy][horizon_days][region, origin])
            if selected_index < 0:
                raise ValueError("The selected origin has no eligible reservation decision.")
            reserved_capacity = float(pool.cap[selected_index])
            vehicle_counts = pool.counts[selected_index]
            scenarios = np.maximum(0.0, point_forecast + residual_window)
            expected_shortage = (
                float(np.maximum(scenarios - base_capacity - reserved_capacity, 0.0).mean())
                if len(scenarios)
                else None
            )
            reservation_cost = float(pool.cost[selected_index])
            expected_total_cost = (
                reservation_cost + shortage_penalty * expected_shortage
                if expected_shortage is not None
                else None
            )
            gate_open = bool(decisions["gates"][policy][horizon_days])
            validation_cost = float(decisions["validation_costs"][policy][horizon_days])
            reactive_validation_cost = float(
                decisions["validation_costs"]["reactive"][horizon_days]
            )
            low, high = (0.1, 0.9)
            calibrated_interval = None
            residual_sd = None
            if len(residual_window) >= MIN_RESIDUALS:
                calibrated_interval = [
                    point_forecast + float(np.quantile(residual_window, low)),
                    point_forecast + float(np.quantile(residual_window, high)),
                ]
                residual_sd = float(np.std(residual_window, ddof=1))
            realized_shortage = max(
                actual_demand - base_capacity - reserved_capacity,
                0.0,
            )
            decisions_by_policy[policy] = {
                "policy": "HCCR (horizon-specific)" if policy == "hspec" else "Pooled residuals",
                "residual_count": int(len(residual_window)),
                "minimum_residual_count": MIN_RESIDUALS,
                "calibration_status": "calibrated" if len(residual_window) >= MIN_RESIDUALS else "insufficient_calibration",
                "residual_standard_deviation": residual_sd,
                "central_80_interval_units": calibrated_interval,
                "gate_open": gate_open,
                "validation_mean_total_cost": validation_cost,
                "validation_reactive_mean_total_cost": reactive_validation_cost,
                "gate_explanation": (
                    "The policy passed its validation-only mean-cost gate."
                    if gate_open
                    else "The policy's validation-only mean cost was not below reactive; reservation was gated off."
                ),
                "vehicle_counts_by_capacity": [
                    {"capacity_units": int(capacity), "count": int(count)}
                    for capacity, count in zip(config["reserve_vehicle_capacities"], vehicle_counts)
                    if count
                ],
                "reserved_vehicle_count": int(pool.nveh[selected_index]),
                "reserved_capacity_units": reserved_capacity,
                "reservation_cost": reservation_cost,
                "expected_shortage_units": expected_shortage,
                "expected_total_objective": expected_total_cost,
                "realized_test_demand_units": actual_demand,
                "realized_test_shortage_units": realized_shortage,
                "realized_test_total_cost": reservation_cost + shortage_penalty * realized_shortage,
            }

        return {
            "provenance": "Synthetic simulation; not operational fleet data.",
            "regime": regime,
            "seed": seed,
            "region_index": region,
            "horizon_days": horizon_days,
            "origin_index": origin,
            "model": "Direct-horizon seasonal linear regression",
            "point_forecast_units": point_forecast,
            "base_capacity_units": base_capacity,
            "base_capacity_rule": "ceil(kappa * mean demand over the initial fit period)",
            "shortage_penalty": shortage_penalty,
            "scenario_demand_unit": "Synthetic load units; not calibrated to live vehicle units.",
            "calibration_residual_eligibility": "Residual target origin+horizon must be observed by decision origin; newest eligible residuals only.",
            "policies": decisions_by_policy,
        }

    def get_download_path(self, filename: str) -> Path | None:
        """Return an allowlisted artifact path, or None for absent/unsupported names."""
        if filename not in HCCR_DOWNLOADS:
            return None
        path = (self._results_dir / filename).resolve()
        if path.parent != self._results_dir.resolve() or not path.is_file():
            return None
        return path