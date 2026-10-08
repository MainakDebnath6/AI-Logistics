"""Business logic for order operations."""

from uuid import UUID

from app.models.order import Order
from app.repositories.order_repository import OrderRepository
from app.schemas.order import OrderCreate, OrderUpdate
from fastapi import HTTPException, status

ORDER_NOT_FOUND = "Order not found."
INVALID_DEMAND = "Demand must be greater than 0."
INVALID_PRIORITY = "Priority must be greater than 0."
INVALID_TIME_WINDOW = "End time must be after start time."


class OrderService:
    """Coordinate order persistence and business rules."""

    def __init__(self, repository: OrderRepository) -> None:
        """Initialize the service with an order repository."""

        self.repository = repository

    def create_order(self, order_data: OrderCreate) -> Order:
        """Create a new order."""

        if order_data.demand <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_DEMAND,
            )

        if order_data.priority <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_PRIORITY,
            )

        if (
            order_data.time_window_start
            and order_data.time_window_end
            and order_data.time_window_end < order_data.time_window_start
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_TIME_WINDOW,
            )

        order = Order(**order_data.model_dump())

        return self.repository.create(order)

    def get_order(self, order_id: UUID) -> Order:
        """Return an order by identifier."""

        order = self.repository.get_by_id(order_id)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ORDER_NOT_FOUND,
            )

        return order

    def list_orders(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Order]:
        """Return orders with pagination."""

        return self.repository.get_all(skip=skip, limit=limit)

    def list_orders_by_status(self, status) -> list[Order]:
        """Return orders matching a status."""

        return self.repository.get_by_status(status)

    def list_orders_by_driver(self, driver_id: UUID) -> list[Order]:
        """Return orders assigned to a driver."""

        return self.repository.get_by_driver(driver_id)

    def list_orders_by_vehicle(self, vehicle_id: UUID) -> list[Order]:
        """Return orders assigned to a vehicle."""

        return self.repository.get_by_vehicle(vehicle_id)

    def list_unassigned_orders(self) -> list[Order]:
        """Return orders awaiting assignment."""

        return self.repository.get_unassigned_orders()

    def update_order(
        self,
        order_id: UUID,
        order_data: OrderUpdate,
    ) -> Order:
        """Update an existing order."""

        order = self.repository.get_by_id(order_id)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ORDER_NOT_FOUND,
            )

        if order_data.demand is not None and order_data.demand <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_DEMAND,
            )

        if order_data.priority is not None and order_data.priority <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_PRIORITY,
            )

        start = (
            order_data.time_window_start
            if order_data.time_window_start is not None
            else order.time_window_start
        )

        end = (
            order_data.time_window_end
            if order_data.time_window_end is not None
            else order.time_window_end
        )

        if start and end and end < start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=INVALID_TIME_WINDOW,
            )

        data = order_data.model_dump(exclude_unset=True)

        return self.repository.update(order, data)

    def delete_order(self, order_id: UUID) -> None:
        """Delete an order."""

        order = self.repository.get_by_id(order_id)

        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ORDER_NOT_FOUND,
            )

        self.repository.delete(order)