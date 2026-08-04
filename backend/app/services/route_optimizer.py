from __future__ import annotations

import math
from typing import Sequence, TypedDict

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from app.models.driver import Driver
from app.models.order import Order
from app.models.vehicle import Vehicle

from app.schemas.optimization import (
	OptimizationResponse,
	OptimizationStop,
	OptimizedRoute,
)


class _OptimizationDataModel(TypedDict):
	"""Typed OR-Tools routing input data."""

	distance_matrix: list[list[int]]
	demands: list[int]
	vehicle_capacities: list[int]
	num_vehicles: int
	depot: int


class RouteOptimizerService:
	"""Service that computes capacitated routes using Google OR-Tools."""

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
		search_parameters.first_solution_strategy = (
			routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
		)
		search_parameters.local_search_metaheuristic = (
			routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
		)
		search_parameters.time_limit.FromSeconds(5)

		solution = routing.SolveWithParameters(search_parameters)
		if solution is None:
			raise RuntimeError("No feasible optimization solution found.")

		routes: list[OptimizedRoute] = []
		total_distance_m = 0

		for vehicle_idx in range(data["num_vehicles"]):
			index = routing.Start(vehicle_idx)
			previous_node = data["depot"]
			sequence = 0
			route_load = 0
			route_distance_m = 0
			stops: list[OptimizationStop] = []

			while not routing.IsEnd(index):
				node = manager.IndexToNode(index)

				if node != data["depot"]:
					sequence += 1
					order_index = node - 1
					segment_m = data["distance_matrix"][previous_node][node]
					route_load += data["demands"][node]
					stops.append(
						OptimizationStop(
							order_id=orders[order_index].id,
							sequence=sequence,
							arrival_time=None,
							distance_km=round(segment_m / 1000.0, 3),
						)
					)

				next_index = solution.Value(routing.NextVar(index))
				route_distance_m += routing.GetArcCostForVehicle(index, next_index, vehicle_idx)
				previous_node = node
				index = next_index

			if stops:
				routes.append(
					OptimizedRoute(
						driver_id=drivers[vehicle_idx].id,
						vehicle_id=vehicles[vehicle_idx].id,
						total_distance_km=round(route_distance_m / 1000.0, 3),
						total_load=route_load,
						stops=stops,
					)
				)
				total_distance_m += route_distance_m

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

		demands = [0, *[int(order.quantity) for order in orders]]
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

