from __future__ import annotations

from pathlib import Path
import csv
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.analytics import (
    download_hccr_research_artifact,
    get_hccr_research_endpoint,
    get_hccr_reservation_decision_endpoint,
    get_research_analytics,
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
