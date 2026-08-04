import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import AnalyticsChart from "../components/AnalyticsChart";
import LoadingSpinner from "../components/LoadingSpinner";
import MetricCard from "../components/MetricCard";
import {
  buildOrderStatusChartData,
  buildUtilizationBreakdown,
  getDashboardAnalytics,
  normalizeDashboardAnalytics,
} from "../services/analyticsService";

function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="8.5" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function TruckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M1 3h15v13H1z" />
      <path d="M16 8h4l3 3v5h-7z" />
      <circle cx="5.5" cy="18.5" r="2.5" />
      <circle cx="18.5" cy="18.5" r="2.5" />
    </svg>
  );
}

function PackageIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M12 2 3 7l9 5 9-5-9-5Z" />
      <path d="M3 7v10l9 5 9-5V7" />
      <path d="M12 12v10" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="m5 13 4 4L19 7" />
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

function GaugeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5">
      <path d="M4 14a8 8 0 1 1 16 0" />
      <path d="m12 12 4-4" />
      <path d="M12 22v-2" />
    </svg>
  );
}

function formatInteger(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return value.toLocaleString();
}

function formatPercentage(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(1)}%`;
}

const quickActions = [
  {
    title: "Driver Management",
    description: "Assign, onboard, and monitor active drivers.",
    to: "/drivers",
  },
  {
    title: "Vehicle Operations",
    description: "Track fleet availability and utilization.",
    to: "/vehicles",
  },
  {
    title: "Order Dispatch",
    description: "Create and prioritize delivery workloads.",
    to: "/orders",
  },
  {
    title: "Route Optimization",
    description: "Improve route plans and delivery performance.",
    to: "/optimization",
  },
];

export default function Dashboard() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    async function loadDashboard() {
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
        setError(requestError?.response?.data?.detail || "Unable to load dashboard analytics.");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      mounted = false;
    };
  }, []);

  const metricCards = useMemo(() => {
    if (!analytics) {
      return [];
    }

    return [
      {
        title: "Total Drivers",
        value: formatInteger(analytics.totalDrivers),
        icon: <UsersIcon />,
        color: "teal",
      },
      {
        title: "Total Vehicles",
        value: formatInteger(analytics.totalVehicles),
        icon: <TruckIcon />,
        color: "blue",
      },
      {
        title: "Total Orders",
        value: formatInteger(analytics.totalOrders),
        icon: <PackageIcon />,
        color: "violet",
      },
      {
        title: "Completed Orders",
        value: formatInteger(analytics.completedOrders),
        icon: <CheckIcon />,
        color: "emerald",
      },
      {
        title: "Pending Orders",
        value: formatInteger(analytics.pendingOrders),
        icon: <ClockIcon />,
        color: "amber",
      },
      {
        title: "Fleet Utilization",
        value: formatPercentage(analytics.fleetUtilization),
        icon: <GaugeIcon />,
        color: "cyan",
      },
    ];
  }, [analytics]);

  const orderStatusData = useMemo(() => buildOrderStatusChartData(analytics), [analytics]);
  const utilizationData = useMemo(() => buildUtilizationBreakdown(analytics), [analytics]);

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-white">Fleet Dashboard</h2>
        <p className="mt-1 text-sm text-slate-300">
          Monitor core fleet KPIs, delivery throughput, and utilization at a glance.
        </p>
      </header>

      {loading ? (
        <LoadingSpinner size="lg" label="Loading fleet dashboard..." fullScreen />
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
              type="pie"
              title="Order Completion Status"
              data={orderStatusData}
              xKey="name"
              dataKey="value"
              colors={["#34d399", "#f59e0b", "#60a5fa", "#f472b6"]}
              emptyMessage="Order status data is not available."
            />
            <AnalyticsChart
              type="bar"
              title="Utilization Snapshot"
              data={utilizationData}
              xKey="name"
              series={[
                { key: "value", name: "Utilization", color: "#2dd4bf" },
              ]}
              unit="%"
              emptyMessage="Utilization data is not available."
            />
          </div>

          <section className="space-y-3">
            <h3 className="text-lg font-semibold text-white">Quick Actions</h3>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {quickActions.map((action) => (
                <Link
                  key={action.to}
                  to={action.to}
                  className="group rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition hover:border-teal-500/50 hover:bg-slate-800/80"
                >
                  <p className="text-sm font-semibold text-white transition group-hover:text-teal-300">
                    {action.title}
                  </p>
                  <p className="mt-1 text-sm text-slate-300">{action.description}</p>
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </section>
  );
}
