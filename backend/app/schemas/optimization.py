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


class OptimizationStop(BaseModel):
	"""Represents a single stop in an optimized route."""

	order_id: UUID
	sequence: int
	arrival_time: datetime | None = None
	distance_km: float | None = None


class OptimizedRoute(BaseModel):
	"""Represents one optimized route assignment."""

	driver_id: UUID
	vehicle_id: UUID
	total_distance_km: float
	total_load: int
	stops: list[OptimizationStop]


class OptimizationResponse(BaseModel):
	"""Aggregated response for an optimization run."""

	model_config = ConfigDict(from_attributes=True)

	total_distance_km: float
	total_orders: int
	total_routes: int
	routes: list[OptimizedRoute]
