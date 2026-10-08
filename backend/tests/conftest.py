from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.models.order import OrderStatus
from app.services.route_optimizer import RouteOptimizerService


class OfflineRoutingService:
    """Disable optional OSRM calls while retaining optimizer behavior."""

    def build_road_route(self, route_coordinates):
        return None


@pytest.fixture
def optimizer() -> RouteOptimizerService:
    return RouteOptimizerService(routing_service=OfflineRoutingService())


@pytest.fixture
def make_driver():
    def factory():
        return SimpleNamespace(
            id=uuid4(),
            user=SimpleNamespace(full_name="Test Driver"),
        )

    return factory


@pytest.fixture
def make_vehicle():
    def factory(capacity: int = 10):
        return SimpleNamespace(
            id=uuid4(),
            registration_number="TEST-001",
            capacity=capacity,
        )

    return factory


@pytest.fixture
def make_order():
    def factory(
        demand: int = 1,
        *,
        latitude: float = 40.0,
        longitude: float = -73.0,
        time_window_start=None,
        time_window_end=None,
        priority: int = 1,
    ):
        order_id = uuid4()
        return SimpleNamespace(
            id=order_id,
            customer_name=f"Customer {str(order_id)[:8]}",
            pickup_address="Pickup address",
            delivery_address="Delivery address",
            pickup_latitude=latitude,
            pickup_longitude=longitude,
            delivery_latitude=latitude + 0.01,
            delivery_longitude=longitude + 0.01,
            demand=demand,
            priority=priority,
            status=OrderStatus.PENDING,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
        )

    return factory
