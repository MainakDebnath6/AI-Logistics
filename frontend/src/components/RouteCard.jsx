import { useMemo, useState } from "react";

function getDriverName(route) {
  return (
    route?.driver?.full_name ||
    route?.driver?.name ||
    route?.driver_name ||
    route?.assigned_driver_name ||
    route?.driver_id ||
    "Unassigned"
  );
}

function getVehicleName(route) {
  return (
    route?.vehicle?.plate_number ||
    route?.vehicle?.plate ||
    route?.vehicle?.registration_number ||
    route?.vehicle_name ||
    route?.assigned_vehicle_name ||
    route?.vehicle_id ||
    "Unassigned"
  );
}

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

function getStopLabel(stop, index) {
  return (
    stop?.customer_name ||
    stop?.name ||
    stop?.dropoff_address ||
    stop?.address ||
    stop?.location_name ||
    `Stop ${index + 1}`
  );
}

function getDistance(route) {
  return (
    toNumber(route?.total_distance) ??
    toNumber(route?.distance) ??
    toNumber(route?.route_distance) ??
    toNumber(route?.metrics?.total_distance)
  );
}

function getLoad(route) {
  return (
    toNumber(route?.total_load) ??
    toNumber(route?.load) ??
    toNumber(route?.total_quantity) ??
    toNumber(route?.metrics?.total_load)
  );
}

function formatDistance(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return `${value.toFixed(2)} km`;
}

function formatLoad(value) {
  if (typeof value !== "number") {
    return "--";
  }
  return value.toLocaleString();
}

function StopRow({ stop, index }) {
  const label = getStopLabel(stop, index);
  const eta = stop?.eta || stop?.estimated_arrival || stop?.expected_arrival;
  const quantity = toNumber(stop?.quantity ?? stop?.load);

  return (
    <li className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm font-medium text-white">{label}</p>
        <span className="rounded-full border border-slate-700 px-2 py-0.5 text-xs text-slate-300">
          Stop {index + 1}
        </span>
      </div>

      {stop?.address || stop?.dropoff_address ? (
        <p className="mt-1 text-xs text-slate-400">{stop.address || stop.dropoff_address}</p>
      ) : null}

      <div className="mt-2 flex flex-wrap gap-4 text-xs text-slate-300">
        {typeof quantity === "number" ? <span>Load: {quantity}</span> : null}
        {eta ? <span>ETA: {eta}</span> : null}
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
  const totalLoad = useMemo(() => getLoad(route), [route]);

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
            Driver: <span className="text-slate-100">{getDriverName(route)}</span>
          </p>
          <p className="text-sm text-slate-300">
            Vehicle: <span className="text-slate-100">{getVehicleName(route)}</span>
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

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Stops</p>
          <p className="mt-1 text-lg font-semibold text-white">{stops.length}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Total Load</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatLoad(totalLoad)}</p>
        </div>
        <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Distance</p>
          <p className="mt-1 text-lg font-semibold text-white">{formatDistance(distance)}</p>
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
