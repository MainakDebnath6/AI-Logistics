import { useMemo, useState } from "react";

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

function getStops(route) {
  return Array.isArray(route?.stops) ? route.stops : [];
}

function getStopLabel(stop, index) {
  return (
    stop?.customer_name ||
    stop?.delivery_address ||
    `Stop ${index + 1}`
  );
}

function getDistance(route) {
  return toNumber(route?.total_distance_km);
}

function getDemand(route) {
  return toNumber(route?.total_demand);
}

function getDurationMinutes(route) {
  return toNumber(route?.total_duration_minutes);
}

function formatDistance(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return `${value.toFixed(2)} km`;
}

function formatDemand(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return value.toLocaleString();
}

function formatDuration(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return `${value.toFixed(1)} min`;
}

function StopRow({ stop, index }) {
  const label = getStopLabel(stop, index);
  const demand = toNumber(stop?.demand);

  return (
    <li className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-medium text-white">{label}</p>
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
          Stop {index + 1}
        </span>
      </div>

      {stop?.delivery_address ? (
        <p className="mt-1 text-xs text-slate-400">{stop.delivery_address}</p>
      ) : null}

      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
        {typeof demand === "number" ? <span>Demand: {demand}</span> : null}
        {stop?.status ? <span>Status: {stop.status}</span> : null}
      </div>
    </li>
  );
}

export default function RouteCard({
  route,
  index,
  isSelected = false,
  onSelect,
}) {
  const [expanded, setExpanded] = useState(false);

  const stops = useMemo(() => getStops(route), [route]);
  const distance = useMemo(() => getDistance(route), [route]);
  const durationMinutes = useMemo(() => getDurationMinutes(route), [route]);
  const totalDemand = useMemo(() => getDemand(route), [route]);
  const totalOrders = useMemo(() => toNumber(route?.total_orders), [route]);

  return (
    <article
      className={`rounded-xl border p-4 transition ${
        isSelected
          ? "border-teal-500/70 bg-teal-500/10"
          : "border-slate-800 bg-slate-900/70"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h4 className="text-base font-semibold text-white">Route {index + 1}</h4>
          <p className="mt-1 text-sm text-slate-300">
            Driver: <span className="text-slate-100">{route?.driver?.full_name || "Unassigned"}</span>
          </p>
          <p className="text-sm text-slate-300">
            Vehicle: <span className="text-slate-100">{route?.vehicle?.registration_number || "Unassigned"}</span>
          </p>
        </div>

        {typeof onSelect === "function" ? (
          <button
            type="button"
            onClick={onSelect}
            className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-800"
          >
            {isSelected ? "Selected" : "View on Map"}
          </button>
        ) : null}
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Stops</p>
          <p className="mt-1 text-lg font-semibold text-white">{totalOrders ?? stops.length}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Total Demand</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatDemand(totalDemand)}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Distance</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatDistance(distance)}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Duration</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatDuration(durationMinutes)}</p>
        </div>
      </div>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => setExpanded((previous) => !previous)}
          className="rounded-md border border-slate-700 px-3 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-800"
        >
          {expanded ? "Hide Stops" : "Show Stops"}
        </button>
      </div>

      {expanded ? (
        <ul className="mt-3 space-y-2">
          {stops.length === 0 ? (
            <li className="rounded-lg border border-dashed border-slate-700 p-3 text-sm text-slate-400">
              No stop details available for this route.
            </li>
          ) : (
            stops.map((stop, stopIndex) => (
              <StopRow
                key={`${stop?.id || stop?.order_id || stop?.uuid || stopIndex}`}
                stop={stop}
                index={stopIndex}
              />
            ))
          )}
        </ul>
      ) : null}
    </article>
  );
}
