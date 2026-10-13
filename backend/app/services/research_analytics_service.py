"""Read the frozen, paper-aligned HCCR study outputs for analytics clients."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


HCCR_ARTIFACT_SPECS = (
    ("forecast_calibration", "forecast_calibration_summary.csv", True, ("regime", "h", "mae", "wape", "cov_hspec", "cov_pooled", "width_hspec", "width_pooled")),
    ("model_comparison", "forecast_model_ablation.csv", False, ("model", "regime", "mae", "wape")),
    ("policy_levels", "policy_levels_main.csv", True, ("policy", "regime", "cost_total", "cost_reserve", "unmet")),
    ("paired_comparisons", "paired_comparisons_main.csv", True, ("horizons", "comparison", "regime", "n", "mean_delta", "ci_lo", "ci_hi")),
    ("paired_horizons", "paired_by_horizon_main.csv", True, ("h", "comparison", "regime", "n", "mean_delta", "ci_lo", "ci_hi")),
    ("gate_rates", "gate_open_rate.csv", False, ("regime", "policy", "h", "gate_open")),
    ("sensitivity", "sensitivity_summary.csv", False, ("param", "value", "regime", "comparator", "n", "mean_delta", "ci_lo", "ci_hi")),
    ("routing", "routing_summary.csv", True, ("policy", "n_instances", "feasibility_rate", "mean_distance_feasible_km")),
    ("routing_paired", "routing_paired_vs_reactive.csv", False, ("policy", "mean_feas_gain_vs_reactive")),
    ("routing_capacity_gap", "routing_capacity_vs_feasibility.csv", False, ("policy", "n_agg_ok", "routing_infeasible_despite_agg_ok")),
    ("forecast_model_paired", "forecast_model_paired.csv", False, ("regime", "comparison", "n", "mean_delta", "ci_lo", "ci_hi")),
    ("replication", "replication_B.csv", False, ("regime", "horizons", "n", "mean_delta", "ci_lo", "ci_hi")),
    ("mechanism_primary", "mechanism_confirm_primary.csv", False, ("contrast", "n_sims", "mean", "ci95_lo", "ci95_hi", "p_holm")),
    ("freshness_primary", "freshness_confirm_primary.csv", False, ("contrast", "n_sims", "mean", "ci95_lo", "ci95_hi", "p_holm")),
    ("decision_disagreement", "decision_disagreement_summary.csv", False, ("sample", "decisions", "regime", "horizons", "n_sims", "mean", "ci_lo", "ci_hi")),
    ("mechanism_residual_summary", "mechanism_confirm_residual_summary.csv", False, ("phi", "h")),
    ("real_data_delta", "realdata_delta.csv", False, ("pi", "h", "delta", "ci_lo", "ci_hi", "n_origins")),
    ("real_data_calibration", "realdata_forecast_calibration.csv", False, ("h", "mae", "wape", "cov_hspec", "cov_pooled")),
    ("real_data_policies", "realdata_policies.csv", False, ("pi", "h", "policy", "total_cost", "unmet")),
    ("comparison_table", "comparison_table.csv", False, ("scope", "regimes", "horizons", "policy", "cost_total", "cost_total_lo", "cost_total_hi", "unmet", "route_feas")),
    ("comparison_forecasters", "comparison_forecasters.csv", False, ("forecaster", "n_units", "cost", "lo", "hi", "wape")),
    ("model_horizon_lr_source", "intervals_main.csv", False, ("regime", "seed", "model", "noise_scale", "h", "mae", "wape")),
    ("model_horizon_ablation_source", "intervals_models.csv", False, ("regime", "seed", "model", "noise_scale", "h", "mae", "wape")),
)

HCCR_SUMMARY_FILES = frozenset(spec[1] for spec in HCCR_ARTIFACT_SPECS)
HCCR_REQUIRED_FILES = frozenset(spec[1] for spec in HCCR_ARTIFACT_SPECS if spec[2])
if len(HCCR_SUMMARY_FILES) != len(HCCR_ARTIFACT_SPECS):
    raise RuntimeError("HCCR artifact manifest contains duplicate filenames.")

LEGACY_JSON_SPECS = (
    ("legacy_forecast_models", "forecast_models.json"),
    ("legacy_horizon_sensitivity", "horizon_sensitivity.json"),
    ("legacy_feature_ablation", "feature_ablation.json"),
    ("legacy_cvrp_benchmark", "cvrp_benchmark.json"),
    ("legacy_hgfc_advisory", "hgfc_advisory.json"),
    ("legacy_reactive_vs_hgfc", "reactive_vs_hgfc.json"),
)


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

    def _read_csv(
        self,
        filename: str,
        required_columns: tuple[str, ...] = (),
    ) -> list[dict[str, Any]] | None:
        return self._read_csv_path(self._results_dir / filename, required_columns)

    @staticmethod
    def _read_csv_path(
        path: Path,
        required_columns: tuple[str, ...] = (),
    ) -> list[dict[str, Any]] | None:
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or not set(required_columns).issubset(reader.fieldnames):
                    return None
                parsed_rows = []
                for row in reader:
                    if None in row or any(value is None for value in row.values()):
                        return None
                    parsed_rows.append({
                        key: _parse_csv_value(value or "")
                        for key, value in row.items()
                        if key is not None
                    })
                if not parsed_rows:
                    return None
                return parsed_rows
        except (OSError, UnicodeDecodeError, csv.Error):
            return None

    @staticmethod
    def _validate_csv_path(path: Path) -> bool:
        """Validate a discovered raw CSV's header and row structure without retaining all rows."""
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                header = next(reader, None)
                if not header or any(not name for name in header) or len(header) != len(set(header)):
                    return False
                first_row = next(reader, None)
                if first_row is None or len(first_row) != len(header):
                    return False
                return all(len(row) == len(header) for row in reader)
        except (OSError, UnicodeDecodeError, csv.Error):
            return False

    def get_artifact_manifest(self) -> list[dict[str, Any]]:
        """List actual package artifacts once each and flag required, optional and malformed files."""
        specs_by_filename = {filename: (key, required, columns) for key, filename, required, columns in HCCR_ARTIFACT_SPECS}
        result_root = self._results_dir.resolve()
        package_root = result_root.parent
        repository_root = package_root.parent
        package_files: dict[str, Path] = {}
        for path in result_root.iterdir() if result_root.is_dir() else ():
            if path.is_file() and path.suffix.lower() in {".csv", ".json"}:
                package_files[path.name] = path
        package_files["study_config.json"] = self._config_path.resolve()
        for name in ("day.csv", "hour.csv"):
            source_path = package_root / "realdata" / "data" / name
            package_files[f"research_hccr/realdata/data/{name}"] = source_path
        legacy_root = repository_root / "experiments" / "results"
        for _key, name in LEGACY_JSON_SPECS:
            package_files[f"experiments/results/{name}"] = legacy_root / name

        manifest: list[dict[str, Any]] = []
        for filename, spec in specs_by_filename.items():
            result_key, required, columns = spec
            path = package_files.get(filename)
            parsed = self._read_csv_path(path, columns) if path is not None and path.is_file() else None
            manifest.append({
                "filename": filename,
                "result_key": result_key,
                "required": required,
                "status": "available" if parsed is not None else "missing" if path is None or not path.is_file() else "malformed",
                "content_type": "text/csv",
                "size_bytes": path.stat().st_size if path is not None and path.is_file() else None,
            })

        config_fields = {"T", "n_regions", "t_calibration_start", "t_validation_start", "t_test_start", "horizons", "n_seeds_main"}
        config_payload = self._read_json(self._config_path)
        config_valid = config_payload is not None and config_fields.issubset(config_payload)
        manifest.append({
            "filename": "study_config.json",
            "result_key": "configuration",
            "required": True,
            "status": "available" if config_valid else "missing" if not self._config_path.is_file() else "malformed",
            "content_type": "application/json",
            "size_bytes": self._config_path.stat().st_size if self._config_path.is_file() else None,
        })

        represented = set(specs_by_filename) | {"study_config.json"}
        for filename, path in sorted(package_files.items()):
            if filename in represented:
                continue
            if not path.is_file():
                parsed_ok = False
                artifact_status = "missing"
            elif path.suffix.lower() == ".json":
                json_payload = self._read_json(path)
                parsed_ok = json_payload is not None and (
                    filename not in {f"experiments/results/{name}" for _, name in LEGACY_JSON_SPECS}
                    or isinstance(json_payload.get("results"), list)
                )
                artifact_status = "available" if parsed_ok else "malformed"
            else:
                parsed_ok = self._validate_csv_path(path)
                artifact_status = "available" if parsed_ok else "malformed"
            manifest.append({
                "filename": filename,
                "result_key": next((key for key, name in LEGACY_JSON_SPECS if filename == f"experiments/results/{name}"), None),
                "required": False,
                "status": artifact_status,
                "content_type": "application/json" if path.suffix.lower() == ".json" else "text/csv",
                "size_bytes": path.stat().st_size if path.is_file() else None,
            })
        return sorted(manifest, key=lambda item: item["filename"])

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

    def _policy_horizon_metrics(self) -> list[dict[str, Any]]:
        """Summarize archived gated test policy costs by regime and horizon."""
        source = self._read_csv("operational_main.csv", ("regime", "seed", "h", "policy", "variant", "cost_total"))
        if source is None:
            return []
        groups: dict[tuple[str, float, str], list[dict[str, Any]]] = {}
        for row in source:
            if row.get("variant") != "gated":
                continue
            regime = row.get("regime")
            horizon = row.get("h")
            policy = row.get("policy")
            if not isinstance(regime, str) or not isinstance(horizon, (int, float)) or not isinstance(policy, str):
                continue
            groups.setdefault((regime, float(horizon), policy), []).append(row)

        metrics = ("cost_total", "cost_reserve", "unmet", "n_reserved", "shortage_day_rate")
        output: list[dict[str, Any]] = []
        for (regime, horizon, policy), rows in sorted(groups.items()):
            item: dict[str, Any] = {
                "regime": regime,
                "horizon_days": horizon,
                "policy": policy,
                "seed_count": len({row.get("seed") for row in rows}),
            }
            for metric in metrics:
                values = [row[metric] for row in rows if isinstance(row.get(metric), (int, float))]
                item[metric] = sum(values) / len(values) if values else None
            output.append(item)
        return output

    def get_hccr_analytics(self) -> dict[str, Any]:
        """Return method, provenance and available summary results for the dashboard."""
        config = self._read_json(self._config_path)
        summary = self._read_json(self._results_dir / "experiment_summary.json")
        real_data = self._read_json(self._results_dir / "realdata_meta.json")
        manifest = self.get_artifact_manifest()
        artifacts = {
            key: self._read_csv(filename, columns)
            for key, filename, _required, columns in HCCR_ARTIFACT_SPECS
        }
        missing_required = sorted(
            row["filename"] for row in manifest
            if row["required"] and row["status"] != "available"
        )
        unavailable_optional = sorted(
            row["filename"] for row in manifest
            if not row["required"] and row["status"] != "available"
        )
        status = "available" if config and not missing_required else "partial"
        repository_root = self._results_dir.resolve().parent.parent
        legacy_results_dir = repository_root / "experiments" / "results"
        legacy_artifacts: dict[str, dict[str, Any] | None] = {}
        legacy_forecast_artifacts = []
        for result_key, filename in LEGACY_JSON_SPECS:
            path = legacy_results_dir / filename
            payload = self._read_json(path)
            valid = payload is not None and isinstance(payload.get("results"), list)
            legacy_artifacts[result_key] = payload if valid else None
            if valid and result_key in {"legacy_forecast_models", "legacy_horizon_sensitivity"}:
                legacy_forecast_artifacts.append({"filename": filename, "results": payload["results"]})

        return {
            "status": status,
            "missing_artifacts": missing_required,
            "unavailable_optional_artifacts": unavailable_optional,
            "artifact_manifest": manifest,
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
            "legacy_artifacts": legacy_artifacts,
            "legacy_forecast_artifacts": legacy_forecast_artifacts,
            "model_horizon_accuracy": self._model_horizon_accuracy(
                int((config or {}).get("n_seeds_forecast_models", 0))
            ),
            "policy_horizon_metrics": self._policy_horizon_metrics(),
            "downloads": sorted(
                row["filename"] for row in manifest if row["status"] == "available"
            ),
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
        entry = next(
            (item for item in self.get_artifact_manifest() if item["filename"] == filename),
            None,
        )
        if entry is None or entry["status"] != "available":
            return None
        research_package = self._results_dir.parent.resolve()
        repository_root = research_package.parent
        if filename == "study_config.json":
            path = self._config_path.resolve()
        elif filename.startswith("research_hccr/realdata/data/"):
            path = (repository_root / filename).resolve()
        elif filename.startswith("experiments/results/"):
            path = (repository_root / filename).resolve()
        else:
            path = (self._results_dir / filename).resolve()
        if repository_root not in path.parents or not path.is_file():
            return None
        return path