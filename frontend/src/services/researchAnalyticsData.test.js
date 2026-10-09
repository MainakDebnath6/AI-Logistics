import assert from "node:assert/strict";
import test from "node:test";
import {
  buildFeatureAblationData,
  buildForecastComparisonData,
  buildHorizonSensitivityData,
  buildPairedRoutingData,
} from "./researchAnalyticsData.js";
import forecastModels from "../../../experiments/results/forecast_models.json" with { type: "json" };
import horizonSensitivity from "../../../experiments/results/horizon_sensitivity.json" with { type: "json" };
import featureAblation from "../../../experiments/results/feature_ablation.json" with { type: "json" };
import pairedRouting from "../../../experiments/results/reactive_vs_hgfc.json" with { type: "json" };

test("research charts map actual generated metric artifacts", () => {
  assert.equal(buildForecastComparisonData({ forecast_models: forecastModels }).length, 3);
  const horizons = buildHorizonSensitivityData({ horizon_sensitivity: horizonSensitivity });
  assert.deepEqual(horizons.map((row) => row.horizon), ["H7", "H14", "H30", "H60"]);
  assert.equal(horizons[0].naive_previous_week, horizonSensitivity.results[0].mae);
  assert.equal(buildFeatureAblationData({ feature_ablation: featureAblation }).length, 6);
  assert.equal(buildPairedRoutingData({ reactive_vs_hgfc: pairedRouting }).length, 6);
  assert.equal(
    buildForecastComparisonData({ forecast_models: forecastModels })[0].mae,
    forecastModels.results[0].mae,
  );
});

test("missing or invalid MAE is excluded instead of becoming a fake zero", () => {
  const payload = {
    forecast_models: {
      results: [
        { model: "missing", rmse: 4 },
        { model: "invalid", mae: "not-a-number" },
        { model: "valid", mae: 2.5 },
      ],
    },
    horizon_sensitivity: { results: [{ model: "missing", horizon_days: 7 }] },
    feature_ablation: { results: [{ ablation: "missing" }] },
  };

  assert.deepEqual(buildForecastComparisonData(payload), [
    { model: "valid", mae: 2.5, rmse: null, mape: null },
  ]);
  assert.deepEqual(buildHorizonSensitivityData(payload), []);
  assert.deepEqual(buildFeatureAblationData(payload), []);
});