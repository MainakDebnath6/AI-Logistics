function toFiniteNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function getResults(payload, key) {
  const results = payload?.[key]?.results;
  return Array.isArray(results) ? results : [];
}

function normalizeErrorMetrics(entry) {
  return {
    mae: toFiniteNumber(entry.mae),
    rmse: toFiniteNumber(entry.rmse),
    mape: toFiniteNumber(entry.mape_percent),
  };
}

export function buildSyntheticDemandSeries(payload) {
  const observations = payload?.synthetic_demand?.observations;
  if (!Array.isArray(observations)) {
    return [];
  }

  return observations
    .map((entry) => ({ date: entry?.date, demand: toFiniteNumber(entry?.demand) }))
    .filter((entry) => typeof entry.date === "string" && entry.demand !== null);
}

export function buildForecastComparisonData(payload) {
  return getResults(payload, "forecast_models")
    .map((entry) => ({
      model: entry.model,
      ...normalizeErrorMetrics(entry),
    }))
    .filter((entry) => typeof entry.model === "string" && entry.mae !== null);
}

export function buildHorizonSensitivityData(payload) {
  return getResults(payload, "horizon_sensitivity")
    .map((entry) => ({
      horizonDays: toFiniteNumber(entry.horizon_days),
      model: entry.model,
      ...normalizeErrorMetrics(entry),
    }))
    .filter((entry) => entry.horizonDays !== null && typeof entry.model === "string" && entry.mae !== null)
    .map((entry) => ({ ...entry, horizon: `H${entry.horizonDays}` }));
}

export function buildFeatureAblationData(payload) {
  return getResults(payload, "feature_ablation")
    .map((entry) => ({
      ablation: entry.ablation,
      ...normalizeErrorMetrics(entry),
    }))
    .filter((entry) => typeof entry.ablation === "string" && entry.mae !== null);
}

export function buildCvrpBenchmarkData(payload) {
  return getResults(payload, "cvrp_benchmark")
    .map((entry) => ({
      scenarioId: toFiniteNumber(entry.scenario_id),
      feasible: entry.feasible,
      demand: toFiniteNumber(entry.confirmed_demand),
      capacity: toFiniteNumber(entry.available_capacity),
      serviceLevel: toFiniteNumber(entry.service_level_percent),
    }))
    .filter((entry) => entry.scenarioId !== null && typeof entry.feasible === "boolean")
    .map((entry) => ({ ...entry, scenario: `Scenario ${entry.scenarioId}` }));
}

export function buildHgfcAdvisoryData(payload) {
  return getResults(payload, "hgfc_advisory")
    .map((entry) => ({
      leadDays: toFiniteNumber(entry.forecast_lead_days),
      forecastDemand: toFiniteNumber(entry.forecast_demand),
      risk: toFiniteNumber(entry.capacity_risk),
      intervention: Boolean(entry.preparation_intervention),
    }))
    .filter((entry) => entry.leadDays !== null && entry.forecastDemand !== null);
}