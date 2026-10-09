from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import get_settings
from app.schemas.optimization import RouteCoordinate


@dataclass(frozen=True)
class RoadRouteResult:
	"""Road-routing output normalized for optimization responses."""

	road_geometry: list[RouteCoordinate]
	distance_meters: float
	duration_seconds: float


class RoutingService:
	"""Service for external road geometry enrichment of optimized routes."""

	def __init__(self) -> None:
		self._settings = get_settings()

	def build_road_route(self, route_coordinates: Sequence[RouteCoordinate]) -> RoadRouteResult | None:
		"""Resolve route geometry via OSRM. Returns None when routing is unavailable."""
		if len(route_coordinates) < 2:
			return None

		base_url = str(
			getattr(
				self._settings,
				"OSRM_BASE_URL",
				"https://router.project-osrm.org",
			)
		).rstrip("/")

		coordinates = ";".join(
			f"{float(point.longitude):.7f},{float(point.latitude):.7f}"
			for point in route_coordinates
		)

		query = urlencode(
			{
				"overview": "full",
				"geometries": "geojson",
				"steps": "false",
			}
		)
		url = f"{base_url}/route/v1/driving/{coordinates}?{query}"
		timeout_seconds = float(
			getattr(
				self._settings,
				"OSRM_TIMEOUT_SECONDS",
				4.0,
			)
		)

		try:
			with urlopen(url, timeout=max(timeout_seconds, 0.5)) as response:
				payload = json.loads(response.read().decode("utf-8"))
		except Exception:
			return None

		if payload.get("code") != "Ok":
			return None

		routes = payload.get("routes")
		if not isinstance(routes, list) or not routes:
			return None

		primary_route = routes[0]
		distance_meters = float(primary_route.get("distance") or 0.0)
		duration_seconds = float(primary_route.get("duration") or 0.0)

		geometry = primary_route.get("geometry")
		geo_coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
		if not isinstance(geo_coordinates, list) or len(geo_coordinates) < 2:
			return None

		road_geometry: list[RouteCoordinate] = []
		for point in geo_coordinates:
			if not isinstance(point, list) or len(point) < 2:
				continue
			lon = float(point[0])
			lat = float(point[1])
			road_geometry.append(RouteCoordinate(latitude=lat, longitude=lon))

		if len(road_geometry) < 2:
			return None

		return RoadRouteResult(
			road_geometry=road_geometry,
			distance_meters=max(distance_meters, 0.0),
			duration_seconds=max(duration_seconds, 0.0),
		)