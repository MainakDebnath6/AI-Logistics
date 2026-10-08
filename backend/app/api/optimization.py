from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_dispatcher
from app.models.driver import Driver
from app.models.order import Order
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.driver_repository import DriverRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.optimization import OptimizationRequest, OptimizationResponse
from app.services.route_optimizer import RouteOptimizerService
from app.services.routing_service import RoutingService

router = APIRouter(
	prefix="/optimization",
	tags=["Optimization"],
)


def get_driver_repository(db: Session = Depends(get_db)) -> DriverRepository:
	"""Create a driver repository instance."""
	return DriverRepository(db)


def get_vehicle_repository(db: Session = Depends(get_db)) -> VehicleRepository:
	"""Create a vehicle repository instance."""
	return VehicleRepository(db)


def get_order_repository(db: Session = Depends(get_db)) -> OrderRepository:
	"""Create an order repository instance."""
	return OrderRepository(db)


def get_route_repository(db: Session = Depends(get_db)) -> RouteRepository:
	"""Create a route repository instance."""
	return RouteRepository(db)


def get_routing_service() -> RoutingService:
	"""Create a road routing service instance."""
	return RoutingService()


def get_route_optimizer_service_with_routing(
	routing_service: RoutingService = Depends(get_routing_service),
) -> RouteOptimizerService:
	"""Create a route optimizer service instance."""
	return RouteOptimizerService(routing_service=routing_service)


def _missing_ids(requested_ids: Sequence[UUID], found_ids: Sequence[UUID]) -> list[UUID]:
	"""Return requested identifiers that were not found."""
	found_set = set(found_ids)
	return [entity_id for entity_id in requested_ids if entity_id not in found_set]


def _raise_if_missing_entities(
	driver_ids: Sequence[UUID],
	found_drivers: Sequence[Driver],
	vehicle_ids: Sequence[UUID],
	found_vehicles: Sequence[Vehicle],
	order_ids: Sequence[UUID],
	found_orders: Sequence[Order],
) -> None:
	"""Raise HTTP 404 when any requested optimization entity is missing."""
	missing_drivers = _missing_ids(driver_ids, [driver.id for driver in found_drivers])
	missing_vehicles = _missing_ids(vehicle_ids, [vehicle.id for vehicle in found_vehicles])
	missing_orders = _missing_ids(order_ids, [order.id for order in found_orders])

	if not (missing_drivers or missing_vehicles or missing_orders):
		return

	raise HTTPException(
		status_code=status.HTTP_404_NOT_FOUND,
		detail={
			"message": "One or more requested entities were not found.",
			"missing_driver_ids": missing_drivers,
			"missing_vehicle_ids": missing_vehicles,
			"missing_order_ids": missing_orders,
		},
	)


def _is_dispatcher_or_admin(user: User) -> bool:
	"""Return whether the authenticated user can run route optimization."""
	role = getattr(user, "role", None)
	if role is None:
		return False

	role_value = getattr(role, "value", role)
	if not isinstance(role_value, str):
		return False

	return role_value.lower() in {"dispatcher", "admin"}


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_routes(
	payload: OptimizationRequest,
	current_dispatcher: User = Depends(get_current_dispatcher),
	driver_repository: DriverRepository = Depends(get_driver_repository),
	vehicle_repository: VehicleRepository = Depends(get_vehicle_repository),
	order_repository: OrderRepository = Depends(get_order_repository),
	route_repository: RouteRepository = Depends(get_route_repository),
	optimizer_service: RouteOptimizerService = Depends(get_route_optimizer_service_with_routing),
) -> OptimizationResponse:
	"""Optimize routes for the requested drivers, vehicles, and orders."""
	if not _is_dispatcher_or_admin(current_dispatcher):
		raise HTTPException(
			status_code=status.HTTP_403_FORBIDDEN,
			detail="Only dispatcher or admin users can optimize routes.",
		)

	drivers = driver_repository.get_by_ids(payload.driver_ids)
	vehicles = vehicle_repository.get_by_ids(payload.vehicle_ids)
	orders = order_repository.get_by_ids(payload.order_ids)

	_raise_if_missing_entities(
		driver_ids=payload.driver_ids,
		found_drivers=drivers,
		vehicle_ids=payload.vehicle_ids,
		found_vehicles=vehicles,
		order_ids=payload.order_ids,
		found_orders=orders,
	)

	optimizer_service.configure(
		time_windows_enabled=payload.time_windows_enabled,
		priority_enabled=payload.priority_enabled,
		optimization_timeout_seconds=payload.optimization_timeout_seconds,
	)

	optimization_started_at = datetime.now(timezone.utc)
	try:
		result = optimizer_service.optimize(
			drivers=drivers,
			vehicles=vehicles,
			orders=orders,
			depot_coordinates=(payload.depot_latitude, payload.depot_longitude)
			if payload.depot_latitude is not None
			else None,
		)
	except ValueError as error:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=str(error),
		) from error
	except RuntimeError as error:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=str(error),
		) from error

	optimization_completed_at = datetime.now(timezone.utc)
	requested_order_ids = set(payload.order_ids)
	served_order_ids = [stop.order_id for route in result.routes for stop in route.stops]
	if len(served_order_ids) != len(set(served_order_ids)) or set(served_order_ids) != requested_order_ids:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Optimizer result did not serve each requested confirmed order exactly once.",
		)

	route_repository.create_many(
		[
			Route(
				driver_id=route.driver.id,
				vehicle_id=route.vehicle.id,
				total_distance_km=route.total_distance_km,
				total_load=route.total_demand,
				optimization_result=route.model_dump(mode="json"),
				optimization_started_at=optimization_started_at,
				optimization_completed_at=optimization_completed_at,
			)
			for route in result.routes
		]
	)
	return result
