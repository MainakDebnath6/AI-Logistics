import assert from "node:assert/strict";
import test from "node:test";
import {
  buildHccrModelMetrics,
  buildHccrHorizonComparisons,
  buildHccrHorizonMetrics,
  buildHccrMechanismMetrics,
  buildHccrReplicationMetrics,
  buildHccrPolicyMetrics,
  buildHccrPrimaryComparisons,
  buildHccrRealDataMetrics,
  buildHccrRoutingMetrics,
} from "./researchHccrAnalytics.js";

const fixture = {
  results: {
    forecast_calibration: [
      { regime: "ar", h: 7, mae: 7.3, wape: 0.063, cov_hspec: 0.777, cov_pooled: 0.788, width_hspec: 22.9, width_pooled: 24.3 },
      { regime: "iid", h: 7, mae: 3.9, wape: 0.034, cov_hspec: 0.79, cov_pooled: 0.8, width_hspec: 12.4, width_pooled: 12.5 },
    ],
        model_horizon_accuracy: [
          { model: "lr", regime: "ar", horizon_days: 7, mae: 7.1, wape: 0.06, seed_count: 10 },
          { model: "naive", regime: "ar", horizon_days: 7, mae: 8.2, wape: 0.07, seed_count: 10 },
          { model: "hw", regime: "ar", horizon_days: 14, mae: 8.3, wape: 0.08, seed_count: 10 },
        ],
    policy_levels: [
      { policy: "hspec", regime: "ar", cost_total: 14.45, cost_reserve: 10.67, unmet: 1.88, n_reserved: 0.68, shortage_day_rate: 0.29 },
      { policy: "oracle", regime: "ar", cost_total: 10.8, cost_reserve: 8, unmet: 1.4, n_reserved: 0.7, shortage_day_rate: 0.2 },
    ],
    paired_comparisons: [
      { horizons: "h1-7-14", comparison: "vs_pooled(B)", regime: "ar", mean_delta: 0.077, ci_lo: 0.055, ci_hi: 0.103, n: 30, p_wilcoxon: 0.001, p_holm: 0.02 },
      { horizons: "h28", comparison: "vs_pooled(B)", regime: "ar", mean_delta: -0.42, ci_lo: -0.56, ci_hi: -0.29, n: 30, p_wilcoxon: 0.01, p_holm: null },
    ],
    paired_horizons: [
      { h: 14, comparison: "vs_pooled", regime: "ar", mean_delta: -0.12, ci_lo: -0.15, ci_hi: -0.1, n: 30, p_wilcoxon: 0.01, dz: -0.5 },
    ],
    routing: [
      { policy: "hspec", n_instances: 240, feasibility_rate: 0.621, feas_ci_lo: 0.56, feas_ci_hi: 0.68, mean_distance_feasible_km: 121.4, runtime_s: 0.11, matched_distance_km: 108.5, n_matched: 63 },
      { policy: "hspec", n_instances: 0, feasibility_rate: null },
    ],
    real_data_delta: [
      { pi: 4, h: 7, delta: 0.1, ci_lo: -0.2, ci_hi: 0.3, disagreement: 0.04, n_origins: 103 },
      { pi: 9, h: 7, delta: 0.2, ci_lo: -0.1, ci_hi: 0.4, disagreement: 0.08, n_origins: 103 },
    ],
    replication: [
      { regime: "ar", horizons: "h1-7-14", n: 30, mean_delta: 0.124, ci_lo: 0.102, ci_hi: 0.146, p_wilcoxon: 0.001, pct_of_hccr: 0.88 },
    ],
    mechanism_primary: [
      { contrast: "Theta_h28", n_sims: 60, mean: 0.323, ci95_lo: 0.282, ci95_hi: 0.365, p_holm: 0.0001, dz: 1.95 },
    ],
  },
};

test("forecast and policy views filter by regime and retain source units", () => {
  const modelSlice = buildHccrModelMetrics(fixture, "ar", 7);
  assert.deepEqual(modelSlice.map((row) => row.model), ["Seasonal linear regression", "Previous-week naive"]);
  assert.equal(modelSlice[0].mae, 7.1);
  const horizon = buildHccrHorizonMetrics(fixture, "ar");
  assert.equal(horizon.length, 1);
  assert.equal(horizon[0].wapePercent, 6.3);
  assert.equal(horizon[0].nominalCoveragePercent, 80);
  const policies = buildHccrPolicyMetrics(fixture, "ar");
  assert.equal(policies[0].policyCode, "hspec");
  assert.equal(policies[0].shortageDayRatePercent, 28.999999999999996);
});

test("confirmatory primary contrasts and exploratory horizon contrasts stay distinct", () => {
  const primary = buildHccrPrimaryComparisons(fixture, "ar");
  const horizons = buildHccrHorizonComparisons(fixture, "ar");
  assert.equal(primary.length, 1);
  assert.equal(primary[0].pHolm, 0.02);
  assert.equal(horizons[0].pooledMinusHccr, -0.12);
  assert.equal(horizons[0].unadjustedP, 0.01);
});

test("routing and public-data views preserve missing measurements", () => {
  const routing = buildHccrRoutingMetrics(fixture);
  assert.equal(routing.length, 2);
  assert.equal(routing[0].feasiblePercent, 62.1);
  assert.equal(routing[0].distanceSolvedKm, 121.4);
  assert.equal(routing[1].instances, 0);
  assert.equal(routing[1].feasiblePercent, null);
  assert.deepEqual(buildHccrRealDataMetrics(fixture, 4).map((row) => row.testOrigins), [103]);
});

test("replication and mechanism outputs retain their own sample sizes and adjusted inference", () => {
  const replicated = buildHccrReplicationMetrics(fixture, "ar");
  const mechanism = buildHccrMechanismMetrics(fixture, "mechanism_primary");
  assert.equal(replicated[0].seeds, 30);
  assert.equal(replicated[0].pooledMinusHccr, 0.124);
  assert.equal(mechanism[0].simulations, 60);
  assert.equal(mechanism[0].holmP, 0.0001);
});