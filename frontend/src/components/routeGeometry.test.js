import assert from "node:assert/strict";
import test from "node:test";
import { extractRoadPolyline } from "./routeGeometry.js";

test("parses successful API road geometry into Leaflet latitude-longitude order", () => {
  const route = {
    road_route_status: "available",
    road_geometry: [
      { latitude: 22.5726, longitude: 88.3639 },
      { latitude: 22.5731, longitude: 88.3644 },
    ],
  };

  assert.deepEqual(extractRoadPolyline(route), [
    [22.5726, 88.3639],
    [22.5731, 88.3644],
  ]);
});

test("never falls back to optimizer stop coordinates when road geometry is missing", () => {
  const route = {
    road_route_status: "failed",
    road_route_error: "OSRM road routing request timed out.",
    road_geometry: [],
    route_coordinates: [
      { latitude: 22.5726, longitude: 88.3639 },
      { latitude: 22.5826, longitude: 88.3739 },
    ],
  };

  assert.deepEqual(extractRoadPolyline(route), []);
});

test("rejects invalid and partial road geometry instead of drawing it", () => {
  assert.deepEqual(
    extractRoadPolyline({
      road_route_status: "available",
      road_geometry: [
        { latitude: 22.5726, longitude: 88.3639 },
        { latitude: 999, longitude: 88.3739 },
      ],
    }),
    [],
  );
  assert.deepEqual(
    extractRoadPolyline({
      road_route_status: "available",
      road_geometry: [{ latitude: 22.5726, longitude: 88.3639 }],
    }),
    [],
  );
});