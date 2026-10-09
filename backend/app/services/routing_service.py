from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
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


class RoadRoutingError(RuntimeError):
	"""Raised when OSRM cannot provide valid road geometry for the requested route."""


class RoutingService:
	"""Service for external road geometry enrichment of optimized routes."""

	def __init__(self) -> None:
		self._settings = get_settings()

	def build_road_route(self, route_coordinates: Sequence[RouteCoordinate]) -> RoadRouteResult:
		"""Resolve and validate ordered road geometry via OSRM."""
		if len(route_coordinates) < 2:
			raise RoadRoutingError("At least two route coordinates are required for road routing.")
		for index, point in enumerate(route_coordinates):
			try:
				latitude = float(point.latitude)
				longitude = float(point.longitude)
			except (AttributeError, OverflowError, TypeError, ValueError) as error:
				raise RoadRoutingError(
					f"Route coordinate {index} has invalid latitude/longitude values."
				) from error
			if (
				not math.isfinite(latitude)
				or not math.isfinite(longitude)
				or not -90.0 <= latitude <= 90.0
				or not -180.0 <= longitude <= 180.0
			):
				raise RoadRoutingError(f"Route coordinate {index} has invalid latitude/longitude values.")

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
			with urlopen(url, timeout=min(max(timeout_seconds, 0.5), 30.0)) as response:
				status = getattr(response, "status", None)
				if status is None:
					status = response.getcode()
				if not 200 <= status < 300:
					raise RoadRoutingError(f"OSRM returned HTTP {status}.")
				payload = json.loads(response.read().decode("utf-8"))
		except RoadRoutingError:
			raise
		except HTTPError as error:
			raise RoadRoutingError(f"OSRM returned HTTP {error.code}.") from error
		except URLError as error:
			if isinstance(error.reason, TimeoutError) or "timed out" in str(error.reason).lower():
				raise RoadRoutingError("OSRM road routing request timed out.") from error
			raise RoadRoutingError(f"OSRM road routing request failed: {error.reason}.") from error
		except (TimeoutError, OSError) as error:
			if isinstance(error, (TimeoutError,)) or "timed out" in str(error).lower():
				raise RoadRoutingError("OSRM road routing request timed out.") from error
			raise RoadRoutingError(f"OSRM road routing request failed: {error}.") from error
		except (UnicodeDecodeError, json.JSONDecodeError) as error:
			raise RoadRoutingError("OSRM returned malformed JSON.") from error
		except Exception as error:
			raise RoadRoutingError(f"OSRM response could not be read: {error}.") from error

		if not isinstance(payload, dict):
			raise RoadRoutingError("OSRM returned a malformed response object.")
		if payload.get("code") != "Ok":
			code = payload.get("code")
			message = {
				"NoRoute": "OSRM found no drivable route between the requested stops.",
				"NoSegment": "OSRM could not match one or more requested coordinates to a road.",
			}.get(code, f"OSRM could not route the requested stops (code: {code}).")
			raise RoadRoutingError(message)

		routes = payload.get("routes")
		if not isinstance(routes, list) or not routes:
			raise RoadRoutingError("OSRM returned no route for the requested stops.")

		primary_route = routes[0]
		if not isinstance(primary_route, dict):
			raise RoadRoutingError("OSRM returned a malformed route object.")
		try:
			distance_meters = float(primary_route["distance"])
			duration_seconds = float(primary_route["duration"])
		except (KeyError, OverflowError, TypeError, ValueError) as error:
			raise RoadRoutingError("OSRM route is missing valid distance or duration metrics.") from error
		if not math.isfinite(distance_meters) or distance_meters <= 0.0:
			raise RoadRoutingError("OSRM returned an invalid route distance.")
		if not math.isfinite(duration_seconds) or duration_seconds <= 0.0:
			raise RoadRoutingError("OSRM returned an invalid route duration.")

		waypoints = payload.get("waypoints")
		if not isinstance(waypoints, list) or len(waypoints) != len(route_coordinates):
			raise RoadRoutingError("OSRM response does not contain the requested ordered waypoints.")
		for index, (waypoint, requested_point) in enumerate(zip(waypoints, route_coordinates)):
			if not isinstance(waypoint, dict):
				raise RoadRoutingError(f"OSRM returned a malformed snapped waypoint at index {index}.")
			location = waypoint.get("location")
			if not self._valid_lon_lat(location):
				raise RoadRoutingError(f"OSRM returned an invalid snapped waypoint at index {index}.")
			try:
				snap_distance = float(waypoint["distance"])
			except (KeyError, OverflowError, TypeError, ValueError) as error:
				raise RoadRoutingError(f"OSRM omitted snap distance for waypoint {index}.") from error
			if not math.isfinite(snap_distance) or snap_distance < 0.0:
				raise RoadRoutingError(f"OSRM returned an invalid snap distance for waypoint {index}.")
			requested_gap = self._haversine_distance_meters(
				float(requested_point.latitude),
				float(requested_point.longitude),
				float(location[1]),
				float(location[0]),
			)
			if abs(requested_gap - snap_distance) > max(25.0, requested_gap * 0.05):
				raise RoadRoutingError(
					f"OSRM snapped waypoint {index} does not correspond to the requested coordinate."
				)

		geometry = primary_route.get("geometry")
		if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
			raise RoadRoutingError("OSRM returned geometry that is not a GeoJSON LineString.")
		geo_coordinates = geometry.get("coordinates")
		if not isinstance(geo_coordinates, list) or len(geo_coordinates) < 2:
			raise RoadRoutingError("OSRM returned no detailed road geometry.")

		road_geometry: list[RouteCoordinate] = []
		for point in geo_coordinates:
			if not self._valid_lon_lat(point):
				raise RoadRoutingError("OSRM road geometry contains an invalid longitude/latitude point.")
			lon = float(point[0])
			lat = float(point[1])
			road_geometry.append(RouteCoordinate(latitude=lat, longitude=lon))

		first_waypoint = waypoints[0]["location"]
		last_waypoint = waypoints[-1]["location"]
		if not self._same_point(road_geometry[0], first_waypoint):
			raise RoadRoutingError("OSRM geometry start does not match the first optimized stop.")
		if not self._same_point(road_geometry[-1], last_waypoint):
			raise RoadRoutingError("OSRM geometry end does not match the final optimized stop.")
		self._validate_waypoint_sequence(road_geometry, waypoints)

		return RoadRouteResult(
			road_geometry=road_geometry,
			distance_meters=distance_meters,
			duration_seconds=duration_seconds,
		)

	@staticmethod
	def _haversine_distance_meters(
		latitude_a: float,
		longitude_a: float,
		latitude_b: float,
		longitude_b: float,
	) -> float:
		"""Measure input-to-snapped waypoint separation for response validation."""
		radius_meters = 6_371_000.0
		latitude_delta = math.radians(latitude_b - latitude_a)
		longitude_delta = math.radians(longitude_b - longitude_a)
		a = (
			math.sin(latitude_delta / 2.0) ** 2
			+ math.cos(math.radians(latitude_a))
			* math.cos(math.radians(latitude_b))
			* math.sin(longitude_delta / 2.0) ** 2
		)
		return 2.0 * radius_meters * math.asin(math.sqrt(min(a, 1.0)))

	@staticmethod
	def _valid_lon_lat(point: object) -> bool:
		if not isinstance(point, (list, tuple)) or len(point) < 2:
			return False
		try:
			longitude, latitude = float(point[0]), float(point[1])
		except (OverflowError, TypeError, ValueError):
			return False
		return (
			math.isfinite(longitude)
			and math.isfinite(latitude)
			and -180.0 <= longitude <= 180.0
			and -90.0 <= latitude <= 90.0
		)

	@staticmethod
	def _same_point(point: RouteCoordinate, lon_lat: Sequence[float]) -> bool:
		return (
			abs(float(point.longitude) - float(lon_lat[0])) <= 1e-5
			and abs(float(point.latitude) - float(lon_lat[1])) <= 1e-5
		)

	@classmethod
	def _validate_waypoint_sequence(
		cls,
		geometry: Sequence[RouteCoordinate],
		waypoints: Sequence[dict],
	) -> None:
		geometry_index = 0
		for waypoint in waypoints:
			location = waypoint["location"]
			while geometry_index < len(geometry) and not cls._same_point(
				geometry[geometry_index], location
			):
				geometry_index += 1
			if geometry_index == len(geometry):
				raise RoadRoutingError("OSRM geometry does not follow the optimized stop sequence.")
			geometry_index += 1