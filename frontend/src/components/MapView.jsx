import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useMemo } from "react";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import LoadingSpinner from "./LoadingSpinner";

L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const driverIcon = L.divIcon({
  html: '<div style="width:14px;height:14px;border-radius:9999px;background:#14b8a6;border:2px solid #0f172a;"></div>',
  className: "",
  iconSize: [14, 14],
  iconAnchor: [7, 7],
});

const stopIcon = L.divIcon({
  html: '<div style="width:12px;height:12px;border-radius:9999px;background:#60a5fa;border:2px solid #0f172a;"></div>',
  className: "",
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

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

function readCoordinate(source, latKeyCandidates, lngKeyCandidates) {
  if (!source || typeof source !== "object") {
    return null;
  }

  let lat = null;
  let lng = null;

  for (const key of latKeyCandidates) {
    lat = toNumber(source[key]);
    if (lat !== null) {
      break;
    }
  }

  for (const key of lngKeyCandidates) {
    lng = toNumber(source[key]);
    if (lng !== null) {
      break;
    }
  }

  if (lat === null || lng === null) {
    return null;
  }

  return [lat, lng];
}

function readLatLng(source) {
  return readCoordinate(
    source,
    ["lat", "latitude", "driver_latitude", "pickup_latitude", "delivery_latitude", "dropoff_latitude"],
    ["lng", "lon", "longitude", "driver_longitude", "pickup_longitude", "delivery_longitude", "dropoff_longitude"]
  );
}

function extractRoutePolyline(route) {
  if (!route || typeof route !== "object") {
    return [];
  }

  if (Array.isArray(route.route_coordinates)) {
    return route.route_coordinates
      .map((point) => {
        if (Array.isArray(point) && point.length >= 2) {
          const lat = toNumber(point[0]);
          const lng = toNumber(point[1]);
          return lat !== null && lng !== null ? [lat, lng] : null;
        }
        return readLatLng(point);
      })
      .filter(Boolean);
  }

  if (Array.isArray(route.path)) {
    return route.path
      .map((point) => {
        if (Array.isArray(point) && point.length >= 2) {
          const lat = toNumber(point[0]);
          const lng = toNumber(point[1]);
          return lat !== null && lng !== null ? [lat, lng] : null;
        }
        return readLatLng(point);
      })
      .filter(Boolean);
  }

  if (Array.isArray(route.geometry?.coordinates)) {
    return route.geometry.coordinates
      .map((point) => {
        if (!Array.isArray(point) || point.length < 2) {
          return null;
        }
        const lng = toNumber(point[0]);
        const lat = toNumber(point[1]);
        return lat !== null && lng !== null ? [lat, lng] : null;
      })
      .filter(Boolean);
  }

  return [];
}

function extractStops(route) {
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

function extractDriverPoint(route) {
  if (route?.driver?.location && typeof route.driver.location === "object") {
    return readLatLng(route.driver.location);
  }

  if (route?.driver && typeof route.driver === "object") {
    const nested = readLatLng(route.driver);
    if (nested) {
      return nested;
    }
  }

  const direct = readCoordinate(
    route,
    ["driver_latitude", "start_latitude", "origin_latitude"],
    ["driver_longitude", "start_longitude", "origin_longitude"]
  );

  return direct;
}

function FitBounds({ points }) {
  const map = useMap();

  if (Array.isArray(points) && points.length > 0) {
    const bounds = L.latLngBounds(points);
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }

  return null;
}

export default function MapView({
  route,
  loading = false,
  className = "",
}) {
  const polyline = useMemo(() => extractRoutePolyline(route), [route]);
  const stops = useMemo(() => extractStops(route), [route]);
  const driverPoint = useMemo(() => extractDriverPoint(route), [route]);

  const stopPoints = useMemo(
    () =>
      stops
        .map((stop) => readLatLng(stop))
        .filter(Boolean),
    [stops]
  );

  const allPoints = useMemo(() => {
    const points = [];

    if (driverPoint) {
      points.push(driverPoint);
    }

    stopPoints.forEach((point) => points.push(point));
    polyline.forEach((point) => points.push(point));

    return points;
  }, [driverPoint, stopPoints, polyline]);

  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900/70 p-4 ${className}`}>
      <header className="mb-3">
        <h3 className="text-base font-semibold text-white">Route Map</h3>
      </header>

      <div className="relative overflow-hidden rounded-lg border border-slate-800 bg-slate-950" style={{ height: 360 }}>
        {loading ? (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/70">
            <LoadingSpinner label="Preparing map..." />
          </div>
        ) : null}

        {!route ? (
          <div className="flex h-full items-center justify-center p-4 text-sm text-slate-400">
            Optimize routes to visualize route maps.
          </div>
        ) : allPoints.length === 0 ? (
          <div className="flex h-full items-center justify-center p-4 text-sm text-slate-400">
            Coordinates are not available for this route.
          </div>
        ) : (
          <MapContainer
            center={allPoints[0]}
            zoom={12}
            className="h-full w-full"
            scrollWheelZoom
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <FitBounds points={allPoints} />

            {driverPoint ? (
              <Marker position={driverPoint} icon={driverIcon}>
                <Popup>
                  <div>
                    <strong>Driver Start</strong>
                    <div>{route?.driver?.full_name || route?.driver?.name || route?.driver_name || "Driver"}</div>
                  </div>
                </Popup>
              </Marker>
            ) : null}

            {stopPoints.map((point, index) => {
              const stop = stops[index];
              return (
                <Marker key={`${stop?.id || stop?.order_id || index}`} position={point} icon={stopIcon}>
                  <Popup>
                    <div>
                      <strong>{stop?.customer_name || stop?.name || `Stop ${index + 1}`}</strong>
                      <div>{stop?.address || stop?.dropoff_address || ""}</div>
                    </div>
                  </Popup>
                </Marker>
              );
            })}

            {polyline.length >= 2 ? (
              <Polyline positions={polyline} color="#22d3ee" weight={4} opacity={0.85} />
            ) : null}
          </MapContainer>
        )}
      </div>
    </section>
  );
}
