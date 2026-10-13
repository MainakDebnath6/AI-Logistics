import assert from "node:assert/strict";
import test from "node:test";
import {
  buildPublicBikeMonthlyData,
  buildSyntheticDemandChartData,
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
  const paired = buildPairedRoutingData({ reactive_vs_hgfc: pairedRouting });
  assert.equal(paired.length, 6);
  assert.ok(paired.some((row) => row.infeasible && row.reactiveDistance === null && row.advisoryDistance === null));
  assert.ok(paired.some((row) => !row.infeasible && row.reactiveDistance > 0 && row.advisoryDistance > 0));
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

test("synthetic demand chart keeps the chronological 670/60 split and original observations", () => {
  const payload = {
    synthetic_demand: {
      split: { train_observations: 670, holdout_observations: 60 },
      observations: Array.from({ length: 730 }, (_, index) => ({
        date: `2024-01-${String(index + 1).padStart(2, "0")}`,
        demand: index + 0.5,
      })),
    },
  };
  const chartRows = buildSyntheticDemandChartData(payload);

  assert.equal(chartRows.length, 730);
  assert.equal(chartRows[0].trainingDemand, 0.5);
  assert.equal(chartRows[669].trainingDemand, 669.5);
  assert.equal(chartRows[670].trainingDemand, null);
  assert.equal(chartRows[670].holdoutDemand, 670.5);
  assert.equal(chartRows[729].holdoutDemand, 729.5);
});

test("public bike monthly series maps actual metrics and excludes missing totals", () => {
  const result = buildPublicBikeMonthlyData({ monthly_observations: [
    { month: "2011-01", observation_days: 31, total_rentals: "38189", casual_rentals: 3073, registered_rentals: 35116, mean_daily_rentals: 1231.9 },
    { month: "2011-02", total_rentals: null },
  ] });
  assert.deepEqual(result, [{
    month: "2011-01",
    observationDays: 31,
    totalRentals: 38189,
    casualRentals: 3073,
    registeredRentals: 35116,
    meanDailyRentals: 1231.9,
  }]);
});