"""Order API routes."""

from uuid import UUID

from app.dependencies.auth import get_current_admin, get_current_dispatcher
from app.dependencies.database import get_db
from app.models.order import OrderStatus
from app.models.user import User
from app.repositories.order_repository import OrderRepository
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)
from app.services.order_service import OrderService
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Build the order service for the active database session."""

    return OrderService(OrderRepository(db))


@router.get("/", response_model=list[OrderResponse])
def list_orders(
    skip: int = 0,
    limit: int = 100,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[OrderResponse]:
    """Return all orders."""

    return order_service.list_orders(skip=skip, limit=limit)


@router.get("/unassigned", response_model=list[OrderResponse])
def list_unassigned_orders(
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[OrderResponse]:
    """Return all unassigned orders."""

    return order_service.list_unassigned_orders()


@router.get("/status/{status}", response_model=list[OrderResponse])
def list_orders_by_status(
    status: OrderStatus,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[OrderResponse]:
    """Return orders by status."""

    return order_service.list_orders_by_status(status)


@router.get("/driver/{driver_id}", response_model=list[OrderResponse])
def list_orders_by_driver(
    driver_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[OrderResponse]:
    """Return orders assigned to a driver."""

    return order_service.list_orders_by_driver(driver_id)


@router.get("/vehicle/{vehicle_id}", response_model=list[OrderResponse])
def list_orders_by_vehicle(
    vehicle_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> list[OrderResponse]:
    """Return orders assigned to a vehicle."""

    return order_service.list_orders_by_vehicle(vehicle_id)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_dispatcher),
) -> OrderResponse:
    """Return one order by identifier."""

    return order_service.get_order(order_id)


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    payload: OrderCreate,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_admin),
) -> OrderResponse:
    """Create a new order."""

    return order_service.create_order(payload)


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_admin),
) -> OrderResponse:
    """Update an existing order."""

    return order_service.update_order(order_id, payload)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_order(
    order_id: UUID,
    order_service: OrderService = Depends(get_order_service),
    _current_user: User = Depends(get_current_admin),
) -> Response:
    """Delete an order."""

    order_service.delete_order(order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)