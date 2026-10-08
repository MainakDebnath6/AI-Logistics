import { useEffect, useMemo, useState } from "react";
import AnalyticsChart from "../components/AnalyticsChart";
import LoadingSpinner from "../components/LoadingSpinner";
import MetricCard from "../components/MetricCard";
import {
  buildEtaVsDistanceData,
  buildKpiTrendSeries,
  buildUtilizationBreakdown,
  getDashboardAnalytics,
  normalizeDashboardAnalytics,
} from "../services/analyticsService";

function GaugeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M4 14a8 8 0 1 1 16 0" />
      <path d="m12 12 4-4" />
      <path d="M12 22v-2" />
    </svg>
  );
}

function RouteIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <circle cx="6" cy="19" r="2" />
      <circle cx="18" cy="5" r="2" />
      <path d="M8 19h3a4 4 0 0 0 4-4V7" />
      <path d="M15 15h3" />
    </svg>
  );
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v6l4 2" />
    </svg>
  );
}

function DeliveryIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M3 7h11v8H3z" />
      <path d="M14 10h4l3 3v2h-7z" />
      <circle cx="7" cy="18" r="2" />
      <circle cx="18" cy="18" r="2" />
    </svg>
  );
}

function DistanceIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M3 12h18" />
      <path d="m14 5 7 7-7 7" />
    </svg>
  );
}

function formatPercentage(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(1)}%`;
}

function formatEta(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(1)} min`;
}

function formatDistance(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toLocaleString()} km`;
}

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadAnalytics() {
      try {
        setLoading(true);
        setError("");

        const payload = await getDashboardAnalytics();
        if (!mounted) {
          return;
        }

        setAnalytics(normalizeDashboardAnalytics(payload));
      } catch (requestError) {
        if (!mounted) {
          return;
        }
        setError(requestError?.response?.data?.detail || "Unable to load analytics.");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadAnalytics();

    return () => {
      mounted = false;
    };
  }, []);

  const utilizationData = useMemo(() => buildUtilizationBreakdown(analytics), [analytics]);
  const kpiTrendData = useMemo(() => buildKpiTrendSeries(analytics), [analytics]);
  const etaDistanceData = useMemo(() => buildEtaVsDistanceData(analytics), [analytics]);

  const metricCards = useMemo(() => {
    if (!analytics) {
      return [];
    }

    return [
      {
        title: "Vehicle Utilization",
        value: formatPercentage(analytics.vehicleUtilization),
        icon: <GaugeIcon />,
        color: "blue",
      },
      {
        title: "Driver Utilization",
        value: formatPercentage(analytics.driverUtilization),
        icon: <GaugeIcon />,
        color: "teal",
      },
      {
        title: "Route Efficiency",
        value: formatPercentage(analytics.routeEfficiency),
        icon: <RouteIcon />,
        color: "violet",
      },
      {
        title: "Average ETA",
        value: formatEta(analytics.averageEta),
        icon: <ClockIcon />,
        color: "amber",
      },
      {
        title: "On-Time Delivery",
        value: formatPercentage(analytics.onTimeDelivery),
        icon: <DeliveryIcon />,
        color: "emerald",
      },
      {
        title: "Distance Covered",
        value: formatDistance(analytics.distanceCovered),
        icon: <DistanceIcon />,
        color: "cyan",
      },
    ];
  }, [analytics]);

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-white">Fleet Analytics</h2>
        <p className="mt-1 text-sm text-slate-300">
          Analyze utilization, routing outcomes, and delivery performance trends.
        </p>
      </header>

      {loading ? (
        <LoadingSpinner size="lg" label="Loading analytics..." fullScreen />
      ) : error ? (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {metricCards.map((metric) => (
              <MetricCard key={metric.title} {...metric} />
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <AnalyticsChart
              type="bar"
              title="Vehicle vs Driver Utilization"
              data={utilizationData}
              xKey="name"
              series={[
                { key: "value", name: "Utilization", color: "#38bdf8" },
              ]}
              unit="%"
              emptyMessage="Utilization details are not available."
            />

            <AnalyticsChart
              type="line"
              title="Route KPI Trend"
              data={kpiTrendData}
              xKey="label"
              series={[
                { key: "routeEfficiency", name: "Route Efficiency", color: "#22d3ee" },
                { key: "onTimeDelivery", name: "On-Time Delivery", color: "#34d399" },
              ]}
              unit="%"
              emptyMessage="KPI trend data is not available."
            />
          </div>

          <AnalyticsChart
            type="line"
            title="Average ETA vs Distance"
            data={etaDistanceData}
            xKey="label"
            series={[
              { key: "averageEta", name: "Average ETA", color: "#f59e0b" },
              { key: "distanceCovered", name: "Distance Covered", color: "#60a5fa" },
            ]}
            emptyMessage="ETA and distance trend data is not available."
          />
        </>
      )}
    </section>
  );
}
