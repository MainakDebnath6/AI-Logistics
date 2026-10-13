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

export function buildSyntheticDemandChartData(payload) {
  const observations = buildSyntheticDemandSeries(payload);
  const trainCount = toFiniteNumber(payload?.synthetic_demand?.split?.train_observations);
  if (trainCount === null) return [];
  return observations.map((entry, index) => ({
    ...entry,
    trainingDemand: index < trainCount ? entry.demand : null,
    holdoutDemand: index >= trainCount ? entry.demand : null,
  }));
}

export function buildPublicBikeMonthlyData(payload) {
  const observations = payload?.monthly_observations;
  if (!Array.isArray(observations)) return [];
  return observations.map((entry) => ({
    month: entry?.month,
    observationDays: toFiniteNumber(entry?.observation_days),
    totalRentals: toFiniteNumber(entry?.total_rentals),
    casualRentals: toFiniteNumber(entry?.casual_rentals),
    registeredRentals: toFiniteNumber(entry?.registered_rentals),
    meanDailyRentals: toFiniteNumber(entry?.mean_daily_rentals),
  })).filter((entry) => typeof entry.month === "string" && entry.totalRentals !== null);
}

export function buildForecastComparisonData(payload) {
  return getResults(payload, "forecast_models")
    .map((entry) => ({
      model: {
        naive_previous_week: "Previous-week naive",
        holt_winters_weekly: "Holt-Winters",
        seasonal_linear_regression: "Seasonal linear regression",
      }[entry.model] || entry.model,
      ...normalizeErrorMetrics(entry),
    }))
    .filter((entry) => typeof entry.model === "string" && entry.mae !== null);
}

export function buildHorizonSensitivityData(payload) {
  const modelKeys = [
    "naive_previous_week",
    "holt_winters_weekly",
    "seasonal_linear_regression",
  ];
  const rowsByHorizon = new Map();
  for (const entry of getResults(payload, "horizon_sensitivity")) {
    const horizonDays = toFiniteNumber(entry.horizon_days);
    if (horizonDays === null || !modelKeys.includes(entry.model)) {
      continue;
    }
    const mae = toFiniteNumber(entry.mae);
    if (mae === null) {
      continue;
    }
    const horizonRow = rowsByHorizon.get(horizonDays) || { horizon: `H${horizonDays}` };
    horizonRow[entry.model] = mae;
    rowsByHorizon.set(horizonDays, horizonRow);
  }
  return [...rowsByHorizon.entries()]
    .sort(([left], [right]) => left - right)
    .map(([, row]) => row);
}

export function buildFeatureAblationData(payload) {
  return getResults(payload, "feature_ablation")
    .map((entry) => ({
      ablation: {
        full: "Full model",
        remove_weekly: "Remove weekly seasonality",
        remove_annual: "Remove annual seasonality",
        remove_lags: "Remove lag features",
        remove_rolling: "Remove rolling features",
        remove_weekly_and_annual: "Remove weekly + annual seasonality",
      }[entry.ablation] || entry.ablation,
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

export function buildPairedRoutingData(payload) {
  return getResults(payload, "reactive_vs_hgfc")
    .map((entry) => {
      const reactiveFeasible = typeof entry.reactive_feasible === "boolean" ? entry.reactive_feasible : null;
      const advisoryFeasible = typeof entry.hgfc_feasible === "boolean" ? entry.hgfc_feasible : null;
      return {
        scenarioId: toFiniteNumber(entry.scenario_id),
        leadDays: toFiniteNumber(entry.forecast_lead_days),
        reactiveFeasible,
        advisoryFeasible,
        reactiveDistance: reactiveFeasible === false ? null : toFiniteNumber(entry.reactive_route_distance_km),
        advisoryDistance: advisoryFeasible === false ? null : toFiniteNumber(entry.hgfc_route_distance_km),
        reactiveServiceLevel: toFiniteNumber(entry.reactive_service_level_percent),
        advisoryServiceLevel: toFiniteNumber(entry.hgfc_service_level_percent),
      };
    })
    .filter((entry) => entry.scenarioId !== null)
    .map((entry) => {
      const infeasible = entry.reactiveFeasible === false && entry.advisoryFeasible === false;
      return {
        ...entry,
        infeasible,
        scenario: infeasible ? `Lead ${entry.leadDays ?? "?"}d (infeasible)` : `Lead ${entry.leadDays ?? "?"}d`,
      };
    });
}