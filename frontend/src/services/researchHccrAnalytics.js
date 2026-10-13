function numeric(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function rows(payload, key) {
  const values = payload?.results?.[key];
  return Array.isArray(values) ? values : [];
}

const POLICY_LABELS = {
  reactive: "Reactive",
  point: "Point forecast",
  buffer: "Fixed buffer (validation-tuned)",
  pooled: "Pooled residuals",
  hspec: "HCCR (horizon-specific)",
  robust: "Robust 95% quantile cover",
  oracle: "Oracle (unattainable)",
};

const MODEL_LABELS = {
  lr: "Seasonal linear regression",
  naive: "Previous-week naive",
  hw: "Holt-Winters",
};

const COMPARISON_LABELS = {
  vs_reactive: "Reactive",
  "vs_pooled(B)": "Pooled residuals",
  "vs_point(C)": "Point forecast",
  "vs_buffer(D)": "Fixed buffer",
  "vs_ungated(E)": "Ungated HCCR",
  oracle_gap: "Oracle (unattainable)",
};

export function buildHccrModelMetrics(payload, regime, horizonDays = null) {
  const horizonRows = rows(payload, "model_horizon_accuracy")
    .filter((entry) => entry.regime === regime && (horizonDays === null || numeric(entry.horizon_days) === horizonDays));
  const sourceRows = horizonRows.length > 0
    ? horizonRows
    : rows(payload, "model_comparison").filter((entry) => entry.regime === regime);
  return sourceRows
    .map((entry) => ({
      model: MODEL_LABELS[entry.model] || entry.model,
      horizonDays: numeric(entry.horizon_days),
      mae: numeric(entry.mae),
      wapePercent: numeric(entry.wape) === null ? null : numeric(entry.wape) * 100,
      hccrCost: numeric(entry.cost_hspec),
      reactiveCost: numeric(entry.cost_reactive),
    }))
    .filter((entry) => entry.mae !== null);
}

export function buildHccrHorizonMetrics(payload, regime) {
  return rows(payload, "forecast_calibration")
    .filter((entry) => entry.regime === regime)
    .map((entry) => ({
      horizon: `H${numeric(entry.h) ?? "?"}`,
      horizonDays: numeric(entry.h),
      mae: numeric(entry.mae),
      wapePercent: numeric(entry.wape) === null ? null : numeric(entry.wape) * 100,
      hccrCoveragePercent: numeric(entry.cov_hspec) === null ? null : numeric(entry.cov_hspec) * 100,
      pooledCoveragePercent: numeric(entry.cov_pooled) === null ? null : numeric(entry.cov_pooled) * 100,
      nominalCoveragePercent: 80,
      hccrIntervalWidth: numeric(entry.width_hspec),
      pooledIntervalWidth: numeric(entry.width_pooled),
      hccrCoverageSd: numeric(entry.cov_hspec_sd),
      pooledCoverageSd: numeric(entry.cov_pooled_sd),
    }))
    .filter((entry) => entry.horizonDays !== null)
    .sort((left, right) => left.horizonDays - right.horizonDays);
}

export function buildHccrPolicyMetrics(payload, regime) {
  const order = ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"];
  return rows(payload, "policy_levels")
    .filter((entry) => entry.regime === regime)
    .map((entry) => ({
      policy: POLICY_LABELS[entry.policy] || entry.policy,
      policyCode: entry.policy,
      totalCost: numeric(entry.cost_total),
      reservationCost: numeric(entry.cost_reserve),
      unmetUnits: numeric(entry.unmet),
      reservedVehicles: numeric(entry.n_reserved),
      shortageDayRatePercent: numeric(entry.shortage_day_rate) === null
        ? null
        : numeric(entry.shortage_day_rate) * 100,
    }))
    .sort((left, right) => order.indexOf(left.policyCode) - order.indexOf(right.policyCode));
}

export function buildHccrPrimaryComparisons(payload, regime) {
  return rows(payload, "paired_comparisons")
    .filter((entry) => entry.regime === regime && entry.horizons === "h1-7-14")
    .map((entry) => ({
      comparison: COMPARISON_LABELS[entry.comparison] || entry.comparison,
      comparisonCode: entry.comparison,
      meanDelta: numeric(entry.mean_delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
      seeds: numeric(entry.n),
      effectSizeDz: numeric(entry.dz),
      pWilcoxon: numeric(entry.p_wilcoxon),
      pHolm: numeric(entry.p_holm),
    }))
    .filter((entry) => entry.meanDelta !== null);
}

export function buildHccrHorizonComparisons(payload, regime) {
  return rows(payload, "paired_horizons")
    .filter((entry) => entry.regime === regime && entry.comparison === "vs_pooled")
    .map((entry) => ({
      horizon: `H${numeric(entry.h) ?? "?"}`,
      horizonDays: numeric(entry.h),
      pooledMinusHccr: numeric(entry.mean_delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
      seeds: numeric(entry.n),
      unadjustedP: numeric(entry.p_wilcoxon),
      effectSizeDz: numeric(entry.dz),
    }))
    .filter((entry) => entry.horizonDays !== null)
    .sort((left, right) => left.horizonDays - right.horizonDays);
}

export function buildHccrGateMetrics(payload, regime, horizonDays) {
  return rows(payload, "gate_rates")
    .filter((entry) => entry.regime === regime && numeric(entry.h) === horizonDays)
    .map((entry) => ({
      policy: POLICY_LABELS[entry.policy] || entry.policy,
      openRatePercent: numeric(entry.gate_open) === null ? null : numeric(entry.gate_open) * 100,
    }));
}

export function buildHccrSensitivityMetrics(payload, regime, parameter) {
  return rows(payload, "sensitivity")
    .filter((entry) => entry.regime === regime
      && entry.param === parameter
      && entry.comparator === "pooled")
    .map((entry) => ({
      setting: String(numeric(entry.value) ?? entry.value),
      value: numeric(entry.value),
      pooledMinusHccr: numeric(entry.mean_delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
      simulations: numeric(entry.n),
    }))
    .filter((entry) => entry.value !== null)
    .sort((left, right) => left.value - right.value);
}

export function buildHccrRoutingMetrics(payload) {
  return rows(payload, "routing")
    .map((entry) => ({
      policy: POLICY_LABELS[entry.policy] || entry.policy,
      policyCode: entry.policy,
      feasiblePercent: numeric(entry.feasibility_rate) === null ? null : numeric(entry.feasibility_rate) * 100,
      feasibilityCiLowPercent: numeric(entry.feas_ci_lo) === null ? null : numeric(entry.feas_ci_lo) * 100,
      feasibilityCiHighPercent: numeric(entry.feas_ci_hi) === null ? null : numeric(entry.feas_ci_hi) * 100,
      instances: numeric(entry.n_instances),
      distanceSolvedKm: numeric(entry.mean_distance_feasible_km),
      matchedDistanceKm: numeric(entry.matched_distance_km),
      matchedInstances: numeric(entry.n_matched),
      meanRuntimeSeconds: numeric(entry.runtime_s),
      reservationCost: numeric(entry.mean_reserve_cost),
      activatedVehicles: numeric(entry.mean_n_activated),
      aggregateUnmetRate: numeric(entry.agg_unmet_instances) === null ? null : numeric(entry.agg_unmet_instances) * 100,
    }))
    .filter((entry) => entry.instances !== null);
}

export function buildHccrRealDataMetrics(payload, shortagePenalty) {
  return rows(payload, "real_data_delta")
    .filter((entry) => numeric(entry.pi) === shortagePenalty)
    .map((entry) => ({
      horizon: `H${numeric(entry.h) ?? "?"}`,
      horizonDays: numeric(entry.h),
      pooledMinusHccr: numeric(entry.delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
      disagreementPercent: numeric(entry.disagreement) === null ? null : numeric(entry.disagreement) * 100,
      testOrigins: numeric(entry.n_origins),
    }))
    .filter((entry) => entry.horizonDays !== null)
    .sort((left, right) => left.horizonDays - right.horizonDays);
}

export function buildHccrRealDataCalibration(payload) {
  return rows(payload, "real_data_calibration")
    .map((entry) => ({
      horizon: `H${numeric(entry.h) ?? "?"}`,
      horizonDays: numeric(entry.h),
      mae: numeric(entry.mae),
      wapePercent: numeric(entry.wape) === null ? null : numeric(entry.wape) * 100,
      hccrCoveragePercent: numeric(entry.cov_hspec) === null ? null : numeric(entry.cov_hspec) * 100,
      pooledCoveragePercent: numeric(entry.cov_pooled) === null ? null : numeric(entry.cov_pooled) * 100,
      nominalCoveragePercent: 80,
      hccrIntervalWidth: numeric(entry.width_hspec),
      pooledIntervalWidth: numeric(entry.width_pooled),
    }))
    .filter((entry) => entry.horizonDays !== null)
    .sort((left, right) => left.horizonDays - right.horizonDays);
}

export function buildHccrReplicationMetrics(payload, regime) {
  return rows(payload, "replication")
    .filter((entry) => entry.regime === regime)
    .map((entry) => ({
      horizons: entry.horizons,
      pooledMinusHccr: numeric(entry.mean_delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
      seeds: numeric(entry.n),
      unadjustedP: numeric(entry.p_wilcoxon),
      percentOfHccr: numeric(entry.pct_of_hccr),
    }));
}

export function buildHccrMechanismMetrics(payload, resultKey) {
  return rows(payload, resultKey)
    .map((entry) => ({
      contrast: entry.contrast,
      simulations: numeric(entry.n_sims),
      meanEffect: numeric(entry.mean),
      ciLow: numeric(entry.ci95_lo),
      ciHigh: numeric(entry.ci95_hi),
      holmP: numeric(entry.p_holm),
      effectSizeDz: numeric(entry.dz),
    }))
    .filter((entry) => entry.contrast);
}

export function buildHccrDisagreementMetrics(payload, regime) {
  return rows(payload, "decision_disagreement")
    .filter((entry) => entry.regime === regime && entry.sample === "primary")
    .map((entry) => ({
      horizon: entry.horizons,
      decisions: entry.decisions,
      simulations: numeric(entry.n_sims),
      disagreementPercent: numeric(entry.mean) === null ? null : numeric(entry.mean) * 100,
      ciLowPercent: numeric(entry.ci_lo) === null ? null : numeric(entry.ci_lo) * 100,
      ciHighPercent: numeric(entry.ci_hi) === null ? null : numeric(entry.ci_hi) * 100,
      maximumSimulationPercent: numeric(entry.max_sim) === null ? null : numeric(entry.max_sim) * 100,
    }));
}

export function buildHccrModelPairingMetrics(payload, regime) {
  return rows(payload, "forecast_model_paired")
    .filter((entry) => entry.regime === regime)
    .map((entry) => ({
      comparison: entry.comparison,
      simulations: numeric(entry.n),
      meanCostDifference: numeric(entry.mean_delta),
      ciLow: numeric(entry.ci_lo),
      ciHigh: numeric(entry.ci_hi),
    }));
}