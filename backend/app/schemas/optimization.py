from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OptimizationRequest(BaseModel):
	"""Payload for requesting route optimization inputs."""

	driver_ids: list[UUID]
	vehicle_ids: list[UUID]
	order_ids: list[UUID]
	time_windows_enabled: bool = False
	priority_enabled: bool = False
	optimization_timeout_seconds: int = 5


class OptimizationDriver(BaseModel):
	"""Driver summary for an optimized route."""

	id: UUID
	full_name: str


class OptimizationVehicle(BaseModel):
	"""Vehicle summary for an optimized route."""

	id: UUID
	registration_number: str
	capacity: int


class RouteCoordinate(BaseModel):
	"""Canonical coordinate point for route plotting."""

	latitude: float
	longitude: float


class OptimizationStop(BaseModel):
	"""Represents a single stop in an optimized route."""

	order_id: UUID
	customer_name: str
	pickup_address: str
	delivery_address: str
	pickup_latitude: float
	pickup_longitude: float
	delivery_latitude: float
	delivery_longitude: float
	demand: int
	priority: int
	status: str
	sequence: int
	arrival_time: datetime | None = None


class OptimizedRoute(BaseModel):
	"""Represents one optimized route assignment."""

	driver: OptimizationDriver
	vehicle: OptimizationVehicle
	total_distance_km: float
	total_duration_minutes: float
	total_demand: int
	total_orders: int
	stops: list[OptimizationStop]
	route_coordinates: list[RouteCoordinate]
	road_geometry: list[RouteCoordinate] = []
	distance: float | None = None
	duration: float | None = None


class OptimizationResponse(BaseModel):
	"""Aggregated response for an optimization run."""

	model_config = ConfigDict(from_attributes=True)

	total_distance_km: float
	total_orders: int
	total_routes: int
	routes: list[OptimizedRoute]
