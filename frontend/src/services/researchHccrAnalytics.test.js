import assert from "node:assert/strict";
import test from "node:test";
import {
  buildHccrModelMetrics,
  buildHccrAggregatePolicyComparison,
  buildHccrCapacityFeasibilityMetrics,
  buildHccrHorizonComparisons,
  buildHccrHorizonMetrics,
  buildHccrMechanismMetrics,
  buildHccrReplicationMetrics,
  buildHccrPolicyMetrics,
  buildHccrPolicyHorizonMetrics,
  buildHccrPrimaryComparisons,
  buildHccrRealDataMetrics,
  buildHccrRoutingMetrics,
  buildAggregateForecasterMetrics,
  buildLegacyAblationMetrics,
  buildLegacyForecastModelData,
  buildLegacyHorizonMetrics,
} from "./researchHccrAnalytics.js";

const fixture = {
  results: {
    forecast_calibration: [
      { regime: "ar", h: 7, mae: 7.3, wape: 0.063, cov_hspec: 0.777, cov_pooled: 0.788, width_hspec: 22.9, width_pooled: 24.3 },
      { regime: "iid", h: 7, mae: 3.9, wape: 0.034, cov_hspec: 0.79, cov_pooled: 0.8, width_hspec: 12.4, width_pooled: 12.5 },
    ],
    policy_levels: [
      { policy: "hspec", regime: "ar", cost_total: 14.45, cost_reserve: 10.67, unmet: 1.88, n_reserved: 0.68, shortage_day_rate: 0.29 },
      { policy: "oracle", regime: "ar", cost_total: 10.8, cost_reserve: 8, unmet: 1.4, n_reserved: 0.7, shortage_day_rate: 0.2 },
    ],
    comparison_table: [
      { scope: "aggregate", horizons: "h1-7-14", policy: "reactive", cost_total: 23.96, cost_total_lo: 22.82, cost_total_hi: 25.21, cost_reserve: 0, unmet: 11.98, n_reserved: 0, route_feas: 0.262, route_n_instances: 240, wape: 0.046 },
      { scope: "aggregate", horizons: "h1-7-14", policy: "hspec", cost_total: 12.96, cost_total_lo: 12.49, cost_total_hi: 13.44, cost_reserve: 9.71, unmet: 1.62, n_reserved: 0.66, route_feas: 0.621, route_n_instances: 240, wape: 0.046 },
      { scope: "ar", horizons: "h1-7-14", policy: "hspec", cost_total: 14.4 },
    ],
    comparison_forecasters: [
      { forecaster: "lr", n_units: 40, cost: 13.15, lo: 12.28, hi: 14.14, wape: 0.0457, reactive_cost: 24.68 },
      { forecaster: "hw", n_units: 40, cost: 13.48, lo: 12.59, hi: 14.46, wape: 0.0521, reactive_cost: 24.68 },
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
    routing_capacity_gap: [
      { policy: "hspec", n_agg_ok: 100, routing_infeasible_despite_agg_ok: 12 },
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
  model_horizon_accuracy: [
    { model: "lr", regime: "ar", horizon_days: 7, mae: 7.1, wape: 0.06, seed_count: 10 },
    { model: "naive", regime: "ar", horizon_days: 7, mae: 8.2, wape: 0.07, seed_count: 10 },
    { model: "hw", regime: "ar", horizon_days: 14, mae: 8.3, wape: 0.08, seed_count: 10 },
  ],
  policy_horizon_metrics: [
    { regime: "ar", horizon_days: 7, policy: "reactive", cost_total: 25.0, seed_count: 30 },
    { regime: "ar", horizon_days: 7, policy: "hspec", cost_total: 14.5, seed_count: 30 },
    { regime: "iid", horizon_days: 7, policy: "hspec", cost_total: 11, seed_count: 30 },
  ],
};

test("forecast and policy views filter by regime and retain source units", () => {
  const modelSlice = buildHccrModelMetrics(fixture, "ar", 7);
  assert.deepEqual(modelSlice.map((row) => row.model), ["Seasonal linear regression", "Previous-week naive"]);
  assert.equal(modelSlice[0].mae, 7.1);
  const modelAblation = buildHccrModelMetrics({
    results: {
      model_comparison: [
        { model: "lr", regime: "ar", mae: 7.0, wape: 0.06 },
        { model: "naive", regime: "ar", mae: 8.0, wape: 0.07 },
        { model: "hw", regime: "ar", mae: 7.8, wape: 0.068 },
      ],
    },
  }, "ar", 7);
  assert.deepEqual(modelAblation, []);
  assert.equal(buildHccrModelMetrics({
    results: {
      model_comparison: [
        { model: "lr", regime: "ar", mae: 7.0, wape: 0.06 },
        { model: "naive", regime: "ar", mae: 8.0, wape: 0.07 },
        { model: "hw", regime: "ar", mae: 7.8, wape: 0.068 },
      ],
    },
  }, "ar").length, 3);
  const horizon = buildHccrHorizonMetrics(fixture, "ar");
  assert.equal(horizon.length, 1);
  assert.equal(horizon[0].wapePercent, 6.3);
  assert.equal(horizon[0].nominalCoveragePercent, 80);
  const policies = buildHccrPolicyMetrics(fixture, "ar");
  assert.equal(policies[0].policyCode, "hspec");
  assert.equal(policies[0].shortageDayRatePercent, 28.999999999999996);
  const policyHorizons = buildHccrPolicyHorizonMetrics(fixture, "ar");
  assert.equal(policyHorizons[0].hspec, 14.5);
  assert.equal(policyHorizons[0].reactiveSeedCount, 30);
  const aggregatePolicies = buildHccrAggregatePolicyComparison(fixture);
  assert.equal(aggregatePolicies.length, 2);
  assert.equal(aggregatePolicies[1].routeFeasibilityPercent, 62.1);
  assert.equal(buildAggregateForecasterMetrics(fixture)[0].observations, 40);
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
  assert.equal(buildHccrCapacityFeasibilityMetrics(fixture)[0].routingInfeasibleDespiteAggregate, 12);
});

test("replication and mechanism outputs retain their own sample sizes and adjusted inference", () => {
  const replicated = buildHccrReplicationMetrics(fixture, "ar");
  const mechanism = buildHccrMechanismMetrics(fixture, "mechanism_primary");
  assert.equal(replicated[0].seeds, 30);
  assert.equal(replicated[0].pooledMinusHccr, 0.124);
  assert.equal(mechanism[0].simulations, 60);
  assert.equal(mechanism[0].holmP, 0.0001);
});

test("legacy forecast artifacts map actual metrics without mixing into HCCR rows", () => {
  const models = buildLegacyForecastModelData({ results: [
    { model: "seasonal_linear_regression", horizon_days: 60, mae: 4.5, rmse: 5.7, mape_percent: 4.1, forecast_origins: 1 },
  ] });
  const horizons = buildLegacyHorizonMetrics({ results: [
    { model: "seasonal_linear_regression", horizon_days: 7, mae: 4.6, rmse: 5.9, mape_percent: 4.2, forecast_origins: 54 },
  ] });
  const ablation = buildLegacyAblationMetrics({ results: [
    { ablation: "full", mae: 4.5, rmse: 5.7, mape_percent: 4.1 },
  ] });
  assert.equal(models[0].origins, 1);
  assert.equal(horizons[0].horizon, "H7");
  assert.equal(ablation[0].mae, 4.5);
});

test("a missing requested HCCR model horizon never falls back to unrelated aggregate data", () => {
  const payload = {
    results: {
      model_horizon_accuracy: [{ model: "lr", regime: "ar", horizon_days: 7, mae: 7, wape: 0.06 }],
      model_comparison: [
        { model: "lr", regime: "ar", mae: 5, wape: 0.04 },
        { model: "hw", regime: "ar", mae: 8, wape: 0.07 },
      ],
    },
  };
  assert.deepEqual(buildHccrModelMetrics(payload, "ar", 28), []);
});