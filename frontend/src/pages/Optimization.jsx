import { useMemo, useState } from "react";
import LoadingSpinner from "../components/LoadingSpinner";
import MapView from "../components/MapView";
import OptimizationForm from "../components/OptimizationForm";
import RouteCard from "../components/RouteCard";

function toNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function getRoutesFromResponse(result) {
  if (!result || typeof result !== "object") {
    return [];
  }

  const candidates = [
    result.routes,
    result.optimized_routes,
    result.route_plan,
    result.solution?.routes,
    result.data?.routes,
    result.data?.optimized_routes,
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  return [];
}

function getStops(route) {
  if (Array.isArray(route?.stops)) {
    return route.stops;
  }
  if (Array.isArray(route?.orders)) {
    return route.orders;
  }
  if (Array.isArray(route?.waypoints)) {
    return route.waypoints;
  }
  return [];
}

function getDistance(route) {
  return (
    toNumber(route?.total_distance) ??
    toNumber(route?.distance) ??
    toNumber(route?.route_distance) ??
    toNumber(route?.metrics?.total_distance) ??
    0
  );
}

function formatDistance(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(2)} km`;
}

function extractSummary(result, routes) {
  const explicitTotalRoutes =
    toNumber(result?.total_routes) ??
    toNumber(result?.summary?.total_routes) ??
    toNumber(result?.metrics?.total_routes);

  const explicitTotalDistance =
    toNumber(result?.total_distance) ??
    toNumber(result?.summary?.total_distance) ??
    toNumber(result?.metrics?.total_distance);

  const explicitTotalOrders =
    toNumber(result?.total_orders) ??
    toNumber(result?.summary?.total_orders) ??
    toNumber(result?.metrics?.total_orders);

  const computedDistance = routes.reduce((total, route) => total + getDistance(route), 0);
  const computedOrders = routes.reduce((total, route) => total + getStops(route).length, 0);

  return {
    totalRoutes: explicitTotalRoutes ?? routes.length,
    totalDistance: explicitTotalDistance ?? computedDistance,
    totalOrders: explicitTotalOrders ?? computedOrders,
  };
}

export default function Optimization() {
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState("");
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);

  const routes = useMemo(
    () => getRoutesFromResponse(optimizationResult),
    [optimizationResult]
  );

  const summary = useMemo(
    () => extractSummary(optimizationResult, routes),
    [optimizationResult, routes]
  );

  const selectedRoute = routes[selectedRouteIndex] || null;

  function handleOptimized(result) {
    setError("");
    setOptimizationResult(result);
    setSelectedRouteIndex(0);
  }

  function handleError(message) {
    setError(message);
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold text-white">Route Optimization</h2>
        <p className="mt-1 text-sm text-slate-300">
          Optimize deliveries by balancing drivers, vehicles, and order demand.
        </p>
      </header>

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <OptimizationForm
          onOptimized={handleOptimized}
          onError={handleError}
          onOptimizingChange={setOptimizing}
        />

        <section className="space-y-4">
          {optimizing ? (
            <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-6">
              <LoadingSpinner size="lg" label="Running route optimization..." />
            </div>
          ) : null}

          {error ? (
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 p-4 text-sm text-rose-200">
              {error}
            </div>
          ) : null}

          {!optimizing && !optimizationResult ? (
            <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 p-6 text-sm text-slate-300">
              Submit optimization inputs to generate routes and metrics.
            </div>
          ) : null}

          {optimizationResult ? (
            <>
              <div className="grid gap-4 sm:grid-cols-3">
                <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Total Routes</p>
                  <p className="mt-2 text-2xl font-bold text-white">{summary.totalRoutes}</p>
                </article>

                <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Total Distance</p>
                  <p className="mt-2 text-2xl font-bold text-white">{formatDistance(summary.totalDistance)}</p>
                </article>

                <article className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Total Orders</p>
                  <p className="mt-2 text-2xl font-bold text-white">{summary.totalOrders}</p>
                </article>
              </div>

              <MapView route={selectedRoute} loading={optimizing} />

              {routes.length === 0 ? (
                <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/50 p-6 text-sm text-slate-300">
                  Optimization completed but no routes were returned.
                </div>
              ) : (
                <div className="space-y-3">
                  {routes.map((route, index) => (
                    <RouteCard
                      key={`${route?.id || route?.route_id || index}`}
                      route={route}
                      index={index}
                      isSelected={index === selectedRouteIndex}
                      onSelect={() => setSelectedRouteIndex(index)}
                    />
                  ))}
                </div>
              )}
            </>
          ) : null}
        </section>
      </div>
    </section>
  );
}
