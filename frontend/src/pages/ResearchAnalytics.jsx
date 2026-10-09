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

  const summaryCards = [
    {
      title: "Daily observations",
      value: syntheticDemand.count ?? 0,
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
      title: "Average demand",
      value: Number.isFinite(syntheticDemand.average_demand)
        ? `${Number(syntheticDemand.average_demand).toFixed(2)}`
        : "0.00",
      icon: <AverageIcon />,
      color: "violet",
      subtitle: "Mean daily demand",
    },
  ];

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-white">Research Analytics</h2>
        <p className="mt-1 text-sm text-slate-300">
          Synthetic demand, forecast comparisons, horizon sensitivity, and HGFCI advisory outputs.
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
              title="Forecast model comparison (MAE)"
              data={forecastComparison}
              xKey="model"
              series={[{ key: "mae", name: "MAE", color: "#60a5fa" }]}
              unit=""
              emptyMessage="Forecast model comparison data is not available."
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <AnalyticsChart
              type="bar"
              title="Horizon sensitivity"
              data={horizonSensitivity}
              xKey="horizon"
              series={[{ key: "mae", name: "MAE", color: "#34d399" }]}
              emptyMessage="Horizon sensitivity results are not available."
            />

            <AnalyticsChart
              type="bar"
              title="Feature ablation (MAE)"
              data={featureAblation}
              xKey="ablation"
              series={[{ key: "mae", name: "MAE", color: "#f59e0b" }]}
              emptyMessage="Feature ablation results are not available."
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <AnalyticsChart
              type="bar"
              title="CVRP benchmark"
              data={cvrpBenchmark}
              xKey="scenario"
              series={[{ key: "demand", name: "Confirmed demand", color: "#a78bfa" }]}
              emptyMessage="CVRP benchmark data is not available."
            />

            <AnalyticsChart
              type="bar"
              title="HGFCI advisory capacity risk"
              data={hgfcAdvisory}
              xKey="leadDays"
              series={[{ key: "risk", name: "Capacity risk", color: "#f472b6" }]}
              emptyMessage="HGFCI advisory data is not available."
            />
          </div>
        </>
      )}
    </section>
  );
}
