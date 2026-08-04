import { useMemo, useState } from "react";
import LoadingSpinner from "../components/LoadingSpinner";
import MapView from "../components/MapView";
import OptimizationForm from "../components/OptimizationForm";
import RouteCard from "../components/RouteCard";

function formatDistance(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value.toFixed(2)} km`;
}

export default function Optimization() {
  const [optimizationResult, setOptimizationResult] = useState(null);
  const [optimizing, setOptimizing] = useState(false);
  const [error, setError] = useState("");
  const [selectedRouteIndex, setSelectedRouteIndex] = useState(0);

  const routes = useMemo(
    () => (Array.isArray(optimizationResult?.routes) ? optimizationResult.routes : []),
    [optimizationResult]
  );

  const summary = useMemo(
    () => ({
      totalRoutes: optimizationResult?.total_routes ?? routes.length,
      totalDistance: optimizationResult?.total_distance_km ?? 0,
      totalOrders: optimizationResult?.total_orders ?? 0,
    }),
    [optimizationResult, routes.length]
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
                      key={`${route?.driver?.id || "driver"}-${route?.vehicle?.id || "vehicle"}-${index}`}
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
