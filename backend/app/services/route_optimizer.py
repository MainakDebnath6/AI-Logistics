from __future__ import annotations

import math
from typing import Sequence, TypedDict

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.core.config import get_settings
from app.models.driver import Driver
from app.models.order import Order
from app.models.vehicle import Vehicle

from app.schemas.optimization import (
	OptimizationDriver,
	OptimizationResponse,
	OptimizationStop,
	OptimizedRoute,
	OptimizationVehicle,
	RouteCoordinate,
)


class _OptimizationDataModel(TypedDict):
	"""Typed OR-Tools routing input data."""

	distance_matrix: list[list[int]]
	demands: list[int]
	vehicle_capacities: list[int]
	num_vehicles: int
	depot: int


class _RuntimeOptimizationOptions(TypedDict):
	"""Runtime flags controlling optional optimization behaviors."""

	time_windows_enabled: bool
	priority_enabled: bool
	timeout_seconds: int | None


class RouteOptimizerService:
	"""Service that computes capacitated routes using Google OR-Tools."""

	def __init__(self) -> None:
		"""Initialize optimizer service with application defaults."""
		self._settings = get_settings()
		self._runtime_options: _RuntimeOptimizationOptions = {
			"time_windows_enabled": False,
			"priority_enabled": False,
			"timeout_seconds": None,
		}

	def configure(
		self,
		*,
		time_windows_enabled: bool = False,
		priority_enabled: bool = False,
		optimization_timeout_seconds: int | None = None,
	) -> None:
		"""Configure optional runtime optimization behaviors for next run."""
		timeout_value: int | None = None
		if optimization_timeout_seconds is not None:
			timeout_value = max(int(optimization_timeout_seconds), 1)

		self._runtime_options = {
			"time_windows_enabled": bool(time_windows_enabled),
			"priority_enabled": bool(priority_enabled),
			"timeout_seconds": timeout_value,
		}

	def optimize(
		self,
		drivers: Sequence[Driver],
		vehicles: Sequence[Vehicle],
		orders: Sequence[Order],
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
				routes=[],
			)

		data = self._create_data_model(drivers=drivers, vehicles=vehicles, orders=orders)

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

		if self._runtime_time_windows_enabled(orders):
			self._add_time_windows_constraint(
				routing=routing,
				manager=manager,
				transit_callback_index=transit_callback_index,
				orders=orders,
			)

		if self._runtime_priority_enabled(orders):
			self._add_priority_constraints(
				routing=routing,
				manager=manager,
				orders=orders,
			)

		solution = routing.SolveWithParameters(search_parameters)
		if solution is None:
			raise RuntimeError("No feasible optimization solution found.")

		routes, total_distance_m = self._extract_solution_routes(
			routing=routing,
			manager=manager,
			solution=solution,
			data=data,
			drivers=drivers,
			vehicles=vehicles,
			orders=orders,
		)

		return OptimizationResponse(
			total_distance_km=round(total_distance_m / 1000.0, 3),
			total_orders=len(orders),
			total_routes=len(routes),
			routes=routes,
		)

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
	) -> _OptimizationDataModel:
		"""Create the OR-Tools data model for a capacitated VRP."""
		num_vehicles = min(len(drivers), len(vehicles))
		if num_vehicles <= 0:
			raise ValueError("At least one driver and vehicle pair is required.")

		selected_vehicles = list(vehicles[:num_vehicles])

		depot_coord = (
			float(orders[0].pickup_latitude),
			float(orders[0].pickup_longitude),
		)
		order_coords = [
			(float(order.pickup_latitude), float(order.pickup_longitude))
			for order in orders
		]
		coordinates = [depot_coord, *order_coords]

		demands = [0, *[int(order.demand) for order in orders]]
		vehicle_capacities = [int(vehicle.capacity) for vehicle in selected_vehicles]

		if sum(vehicle_capacities) < sum(demands):
			raise RuntimeError("Insufficient vehicle capacity for all orders.")

		return {
			"distance_matrix": self._build_distance_matrix(coordinates),
			"demands": demands,
			"vehicle_capacities": vehicle_capacities,
			"num_vehicles": num_vehicles,
			"depot": 0,
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
			stops: list[OptimizationStop] = []
			route_coordinates: list[RouteCoordinate] = []

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
						latitude=float(order.pickup_latitude),
						longitude=float(order.pickup_longitude),
					)
					self._append_route_coordinate(
						route_coordinates,
						latitude=float(order.delivery_latitude),
						longitude=float(order.delivery_longitude),
					)

				next_index = solution.Value(routing.NextVar(index))
				index = next_index

			if stops:
				route_distance_m = self._compute_path_distance_m(route_coordinates)
				route_duration_minutes = self._estimate_duration_minutes(route_distance_m)
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
						total_distance_km=round(route_distance_m / 1000.0, 3),
						total_duration_minutes=route_duration_minutes,
						total_demand=route_demand,
						total_orders=len(stops),
						stops=stops,
						route_coordinates=route_coordinates,
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
		average_speed_kmph = float(
			getattr(
				self._settings,
				"DEFAULT_OPTIMIZATION_AVERAGE_SPEED_KMPH",
				35.0,
			)
		)
		safe_speed_kmph = max(average_speed_kmph, 1.0)
		distance_km = float(distance_m) / 1000.0
		return round((distance_km / safe_speed_kmph) * 60.0, 2)

	@staticmethod
	def _time_windows_enabled(orders: Sequence[Order], enabled_by_request: bool = False) -> bool:
		"""Return whether valid order time windows are available and enabled."""
		if not enabled_by_request:
			return False
		for order in orders:
			start = getattr(order, "time_window_start", None)
			end = getattr(order, "time_window_end", None)
			if start is not None and end is not None:
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
		"""Add optional time-window dimension and ranges for order stops."""
		horizon = self._compute_time_window_horizon(orders)
		routing.AddDimension(
			transit_callback_index,
			horizon,
			horizon,
			False,
			"Time",
		)
		time_dimension = routing.GetDimensionOrDie("Time")

		for order_index, order in enumerate(orders, start=1):
			window = self._extract_time_window(order)
			if window is None:
				continue
			node_index = manager.NodeToIndex(order_index)
			time_dimension.CumulVar(node_index).SetRange(window[0], window[1])

	@staticmethod
	def _extract_time_window(order: Order) -> tuple[int, int] | None:
		"""Extract a normalized order time window in minutes."""
		start = getattr(order, "time_window_start", None)
		end = getattr(order, "time_window_end", None)
		if start is None or end is None:
			return None

		start_min = int(start)
		end_min = int(end)
		if end_min < start_min:
			start_min, end_min = end_min, start_min
		return (start_min, end_min)

	def _compute_time_window_horizon(self, orders: Sequence[Order]) -> int:
		"""Compute a stable horizon for the optional time dimension."""
		max_end = 0
		for order in orders:
			window = self._extract_time_window(order)
			if window is None:
				continue
			max_end = max(max_end, window[1])
		return max(max_end + 60, 60)


	def _add_priority_constraints(
		self,
		routing: pywrapcp.RoutingModel,
		manager: pywrapcp.RoutingIndexManager,
		orders: Sequence[Order],
	) -> None:
		"""Add optional priority-aware disjunction penalties for orders."""
		for order_index, order in enumerate(orders, start=1):
			priority = self._extract_priority(order)
			if priority is None:
				continue
			node_index = manager.NodeToIndex(order_index)
			penalty = self._priority_to_penalty(priority)
			routing.AddDisjunction([node_index], penalty)

	@staticmethod
	def _extract_priority(order: Order) -> int | None:
		"""Extract order priority as integer when available."""
		value = getattr(order, "priority", None)
		if value is None:
			return None
		priority = int(value)
		return max(priority, 0)

	@staticmethod
	def _priority_to_penalty(priority: int) -> int:
		"""Convert priority score to OR-Tools disjunction penalty."""
		base_penalty = 10_000
		return base_penalty * (priority + 1)

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
		return int(round(radius_m * c))

