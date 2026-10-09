import { useEffect, useMemo, useState } from "react";
import AnalyticsChart from "../components/AnalyticsChart";
import LoadingSpinner from "../components/LoadingSpinner";
import MetricCard from "../components/MetricCard";
import {
  buildCvrpBenchmarkData,
  buildFeatureAblationData,
  buildForecastComparisonData,
  buildHgfcAdvisoryData,
  buildHorizonSensitivityData,
  buildPairedRoutingData,
  buildSyntheticDemandSeries,
  getResearchAnalytics,
} from "../services/analyticsService";

function DemandIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M4 14V5h16v9" />
      <path d="M7 19h10" />
      <path d="M12 9v7" />
    </svg>
  );
}

function RangeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M8 3v4M16 3v4M3 10h18" />
    </svg>
  );
}

function AverageIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M4 17.5V7.5" />
      <path d="M10 17.5V4.5" />
      <path d="M16 17.5v-9" />
      <path d="M22 17.5v-15" />
    </svg>
  );
}

function formatDateRange(startDate, endDate) {
  if (!startDate && !endDate) {
    return "N/A";
  }
  if (startDate === endDate) {
    return startDate || "N/A";
  }
  return `${startDate || "?"} → ${endDate || "?"}`;
}

export default function ResearchAnalytics() {
  const [research, setResearch] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadResearchAnalytics() {
      try {
        setLoading(true);
        setError("");
        const payload = await getResearchAnalytics();
        if (!mounted) {
          return;
        }
        setResearch(payload);
      } catch (requestError) {
        if (!mounted) {
          return;
        }
        setError(requestError?.response?.data?.detail || "Unable to load research analytics.");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadResearchAnalytics();

    return () => {
      mounted = false;
    };
  }, []);

  const syntheticDemand = research?.synthetic_demand ?? {};
  const demandSeries = useMemo(() => buildSyntheticDemandSeries(research), [research]);
  const forecastComparison = useMemo(() => buildForecastComparisonData(research), [research]);
  const horizonSensitivity = useMemo(() => buildHorizonSensitivityData(research), [research]);
  const featureAblation = useMemo(() => buildFeatureAblationData(research), [research]);
  const cvrpBenchmark = useMemo(() => buildCvrpBenchmarkData(research), [research]);
  const hgfcAdvisory = useMemo(() => buildHgfcAdvisoryData(research), [research]);
  const pairedRouting = useMemo(() => buildPairedRoutingData(research), [research]);
  const experimentConfig = research?.forecast_models?.configuration;
  const comparisonOrigins = research?.forecast_models?.results?.[0]?.forecast_origins;
  const emptyMessage = (artifact, fallback) => research?.[artifact]?.error || fallback;

  const summaryCards = [
    {
      title: "Daily observations",
      value: Number.isFinite(syntheticDemand.count) ? syntheticDemand.count : "--",
      icon: <DemandIcon />,
      color: "teal",
      subtitle: "Synthetic demand records",
    },
    {
      title: "Date range",
      value: formatDateRange(syntheticDemand.start_date, syntheticDemand.end_date),
      icon: <RangeIcon />,
      color: "blue",
      subtitle: "Research dataset window",
    },
    {
      title: "Average daily demand",
      value: Number.isFinite(syntheticDemand.average_demand)
        ? `${Number(syntheticDemand.average_demand).toFixed(2)}`
        : "--",
      icon: <AverageIcon />,
      color: "violet",
      subtitle: "Synthetic dataset units per day",
    },
  ];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-white">Research Analytics</h2>
        <p className="mt-1 text-sm text-slate-300">
          Synthetic demand, forecast comparisons, horizon sensitivity, and advisory-only HGFCI outputs.
        </p>
      </header>

      {loading ? (
        <LoadingSpinner size="lg" label="Loading research analytics..." fullScreen />
      ) : error ? (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : (
        <>
          <aside className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4 text-sm text-amber-100">
            All research results use synthetic demand, not live fleet measurements. The reactive/HGFCI
            artifact reuses identical confirmed orders and fleet inputs; it checks non-interference and
            does not evaluate operational benefit. The model comparison uses {comparisonOrigins ?? "unavailable"}
            {comparisonOrigins === 1 ? " forecast origin" : " forecast origins"}.
            {experimentConfig
              ? ` Evaluation: ${experimentConfig.training_days}-day chronological training prefix, ${experimentConfig.holdout_days}-day holdout, seed ${experimentConfig.seed}.`
              : " Evaluation configuration is unavailable."}
          </aside>

          <div className="grid gap-4 md:grid-cols-3">
            {summaryCards.map((card) => (
              <MetricCard key={card.title} {...card} />
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <AnalyticsChart
              type="line"
              title="Synthetic daily demand time series"
              data={demandSeries}
              xKey="date"
              series={[{ key: "demand", name: "Demand", color: "#2dd4bf" }]}
              emptyMessage="No synthetic demand observations are available."
            />

            <AnalyticsChart
              type="bar"
              title="60-day model comparison (MAE)"
              data={forecastComparison}
              xKey="model"
              series={[{ key: "mae", name: "MAE", color: "#60a5fa" }]}
              unit=" synthetic units"
              emptyMessage={emptyMessage("forecast_models", "Forecast model comparison data is not available.")}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <AnalyticsChart
              type="bar"
              title="Horizon sensitivity"
              data={horizonSensitivity}
              xKey="horizon"
              series={[
                { key: "naive_previous_week", name: "Previous-week naive", color: "#34d399" },
                { key: "holt_winters_weekly", name: "Holt-Winters", color: "#60a5fa" },
                { key: "seasonal_linear_regression", name: "Seasonal linear regression", color: "#f59e0b" },
              ]}
              unit=" synthetic units"
              emptyMessage={emptyMessage("horizon_sensitivity", "Horizon sensitivity results are not available.")}
            />

            <AnalyticsChart
              type="bar"
              title="Feature ablation (MAE)"
              data={featureAblation}
              xKey="ablation"
              series={[{ key: "mae", name: "MAE", color: "#f59e0b" }]}
              unit=" synthetic units"
              emptyMessage={emptyMessage("feature_ablation", "Feature ablation results are not available.")}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <AnalyticsChart
              type="bar"
              title="CVRP benchmark"
              data={cvrpBenchmark}
              xKey="scenario"
              series={[
                { key: "demand", name: "Confirmed demand", color: "#a78bfa" },
                { key: "capacity", name: "Available capacity", color: "#34d399" },
              ]}
              emptyMessage={emptyMessage("cvrp_benchmark", "CVRP benchmark data is not available.")}
            />

            <AnalyticsChart
              type="bar"
              title="HGFCI advisory capacity risk"
              data={hgfcAdvisory}
              xKey="leadDays"
              series={[{ key: "risk", name: "Capacity risk", color: "#f472b6" }]}
              emptyMessage={emptyMessage("hgfc_advisory", "HGFCI advisory data is not available.")}
            />
          </div>

          <AnalyticsChart
            type="bar"
            title="Reactive CVRP vs HGFCI advisory (route distance)"
            data={pairedRouting}
            xKey="scenario"
            series={[
              { key: "reactiveDistance", name: "Reactive CVRP", color: "#60a5fa" },
              { key: "advisoryDistance", name: "HGFCI advisory arm", color: "#f59e0b" },
            ]}
            unit=" km"
            emptyMessage={emptyMessage("reactive_vs_hgfc", "Paired routing experiment results are not available.")}
          />
        </>
      )}
    </section>
  );
}
