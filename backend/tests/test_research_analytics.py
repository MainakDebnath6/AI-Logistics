from __future__ import annotations

from pathlib import Path

from app.api.analytics import get_research_analytics, summarize_synthetic_demand_rows


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
