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
import { extractCanonicalPoint, extractRoadPolyline } from "./routeGeometry";

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

function extractStops(route) {
  return Array.isArray(route?.stops) ? route.stops : [];
}

function extractDriverPoint(route) {
  const depot = Array.isArray(route?.route_coordinates) ? route.route_coordinates[0] : null;
  return extractCanonicalPoint(depot);
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
  const polyline = useMemo(() => extractRoadPolyline(route), [route]);
  const stops = useMemo(() => extractStops(route), [route]);
  const driverPoint = useMemo(() => extractDriverPoint(route), [route]);

  const stopPoints = useMemo(
    () =>
      stops
        .map((stop, index) => {
          const point = extractCanonicalPoint({
            latitude: stop?.delivery_latitude,
            longitude: stop?.delivery_longitude,
          });
          return point ? { point, stop, index } : null;
        })
        .filter(Boolean),
    [stops]
  );

  const allPoints = useMemo(() => {
    const points = [];

    if (driverPoint) {
      points.push(driverPoint);
    }

    stopPoints.forEach(({ point }) => points.push(point));
    polyline.forEach((point) => points.push(point));

    return points;
  }, [driverPoint, stopPoints, polyline]);
  const routeStatus = route?.road_route_status === "available" && polyline.length < 2
    ? "Road geometry is invalid; no route line was drawn."
    : route?.road_route_status === "available"
      ? ""
      : route?.road_route_error || "Road geometry is unavailable; no route line was drawn.";

  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900/70 p-4 ${className}`}>
      <header className="mb-3">
        <h3 className="text-base font-semibold text-white">Route Map</h3>
        {route && routeStatus ? (
          <p role="status" className="mt-1 text-sm text-amber-300">{routeStatus}</p>
        ) : null}
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
                    <div>{route?.driver?.full_name || "Driver"}</div>
                  </div>
                </Popup>
              </Marker>
            ) : null}

            {stopPoints.map(({ point, stop, index }) => {
              return (
                <Marker key={`${stop?.id || stop?.order_id || index}`} position={point} icon={stopIcon}>
                  <Popup>
                    <div>
                      <strong>{stop?.customer_name || `Stop ${index + 1}`}</strong>
                      <div>{stop?.delivery_address || ""}</div>
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
