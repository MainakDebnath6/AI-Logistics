from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from app.api.optimization import optimize_routes
from app.api.predictions import forecast_and_assess_capacity
from app.db.base import Base
from app.dependencies.auth import get_current_admin, get_current_dispatcher
from app.models.driver import Driver
from app.models.order import Order, OrderStatus
from app.models.route import Route
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.repositories.driver_repository import DriverRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.route_repository import RouteRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.hgfc import HGFCForecastRequest, HGFCRequest, HGFCStatus
from app.schemas.optimization import OptimizationRequest, OptimizationResponse
from app.schemas.order import OrderCreate
from app.services.demand_forecast_service import DemandForecastService
from app.services.hgfc_service import HGFCService
from fastapi import HTTPException
from pydantic import ValidationError
from scripts.seed_demo import seed_demo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def test_demand_forecast_fallback_is_deterministic():
    service = DemandForecastService()

    assert service.forecast_demand([10, 20, 30]) == 19.27


def test_demand_forecast_horizon_returns_cumulative_daily_workload():
    service = DemandForecastService()

    assert service.forecast_demand_for_horizon([10, 20, 30], 3) == 57.81
    with pytest.raises(ValueError, match="at least one day"):
        service.forecast_demand_for_horizon([10, 20, 30], 0)
    assert service.forecast_demand([10, 20, 30]) == 19.27


def test_cvrp_routes_respect_vehicle_capacity(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    drivers = [make_driver(), make_driver()]
    vehicles = [make_vehicle(5), make_vehicle(5)]
    orders = [
        make_order(4, latitude=40.0),
        make_order(3, latitude=40.1),
        make_order(2, latitude=40.2),
    ]

    result = optimizer.optimize(drivers, vehicles, orders)

    assert result.total_orders == len(orders)
    assert result.total_routes > 0
    for route in result.routes:
        assert route.total_demand <= route.vehicle.capacity
        assert sum(stop.demand for stop in route.stops) == route.total_demand

    served_order_ids = [stop.order_id for route in result.routes for stop in route.stops]
    assert set(served_order_ids) == {order.id for order in orders}
    assert len(served_order_ids) == len(set(served_order_ids))


def test_insufficient_fleet_capacity_raises_existing_error(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    with pytest.raises(RuntimeError, match="Insufficient vehicle capacity"):
        optimizer.optimize(
            [make_driver()],
            [make_vehicle(4)],
            [make_order(3), make_order(2, latitude=40.1)],
        )


def test_zero_orders_returns_empty_optimization_result(
    optimizer,
    make_driver,
    make_vehicle,
):
    result = optimizer.optimize([make_driver()], [make_vehicle()], [])

    assert result.total_distance_km == 0
    assert result.total_orders == 0
    assert result.total_routes == 0
    assert result.routes == []


def test_priority_option_runs_and_accounts_for_served_and_unserved_orders(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    orders = [
        make_order(2, latitude=40.0, priority=1),
        make_order(2, latitude=40.1, priority=3),
    ]
    optimizer.configure(priority_enabled=True)

    result = optimizer.optimize([make_driver()], [make_vehicle(4)], orders)

    requested_ids = {order.id for order in orders}
    served_ids = {stop.order_id for route in result.routes for stop in route.stops}
    unserved_ids = requested_ids - served_ids

    assert served_ids <= requested_ids
    assert served_ids.isdisjoint(unserved_ids)
    assert served_ids | unserved_ids == requested_ids
    assert sum(route.total_orders for route in result.routes) == len(served_ids)
    assert result.total_orders == len(orders)


def test_time_window_option_accepts_order_datetime_fields(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    order = make_order(
        time_window_start=datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 10, 8, 17, tzinfo=timezone.utc),
    )
    optimizer.configure(time_windows_enabled=True)

    result = optimizer.optimize([make_driver()], [make_vehicle()], [order])

    assert result.total_orders == 1
    assert result.routes[0].stops[0].order_id == order.id


def test_time_window_conversion_normalizes_timezone_aware_datetimes(
    optimizer,
    make_order,
):
    order = make_order(
        time_window_start=datetime.fromisoformat("2026-10-08T09:00:00+02:00"),
        time_window_end=datetime.fromisoformat("2026-10-08T11:00:00+02:00"),
    )

    start_minute, end_minute = optimizer._extract_time_window(order)

    assert end_minute - start_minute == 120
    assert start_minute == int(datetime(2026, 10, 8, 7, tzinfo=timezone.utc).timestamp() // 60)


def test_time_window_conversion_preserves_legacy_minute_values(optimizer, make_order):
    order = make_order(time_window_start=60, time_window_end=120)

    assert optimizer._extract_time_window(order) == (60, 120)


def test_time_window_conversion_rejects_naive_datetimes(optimizer, make_order):
    order = make_order(
        time_window_start=datetime.fromisoformat("2026-10-08T09:00:00"),
        time_window_end=datetime.fromisoformat("2026-10-08T17:00:00"),
    )

    with pytest.raises(ValueError, match="must include timezone information"):
        optimizer._extract_time_window(order)


def test_time_transit_uses_integer_travel_minutes(optimizer):
    assert optimizer._estimate_travel_time_minutes(35_000) == 60


def test_order_schema_rejects_reversed_time_window():
    with pytest.raises(ValidationError, match="time_window_start must be before"):
        OrderCreate(
            customer_name="Test Customer",
            customer_phone="000-000-0000",
            pickup_address="Pickup address",
            delivery_address="Delivery address",
            pickup_latitude=40.0,
            pickup_longitude=-73.0,
            delivery_latitude=40.1,
            delivery_longitude=-73.1,
            demand=1,
            time_window_start=datetime(2026, 10, 8, 17, tzinfo=timezone.utc),
            time_window_end=datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
        )


@pytest.mark.parametrize(
    ("forecast", "capacity", "delta", "rho", "risk", "preparation"),
    [
        (6.0, 10.0, -4.0, 0.6, 0.0, False),
        (10.0, 10.0, 0.0, 1.0, 0.0, False),
        (13.0, 10.0, 3.0, 1.3, 3.0, True),
    ],
)
def test_hgfc_capacity_boundary_math(
    forecast,
    capacity,
    delta,
    rho,
    risk,
    preparation,
):
    result = HGFCService(advisory_horizon_days=14).assess(
        HGFCRequest(
            forecast_demand=forecast,
            available_capacity=capacity,
            horizon_days=7,
        )
    )

    assert result.gate_open
    assert result.capacity_delta == delta
    assert result.rho == pytest.approx(rho)
    assert result.capacity_risk == risk
    assert result.preparation_recommended is preparation


def test_hgfc_zero_capacity_is_defined_without_infinite_ratio():
    result = HGFCService().assess(
        HGFCRequest(forecast_demand=8.0, available_capacity=0.0, horizon_days=1)
    )

    assert result.capacity_delta == 8.0
    assert result.rho is None
    assert result.capacity_risk == 8.0
    assert result.recommended_additional_capacity == 8.0
    assert result.status is HGFCStatus.CAPACITY_SHORTFALL


def test_hgfc_horizon_gate_suppresses_out_of_window_risk():
    result = HGFCService(advisory_horizon_days=14).assess(
        HGFCRequest(forecast_demand=8.0, available_capacity=4.0, horizon_days=30)
    )

    assert not result.gate_open
    assert result.status is HGFCStatus.OUTSIDE_HORIZON
    assert result.capacity_delta is None
    assert result.capacity_risk is None
    assert result.preparation_recommended is False


def test_from_history_prediction_endpoint_uses_cumulative_horizon_forecast():
    response = forecast_and_assess_capacity(
        payload=HGFCForecastRequest(
            historical_demand_values=[10.0, 20.0, 30.0],
            available_capacity=50.0,
            horizon_days=3,
        ),
        current_dispatcher=SimpleNamespace(role=UserRole.DISPATCHER),
        demand_forecast_service=DemandForecastService(),
        hgfc_service=HGFCService(advisory_horizon_days=14),
    )

    assert response.forecast_demand == 57.81
    assert response.capacity_delta == pytest.approx(7.81)
    assert response.preparation_recommended


def test_hgfc_assessment_does_not_mutate_confirmed_orders(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    orders = [make_order(3), make_order(2, latitude=40.1)]
    demands_before = [order.demand for order in orders]
    HGFCService().assess(
        HGFCRequest(forecast_demand=12.0, available_capacity=5.0, horizon_days=7)
    )

    result = optimizer.optimize([make_driver()], [make_vehicle(5)], orders)

    assert [order.demand for order in orders] == demands_before
    assert sum(route.total_demand for route in result.routes) == sum(demands_before)


def test_optimizer_output_validates_against_response_schema(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    result = optimizer.optimize(
        [make_driver()],
        [make_vehicle()],
        [make_order(latitude=40.0)],
    )

    validated = OptimizationResponse.model_validate(result.model_dump())

    assert validated.routes[0].driver.id == result.routes[0].driver.id
    assert validated.routes[0].stops[0].order_id == result.routes[0].stops[0].order_id


@pytest.fixture
def route_repository_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_route_repository_create_read_list_delete(route_repository_session):
    session = route_repository_session
    user = User(
        full_name="Test Dispatcher",
        email="dispatcher@example.test",
        hashed_password="not-a-secret",
        role=UserRole.DISPATCHER,
        is_active=True,
    )
    vehicle = Vehicle(
        registration_number="DB-TEST-001",
        model="Test Model",
        manufacturer="Test Manufacturer",
        capacity=10,
    )
    session.add_all([user, vehicle])
    session.flush()

    driver = Driver(
        user_id=user.id,
        license_number="DB-TEST-LICENSE",
        phone="000-000-0000",
        max_capacity=10,
    )
    session.add(driver)
    session.flush()

    route = Route(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        total_distance_km=12.5,
        total_load=7,
    )
    repository = RouteRepository(session)

    created = repository.create(route)
    assert created.id is not None
    assert created.driver.id == driver.id
    assert created.vehicle.id == vehicle.id
    assert created in driver.routes
    assert created in vehicle.routes
    assert repository.get_by_id(created.id).total_load == 7
    assert [item.id for item in repository.get_all()] == [created.id]
    assert [item.id for item in repository.get_by_driver(driver.id)] == [created.id]
    assert [item.id for item in repository.get_by_vehicle(vehicle.id)] == [created.id]

    repository.delete(created)

    assert repository.get_by_id(created.id) is None
    assert repository.get_all() == []


def test_optimization_endpoint_persists_actual_optimizer_routes(
    route_repository_session,
    optimizer,
):
    session = route_repository_session
    dispatcher = User(
        full_name="Dispatch User",
        email="optimizer@example.test",
        hashed_password="not-a-secret",
        role=UserRole.DISPATCHER,
        is_active=True,
    )
    vehicle = Vehicle(
        registration_number="OPT-TEST-001",
        model="Test Model",
        manufacturer="Test Manufacturer",
        capacity=8,
    )
    session.add_all([dispatcher, vehicle])
    session.flush()
    driver = Driver(
        user_id=dispatcher.id,
        license_number="OPT-TEST-LICENSE",
        phone="000-000-0000",
        max_capacity=8,
        vehicle_id=vehicle.id,
    )
    order = Order(
        customer_name="Confirmed Customer",
        customer_phone="000-000-0000",
        pickup_address="Pickup",
        delivery_address="Delivery",
        pickup_latitude=40.0,
        pickup_longitude=-73.0,
        delivery_latitude=40.01,
        delivery_longitude=-73.01,
        demand=6,
        priority=1,
        status=OrderStatus.PENDING,
    )
    session.add_all([driver, order])
    session.flush()

    route_repository = RouteRepository(session)
    result = optimize_routes(
        payload=OptimizationRequest(
            driver_ids=[driver.id],
            vehicle_ids=[vehicle.id],
            order_ids=[order.id],
        ),
        current_dispatcher=dispatcher,
        driver_repository=DriverRepository(session),
        vehicle_repository=VehicleRepository(session),
        order_repository=OrderRepository(session),
        route_repository=route_repository,
        optimizer_service=optimizer,
    )

    persisted = route_repository.get_all()
    assert len(persisted) == result.total_routes == 1
    assert persisted[0].driver_id == driver.id
    assert persisted[0].vehicle_id == vehicle.id
    assert persisted[0].total_load == sum(stop.demand for stop in result.routes[0].stops)
    assert persisted[0].total_distance_km == result.routes[0].total_distance_km
    assert persisted[0].optimization_result["stops"][0]["order_id"] == str(order.id)
    assert persisted[0].optimization_started_at is not None
    assert persisted[0].optimization_completed_at is not None


def test_empty_optimization_result_persists_no_route_records(
    route_repository_session,
    optimizer,
):
    session = route_repository_session
    dispatcher = User(
        full_name="Dispatch User",
        email="empty-optimizer@example.test",
        hashed_password="not-a-secret",
        role=UserRole.DISPATCHER,
        is_active=True,
    )
    vehicle = Vehicle(
        registration_number="EMPTY-TEST-001",
        model="Test Model",
        manufacturer="Test Manufacturer",
        capacity=8,
    )
    session.add_all([dispatcher, vehicle])
    session.flush()
    driver = Driver(
        user_id=dispatcher.id,
        license_number="EMPTY-TEST-LICENSE",
        phone="000-000-0000",
        max_capacity=8,
        vehicle_id=vehicle.id,
    )
    session.add(driver)
    session.flush()

    result = optimize_routes(
        payload=OptimizationRequest(
            driver_ids=[driver.id],
            vehicle_ids=[vehicle.id],
            order_ids=[],
        ),
        current_dispatcher=dispatcher,
        driver_repository=DriverRepository(session),
        vehicle_repository=VehicleRepository(session),
        order_repository=OrderRepository(session),
        route_repository=RouteRepository(session),
        optimizer_service=optimizer,
    )

    assert result.routes == []
    assert RouteRepository(session).get_all() == []


def test_development_demo_seed_is_idempotent_and_does_not_overwrite(route_repository_session):
    session = route_repository_session

    first_counts = seed_demo(
        session,
        admin_password="test-admin-password",
        driver_password="test-driver-password",
    )
    admin = session.query(User).filter_by(email="dispatcher@demo.local").one()
    original_hash = admin.hashed_password
    second_counts = seed_demo(
        session,
        admin_password="different-password-ignored-for-existing-user",
        driver_password="different-password-ignored-for-existing-user",
    )

    assert first_counts == {"users": 2, "vehicles": 1, "drivers": 1, "orders": 4}
    assert second_counts == {"users": 0, "vehicles": 0, "drivers": 0, "orders": 0}
    assert session.query(User).count() == 2
    assert session.query(Vehicle).count() == 1
    assert session.query(Driver).count() == 1
    assert session.query(Order).count() == 4
    assert admin.hashed_password == original_hash


@pytest.mark.parametrize("role", [UserRole.DISPATCHER, UserRole.ADMIN])
def test_dispatcher_dependency_allows_dispatcher_and_admin(role):
    user = SimpleNamespace(role=role)

    assert get_current_dispatcher(user) is user


def test_admin_dependency_allows_admin():
    user = SimpleNamespace(role=UserRole.ADMIN)

    assert get_current_admin(user) is user


@pytest.mark.parametrize(
    ("dependency", "role"),
    [
        (get_current_dispatcher, UserRole.DRIVER),
        (get_current_admin, UserRole.DISPATCHER),
        (get_current_admin, UserRole.DRIVER),
    ],
)
def test_authorization_dependencies_reject_forbidden_roles(dependency, role):
    user = SimpleNamespace(role=role)

    with pytest.raises(HTTPException) as error:
        dependency(user)

    assert error.value.status_code == 403
