function toCoordinate(value, minimum, maximum) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    return null;
  }
  return value >= minimum && value <= maximum ? value : null;
}

export function extractRoadPolyline(route) {
  if (route?.road_route_status !== "available" || !Array.isArray(route?.road_geometry)) {
    return [];
  }

  const points = route.road_geometry.map((point) => {
    const latitude = toCoordinate(point?.latitude, -90, 90);
    const longitude = toCoordinate(point?.longitude, -180, 180);
    return latitude !== null && longitude !== null ? [latitude, longitude] : null;
  });

  return points.length >= 2 && points.every(Boolean) ? points : [];
}

export function extractCanonicalPoint(point) {
  const latitude = toCoordinate(point?.latitude, -90, 90);
  const longitude = toCoordinate(point?.longitude, -180, 180);
  return latitude !== null && longitude !== null ? [latitude, longitude] : null;
}