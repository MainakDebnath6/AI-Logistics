import { useEffect, useMemo, useState } from "react";
import AnalyticsChart from "../components/AnalyticsChart";
import LoadingSpinner from "../components/LoadingSpinner";
import {
  buildHccrAggregatePolicyComparison,
  buildHccrDisagreementMetrics,
  buildHccrCapacityFeasibilityMetrics,
  buildHccrGateMetrics,
  buildHccrHorizonComparisons,
  buildHccrHorizonMetrics,
  buildHccrMechanismMetrics,
  buildHccrModelMetrics,
  buildHccrModelPairingMetrics,
  buildAggregateForecasterMetrics,
  buildHccrPolicyMetrics,
  buildHccrPolicyHorizonMetrics,
  buildHccrPrimaryComparisons,
  buildHccrReplicationMetrics,
  buildHccrRealDataCalibration,
  buildHccrRealDataMetrics,
  buildHccrRoutingMetrics,
  buildHccrSensitivityMetrics,
} from "../services/researchHccrAnalytics";
import {
  downloadHccrArtifact,
  getHccrReservationDecision,
  getHccrResearchAnalytics,
} from "../services/researchHccrService";
import { resolveHccrDashboardState } from "../services/researchHccrDashboardState";
import {
  buildPublicBikeMonthlyData,
  buildSyntheticDemandChartData,
  buildCvrpBenchmarkData,
  buildFeatureAblationData,
  buildForecastComparisonData,
  buildHgfcAdvisoryData,
  buildHorizonSensitivityData,
  buildPairedRoutingData,
} from "../services/researchAnalyticsData";
import { getResearchAnalytics } from "../services/analyticsService";

const TABS = [
  ["forecast", "Forecast & calibration"],
  ["reservation", "Reservation & statistics"],
  ["routing", "Routing outcomes"],
  ["real", "Public-data check"],
  ["repro", "Reproducibility"],
];
const REGIMES = ["iid", "ar", "surge", "drift"];
const SENSITIVITY_OPTIONS = [
  ["shortage_penalty", "Shortage penalty"],
  ["reserve_cost_scale", "Reservation-cost scale"],
  ["capacity_pressure_kappa", "Base-capacity pressure"],
  ["noise_scale", "Stochastic noise scale"],
];
const PRIMARY_HORIZONS = "horizons 1, 7 and 14 days";

function number(value, digits = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "Unavailable";
}

function percent(value, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(digits)}%` : "Unavailable";
}

function ResearchTable({ columns, rows, emptyMessage = "No matching artifact rows are available." }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return <p className="py-5 text-sm text-slate-400">{emptyMessage}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-170 border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-xs uppercase text-slate-400">
            {columns.map((column) => <th key={column.key} className="px-3 py-2 font-medium">{column.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.policyCode || row.policy || row.comparisonCode || row.horizon || row.model || row.setting || "row"}-${index}`} className="border-b border-slate-800 text-slate-200 last:border-0">
              {columns.map((column) => {
                const value = row[column.key];
                return <td key={column.key} className="px-3 py-2 align-top">{column.format ? column.format(value, row) : value ?? "Unavailable"}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SelectControl({ label, value, onChange, options, disabled = false }) {
  return (
    <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-300">
      <span>{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white disabled:opacity-60"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>{optionLabel}</option>
        ))}
      </select>
    </label>
  );
}

function Metric({ label, value, detail }) {
  return (
    <div className="border-l-2 border-teal-400 pl-3">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
      {detail ? <p className="mt-1 text-xs text-slate-400">{detail}</p> : null}
    </div>
  );
}

function Panel({ title, children, description }) {
  return (
    <section className="space-y-2 border-t border-slate-800 pt-4">
      <div>
        <h3 className="text-base font-semibold text-white">{title}</h3>
        {description ? <p className="mt-1 text-sm text-slate-400">{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

function FilterBar({ regime, setRegime, horizon, setHorizon }) {
  return (
    <div className="flex flex-wrap gap-3 border-y border-slate-800 py-3">
      <SelectControl label="Simulation regime" value={regime} onChange={setRegime} options={REGIMES.map((name) => [name, name.toUpperCase()])} />
      <SelectControl label="Forecast horizon" value={horizon} onChange={setHorizon} options={[[1, "1 day"], [7, "7 days"], [14, "14 days"], [28, "28 days"]]} />
    </div>
  );
}

function ForecastTab({ research, regime, horizon, modelFilter, setModelFilter }) {
  const [legacyHorizon, setLegacyHorizon] = useState("7");
  const allModels = buildHccrModelMetrics(research, regime, Number(horizon));
  const modelNames = {
    lr: "Seasonal linear regression",
    naive: "Previous-week naive",
    hw: "Holt-Winters",
  };
  const models = modelFilter === "all"
    ? allModels
    : allModels.filter((entry) => entry.model === modelNames[modelFilter]);
  const selectedModelMetrics = models;
  const modelPairs = buildHccrModelPairingMetrics(research, regime);
  const aggregateForecasters = buildAggregateForecasterMetrics(research);
  const legacyArtifacts = research?.legacy_artifacts || {};
  const legacyForecastComparison = buildForecastComparisonData({ forecast_models: legacyArtifacts.legacy_forecast_models });
  const legacyHorizonRows = buildHorizonSensitivityData({ horizon_sensitivity: legacyArtifacts.legacy_horizon_sensitivity });
  const legacySelectedHorizon = legacyHorizonRows.filter((row) => row.horizon === `H${legacyHorizon}`);
  const legacyFeatureAblations = buildFeatureAblationData({ feature_ablation: legacyArtifacts.legacy_feature_ablation });
  const byHorizon = buildHccrHorizonMetrics(research, regime);
  const selectedHorizon = byHorizon.find((row) => row.horizonDays === Number(horizon));
  const modelCount = research?.configuration?.n_seeds_forecast_models;
  const mainSeeds = research?.configuration?.n_seeds_main;
  const syntheticDemand = research?.synthetic_demand;
  const syntheticSeries = buildSyntheticDemandChartData(research);

  return (
    <div className="space-y-6">
      <Panel title="Daily synthetic demand" description="Checked-in controlled synthetic series or populated public.synthetic_demand table; chronological split only, not measured logistics demand or an HCCR result.">
        <div className="grid gap-4 border-b border-slate-800 pb-4 sm:grid-cols-2 xl:grid-cols-4">
          <Metric label="Returned observations" value={syntheticDemand?.observation_count ?? "Unavailable"} detail="Daily synthetic demand units" />
          <Metric label="Date range" value={syntheticDemand?.start_date && syntheticDemand?.end_date ? `${syntheticDemand.start_date} to ${syntheticDemand.end_date}` : "Unavailable"} detail={syntheticDemand?.source || "Source unavailable"} />
          <Metric label="Chronological training" value={syntheticDemand?.split?.train_observations ?? "Unavailable"} detail="First observations; no shuffling" />
          <Metric label="Chronological holdout" value={syntheticDemand?.split?.holdout_observations ?? "Unavailable"} detail="Final observations" />
        </div>
        {syntheticDemand?.provenance ? <p className="text-xs text-slate-400">{syntheticDemand.provenance}{syntheticDemand.fallback_reason ? ` Fallback reason: ${syntheticDemand.fallback_reason}` : ""}</p> : null}
        <AnalyticsChart
          type="line"
          title="Daily synthetic demand (units/day)"
          description="Original dated observations; the series is split at the documented 670/60 boundary when all 730 points are present."
          data={syntheticSeries}
          xKey="date"
          series={[
            { key: "trainingDemand", name: "Training", color: "#60a5fa" },
            { key: "holdoutDemand", name: "Holdout", color: "#f59e0b" },
          ]}
          unit=" synthetic units/day"
          emptyMessage={research?.synthetic_demand_error || syntheticDemand?.error || "No valid daily synthetic demand observations were returned."}
        />
      </Panel>

      <div className="grid gap-5 border-b border-slate-800 pb-4 sm:grid-cols-3">
        <Metric label="Test forecast MAE" value={number(selectedHorizon?.mae)} detail="Synthetic load units; direct-horizon Seasonal LR" />
        <Metric label="Test forecast WAPE" value={percent(selectedHorizon ? selectedHorizon.wapePercent : null)} detail="Sum absolute error / sum actual demand" />
        <Metric label="Calibration replications" value={mainSeeds ?? "Unavailable"} detail="Independent simulation seeds for the main study" />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <SelectControl label="Forecast model" value={modelFilter} onChange={setModelFilter} options={[
          ["all", "All models"],
          ["lr", "Seasonal linear regression"],
          ["naive", "Previous-week naive"],
          ["hw", "Holt-Winters"],
        ]} />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <AnalyticsChart
          title="Forecast model comparison: MAE (synthetic load units)"
          description={`Direct forecast accuracy at H${horizon}; ${modelCount ?? "Unavailable"} matched seeds, same simulator and origin cohort.`}
          data={models}
          xKey="model"
          series={[{ key: "mae", name: "MAE", color: "#2dd4bf" }]}
          unit=" load units"
              emptyMessage={selectedModelMetrics.length === 0
                ? modelFilter === "all"
                  ? `No finite MAE rows from intervals_main.csv and intervals_models.csv exist for ${regime.toUpperCase()} at H${horizon}.`
                  : `No finite MAE row for ${modelNames[modelFilter]} exists in intervals_main.csv or intervals_models.csv for ${regime.toUpperCase()} at H${horizon}.`
                : `No finite MAE values from intervals_main.csv or intervals_models.csv exist for ${regime.toUpperCase()} at H${horizon}.`}
        />
        <AnalyticsChart
          title="Aggregate forecaster ablation: cost (simulation units)"
          description="Archived comparison_forecasters.csv, n=40 units. This summary is not regime/horizon-specific and is shown separately from the AR/H7 model filter."
          data={aggregateForecasters}
          xKey="model"
          series={[{ key: "cost", name: "HCCR objective", color: "#f59e0b" }]}
          unit=" cost units"
              emptyMessage="comparison_forecasters.csv is absent, malformed, or contains no finite cost values."
        />
        <AnalyticsChart
          title="Aggregate forecaster ablation: WAPE (%)"
          description="Archived source WAPE by model, not mixed with per-regime horizon metrics."
          data={aggregateForecasters}
          xKey="model"
          series={[{ key: "wapePercent", name: "WAPE", color: "#60a5fa" }]}
          unit="%"
              emptyMessage="comparison_forecasters.csv is absent, malformed, or contains no finite WAPE values."
        />
        <AnalyticsChart
          title="Forecast model comparison: WAPE (%)"
          description="Weighted absolute percentage error; weighted by total actual demand, not the unweighted mean of daily percentage errors."
          data={models}
          xKey="model"
          series={[{ key: "wapePercent", name: "WAPE", color: "#f59e0b" }]}
          unit="%"
              emptyMessage={`No finite WAPE values from intervals_main.csv or intervals_models.csv exist for ${regime.toUpperCase()} at H${horizon}.`}
        />
        <AnalyticsChart
          type="line"
          title="Seasonal LR error by horizon"
          description="Rolling test-origin MAE; each horizon is forecast directly and evaluated on the held-out test period."
          data={byHorizon}
          xKey="horizon"
          series={[{ key: "mae", name: "MAE", color: "#60a5fa" }]}
          unit=" load units"
              emptyMessage={`forecast_calibration_summary.csv has no finite MAE values for ${regime.toUpperCase()}.`}
        />
        <AnalyticsChart
          type="line"
          title="Seasonal LR WAPE by horizon"
          description="WAPE stays separate from MAE because it is dimensionless and demand-weighted."
          data={byHorizon}
          xKey="horizon"
          series={[{ key: "wapePercent", name: "WAPE", color: "#f472b6" }]}
          unit="%"
              emptyMessage={`forecast_calibration_summary.csv has no finite WAPE values for ${regime.toUpperCase()}.`}
        />
        <AnalyticsChart
          type="line"
          title="Central 80% residual interval coverage"
          description="Empirical fraction of held-out targets inside each policy's residual-quantile interval; nominal target is 80%, with no distribution-free guarantee."
          data={byHorizon}
          xKey="horizon"
          series={[
            { key: "hccrCoveragePercent", name: "HCCR horizon-specific", color: "#2dd4bf" },
            { key: "pooledCoveragePercent", name: "Pooled residuals", color: "#f59e0b" },
            { key: "nominalCoveragePercent", name: "Nominal 80%", color: "#94a3b8" },
          ]}
          unit="%"
              emptyMessage={`forecast_calibration_summary.csv has no finite interval-coverage values for ${regime.toUpperCase()}.`}
        />
        <AnalyticsChart
          type="line"
          title="Central 80% interval width (synthetic load units)"
          description="Mean upper-minus-lower residual-quantile interval width; narrower is not automatically better unless coverage is adequate."
          data={byHorizon}
          xKey="horizon"
          series={[
            { key: "hccrIntervalWidth", name: "HCCR horizon-specific", color: "#2dd4bf" },
            { key: "pooledIntervalWidth", name: "Pooled residuals", color: "#f59e0b" },
          ]}
          unit=" load units"
              emptyMessage={`forecast_calibration_summary.csv has no finite interval-width values for ${regime.toUpperCase()}.`}
        />
      </div>

      <Panel title={`Calibration detail at horizon ${horizon} days`} description={`Coverage standard deviations are across simulation seeds (n=${mainSeeds ?? "unavailable"}); they are not confidence intervals.`}>
        <ResearchTable
          rows={selectedHorizon ? [{ ...selectedHorizon, regime }] : []}
          columns={[
            { key: "regime", label: "Regime" },
            { key: "horizon", label: "Horizon" },
            { key: "hccrCoveragePercent", label: "HCCR coverage", format: percent },
            { key: "hccrCoverageSd", label: "HCCR across-seed SD", format: (value) => number(value, 3) },
            { key: "pooledCoveragePercent", label: "Pooled coverage", format: percent },
            { key: "pooledCoverageSd", label: "Pooled across-seed SD", format: (value) => number(value, 3) },
            { key: "hccrIntervalWidth", label: "HCCR width (units)", format: number },
            { key: "pooledIntervalWidth", label: "Pooled width (units)", format: number },
          ]}
        />
      </Panel>
      <Panel title="Paired forecaster policy-cost ablation" description="Positive model-minus-LR differences mean seasonal LR has lower simulated HCCR cost. Ten matched seeds; intervals are unadjusted.">
        <ResearchTable rows={modelPairs} columns={[
          { key: "comparison", label: "Model cost minus LR cost" },
          { key: "meanCostDifference", label: "Mean difference", format: number },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "simulations", label: "Seeds", format: (value) => value ?? "Unavailable" },
        ]} />
      </Panel>
      <Panel title="Earlier repository forecast experiment" description="Separate 730-day aggregate synthetic series; not mixed with the four-regime HCCR simulation. The archived 60-day model comparison and ablation each use one holdout origin.">
        <SelectControl label="Legacy forecast horizon" value={legacyHorizon} onChange={setLegacyHorizon} options={[[7, "7 days"], [14, "14 days"], [30, "30 days"], [60, "60 days"]]} />
        <div className="grid gap-5 xl:grid-cols-2">
          <AnalyticsChart type="bar" title="Legacy model comparison: MAE (legacy units)" description="Source forecast_models.json; one 60-day origin." data={legacyForecastComparison} xKey="model" series={[{ key: "mae", name: "MAE", color: "#60a5fa" }]} unit=" legacy units" emptyMessage="experiments/results/forecast_models.json is absent, malformed, or has no finite MAE values." />
          <AnalyticsChart type="bar" title={`Legacy horizon sensitivity H${legacyHorizon}: MAE (legacy units)`} description="Source horizon_sensitivity.json; rolling-origin results filtered by its supported horizon selector." data={legacySelectedHorizon} xKey="horizon" series={[
            { key: "naive_previous_week", name: "Previous-week naive", color: "#34d399" },
            { key: "holt_winters_weekly", name: "Holt-Winters", color: "#60a5fa" },
            { key: "seasonal_linear_regression", name: "Seasonal linear regression", color: "#f59e0b" },
          ]} unit=" legacy units" emptyMessage={`horizon_sensitivity.json contains no finite supported-model MAE values at H${legacyHorizon}.`} />
          <AnalyticsChart type="bar" title="Legacy feature ablation: MAE (legacy units)" description="Source feature_ablation.json; single 60-day origin." data={legacyFeatureAblations} xKey="ablation" series={[{ key: "mae", name: "MAE", color: "#f472b6" }]} unit=" legacy units" emptyMessage="experiments/results/feature_ablation.json is absent, malformed, or has no finite MAE values." />
        </div>
      </Panel>
    </div>
  );
}

function ReservationDecision({ regime, horizon }) {
  const [seed, setSeed] = useState("0");
  const [region, setRegion] = useState("0");
  const [origin, setOrigin] = useState("800");
  const [request, setRequest] = useState({ status: "idle", key: null, data: null, error: "" });
  const key = `${regime}:${seed}:${region}:${horizon}:${origin}`;
  const current = request.key === key ? request : { status: "idle", data: null, error: "" };

  async function loadDecision() {
    setRequest({ status: "loading", key, data: null, error: "" });
    try {
      const data = await getHccrReservationDecision({
        regime,
        seed: Number(seed),
        region: Number(region),
        horizon_days: Number(horizon),
        origin: Number(origin),
      });
      setRequest({ status: "success", key, data, error: "" });
    } catch (error) {
      setRequest({
        status: "error",
        key,
        data: null,
        error: error?.message || "Unable to calculate the selected research decision.",
      });
    }
  }

  const decisionInputs = [
    ["Seed", seed, setSeed, Array.from({ length: 30 }, (_, index) => [index, String(index)])],
    ["Region index", region, setRegion, [[0, "Region 0"], [1, "Region 1"], [2, "Region 2"], [3, "Region 3"]]],
  ];
  const decisions = current.data?.policies;

  return (
    <Panel
      title="Single-origin paper-policy decision"
      description="Recomputed from the frozen synthetic simulator. Validation chooses the gate; test demand is shown only as a retrospective outcome. No routing request is made."
    >
      <div className="flex flex-wrap items-end gap-3">
        {decisionInputs.map(([label, value, setter, options]) => (
          <SelectControl key={label} label={label} value={value} onChange={setter} options={options} />
        ))}
        <label className="flex min-w-36 flex-col gap-1 text-xs text-slate-300">
          <span>Simulation origin index</span>
          <input type="number" min="800" max="1071" value={origin} onChange={(event) => setOrigin(event.target.value)} className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white" />
        </label>
        <button type="button" onClick={loadDecision} disabled={current.status === "loading"} className="rounded-md bg-teal-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60">
          {current.status === "loading" ? "Calculating..." : "Calculate decision"}
        </button>
      </div>

      {current.status === "idle" ? <p className="mt-3 text-sm text-slate-400">Select a simulation seed, region, horizon and test origin, then calculate the policy decisions.</p> : null}
      {current.status === "loading" ? <p role="status" className="mt-3 text-sm text-slate-300">Running one deterministic simulation and applying the validation-fitted gate...</p> : null}
      {current.status === "error" ? <p role="alert" className="mt-3 text-sm text-rose-300">{current.error}</p> : null}
      {decisions ? (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Metric label="Direct-horizon point forecast" value={`${number(current.data.point_forecast_units)} synthetic load units`} detail={`${current.data.model}; simulation day ${current.data.origin_index}, H${current.data.horizon_days}`} />
            <Metric label="Base capacity" value={`${number(current.data.base_capacity_units)} synthetic load units`} detail={`Shortage penalty = ${number(current.data.shortage_penalty)} cost units per unmet unit`} />
          </div>
          <div className="mt-4 grid gap-5 xl:grid-cols-2">
            {[["hspec", "HCCR (horizon-specific)"], ["pooled", "Pooled residuals"]].map(([policy, title]) => {
              const record = decisions[policy];
              return (
                <section key={policy} className="border-t border-slate-700 pt-3">
                  <h4 className="font-semibold text-white">{title}</h4>
                  <p className={`mt-1 text-xs ${record.gate_open ? "text-emerald-300" : "text-amber-300"}`}>
                    Validation gate {record.gate_open ? "open" : "closed"}: {record.gate_explanation}
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-3">
                    <Metric label="Eligible residuals" value={`${record.residual_count} / ${record.minimum_residual_count} minimum`} />
                    <Metric label="Residual SD" value={record.residual_standard_deviation === null ? "Unavailable" : `${number(record.residual_standard_deviation)} units`} />
                    <Metric label="Central 80% interval" value={record.central_80_interval_units ? `${number(record.central_80_interval_units[0])} to ${number(record.central_80_interval_units[1])} units` : "Insufficient calibration data"} />
                    <Metric label="Selected reserve set" value={record.reserved_vehicle_count === 0 ? "No vehicles" : record.vehicle_counts_by_capacity.map((item) => `${item.count} x ${item.capacity_units}`).join("; ")} detail={`${number(record.reserved_capacity_units)} reserved capacity units`} />
                    <Metric label="Reservation cost" value={number(record.reservation_cost)} detail="Simulation cost units" />
                    <Metric label="Expected shortage" value={record.expected_shortage_units === null ? "Unavailable" : `${number(record.expected_shortage_units)} units`} />
                    <Metric label="Expected total objective" value={number(record.expected_total_objective)} detail="Reservation cost + penalty x expected scenario shortage" />
                    <Metric label="Realized test shortage" value={`${number(record.realized_test_shortage_units)} units`} detail={`Held-out actual demand ${number(record.realized_test_demand_units)} units; not used in selection`} />
                  </div>
                  <p className="mt-3 text-xs text-slate-400">
                    Validation mean costs: policy {number(record.validation_mean_total_cost)}; reactive {number(record.validation_reactive_mean_total_cost)}. Residuals are restricted to targets observed by the decision origin.
                  </p>
                </section>
              );
            })}
          </div>
          <p className="mt-3 text-xs text-amber-200">This is a synthetic research reservation decision, not an operational fleet recommendation. Reserved capacity is not added to the confirmed-order CVRP fleet.</p>
        </>
      ) : null}
    </Panel>
  );
}

function ReservationTab({ research, regime, horizon, setSensitivityParameter, sensitivityParameter }) {
  const policies = buildHccrPolicyMetrics(research, regime);
  const aggregatePolicies = buildHccrAggregatePolicyComparison(research);
  const policyHorizons = buildHccrPolicyHorizonMetrics(research, regime);
  const primary = buildHccrPrimaryComparisons(research, regime);
  const byHorizon = buildHccrHorizonComparisons(research, regime);
  const gates = buildHccrGateMetrics(research, regime, Number(horizon));
  const sensitivity = buildHccrSensitivityMetrics(research, regime, sensitivityParameter);
  const replication = buildHccrReplicationMetrics(research, regime);
  const mechanism = buildHccrMechanismMetrics(research, "mechanism_primary");
  const freshness = buildHccrMechanismMetrics(research, "freshness_primary");
  const disagreement = buildHccrDisagreementMetrics(research, regime);
  const params = { ...(research?.configuration?.sensitivity || {}), noise_scale: [0.5, 2.0] };

  return (
    <div className="space-y-6">
      <ReservationDecision regime={regime} horizon={horizon} />
      <Panel title="Gated policy comparison" description="Means over gated test decisions at horizons 1, 7 and 14, averaged by simulation seed. Costs are synthetic objective units; shortages are synthetic load units.">
        <div className="grid gap-5 xl:grid-cols-3">
          <AnalyticsChart type="bar" title="Aggregate total objective (cost units)" description="H1/H7/H14 aggregate means and 95% CIs are listed below; archived aggregate capacity uses nearest rounding." data={aggregatePolicies} xKey="policy" series={[{ key: "totalCost", name: "Total cost", color: "#2dd4bf" }]} unit=" cost units" emptyMessage="comparison_table.csv has no aggregate-scope rows with finite total costs." />
          <AnalyticsChart title="Reservation cost (simulation cost units)" description="Mean paid reserve cost, separate from shortage penalty and routing cost." data={policies} xKey="policy" series={[{ key: "reservationCost", name: "Reservation cost", color: "#60a5fa" }]} unit=" cost units" emptyMessage={`policy_levels_main.csv has no finite reservation costs for ${regime.toUpperCase()}.`} />
          <AnalyticsChart type="bar" title="Aggregate realized shortage (load units)" description="Unmet load units from the same aggregate policy table; not a count of unserved routes/orders." data={aggregatePolicies} xKey="policy" series={[{ key: "unmetUnits", name: "Unmet units", color: "#f59e0b" }]} unit=" load units" emptyMessage="comparison_table.csv has no aggregate-scope rows with finite unmet-load values." />
        </div>
        <ResearchTable rows={aggregatePolicies} columns={[
          { key: "policy", label: "Policy" },
          { key: "totalCost", label: "Total objective", format: number },
          { key: "costCiLow", label: "95% CI low", format: number },
          { key: "costCiHigh", label: "95% CI high", format: number },
          { key: "reservationCost", label: "Reserve cost", format: number },
          { key: "unmetUnits", label: "Unmet units", format: number },
          { key: "routeFeasibilityPercent", label: "Route feasible", format: percent },
        ]} />
        <details className="border-t border-slate-800 pt-3">
          <summary className="cursor-pointer text-sm text-slate-300">Per-regime, seed-aggregated detail</summary>
        <ResearchTable rows={policies} columns={[
          { key: "policy", label: "Policy" },
          { key: "totalCost", label: "Total objective", format: number },
          { key: "reservationCost", label: "Reserve cost", format: number },
          { key: "unmetUnits", label: "Unmet units", format: number },
          { key: "shortageDayRatePercent", label: "Shortage days", format: percent },
          { key: "reservedVehicles", label: "Vehicles reserved", format: number },
        ]} />
        </details>
      </Panel>

      <Panel title="Archived aggregate policy comparison" description="H1/H7/H14 aggregate means and 95% confidence intervals from comparison_table.csv. These archived results use nearest-integer base-capacity rounding; the paper's ceiling rule has not been rerun for these aggregates.">
        <div className="grid gap-5 xl:grid-cols-2">
          <AnalyticsChart
            type="bar"
            title="Aggregate total objective by policy (cost units)"
            description="Bars are stored aggregate means over the paper's primary horizons; confidence limits are listed below."
            data={aggregatePolicies}
            xKey="policy"
            series={[{ key: "totalCost", name: "Total objective", color: "#2dd4bf" }]}
            unit=" cost units"
            emptyMessage="comparison_table.csv has no aggregate-scope rows with finite total costs."
          />
          <AnalyticsChart
            type="bar"
            title="Aggregate realized shortage (synthetic load units)"
            description="Mean unmet units for the same aggregate policy rows; not CVRP unserved orders."
            data={aggregatePolicies}
            xKey="policy"
            series={[{ key: "unmetUnits", name: "Unmet load units", color: "#f59e0b" }]}
            unit=" load units"
            emptyMessage="comparison_table.csv has no aggregate-scope rows with finite unmet-load values."
          />
        </div>
        <ResearchTable rows={aggregatePolicies} columns={[
          { key: "policy", label: "Policy" },
          { key: "totalCost", label: "Total objective", format: number },
          { key: "costCiLow", label: "95% CI low", format: number },
          { key: "costCiHigh", label: "95% CI high", format: number },
          { key: "reservationCost", label: "Reservation cost", format: number },
          { key: "unmetUnits", label: "Unmet units", format: number },
          { key: "routeFeasibilityPercent", label: "CVRP feasible", format: percent },
          { key: "routingInstances", label: "Routing instances", format: (value) => value ?? "Unavailable" },
        ]} />
      </Panel>

      <Panel title="Horizon-specific gated policy cost" description="Mean total reservation-plus-shortage objective at each test horizon for the selected regime. These are archived aggregate outputs and retain their original rounding rule.">
        <AnalyticsChart
          type="bar"
          title="Mean objective by policy and horizon (synthetic cost units)"
          description="Each series is one archived gated policy; horizons are H1, H7, H14 and H28."
          data={policyHorizons}
          xKey="horizon"
          series={[
            { key: "reactive", name: "Reactive", color: "#94a3b8" },
            { key: "point", name: "Point forecast", color: "#60a5fa" },
            { key: "buffer", name: "Fixed buffer", color: "#f59e0b" },
            { key: "pooled", name: "Pooled residuals", color: "#f472b6" },
            { key: "hspec", name: "HCCR", color: "#2dd4bf" },
            { key: "robust", name: "Robust cover", color: "#a78bfa" },
            { key: "oracle", name: "Oracle (unattainable)", color: "#34d399" },
          ]}
          unit=" cost units"
          emptyMessage={`operational_main.csv has no finite gated cost rows for ${regime.toUpperCase()} at the included horizons.`}
        />
      </Panel>

      <Panel title={`Validation gate at horizon ${horizon} days`} description="Gate-open rates over seeds; each policy is gated by whether its validation-window mean cost is below reactive. This is not a test-period selection.">
        <ResearchTable rows={gates} columns={[
          { key: "policy", label: "Policy" },
          { key: "openRatePercent", label: "Gate open rate", format: percent },
        ]} />
      </Panel>

      <Panel title={`Paired primary comparisons (${PRIMARY_HORIZONS})`} description="Delta = comparator cost - HCCR cost; positive values favor HCCR. Confidence intervals are seed-level percentile bootstrap. Holm p-values cover the paper's 20 confirmatory tests (5 comparisons x 4 regimes); oracle is descriptive.">
        <ResearchTable rows={primary} columns={[
          { key: "comparison", label: "Comparator" },
          { key: "meanDelta", label: "Paired delta", format: number },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "seeds", label: "Seeds", format: (value) => value ?? "Unavailable" },
          { key: "effectSizeDz", label: "Effect size dz", format: number },
          { key: "pWilcoxon", label: "Wilcoxon p", format: (value) => value === null ? "Unavailable" : value.toExponential(2) },
          { key: "pHolm", label: "Holm-adjusted p", format: (value) => value === null ? "Not in confirmatory family" : value.toExponential(2) },
        ]} />
      </Panel>

      <Panel title="HCCR versus pooled by horizon" description="Per-horizon paired differences are exploratory, unadjusted rows; do not read their p-values as part of the Holm-corrected primary family.">
        <ResearchTable rows={byHorizon} columns={[
          { key: "horizon", label: "Horizon" },
          { key: "pooledMinusHccr", label: "Pooled - HCCR cost", format: number },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "seeds", label: "Seeds", format: (value) => value ?? "Unavailable" },
          { key: "effectSizeDz", label: "Effect size dz", format: number },
          { key: "unadjustedP", label: "Unadjusted p", format: (value) => value === null ? "Unavailable" : value.toExponential(2) },
        ]} />
      </Panel>

      <Panel title="Independent-seed replication" description="Fresh seeds 100-129; p-values are unadjusted in this replication. The horizon reversal is retained and is not operational evidence.">
        <ResearchTable rows={replication} columns={[
          { key: "horizons", label: "Horizon set" },
          { key: "pooledMinusHccr", label: "Pooled - HCCR", format: number },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "seeds", label: "Seeds", format: (value) => value ?? "Unavailable" },
          { key: "unadjustedP", label: "Unadjusted p", format: (value) => value === null ? "Unavailable" : value.toExponential(2) },
          { key: "percentOfHccr", label: "% of HCCR objective", format: percent },
        ]} />
      </Panel>

      <Panel title="Pre-registered mechanism and relative-freshness tests" description="Theta uses an anticipative residual window and is a non-deployable diagnostic. Psi ages only pooled calibration information and is deployable within the simulator. The two analyses use separate Holm families.">
        <h4 className="mb-2 text-sm font-semibold text-slate-200">Anticipative-window diagnostic (not deployable)</h4>
        <ResearchTable rows={mechanism} columns={[
          { key: "contrast", label: "Contrast" },
          { key: "meanEffect", label: "Mean effect" },
          { key: "ciLow", label: "95% CI low" },
          { key: "ciHigh", label: "95% CI high" },
          { key: "simulations", label: "Simulations", format: (value) => value ?? "Unavailable" },
          { key: "effectSizeDz", label: "Effect size dz", format: number },
          { key: "holmP", label: "Holm-adjusted p", format: (value) => value === null ? "Unavailable" : value.toExponential(2) },
        ]} />
        <h4 className="mb-2 mt-5 text-sm font-semibold text-slate-200">Deployable relative-freshness intervention</h4>
        <ResearchTable rows={freshness} columns={[
          { key: "contrast", label: "Contrast" },
          { key: "meanEffect", label: "Mean effect" },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "simulations", label: "Simulations", format: (value) => value ?? "Unavailable" },
          { key: "effectSizeDz", label: "Effect size dz", format: number },
          { key: "holmP", label: "Holm-adjusted p", format: (value) => value === null ? "Unavailable" : value.toExponential(2) },
        ]} />
      </Panel>

      <Panel title="Reserve-set disagreement" description="Share of test decisions selecting different discrete sets; intervals are seed-level bootstrap CIs. Coverage and decision changes are distinct outcomes.">
        <ResearchTable rows={disagreement} columns={[
          { key: "decisions", label: "Decision set" },
          { key: "horizon", label: "Horizon" },
          { key: "disagreementPercent", label: "Disagreement", format: percent },
          { key: "ciLowPercent", label: "95% CI low", format: percent },
          { key: "ciHighPercent", label: "95% CI high", format: percent },
          { key: "simulations", label: "Simulations", format: (value) => value ?? "Unavailable" },
          { key: "maximumSimulationPercent", label: "Maximum seed disagreement", format: percent },
        ]} />
      </Panel>

      <Panel title="Sensitivity: HCCR against pooled residuals" description="Paired cost delta by one-at-a-time setting; sensitivity runs use 15 seeds per regime and are descriptive, not confirmatory.">
        <div className="mb-3">
          <SelectControl label="Sensitivity parameter" value={sensitivityParameter} onChange={setSensitivityParameter} options={Object.keys(params).length ? Object.keys(params).map((key) => [key, SENSITIVITY_OPTIONS.find((entry) => entry[0] === key)?.[1] || key]) : SENSITIVITY_OPTIONS} />
        </div>
        <AnalyticsChart type="line" title="Pooled cost minus HCCR cost (synthetic cost units)" description="Positive values favor HCCR. Error intervals are listed in the table from the stored seed-bootstrap artifact." data={sensitivity} xKey="setting" series={[{ key: "pooledMinusHccr", name: "Pooled - HCCR", color: "#f59e0b" }]} unit=" cost units" emptyMessage={`sensitivity_summary.csv has no finite pooled-comparison rows for ${regime.toUpperCase()} and ${sensitivityParameter}.`} />
        <ResearchTable rows={sensitivity} columns={[
          { key: "setting", label: "Setting" },
          { key: "pooledMinusHccr", label: "Paired delta", format: number },
          { key: "ciLow", label: "95% CI low", format: number },
          { key: "ciHigh", label: "95% CI high", format: number },
          { key: "simulations", label: "Simulations", format: (value) => value ?? "Unavailable" },
        ]} />
      </Panel>
    </div>
  );
}

function RoutingTab({ research }) {
  const routing = buildHccrRoutingMetrics(research);
  const capacityGap = buildHccrCapacityFeasibilityMetrics(research);
  const legacyArtifacts = research?.legacy_artifacts || {};
  const legacyCvrp = buildCvrpBenchmarkData({ cvrp_benchmark: legacyArtifacts.legacy_cvrp_benchmark });
  const legacyHgfc = buildHgfcAdvisoryData({ hgfc_advisory: legacyArtifacts.legacy_hgfc_advisory });
  const legacyPaired = buildPairedRoutingData({ reactive_vs_hgfc: legacyArtifacts.legacy_reactive_vs_hgfc });
  return (
    <div className="space-y-6">
      <aside className="border-l-2 border-amber-400 py-1 pl-3 text-sm text-amber-100">
        Forecasts influence only simulated reservation and confirmed-demand activation. OR-Tools receives confirmed orders and active-fleet capacities; forecasts are never CVRP demand or capacity constraints. Results are synthetic, not operational or road-network validation.
      </aside>
      <div className="grid gap-5 xl:grid-cols-2">
        <AnalyticsChart title="Confirmed-order CVRP feasibility (%)" description="Share of routing instances where OR-Tools served all confirmed orders; bars are policy means, intervals are in the table." data={routing} xKey="policy" series={[{ key: "feasiblePercent", name: "Feasible instances", color: "#2dd4bf" }]} unit="%" emptyMessage="routing_summary.csv has no policy rows with a finite feasibility rate." />
        <AnalyticsChart title="Solver distance on solved instances (km)" description="Mean Haversine objective distance among successful routes only; infeasible instances do not contribute zero-distance observations." data={routing} xKey="policy" series={[{ key: "distanceSolvedKm", name: "Solved-route distance", color: "#60a5fa" }]} unit=" km" emptyMessage="routing_summary.csv has no finite successful-route distances; infeasible routes have no measured distance." />
      </div>
      <ResearchTable rows={routing} columns={[
        { key: "policy", label: "Policy" },
        { key: "instances", label: "Instances", format: (value) => value ?? "Unavailable" },
        { key: "feasiblePercent", label: "Feasible", format: percent },
        { key: "feasibilityCiLowPercent", label: "95% CI low", format: percent },
        { key: "feasibilityCiHighPercent", label: "95% CI high", format: percent },
        { key: "distanceSolvedKm", label: "Distance, solved only (km)", format: number },
        { key: "matchedDistanceKm", label: "Distance on 63 all-policy matches (km)", format: number },
        { key: "meanRuntimeSeconds", label: "Solver runtime (s)", format: number },
        { key: "reservationCost", label: "Reserve cost", format: number },
        { key: "activatedVehicles", label: "Activated vehicles", format: number },
      ]} />
      <AnalyticsChart
        type="bar"
        title="Aggregate-capacity feasible, but CVRP unroutable (instances)"
        description="The paper separates a scalar capacity shortfall from actual indivisible-order routing feasibility. This is the count where aggregate capacity covered demand but OR-Tools still failed."
        data={capacityGap}
        xKey="policy"
        series={[
          { key: "aggregateFeasibleInstances", name: "Aggregate capacity sufficient", color: "#60a5fa" },
          { key: "routingInfeasibleDespiteAggregate", name: "Still unroutable", color: "#f59e0b" },
        ]}
        unit=" instances"
        emptyMessage="routing_capacity_vs_feasibility.csv has no policy rows with finite aggregate-feasible counts."
      />
      <Panel title="Earlier repository CVRP and HGFCI artifacts" description="Legacy six-scenario outputs use a different aggregate synthetic series and the older HGFCI advisory experiment. They are not merged with the paper HCCR routing study.">
        {legacyCvrp.length || legacyHgfc.length || legacyPaired.length ? (
          <div className="grid gap-5 xl:grid-cols-2">
            <AnalyticsChart type="bar" title="Legacy CVRP: confirmed demand versus capacity" description="Six stored synthetic cases; feasibility is separate from advisory outputs." data={legacyCvrp} xKey="scenario" series={[
              { key: "demand", name: "Confirmed demand", color: "#60a5fa" },
              { key: "capacity", name: "Fleet capacity", color: "#2dd4bf" },
            ]} unit=" load units" emptyMessage="experiments/results/cvrp_benchmark.json has no valid demand/capacity cases." />
            <AnalyticsChart type="bar" title="Legacy HGFCI point-advisory risk" description="Legacy HGFCI risk artifact; it is not horizon-specific residual calibration or HCCR." data={legacyHgfc} xKey="leadDays" series={[{ key: "risk", name: "Capacity risk", color: "#f59e0b" }]} unit=" legacy units" emptyMessage="experiments/results/hgfc_advisory.json has no finite capacity-risk values." />
            <AnalyticsChart type="bar" title="Legacy reactive versus HGFCI route distance (km)" description="Paired artifacts reuse identical CVRP arms by design. Infeasible routes have no distance and are not shown as zero." data={legacyPaired} xKey="scenario" series={[
              { key: "reactiveDistance", name: "Reactive", color: "#60a5fa" },
              { key: "advisoryDistance", name: "HGFCI arm", color: "#f59e0b" },
            ]} unit=" km" emptyMessage="experiments/results/reactive_vs_hgfc.json has no measured feasible-route distances." />
          </div>
        ) : <p className="py-5 text-sm text-slate-400">Legacy CVRP/HGFCI JSON outputs are absent from this runtime; HCCR routing charts above remain available.</p>}
      </Panel>
      <p className="text-xs text-slate-400">The routing study used 10 seeds x 6 outcome-blind instances per seed at horizon 7. Distance is the optimizer's local Haversine objective, not OSRM road distance. A route-infeasible instance has no measured route distance.</p>
    </div>
  );
}

function RealDataTab({ research }) {
  const meta = research?.real_data_metadata;
  const publicDataset = research?.public_dataset;
  const monthlyRentals = buildPublicBikeMonthlyData(publicDataset);
  const [penalty, setPenalty] = useState(String(meta?.primary_pi ?? 4));
  const calibration = buildHccrRealDataCalibration(research);
  const differences = buildHccrRealDataMetrics(research, Number(penalty));
  return (
    <div className="space-y-6">
      <aside className="border-l-2 border-sky-400 py-1 pl-3 text-sm text-sky-100">
        Separate descriptive public-data check: UCI Bike Sharing rental counts are supply-censored and are not logistics orders. This dataset has no vehicle capacities, coordinates or routing evaluation and is not combined with synthetic simulation results.
      </aside>
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Public-data days" value={publicDataset?.observation_count ?? "Unavailable"} detail="Rows read from day.csv" />
        <Metric label="Daily date range" value={publicDataset?.start_date && publicDataset?.end_date ? `${publicDataset.start_date} to ${publicDataset.end_date}` : "Unavailable"} detail={publicDataset?.source_path || "Source file unavailable"} />
        <Metric label="Total rentals" value={publicDataset?.total_rentals?.toLocaleString?.() ?? "Unavailable"} detail="Sum of daily cnt values" />
        <Metric label="Mean rentals per day" value={number(publicDataset?.mean_daily_rentals)} detail="Actual daily cnt observations" />
      </div>
      <div className="grid gap-5 sm:grid-cols-2">
        <Metric label="Held-out origins" value={meta?.n_test_origins ?? "Unavailable"} detail="Block-bootstrap unit remains temporal origins" />
        <Metric label="Segments" value={Array.isArray(meta?.segments) ? meta.segments.length : "Unavailable"} detail={Array.isArray(meta?.segments) ? meta.segments.join(", ") : "Unavailable"} />
      </div>
      <Panel title="Bike-sharing rental time series (monthly totals)" description={`${publicDataset?.source || "UCI Bike Sharing"}; source ${publicDataset?.source_path || "research_hccr/realdata/data/day.csv"}. Monthly totals are aggregated from daily cnt values; rentals/month, not logistics demand.`}>
        {publicDataset?.error ? <p className="text-sm text-amber-200">{publicDataset.error}</p> : null}
        <AnalyticsChart
          type="line"
          title="Monthly rental counts"
          description="24 monthly points aggregated from the original daily public dataset."
          data={monthlyRentals}
          xKey="month"
          series={[{ key: "totalRentals", name: "Total rentals", color: "#60a5fa" }]}
          unit=" rentals/month"
          emptyMessage={publicDataset?.error || "The bundled public daily bike-sharing CSV is missing or contains no valid monthly rental totals."}
        />
      </Panel>
      <div className="flex flex-wrap items-end gap-3">
        <SelectControl label="Shortage penalty" value={penalty} onChange={setPenalty} options={[[1, "1"], [2, "2"], [4, "4 (primary)"], [9, "9"], [19, "19"]]} />
      </div>
      <div className="grid gap-5 xl:grid-cols-2">
        <AnalyticsChart type="line" title="Public-data forecast WAPE by horizon (%)" description="Measured on bike rental counts after training-period-only scaling; no routing inference." data={calibration} xKey="horizon" series={[{ key: "wapePercent", name: "WAPE", color: "#60a5fa" }]} unit="%" emptyMessage="realdata_forecast_calibration.csv has no finite WAPE values by horizon." />
        <AnalyticsChart type="line" title="Public-data central 80% coverage (%)" description="Horizon-specific versus pooled residual intervals; nominal coverage is 80%. This remains a single-city diagnostic." data={calibration} xKey="horizon" series={[
          { key: "hccrCoveragePercent", name: "HCCR", color: "#2dd4bf" },
          { key: "pooledCoveragePercent", name: "Pooled", color: "#f59e0b" },
          { key: "nominalCoveragePercent", name: "Nominal 80%", color: "#94a3b8" },
        ]} unit="%" emptyMessage="realdata_forecast_calibration.csv has no finite interval-coverage values by horizon." />
      </div>
      <AnalyticsChart
        type="line"
        title={`Public-data pooled-minus-HCCR cost by horizon (normalized cost units; pi=${penalty})`}
        description="Positive values favor HCCR. The table below carries the 28-day block-bootstrap intervals; no delivery routing is evaluated."
        data={differences}
        xKey="horizon"
        series={[{ key: "pooledMinusHccr", name: "Pooled - HCCR", color: "#f59e0b" }]}
        unit=" normalized cost units"
        emptyMessage={`realdata_delta.csv has no finite cost deltas for shortage penalty ${penalty}.`}
      />
      <Panel title={`Public-data pooled-minus-HCCR cost at penalty ${penalty}`} description="Positive favors HCCR. The confidence interval uses the study's 28-day block bootstrap; these are normalized scenario cost units, not observed monetary cost.">
        <ResearchTable rows={differences} columns={[
          { key: "horizon", label: "Horizon" },
          { key: "pooledMinusHccr", label: "Pooled - HCCR", format: number },
          { key: "ciLow", label: "95% block-bootstrap CI low", format: number },
          { key: "ciHigh", label: "95% block-bootstrap CI high", format: number },
          { key: "disagreementPercent", label: "Decision disagreement", format: percent },
          { key: "testOrigins", label: "Test origins", format: (value) => value ?? "Unavailable" },
        ]} />
      </Panel>
      <p className="text-xs text-slate-400">No delivery-route, fleet-capacity, or operational performance claim can be drawn from this dataset.</p>
    </div>
  );
}

function ReproducibilityTab({ research, onDownload }) {
  const config = research?.configuration || {};
  const real = research?.real_data_metadata || {};
  const manifest = research?.artifact_manifest || [];
  const methodWarnings = research?.method_discrepancies || [];
  const [artifact, setArtifact] = useState("operational_main.csv");
  const downloads = research?.downloads || [];
  const downloadChoices = downloads.map((filename) => [filename, filename]);
  return (
    <div className="space-y-6">
      <aside className="border-l-2 border-teal-400 py-1 pl-3 text-sm text-teal-100">
        Results were loaded from the supplied frozen Research_files package. The archived CSVs are not regenerated by this page; execution timestamps were not recorded in the source outputs.
      </aside>
      <Panel title="Synthetic study configuration" description="All primary settings come from configs/study_config.json; test data are excluded from fitting, residual eligibility and validation gate selection.">
        <ResearchTable rows={[
          { setting: "Daily horizon length", value: config.T, detail: "synthetic simulation days" },
          { setting: "Regions", value: config.n_regions, detail: Array.isArray(config.region_levels) ? `${config.region_levels.length} synthetic demand series` : "Unavailable" },
          { setting: "Chronological initial fit", value: config.t_calibration_start, detail: "days [0, 399]" },
          { setting: "Calibration starts", value: config.t_calibration_start, detail: "causal residual window; max 200 per horizon" },
          { setting: "Validation starts", value: config.t_validation_start, detail: "buffer and horizon-gate selection" },
          { setting: "Test starts", value: config.t_test_start, detail: "held-out decision origins" },
          { setting: "Horizons", value: Array.isArray(config.horizons) ? config.horizons.join(", ") : null, detail: "days" },
          { setting: "Main seeds", value: config.n_seeds_main, detail: "per regime" },
          { setting: "Reservation candidates", value: "27", detail: "3 vehicle types; 0, 1 or 2 of each" },
          { setting: "Shortage penalty", value: config.shortage_penalty, detail: "simulation cost units per unmet load unit" },
          { setting: "Execution timestamp", value: research?.provenance?.created_at, detail: research?.provenance?.created_at_note },
        ]} columns={[
          { key: "setting", label: "Setting" },
          { key: "value", label: "Value" },
          { key: "detail", label: "Definition" },
        ]} />
      </Panel>
      <Panel title="Separate public-data source" description="This diagnostic is reported separately from synthetic simulator results.">
        <ResearchTable rows={[
          { setting: "Source", value: real.source, detail: "UCI Bike Sharing; CC BY 4.0 per supplied study metadata" },
          { setting: "Observations", value: real.n_days, detail: "daily rental counts" },
          { setting: "Temporal split", value: real.split ? `${real.split.t_calibration_start}/${real.split.t_validation_start}/${real.split.t_test_start}/${real.split.t_test_last_origin}` : null, detail: "fit / validation / test boundaries" },
          { setting: "Routing evaluation", value: "Not performed", detail: "No order, vehicle-capacity or route data" },
        ]} columns={[
          { key: "setting", label: "Field" },
          { key: "value", label: "Value" },
          { key: "detail", label: "Notes" },
        ]} />
      </Panel>
      <Panel title="Artifact export" description="Download the original stored CSV/JSON evidence; no chart values are hard-coded in the browser.">
        {downloadChoices.length > 0 ? (
          <div className="flex flex-wrap items-end gap-3">
            <SelectControl label="Research artifact" value={artifact} onChange={setArtifact} options={downloadChoices} />
            <button type="button" onClick={() => onDownload(artifact)} className="rounded-md border border-teal-500 px-4 py-2 text-sm font-medium text-teal-100 hover:bg-teal-500/10">Download artifact</button>
          </div>
        ) : <p className="py-3 text-sm text-slate-400">No downloadable research artifacts are available.</p>}
      </Panel>
      <details className="border-t border-slate-800 pt-4 text-sm text-slate-300">
        <summary className="cursor-pointer font-medium text-slate-200">Artifact audit ({manifest.filter((item) => item.status === "available").length} available / {manifest.length} listed)</summary>
        <ResearchTable rows={manifest} columns={[
          { key: "filename", label: "Artifact" },
          { key: "result_key", label: "Dashboard use", format: (value) => value || "Download only" },
          { key: "required", label: "Requirement", format: (value) => value ? "Required" : "Optional" },
          { key: "status", label: "Status" },
          { key: "size_bytes", label: "Bytes", format: (value) => typeof value === "number" ? value.toLocaleString() : "Unavailable" },
        ]} emptyMessage="No artifacts were discovered." />
        {research?.unavailable_optional_artifacts?.length ? (
          <p className="mt-2 text-xs text-slate-400">Optional artifacts absent or invalid: {research.unavailable_optional_artifacts.join(", ")}</p>
        ) : null}
        {methodWarnings.map((warning) => <p key={warning} className="mt-2 border-l-2 border-amber-500 pl-3 text-xs text-amber-200">Method audit: {warning}</p>)}
      </details>
      <p className="text-xs text-slate-400">The supplied paper package also reports independent-seed, mechanism, sensitivity and model-ablation outputs. See the downloadable result CSVs and bundled preregistration/audit documents for sample counts and study-specific boundaries.</p>
    </div>
  );
}

export default function HccrResearchDashboard() {
  const [research, setResearch] = useState(null);
  const [loadState, setLoadState] = useState({ status: "loading", message: "" });
  const [activeTab, setActiveTab] = useState("forecast");
  const [regime, setRegime] = useState("ar");
  const [horizon, setHorizon] = useState("7");
  const [modelFilter, setModelFilter] = useState("all");
  const [sensitivityParameter, setSensitivityParameter] = useState("capacity_pressure_kappa");
  const [downloadError, setDownloadError] = useState("");
  const dashboardState = resolveHccrDashboardState(loadState.status, research, loadState.message);
  const unavailableOptionalCount = research?.unavailable_optional_artifacts?.length || 0;

  useEffect(() => {
    let active = true;
    Promise.allSettled([getHccrResearchAnalytics(), getResearchAnalytics()]).then(([hccr, legacy]) => {
      if (!active) return;
      if (hccr.status === "rejected") {
        setLoadState({ status: "error", message: hccr.reason?.message || "Research artifacts could not be loaded." });
        return;
      }
      const syntheticDemand = legacy.status === "fulfilled"
        ? legacy.value?.synthetic_demand
        : null;
      setResearch({
        ...hccr.value,
        synthetic_demand: syntheticDemand,
        synthetic_demand_error: legacy.status === "rejected"
          ? legacy.reason?.message || "The synthetic demand endpoint could not be loaded."
          : syntheticDemand?.error || null,
      });
      setLoadState({ status: hccr.value?.status === "available" ? "success" : "partial", message: "" });
    });
    return () => { active = false; };
  }, []);

  const horizonMetrics = useMemo(() => buildHccrHorizonMetrics(research, regime), [research, regime]);
  const horizonValue = Number(horizon);
  const selectedHorizon = horizonMetrics.find((row) => row.horizonDays === horizonValue);
  const activeContent = {
    forecast: <ForecastTab research={research} regime={regime} horizon={horizon} modelFilter={modelFilter} setModelFilter={setModelFilter} />,
    reservation: <ReservationTab research={research} regime={regime} horizon={horizon} setSensitivityParameter={setSensitivityParameter} sensitivityParameter={sensitivityParameter} />,
    routing: <RoutingTab research={research} />,
    real: <RealDataTab research={research} />,
    repro: <ReproducibilityTab research={research} onDownload={async (filename) => {
      setDownloadError("");
      try {
        await downloadHccrArtifact(filename);
      } catch (error) {
        setDownloadError(error?.message || "Artifact download failed.");
      }
    }} />,
  }[activeTab];

  if (dashboardState.status === "loading") {
    return <LoadingSpinner size="lg" label={dashboardState.message} fullScreen />;
  }
  if (dashboardState.status === "error" || dashboardState.status === "empty") {
    return <section className="space-y-4"><h2 className="text-2xl font-bold text-white">Research Analytics</h2><p role="alert" className="border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">{dashboardState.message}</p></section>;
  }

  return (
    <section className="space-y-5">
      <header>
        <h2 className="text-2xl font-bold text-white">HCCR Research Analytics</h2>
        <p className="mt-1 max-w-4xl text-sm text-slate-300">Horizon-specific residual calibration versus pooled residuals, reservation policy outcomes, and confirmed-order routing diagnostics from the frozen research study.</p>
      </header>

      <aside className={`border-l-2 py-2 pl-3 text-sm ${dashboardState.status === "partial" ? "border-amber-400 text-amber-100" : "border-teal-400 text-teal-100"}`}>
        Research outputs loaded. Synthetic and public-data diagnostics are separate; forecasts guide reservation only and never enter CVRP demand or capacity.
        {dashboardState.status === "partial" ? ` Required artifacts unavailable: ${dashboardState.message || "see artifact audit"}.` : null}
        {unavailableOptionalCount > 0 ? ` ${unavailableOptionalCount} optional artifacts unavailable; core charts remain enabled.` : null}
      </aside>

      <div className="flex flex-wrap gap-1 border-b border-slate-700" role="tablist" aria-label="Research analytics sections">
        {TABS.map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={activeTab === id} onClick={() => setActiveTab(id)} className={`border-b-2 px-3 py-2 text-sm ${activeTab === id ? "border-teal-400 text-white" : "border-transparent text-slate-400 hover:text-slate-200"}`}>
            {label}
          </button>
        ))}
      </div>

      {activeTab !== "real" && activeTab !== "repro" ? (
        <FilterBar regime={regime} setRegime={setRegime} horizon={horizon} setHorizon={setHorizon} />
      ) : null}

      {activeContent}

      {activeTab === "forecast" && selectedHorizon ? (
        <p className="text-xs text-slate-500">Selected forecast: horizon {horizonValue} days; HCCR interval empirical coverage {percent(selectedHorizon.hccrCoveragePercent)}. Model comparison contains {research?.configuration?.n_seeds_forecast_models ?? "unavailable"} seeds per regime; calibration results contain {research?.configuration?.n_seeds_main ?? "unavailable"} main-study seeds.</p>
      ) : null}
      {downloadError ? <p role="alert" className="text-sm text-rose-300">{downloadError}</p> : null}
    </section>
  );
}
