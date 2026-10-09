from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OptimizationRequest(BaseModel):
	"""Payload for requesting route optimization inputs."""

	driver_ids: list[UUID]
	vehicle_ids: list[UUID]
	order_ids: list[UUID]
	time_windows_enabled: bool = False
	priority_enabled: bool = False
	optimization_timeout_seconds: int = 5
	depot_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
	depot_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)

	@model_validator(mode="after")
	def validate_depot_coordinates(self) -> "OptimizationRequest":
		if (self.depot_latitude is None) != (self.depot_longitude is None):
			raise ValueError("depot_latitude and depot_longitude must be provided together.")
		for field_name in ("driver_ids", "vehicle_ids", "order_ids"):
			values = getattr(self, field_name)
			if len(values) != len(set(values)):
				raise ValueError(f"{field_name} must not contain duplicate identifiers.")
		return self


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

	latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
	longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)


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
	total_duration_minutes: float | None
	total_demand: int
	total_orders: int
	stops: list[OptimizationStop]
	route_coordinates: list[RouteCoordinate]
	road_geometry: list[RouteCoordinate] = Field(default_factory=list)
	road_route_status: str = "unavailable"
	road_route_error: str | None = None
	distance: float | None = None
	duration: float | None = None
	road_distance_km: float | None = None


class OptimizationResponse(BaseModel):
	"""Aggregated response for an optimization run."""

	model_config = ConfigDict(from_attributes=True)

	total_distance_km: float
	total_orders: int
	total_routes: int
	routes: list[OptimizedRoute] = Field(default_factory=list)
	requested_orders: int | None = None
	served_order_ids: list[UUID] = Field(default_factory=list)
	unserved_order_ids: list[UUID] = Field(default_factory=list)
