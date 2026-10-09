from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import TypedDict

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.core.config import get_settings
from app.models.driver import Driver
from app.models.order import Order
from app.models.vehicle import Vehicle
from app.schemas.optimization import (
	OptimizationDriver,
	OptimizationResponse,
	OptimizationStop,
	OptimizationVehicle,
	OptimizedRoute,
	RouteCoordinate,
)
from app.services.routing_service import RoadRoutingError, RoutingService

logger = logging.getLogger(__name__)


class _OptimizationDataModel(TypedDict):
	"""Typed OR-Tools routing input data."""

	distance_matrix: list[list[int]]
	demands: list[int]
	vehicle_capacities: list[int]
	num_vehicles: int
	depot: int
	coordinates: list[tuple[float, float]]


class _RuntimeOptimizationOptions(TypedDict):
	"""Runtime flags controlling optional optimization behaviors."""

	time_windows_enabled: bool
	priority_enabled: bool
	timeout_seconds: int | None
	solution_limit: int | None


class RouteOptimizerService:
	"""Service that computes capacitated routes using Google OR-Tools."""

	def __init__(self, routing_service: RoutingService | None = None) -> None:
		"""Initialize optimizer service with application defaults."""
		self._settings = get_settings()
		self._routing_service = routing_service or RoutingService()
		self._runtime_options: _RuntimeOptimizationOptions = {
			"time_windows_enabled": False,
			"priority_enabled": False,
			"timeout_seconds": None,
			"solution_limit": None,
		}

	def configure(
		self,
		*,
		time_windows_enabled: bool = False,
		priority_enabled: bool = False,
		optimization_timeout_seconds: int | None = None,
		optimization_solution_limit: int | None = None,
	) -> None:
		"""Configure optional runtime optimization behaviors for next run."""
		timeout_value: int | None = None
		if optimization_timeout_seconds is not None:
			timeout_value = max(int(optimization_timeout_seconds), 1)
		solution_limit = (
			max(int(optimization_solution_limit), 1)
			if optimization_solution_limit is not None
			else None
		)

		self._runtime_options = {
			"time_windows_enabled": bool(time_windows_enabled),
			"priority_enabled": bool(priority_enabled),
			"timeout_seconds": timeout_value,
			"solution_limit": solution_limit,
		}

	def optimize(
		self,
		drivers: Sequence[Driver],
		vehicles: Sequence[Vehicle],
		orders: Sequence[Order],
		*,
		depot_coordinates: tuple[float, float] | None = None,
	) -> OptimizationResponse:
		"""Optimize routes for the provided drivers, vehicles, and orders."""
		if not drivers:
			raise ValueError("At least one driver is required for optimization.")
		if not vehicles:
			raise ValueError("At least one vehicle is required for optimization.")
		if not orders:
			return OptimizationResponse(
				total_distance_km=0.0,
				total_orders=0,
				total_routes=0,
				requested_orders=0,
				served_order_ids=[],
				unserved_order_ids=[],
			)

		paired_drivers, paired_vehicles = self._pair_drivers_and_vehicles(drivers, vehicles)
		optimization_orders = list(orders)
		if self._runtime_priority_enabled(orders):
			optimization_orders.sort(key=lambda order: -int(getattr(order, "priority", 0) or 0))

		data = self._create_data_model(
			drivers=paired_drivers,
			vehicles=paired_vehicles,
			orders=optimization_orders,
			depot_coordinates=depot_coordinates,
		)

		manager = pywrapcp.RoutingIndexManager(
			len(data["distance_matrix"]),
			data["num_vehicles"],
			data["depot"],
		)
		routing = pywrapcp.RoutingModel(manager)

		def distance_callback(from_index: int, to_index: int) -> int:
			from_node = manager.IndexToNode(from_index)
			to_node = manager.IndexToNode(to_index)
			return data["distance_matrix"][from_node][to_node]

		transit_callback_index = routing.RegisterTransitCallback(distance_callback)
		routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

		def demand_callback(from_index: int) -> int:
			from_node = manager.IndexToNode(from_index)
			return data["demands"][from_node]

		demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
		routing.AddDimensionWithVehicleCapacity(
			demand_callback_index,
			0,
			data["vehicle_capacities"],
			True,
			"Capacity",
		)

		search_parameters = pywrapcp.DefaultRoutingSearchParameters()
		search_parameters.first_solution_strategy = self._resolve_first_solution_strategy()
		search_parameters.local_search_metaheuristic = self._resolve_local_search_metaheuristic()
		search_parameters.time_limit.FromSeconds(self._resolve_timeout_seconds())
		solution_limit = self._runtime_options.get("solution_limit")
		if solution_limit is not None:
			search_parameters.solution_limit = solution_limit

		if self._runtime_time_windows_enabled(optimization_orders):
			def time_callback(from_index: int, to_index: int) -> int:
				from_node = manager.IndexToNode(from_index)
				to_node = manager.IndexToNode(to_index)
				distance_m = data["distance_matrix"][from_node][to_node]
				return self._estimate_travel_time_minutes(distance_m)

			time_transit_callback_index = routing.RegisterTransitCallback(time_callback)
			self._add_time_windows_constraint(
				routing=routing,
				manager=manager,
				transit_callback_index=time_transit_callback_index,
				orders=optimization_orders,
			)

		solution = routing.SolveWithParameters(search_parameters)
		if solution is None:
			raise RuntimeError("No feasible optimization solution found.")

		routes, total_distance_m = self._extract_solution_routes(
			routing=routing,
			manager=manager,
			solution=solution,
			data=data,
			drivers=paired_drivers,
			vehicles=paired_vehicles,
			orders=optimization_orders,
		)
		served_order_ids = [stop.order_id for route in routes for stop in route.stops]
		served_ids = set(served_order_ids)
		unserved_order_ids = [order.id for order in orders if order.id not in served_ids]

		return OptimizationResponse(
			total_distance_km=round(total_distance_m / 1000.0, 3),
			total_orders=len(served_order_ids),
			total_routes=len(routes),
			routes=routes,
			requested_orders=len(orders),
			served_order_ids=served_order_ids,
			unserved_order_ids=unserved_order_ids,
		)

	@staticmethod
	def _pair_drivers_and_vehicles(
		drivers: Sequence[Driver],
		vehicles: Sequence[Vehicle],
	) -> tuple[list[Driver], list[Vehicle]]:
		"""Validate and order resources by each driver's actual vehicle assignment."""
		if len(drivers) != len(vehicles):
			raise ValueError("Each selected driver must have exactly one selected vehicle.")

		vehicles_by_id = {vehicle.id: vehicle for vehicle in vehicles}
		if len(vehicles_by_id) != len(vehicles):
			raise ValueError("Duplicate vehicles are not allowed.")

		paired_vehicles: list[Vehicle] = []
		seen_vehicle_ids = set()
		for driver in drivers:
			vehicle_id = getattr(driver, "vehicle_id", None)
			vehicle = vehicles_by_id.get(vehicle_id)
			if vehicle is None:
				raise ValueError(f"Driver {driver.id} is not assigned to a selected vehicle.")
			if vehicle.id in seen_vehicle_ids:
				raise ValueError("A selected vehicle cannot be assigned to multiple drivers.")
			seen_vehicle_ids.add(vehicle.id)
			paired_vehicles.append(vehicle)

		return list(drivers), paired_vehicles

	def _build_distance_matrix(
		self,
		coordinates: Sequence[tuple[float, float]],
	) -> list[list[int]]:
		"""Build a symmetric integer-meter distance matrix from coordinates."""
		size = len(coordinates)
		matrix: list[list[int]] = [[0 for _ in range(size)] for _ in range(size)]

		for i in range(size):
			for j in range(i + 1, size):
				distance_m = self._haversine_distance_meters(
					coordinates[i][0],
					coordinates[i][1],
					coordinates[j][0],
					coordinates[j][1],
				)
				matrix[i][j] = distance_m
				matrix[j][i] = distance_m

		return matrix

	def _create_data_model(
		self,
		drivers: Sequence[Driver],
		vehicles: Sequence[Vehicle],
		orders: Sequence[Order],
		depot_coordinates: tuple[float, float] | None = None,
	) -> _OptimizationDataModel:
		"""Create the OR-Tools data model for a capacitated VRP."""
		num_vehicles = len(drivers)
		if num_vehicles <= 0:
			raise ValueError("At least one driver and vehicle pair is required.")
		if len(vehicles) != num_vehicles:
			raise ValueError("Each selected driver must have exactly one selected vehicle.")

		if depot_coordinates is None:
			depot_latitude = self._settings.DEFAULT_DEPOT_LATITUDE
			depot_longitude = self._settings.DEFAULT_DEPOT_LONGITUDE
			if depot_latitude is None or depot_longitude is None:
				raise ValueError(
					"Depot coordinates are required; provide both depot coordinates in the request "
					"or configure DEFAULT_DEPOT_LATITUDE and DEFAULT_DEPOT_LONGITUDE."
				)
			depot_coordinates = (float(depot_latitude), float(depot_longitude))
		try:
			depot_coord = (float(depot_coordinates[0]), float(depot_coordinates[1]))
		except (IndexError, TypeError, ValueError) as error:
			raise ValueError("Depot coordinates must contain valid latitude and longitude values.") from error

		order_coords: list[tuple[float, float]] = []
		for order_index, order in enumerate(orders):
			try:
				order_coords.append(
					(float(order.delivery_latitude), float(order.delivery_longitude))
				)
			except (AttributeError, TypeError, ValueError) as error:
				raise ValueError(
					f"Order at optimization index {order_index} has missing or invalid delivery coordinates."
				) from error
		coordinates = [depot_coord, *order_coords]
		for index, (latitude, longitude) in enumerate(coordinates):
			if (
				not math.isfinite(latitude)
				or not math.isfinite(longitude)
				or not -90.0 <= latitude <= 90.0
				or not -180.0 <= longitude <= 180.0
			):
				raise ValueError(f"Route coordinate {index} has invalid latitude/longitude values.")

		demands = [0, *[int(order.demand) for order in orders]]
		vehicle_capacities = [int(vehicle.capacity) for vehicle in vehicles]

		if sum(vehicle_capacities) < sum(demands):
			raise RuntimeError("Insufficient vehicle capacity for all orders.")

		return {
			"distance_matrix": self._build_distance_matrix(coordinates),
			"demands": demands,
			"vehicle_capacities": vehicle_capacities,
			"num_vehicles": num_vehicles,
			"depot": 0,
			"coordinates": coordinates,
		}

	def _resolve_timeout_seconds(self) -> int:
		"""Resolve optimization timeout in seconds from settings."""
		runtime_timeout = self._runtime_options.get("timeout_seconds")
		if runtime_timeout is not None:
			return max(int(runtime_timeout), 1)

		timeout = int(
			getattr(
				self._settings,
				"DEFAULT_OPTIMIZATION_TIMEOUT_SECONDS",
				getattr(self._settings, "optimization_timeout_seconds", 5),
			)
		)
		return max(timeout, 1)

	def _resolve_first_solution_strategy(self) -> int:
		"""Resolve first-solution strategy from settings with safe fallback."""
		strategy_name = str(
			getattr(
				self._settings,
				"DEFAULT_FIRST_SOLUTION_STRATEGY",
				"PATH_CHEAPEST_ARC",
			)
		)
		strategy = getattr(
			routing_enums_pb2.FirstSolutionStrategy,
			strategy_name,
			routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
		)
		return int(strategy)

	def _resolve_local_search_metaheuristic(self) -> int:
		"""Resolve local-search metaheuristic from settings with safe fallback."""
		meta_name = str(
			getattr(
				self._settings,
				"DEFAULT_LOCAL_SEARCH_METAHEURISTIC",
				getattr(self._settings, "DEFAULT_LOCAL_SEARCH", "GUIDED_LOCAL_SEARCH"),
			)
		)
		metaheuristic = getattr(
			routing_enums_pb2.LocalSearchMetaheuristic,
			meta_name,
			routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
		)
		return int(metaheuristic)

	def _extract_solution_routes(
		self,
		*,
		routing: pywrapcp.RoutingModel,
		manager: pywrapcp.RoutingIndexManager,
		solution: pywrapcp.Assignment,
		data: _OptimizationDataModel,
		drivers: Sequence[Driver],
		vehicles: Sequence[Vehicle],
		orders: Sequence[Order],
	) -> tuple[list[OptimizedRoute], int]:
		"""Extract robust route outputs from an OR-Tools solution."""
		routes: list[OptimizedRoute] = []
		total_distance_m = 0

		for vehicle_idx in range(data["num_vehicles"]):
			index = routing.Start(vehicle_idx)
			sequence = 0
			route_demand = 0
			route_distance_m = 0
			stops: list[OptimizationStop] = []
			depot_latitude, depot_longitude = data["coordinates"][data["depot"]]
			route_coordinates: list[RouteCoordinate] = [
				RouteCoordinate(latitude=depot_latitude, longitude=depot_longitude)
			]

			while not routing.IsEnd(index):
				node = manager.IndexToNode(index)

				if node != data["depot"] and 0 <= node - 1 < len(orders):
					sequence += 1
					order_index = node - 1
					order = orders[order_index]
					route_demand += int(order.demand)
					stops.append(
						OptimizationStop(
							order_id=order.id,
							customer_name=order.customer_name,
							pickup_address=order.pickup_address,
							delivery_address=order.delivery_address,
							pickup_latitude=float(order.pickup_latitude),
							pickup_longitude=float(order.pickup_longitude),
							delivery_latitude=float(order.delivery_latitude),
							delivery_longitude=float(order.delivery_longitude),
							demand=int(order.demand),
							priority=int(order.priority),
							status=str(order.status.value if hasattr(order.status, "value") else order.status),
							sequence=sequence,
							arrival_time=None,
						)
					)
					self._append_route_coordinate(
						route_coordinates,
						latitude=data["coordinates"][node][0],
						longitude=data["coordinates"][node][1],
					)

				next_index = solution.Value(routing.NextVar(index))
				next_node = manager.IndexToNode(next_index)
				route_distance_m += data["distance_matrix"][node][next_node]
				index = next_index

			if stops:
				self._append_route_coordinate(
					route_coordinates,
					latitude=depot_latitude,
					longitude=depot_longitude,
				)
				road_geometry: list[RouteCoordinate] = []
				road_distance_km: float | None = None
				duration_seconds: float | None = None
				road_route_status = "failed"
				road_route_error: str | None = None
				try:
					road_route = self._routing_service.build_road_route(route_coordinates)
					if road_route is None:
						raise RoadRoutingError("Road routing service returned no route geometry.")
				except RoadRoutingError as error:
					road_route_error = str(error) or "Road routing failed without a diagnostic message."
					logger.warning(
						"Road routing unavailable for driver_id=%s: %s",
						drivers[vehicle_idx].id,
						road_route_error,
					)
				except Exception as error:  # noqa: BLE001
					road_route_error = "Road routing provider failed unexpectedly."
					logger.warning(
						"Road routing provider raised %s for driver_id=%s",
						type(error).__name__,
						drivers[vehicle_idx].id,
					)
				else:
					road_geometry = road_route.road_geometry
					road_distance_km = float(road_route.distance_meters) / 1000.0
					duration_seconds = float(road_route.duration_seconds)
					road_route_status = "available"

				route_distance_km = round(route_distance_m / 1000.0, 3)
				route_duration_minutes = (
					round(duration_seconds / 60.0, 2)
					if duration_seconds is not None
					else None
				)
				driver = drivers[vehicle_idx]
				vehicle = vehicles[vehicle_idx]
				driver_full_name = getattr(getattr(driver, "user", None), "full_name", None) or f"Driver {driver.id}"

				routes.append(
					OptimizedRoute(
						driver=OptimizationDriver(
							id=driver.id,
							full_name=driver_full_name,
						),
						vehicle=OptimizationVehicle(
							id=vehicle.id,
							registration_number=vehicle.registration_number,
							capacity=int(vehicle.capacity),
						),
						total_distance_km=route_distance_km,
						total_duration_minutes=route_duration_minutes,
						total_demand=route_demand,
						total_orders=len(stops),
						stops=stops,
						route_coordinates=route_coordinates,
						road_geometry=road_geometry,
						road_route_status=road_route_status,
						road_route_error=road_route_error,
						distance=float(route_distance_m),
						duration=duration_seconds,
						road_distance_km=road_distance_km,
					)
				)
				total_distance_m += route_distance_m

		return routes, total_distance_m

	def _compute_path_distance_m(self, coordinates: Sequence[RouteCoordinate]) -> int:
		"""Compute distance for a route polyline built from visiting coordinates."""
		if len(coordinates) < 2:
			return 0

		distance_m = 0
		for idx in range(1, len(coordinates)):
			start = coordinates[idx - 1]
			end = coordinates[idx]
			distance_m += self._haversine_distance_meters(
				float(start.latitude),
				float(start.longitude),
				float(end.latitude),
				float(end.longitude),
			)
		return distance_m

	@staticmethod
	def _append_route_coordinate(
		route_coordinates: list[RouteCoordinate],
		*,
		latitude: float,
		longitude: float,
	) -> None:
		"""Append route coordinate while skipping duplicate consecutive points."""
		if route_coordinates:
			last = route_coordinates[-1]
			if float(last.latitude) == float(latitude) and float(last.longitude) == float(longitude):
				return

		route_coordinates.append(
			RouteCoordinate(latitude=float(latitude), longitude=float(longitude))
		)

	def _estimate_duration_minutes(self, distance_m: int) -> float:
		"""Estimate route duration from distance and configured average speed."""
		average_speed_kmph = self._average_speed_kmph()
		distance_km = float(distance_m) / 1000.0
		return round((distance_km / average_speed_kmph) * 60.0, 2)

	def _estimate_travel_time_minutes(self, distance_m: int) -> int:
		"""Estimate integer travel minutes for the OR-Tools time dimension."""
		distance_km = float(distance_m) / 1000.0
		return math.ceil((distance_km / self._average_speed_kmph()) * 60.0)

	def _average_speed_kmph(self) -> float:
		"""Return a positive configured average speed for duration estimates."""
		average_speed_kmph = float(
			getattr(
				self._settings,
				"DEFAULT_OPTIMIZATION_AVERAGE_SPEED_KMPH",
				35.0,
			)
		)
		return max(average_speed_kmph, 1.0)

	@staticmethod
	def _time_windows_enabled(orders: Sequence[Order], enabled_by_request: bool = False) -> bool:
		"""Return whether valid order time windows are available and enabled."""
		if not enabled_by_request:
			return False
		for order in orders:
			start = getattr(order, "time_window_start", None)
			end = getattr(order, "time_window_end", None)
			if start is not None or end is not None:
				return True
		return False

	@staticmethod
	def _priority_constraints_enabled(orders: Sequence[Order], enabled_by_request: bool = False) -> bool:
		"""Return whether priority constraints can be applied and enabled."""
		if not enabled_by_request:
			return False
		return any(getattr(order, "priority", None) is not None for order in orders)

	def _runtime_time_windows_enabled(self, orders: Sequence[Order]) -> bool:
		"""Resolve time window enablement from runtime options and order data."""
		return self._time_windows_enabled(
			orders,
			enabled_by_request=bool(self._runtime_options.get("time_windows_enabled", False)),
		)

	def _runtime_priority_enabled(self, orders: Sequence[Order]) -> bool:
		"""Resolve priority enablement from runtime options and order data."""
		return self._priority_constraints_enabled(
			orders,
			enabled_by_request=bool(self._runtime_options.get("priority_enabled", False)),
		)

	def _add_time_windows_constraint(
		self,
		routing: pywrapcp.RoutingModel,
		manager: pywrapcp.RoutingIndexManager,
		transit_callback_index: int,
		orders: Sequence[Order],
	) -> None:
		"""Add optional time windows on a relative UTC-minute planning timeline."""
		windows = [self._extract_time_window(order) for order in orders]
		valid_windows = [window for window in windows if window is not None]
		if not valid_windows:
			return
		window_types = {
			isinstance(getattr(order, "time_window_start", None), datetime)
			for order in orders
			if getattr(order, "time_window_start", None) is not None
		}
		if len(window_types) > 1:
			raise ValueError("All order windows in one optimization must use the same time representation.")
		reference_minute = min(window[0] for window in valid_windows)
		horizon = max(window[1] - reference_minute for window in valid_windows) + 60
		routing.AddDimension(
			transit_callback_index,
			horizon,
			horizon,
			True,
			"Time",
		)
		time_dimension = routing.GetDimensionOrDie("Time")

		for order_index, order in enumerate(orders, start=1):
			window = self._extract_time_window(order)
			if window is None:
				continue
			node_index = manager.NodeToIndex(order_index)
			time_dimension.CumulVar(node_index).SetRange(
				window[0] - reference_minute,
				window[1] - reference_minute,
			)

	@staticmethod
	def _extract_time_window(order: Order) -> tuple[int, int] | None:
		"""Convert datetime bounds to absolute UTC minutes; naive datetimes mean UTC."""
		start = getattr(order, "time_window_start", None)
		end = getattr(order, "time_window_end", None)
		if start is None and end is None:
			return None
		if start is None or end is None:
			raise ValueError("Both time-window bounds must be provided.")

		if isinstance(start, datetime) or isinstance(end, datetime):
			if not isinstance(start, datetime) or not isinstance(end, datetime):
				raise ValueError("Time-window bounds must use the same value type.")
			start_utc = start.replace(tzinfo=timezone.utc) if start.utcoffset() is None else start.astimezone(timezone.utc)
			end_utc = end.replace(tzinfo=timezone.utc) if end.utcoffset() is None else end.astimezone(timezone.utc)
			if end_utc <= start_utc:
				raise ValueError("time_window_end must be after time_window_start.")
			start_min = int(start_utc.timestamp() // 60)
			end_min = int(end_utc.timestamp() // 60)
		else:
			start_min = int(start)
			end_min = int(end)
			if end_min <= start_min:
				raise ValueError("time_window_end must be after time_window_start.")
		return (start_min, end_min)

	def _compute_time_window_horizon(self, orders: Sequence[Order]) -> int:
		"""Compute a stable horizon for the optional time dimension."""
		windows = [self._extract_time_window(order) for order in orders]
		valid_windows = [window for window in windows if window is not None]
		if not valid_windows:
			return 60
		reference_minute = min(window[0] for window in valid_windows)
		max_end = 0
		for order in orders:
			window = self._extract_time_window(order)
			if window is None:
				continue
			max_end = max(max_end, window[1] - reference_minute)
		return max(max_end + 60, 60)


	@staticmethod
	def _haversine_distance_meters(
		lat1: float,
		lon1: float,
		lat2: float,
		lon2: float,
	) -> int:
		"""Compute great-circle distance in meters using the Haversine formula."""
		radius_m = 6_371_000.0
		phi1 = math.radians(lat1)
		phi2 = math.radians(lat2)
		d_phi = math.radians(lat2 - lat1)
		d_lambda = math.radians(lon2 - lon1)

		a = (
			math.sin(d_phi / 2.0) ** 2
			+ math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
		)
		c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
		return round(radius_m * c)

