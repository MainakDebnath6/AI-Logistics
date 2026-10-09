from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.models.driver import DriverStatus
from app.models.order import OrderStatus
from app.models.route import Route
from app.models.vehicle import VehicleStatus
from app.schemas.driver import DriverResponse
from app.services.analytics_service import AnalyticsService


def test_driver_response_exposes_linked_name_without_removing_existing_fields():
    now = datetime.now(timezone.utc)
    driver = SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        user=SimpleNamespace(full_name="Sam Dispatcher"),
        license_number="LIC-100",
        phone="555-0100",
        vehicle_id=None,
        status=DriverStatus.AVAILABLE,
        current_latitude=None,
        current_longitude=None,
        max_capacity=10,
        is_available=True,
        created_at=now,
        updated_at=now,
    )

    response = DriverResponse.model_validate(driver)

    assert response.full_name == "Sam Dispatcher"
    assert response.license_number == "LIC-100"
    assert response.model_dump()["full_name"] == "Sam Dispatcher"


def test_dashboard_uses_live_assignments_and_persisted_route_history():
    vehicle_ids = [uuid4(), uuid4(), uuid4()]
    driver_ids = [uuid4(), uuid4(), uuid4()]
    orders = [
        SimpleNamespace(status=OrderStatus.PENDING, assigned_driver_id=None, assigned_vehicle_id=None),
        SimpleNamespace(status=OrderStatus.ASSIGNED, assigned_driver_id=driver_ids[0], assigned_vehicle_id=vehicle_ids[0]),
        SimpleNamespace(status=OrderStatus.IN_TRANSIT, assigned_driver_id=driver_ids[0], assigned_vehicle_id=vehicle_ids[0]),
        SimpleNamespace(status=OrderStatus.DELIVERED, assigned_driver_id=None, assigned_vehicle_id=None),
        SimpleNamespace(status=OrderStatus.CANCELLED, assigned_driver_id=driver_ids[1], assigned_vehicle_id=vehicle_ids[1]),
    ]
    drivers = [
        SimpleNamespace(id=driver_ids[0], status=DriverStatus.BUSY),
        SimpleNamespace(id=driver_ids[1], status=DriverStatus.AVAILABLE),
        SimpleNamespace(id=driver_ids[2], status=DriverStatus.OFFLINE),
    ]
    vehicles = [
        SimpleNamespace(id=vehicle_ids[0], is_active=True, status=VehicleStatus.IN_USE),
        SimpleNamespace(id=vehicle_ids[1], is_active=True, status=VehicleStatus.AVAILABLE),
        SimpleNamespace(id=vehicle_ids[2], is_active=False, status=VehicleStatus.OUT_OF_SERVICE),
    ]
    route_history = [
        Route(
            id=uuid4(),
            driver_id=driver_ids[0],
            vehicle_id=vehicle_ids[0],
            total_distance_km=12.0,
            total_load=5,
            optimization_result={
                "road_route_status": "available",
                "total_duration_minutes": 24.0,
            },
        ),
        Route(
            id=uuid4(),
            driver_id=driver_ids[1],
            vehicle_id=vehicle_ids[1],
            total_distance_km=18.0,
            total_load=7,
            optimization_result={
                "road_route_status": "failed",
                "total_duration_minutes": None,
            },
        ),
    ]

    result = AnalyticsService().get_dashboard_metrics(
        drivers=drivers,
        vehicles=vehicles,
        orders=orders,
        route_history=route_history,
    )

    assert result.completed_orders == 1
    assert result.pending_orders == 3
    assert result.cancelled_orders == 1
    assert result.total_orders == 5
    assert result.completed_orders + result.pending_orders + result.cancelled_orders == result.total_orders
    assert result.driver_utilization_percentage == 50.0
    assert result.vehicle_utilization_percentage == 50.0
    assert result.average_route_distance_km == 15.0
    assert result.average_eta_minutes == 24.0
    assert result.route_efficiency_percentage == 25.0
    assert result.on_time_delivery_percentage is None

    current_result = SimpleNamespace(
        routes=[
            SimpleNamespace(
                total_distance_km=999.0,
                model_dump=lambda mode: {
                    "road_route_status": "available",
                    "total_duration_minutes": 999.0,
                },
            )
        ]
    )
    assert AnalyticsService._compute_average_route_distance_km(current_result, route_history) == 15.0
    assert AnalyticsService._compute_average_eta_minutes(current_result, route_history) == 24.0


def test_unavailable_dashboard_metrics_remain_null_not_zero():
    result = AnalyticsService().get_dashboard_metrics(
        drivers=[],
        vehicles=[],
        orders=[],
        route_history=[],
    )

    assert result.vehicle_utilization_percentage is None
    assert result.driver_utilization_percentage is None
    assert result.average_route_distance_km is None
    assert result.average_eta_minutes is None
    assert result.route_efficiency_percentage is None
    assert result.on_time_delivery_percentage is None