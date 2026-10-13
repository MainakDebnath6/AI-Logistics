from __future__ import annotations

from pathlib import Path
import csv
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.api.analytics import (
    download_hccr_research_artifact,
    get_hccr_research_endpoint,
    get_hccr_reservation_decision_endpoint,
    get_research_analytics,
    summarize_synthetic_demand,
    summarize_synthetic_demand_rows,
)
from app.services.research_analytics_service import ResearchAnalyticsService


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None


class FakeSession:
    def __init__(self):
        self.rows = [
            {"date": "2024-01-01", "demand": 100.0},
            {"date": "2024-01-02", "demand": 110.0},
            {"date": "2024-01-03", "demand": 120.0},
        ]

    def execute(self, statement, params=None):
        text = str(statement)
        if "COUNT(*)" in text:
            return FakeResult([{"count": 3}])
        if "AVG" in text:
            return FakeResult([{"avg": 110.0}])
        if "MIN" in text:
            return FakeResult([{"min_demand": 100.0}])
        if "MAX" in text:
            return FakeResult([{"max_demand": 120.0}])
        return FakeResult(self.rows)


def test_summarize_synthetic_demand_returns_ordered_metrics():
    result = summarize_synthetic_demand_rows(
        [
            {"date": "2024-01-03", "demand": 120.0},
            {"date": "2024-01-01", "demand": 100.0},
            {"date": "2024-01-02", "demand": 110.0},
        ]
    )

    assert result["count"] == 3
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2024-01-03"
    assert result["average_demand"] == 110.0
    assert result["observations"][0]["demand"] == 100.0


def test_synthetic_demand_prefers_populated_database_rows():
    class Database:
        def execute(self, statement, _params=None):
            if "COUNT(*)" in str(statement):
                return FakeResult([{"count": 2}])
            return FakeResult([
                {"date": "2025-01-01", "demand": 12.5},
                {"date": "2025-01-02", "demand": 18.5},
            ])

    result = summarize_synthetic_demand(Database())
    assert result["source"] == "public.synthetic_demand"
    assert result["observation_count"] == 2
    assert result["average_demand"] == 15.5
    assert result["split"] == {
        "train_observations": 2,
        "holdout_observations": 0,
        "chronological": True,
    }


@pytest.mark.parametrize("database_error", [
    OperationalError("query", {}, OSError("connection refused")),
    ProgrammingError("query", {}, SimpleNamespace(sqlstate="42P01")),
])
def test_synthetic_demand_falls_back_to_csv_when_database_is_unavailable(database_error):
    class Database:
        def execute(self, _statement, _params=None):
            raise database_error

    result = summarize_synthetic_demand(Database())
    assert result["source"] == "data/raw/synthetic_demand.csv"
    assert result["count"] == result["observation_count"] == 730
    assert result["start_date"] == "2024-01-01"
    assert result["end_date"] == "2025-12-30"
    assert result["split"]["train_observations"] == 670
    assert result["split"]["holdout_observations"] == 60
    assert result["fallback_reason"] == "The public.synthetic_demand table could not be read."


def test_empty_database_uses_checked_in_synthetic_csv():
    class EmptyDatabase:
        def execute(self, statement, _params=None):
            return FakeResult([{"count": 0}]) if "COUNT(*)" in str(statement) else FakeResult([])

    result = summarize_synthetic_demand(EmptyDatabase())
    assert result["source"] == "data/raw/synthetic_demand.csv"
    assert result["observation_count"] == 730
    assert result["fallback_reason"] == "The public.synthetic_demand table is empty."


def test_unrelated_database_failure_is_not_hidden_by_csv_fallback():
    class BrokenDatabase:
        def execute(self, _statement, _params=None):
            raise RuntimeError("unexpected query bug")

    with pytest.raises(HTTPException) as error:
        summarize_synthetic_demand(BrokenDatabase())
    assert error.value.status_code == 503
    assert "Synthetic demand dataset is unavailable" in error.value.detail


def test_missing_csv_returns_diagnostic_without_fabricated_metrics(tmp_path, monkeypatch):
    from app.api import analytics

    monkeypatch.setattr(analytics, "SYNTHETIC_DEMAND_CSV_PATH", tmp_path / "missing.csv")
    result = summarize_synthetic_demand()
    assert result["source"] == "unavailable"
    assert result["observation_count"] == 0
    assert result["average_demand"] is None
    assert result["error"].startswith("Synthetic demand CSV is missing")


def test_get_research_analytics_uses_real_experiment_results():
    payload = get_research_analytics()

    assert payload["synthetic_demand"]["count"] > 0
    assert payload["forecast_models"]["results"]
    assert payload["horizon_sensitivity"]["results"]
    assert payload["feature_ablation"]["results"]
    assert payload["cvrp_benchmark"]["results"]
    assert payload["hgfc_advisory"]["results"]
    assert payload["reactive_vs_hgfc"]["results"]
    assert payload["reactive_vs_hgfc"]["methodology"]["routing_arms"].startswith("identical confirmed demand")


def test_runtime_image_declares_research_artifact_inputs():
    repository_root = Path(__file__).resolve().parents[2]
    dockerfile = (repository_root / "Dockerfile").read_text(encoding="utf-8")

    for filename in (
        "forecast_models.json",
        "horizon_sensitivity.json",
        "feature_ablation.json",
        "cvrp_benchmark.json",
        "hgfc_advisory.json",
        "reactive_vs_hgfc.json",
    ):
        assert f"COPY experiments/results/{filename} ./experiments/results/{filename}" in dockerfile
        assert (repository_root / "experiments/results" / filename).is_file()
    assert "COPY data/raw/synthetic_demand.csv ./data/raw/synthetic_demand.csv" in dockerfile
    assert "COPY research_hccr ./research_hccr" in dockerfile
    assert "test -f research_hccr/realdata/data/day.csv" in dockerfile
    assert "test -f research_hccr/results/operational_main.csv" in dockerfile
    assert (repository_root / "research_hccr/configs/study_config.json").is_file()
    assert (repository_root / "research_hccr/study.py").is_file()
    for filename in ("forecast_calibration_summary.csv", "operational_main.csv", "routing_summary.csv"):
        assert (repository_root / "research_hccr/results" / filename).is_file()
    for filename in ("day.csv", "hour.csv"):
        assert (repository_root / "research_hccr/realdata/data" / filename).is_file()


def test_public_dataset_response_uses_bundled_daily_bike_sharing_rows():
    result = ResearchAnalyticsService().get_hccr_analytics()["public_dataset"]

    assert result["status"] == "available"
    assert result["source_path"] == "research_hccr/realdata/data/day.csv"
    assert result["observation_count"] == result["expected_observation_count"] == 731
    assert result["start_date"] == "2011-01-01"
    assert result["end_date"] == "2012-12-31"
    assert len(result["monthly_observations"]) == 24
    assert result["monthly_observations"][0]["month"] == "2011-01"
    assert result["monthly_observations"][0]["total_rentals"] == 38189
    assert sum(row["total_rentals"] for row in result["monthly_observations"]) == result["total_rentals"]
    assert result["mean_daily_rentals"] > 0


def test_research_artifact_loader_reports_missing_and_malformed_files(tmp_path, monkeypatch):
    from app.api import analytics

    monkeypatch.setattr(analytics, "RESEARCH_RESULTS_DIR", tmp_path)
    missing = analytics._load_research_result_file("missing.json")
    assert missing["results"] == []
    assert "unavailable" in missing["error"]

    (tmp_path / "broken.json").write_text("{broken", encoding="utf-8")
    malformed = analytics._load_research_result_file("broken.json")
    assert malformed["results"] == []
    assert "could not be read" in malformed["error"]

    (tmp_path / "wrong-shape.json").write_text("[]", encoding="utf-8")
    invalid = analytics._load_research_result_file("wrong-shape.json")
    assert invalid["results"] == []
    assert "invalid structure" in invalid["error"]


def test_research_artifact_loader_resolves_paths_from_module_not_current_directory(tmp_path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(tmp_path)
    result = ResearchAnalyticsService().get_hccr_analytics()

    assert result["status"] == "available"
    assert any(
        row["filename"] == "forecast_calibration_summary.csv" and row["status"] == "available"
        for row in result["artifact_manifest"]
    )
    assert (repository_root / "research_hccr/results/forecast_calibration_summary.csv").is_file()


def test_hccr_dashboard_metrics_match_frozen_result_csvs():
    repository_root = Path(__file__).resolve().parents[2]
    service = ResearchAnalyticsService()
    result = service.get_hccr_analytics()
    with (repository_root / "research_hccr/results/forecast_calibration_summary.csv").open(
        newline="", encoding="utf-8"
    ) as handle:
        source = next(
            row for row in csv.DictReader(handle)
            if row["regime"] == "ar" and row["h"] == "1"
        )

    assert result["status"] == "available"
    dashboard_row = next(
        row for row in result["results"]["forecast_calibration"]
        if row["regime"] == "ar" and row["h"] == 1.0
    )
    assert dashboard_row["cov_hspec"] == pytest.approx(float(source["cov_hspec"]))
    assert dashboard_row["width_pooled"] == pytest.approx(float(source["width_pooled"]))
    assert result["configuration"]["calibration_window"] == 200
    assert result["provenance"]["created_at"] is None
    assert "np.round" in result["method_discrepancies"][0]
    model_row = next(
        row for row in result["model_horizon_accuracy"]
        if row["regime"] == "ar" and row["model"] == "lr" and row["horizon_days"] == 7.0
    )
    assert model_row["seed_count"] == 10
    assert result["legacy_artifacts"]["legacy_forecast_models"]["results"]
    assert result["legacy_artifacts"]["legacy_feature_ablation"]["results"]
    aggregate_forecasters = result["results"]["comparison_forecasters"]
    assert {row["forecaster"] for row in aggregate_forecasters} == {"lr", "hw", "naive"}
    lr_aggregate = next(row for row in aggregate_forecasters if row["forecaster"] == "lr")
    assert lr_aggregate["n_units"] == 40.0
    assert lr_aggregate["cost"] == pytest.approx(13.153126585216047)
    assert lr_aggregate["wape"] == pytest.approx(0.045664144460362995)
    aggregate = next(
        row for row in result["results"]["comparison_table"]
        if row["scope"] == "aggregate" and row["policy"] == "hspec"
    )
    assert aggregate["cost_total"] == pytest.approx(12.9575632714)
    assert any(
        row["filename"] == "experiments/results/forecast_models.json"
        and row["result_key"] == "legacy_forecast_models"
        and row["status"] == "available"
        for row in result["artifact_manifest"]
    )


def test_hccr_manifest_is_unique_complete_and_ar_h7_rows_are_present():
    repository_root = Path(__file__).resolve().parents[2]
    service = ResearchAnalyticsService()
    payload = service.get_hccr_analytics()
    manifest = payload["artifact_manifest"]
    filenames = [entry["filename"] for entry in manifest]
    actual_outputs = {
        path.name for path in (repository_root / "research_hccr/results").iterdir()
        if path.is_file() and path.suffix.lower() in {".csv", ".json"}
    }

    assert len(filenames) == len(set(filenames))
    assert actual_outputs.issubset(set(filenames))
    assert all(entry["status"] == "available" for entry in manifest if entry["filename"] in actual_outputs)
    assert payload["missing_artifacts"] == []
    assert len(payload["unavailable_optional_artifacts"]) == len(set(payload["unavailable_optional_artifacts"]))
    assert set(payload["downloads"]) == {
        entry["filename"] for entry in manifest if entry["status"] == "available"
    }

    ar_h7_models = [
        row for row in payload["model_horizon_accuracy"]
        if row["regime"] == "ar" and row["horizon_days"] == 7.0
    ]
    assert {row["model"] for row in ar_h7_models} == {"lr", "naive", "hw"}
    assert all(row["mae"] is not None for row in ar_h7_models)
    ar_h7_calibration = next(
        row for row in payload["results"]["forecast_calibration"]
        if row["regime"] == "ar" and row["h"] == 7.0
    )
    assert ar_h7_calibration["mae"] == pytest.approx(7.338486126363191)
    raw_models = payload["results"]["model_horizon_ablation_source"]
    assert raw_models is not None
    assert any(
        row["regime"] == "ar" and row["model"] == "naive" and row["h"] == 7.0
        for row in raw_models
    )
    assert any(
        row["regime"] == "ar" and row["policy"] == "hspec" and row["horizon_days"] == 7.0
        for row in payload["policy_horizon_metrics"]
    )
    policy_h7 = [
        row for row in payload["policy_horizon_metrics"]
        if row["regime"] == "ar" and row["horizon_days"] == 7.0
    ]
    assert {row["policy"] for row in policy_h7} >= {"reactive", "point", "buffer", "pooled", "hspec"}


def test_optional_absence_does_not_mark_dashboard_partial_and_required_schema_is_checked(tmp_path):
    results_dir = tmp_path / "results"
    config_path = tmp_path / "configs" / "study_config.json"
    results_dir.mkdir()
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({
        "T": 10,
        "n_regions": 1,
        "t_calibration_start": 2,
        "t_validation_start": 4,
        "t_test_start": 6,
        "horizons": [1],
        "n_seeds_main": 1,
        "n_seeds_forecast_models": 0,
    }), encoding="utf-8")

    required_csvs = {
        "forecast_calibration_summary.csv": "regime,h,mae,wape,cov_hspec,cov_pooled,width_hspec,width_pooled\nar,7,1,1,.8,.8,2,2\n",
        "policy_levels_main.csv": "policy,regime,cost_total,cost_reserve,unmet\nreactive,ar,1,0,0\n",
        "paired_comparisons_main.csv": "horizons,comparison,regime,n,mean_delta,ci_lo,ci_hi\nh1-7-14,vs_pooled,ar,1,0,0,0\n",
        "paired_by_horizon_main.csv": "h,comparison,regime,n,mean_delta,ci_lo,ci_hi\n7,vs_pooled,ar,1,0,0,0\n",
        "routing_summary.csv": "policy,n_instances,feasibility_rate,mean_distance_feasible_km\nhspec,1,1,1\n",
    }
    for filename, content in required_csvs.items():
        (results_dir / filename).write_text(content, encoding="utf-8")

    service = ResearchAnalyticsService(results_dir=results_dir, config_path=config_path)
    payload = service.get_hccr_analytics()
    assert payload["status"] == "available"
    assert payload["missing_artifacts"] == []
    assert "comparison_table.csv" in payload["unavailable_optional_artifacts"]
    assert len(payload["artifact_manifest"]) == len({row["filename"] for row in payload["artifact_manifest"]})

    (results_dir / "forecast_calibration_summary.csv").write_text("wrong,columns\n1,2\n", encoding="utf-8")
    malformed = service.get_hccr_analytics()
    assert malformed["status"] == "partial"
    assert malformed["missing_artifacts"].count("forecast_calibration_summary.csv") == 1


def test_hccr_research_api_authorizes_and_exposes_frozen_artifact_values():
    admin = SimpleNamespace(role="admin")
    payload = get_hccr_research_endpoint(
        current_user=admin,
        research_service=ResearchAnalyticsService(),
    )
    assert payload["status"] == "available"
    assert payload["results"]["routing"][0]["n_instances"] == 240.0

    with pytest.raises(HTTPException) as error:
        get_hccr_research_endpoint(
            current_user=SimpleNamespace(role="driver"),
            research_service=ResearchAnalyticsService(),
        )
    assert error.value.status_code == 403


def test_hccr_download_route_allows_named_artifacts_only():
    admin = SimpleNamespace(role="admin")
    response = download_hccr_research_artifact(
        filename="forecast_calibration_summary.csv",
        current_user=admin,
        research_service=ResearchAnalyticsService(),
    )
    assert Path(response.path).name == "forecast_calibration_summary.csv"
    assert response.media_type == "text/csv"

    json_response = download_hccr_research_artifact(
        filename="study_config.json",
        current_user=admin,
        research_service=ResearchAnalyticsService(),
    )
    assert json_response.media_type == "application/json"
    legacy_response = download_hccr_research_artifact(
        filename="experiments/results/forecast_models.json",
        current_user=admin,
        research_service=ResearchAnalyticsService(),
    )
    assert Path(legacy_response.path).name == "forecast_models.json"
    assert legacy_response.filename == "forecast_models.json"
    assert legacy_response.media_type == "application/json"


def test_hccr_download_route_uses_path_converter_for_nested_filenames():
    from app.api.analytics import router

    admin = SimpleNamespace(role="admin")
    route = next(
        route for route in router.routes
        if getattr(route, "name", "") == "download_hccr_research_artifact"
    )
    assert route.path == "/analytics/hccr-research/download/{filename:path}"

    with pytest.raises(HTTPException) as error:
        download_hccr_research_artifact(
            filename="..%2f..%2f.env",
            current_user=admin,
            research_service=ResearchAnalyticsService(),
        )
    assert error.value.status_code == 404


def test_hccr_decision_endpoint_reports_causal_windows_and_exact_objective():
    result = get_hccr_reservation_decision_endpoint(
        regime="ar",
        seed=0,
        region=0,
        horizon_days=7,
        origin=800,
        current_user=SimpleNamespace(role="dispatcher"),
        research_service=ResearchAnalyticsService(),
    )

    assert result["horizon_days"] == 7
    assert "Synthetic simulation" in result["provenance"]
    hccr = result["policies"]["hspec"]
    pooled = result["policies"]["pooled"]
    assert hccr["residual_count"] <= 200
    assert pooled["residual_count"] >= hccr["residual_count"]
    for decision in (hccr, pooled):
        assert decision["calibration_status"] == "calibrated"
        assert decision["central_80_interval_units"] is not None
        assert sum(item["count"] for item in decision["vehicle_counts_by_capacity"]) == decision["reserved_vehicle_count"]
        assert decision["expected_total_objective"] == pytest.approx(
            decision["reservation_cost"]
            + result["shortage_penalty"] * decision["expected_shortage_units"]
        )
        assert decision["realized_test_total_cost"] == pytest.approx(
            decision["reservation_cost"]
            + result["shortage_penalty"] * decision["realized_test_shortage_units"]
        )


def test_hccr_decision_endpoint_rejects_unsupported_horizon():
    with pytest.raises(HTTPException) as error:
        get_hccr_reservation_decision_endpoint(
            regime="iid",
            seed=0,
            region=0,
            horizon_days=2,
            origin=800,
            current_user=SimpleNamespace(role="dispatcher"),
            research_service=ResearchAnalyticsService(),
        )
    assert error.value.status_code == 422
