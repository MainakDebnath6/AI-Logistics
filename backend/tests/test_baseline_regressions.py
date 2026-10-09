from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api.optimization import optimize_routes
from app.api.predictions import forecast_and_assess_capacity
from app.core.config import Settings
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
from app.schemas.optimization import OptimizationRequest, OptimizationResponse, RouteCoordinate
from app.schemas.order import OrderCreate
from app.services.demand_forecast_service import DemandForecastService
from app.services.hgfc_service import HGFCService
from app.services.routing_service import RoutingService
from fastapi import HTTPException
from pydantic import ValidationError
from scripts.seed_demo import seed_demo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _cors_response(monkeypatch, origin: str):
    import app.main as main

    settings = Settings(backend_cors_origins="https://existing.example")
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver"), (b"origin", origin.encode())],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
    }
    asyncio.run(main.create_app()(scope, receive, send))
    response_start = next(message for message in messages if message["type"] == "http.response.start")
    headers = {key.decode(): value.decode() for key, value in response_start["headers"]}
    return settings, headers


def test_cors_allows_exact_production_frontend_origin(monkeypatch):
    settings, response = _cors_response(
        monkeypatch,
        "https://ai-logistics-umber.vercel.app",
    )

    assert "https://existing.example" in settings.cors_origins
    assert response["access-control-allow-origin"] == "https://ai-logistics-umber.vercel.app"
    assert response["access-control-allow-credentials"] == "true"


def test_cors_allows_project_preview_origin(monkeypatch):
    _, response = _cors_response(
        monkeypatch,
        "https://ai-logistics-feature-123-mainak-d.vercel.app",
    )

    assert response["access-control-allow-origin"] == (
        "https://ai-logistics-feature-123-mainak-d.vercel.app"
    )
    assert response["access-control-allow-credentials"] == "true"


def test_cors_rejects_unrelated_vercel_origin(monkeypatch):
    _, response = _cors_response(
        monkeypatch,
        "https://another-project-mainak-d.vercel.app",
    )

    assert "access-control-allow-origin" not in response


def test_demand_forecast_fallback_is_deterministic():
    service = DemandForecastService()

    assert service.forecast_demand([10, 20, 30]) == 19.27


def test_demand_forecast_horizon_returns_cumulative_daily_workload():
    service = DemandForecastService()

    assert service.forecast_demand_for_horizon([10, 20, 30], 3) == 57.81
    with pytest.raises(ValueError, match="at least one day"):
        service.forecast_demand_for_horizon([10, 20, 30], 0)
    assert service.forecast_demand([10, 20, 30]) == 19.27


def test_routing_service_preserves_geojson_longitude_latitude_order(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        status = 200

        def __exit__(self, *_args):
            return None

        def read(self):
            return b'{"code":"Ok","waypoints":[{"waypoint_index":0,"location":[88.3639,22.5726],"distance":0},{"waypoint_index":1,"location":[88.3739,22.5826],"distance":0}],"routes":[{"distance":1000,"duration":120,"geometry":{"coordinates":[[88.3639,22.5726],[88.3739,22.5826]]}}]}'

    monkeypatch.setattr("app.services.routing_service.urlopen", lambda *_args, **_kwargs: FakeResponse())
    route = RoutingService().build_road_route(
        [
            RouteCoordinate(latitude=22.5726, longitude=88.3639),
            RouteCoordinate(latitude=22.5826, longitude=88.3739),
        ]
    )

    assert route is not None
    assert [(point.latitude, point.longitude) for point in route.road_geometry] == [
        (22.5726, 88.3639),
        (22.5826, 88.3739),
    ]


def test_optimizer_requires_explicit_depot_when_not_configured(optimizer, make_driver, make_vehicle, make_order):
    optimizer._settings = Settings(DEFAULT_DEPOT_LATITUDE=None, DEFAULT_DEPOT_LONGITUDE=None)
    vehicle = make_vehicle()

    with pytest.raises(ValueError, match="Depot coordinates are required"):
        optimizer.optimize(
            [make_driver(vehicle.id)],
            [vehicle],
            [make_order()],
        )


def test_optimizer_rejects_missing_delivery_coordinates(optimizer, make_driver, make_vehicle, make_order):
    vehicle = make_vehicle()
    order = make_order()
    order.delivery_latitude = None

    with pytest.raises(ValueError, match="missing or invalid delivery coordinates"):
        optimizer.optimize(
            [make_driver(vehicle.id)],
            [vehicle],
            [order],
            depot_coordinates=(22.5726, 88.3639),
        )


def test_kolkata_route_uses_latitude_longitude_and_stays_local(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    depot = (22.5726, 88.3639)
    orders = [
        make_order(60, latitude=22.5800, longitude=88.3700),
        make_order(80, latitude=22.5900, longitude=88.3800),
        make_order(80, latitude=22.5650, longitude=88.3500),
    ]
    vehicle = make_vehicle(220)
    result = optimizer.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
        orders,
        depot_coordinates=depot,
    )
    route = result.routes[0]

    assert (route.route_coordinates[0].latitude, route.route_coordinates[0].longitude) == depot
    assert (route.route_coordinates[-1].latitude, route.route_coordinates[-1].longitude) == depot
    assert route.total_orders == len(orders)
    assert route.total_demand == 220
    assert route.total_distance_km == pytest.approx(route.distance / 1000.0, abs=0.001)
    assert route.total_distance_km < 100
    assert [
        (point.latitude, point.longitude) for point in route.route_coordinates[1:-1]
    ] == [
        (stop.delivery_latitude, stop.delivery_longitude) for stop in route.stops
    ]
    for stop in route.stops:
        assert abs(stop.delivery_latitude - depot[0]) < 1
        assert abs(stop.delivery_longitude - depot[1]) < 1


def test_cvrp_routes_respect_vehicle_capacity(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicles = [make_vehicle(5), make_vehicle(5)]
    drivers = [make_driver(vehicle.id) for vehicle in vehicles]
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


def test_cvrp_uses_explicit_depot_and_returns_same_optimized_path(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicle = make_vehicle(10)
    order = make_order(4, latitude=45.0, longitude=-70.0)
    result = optimizer.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
        [order],
        depot_coordinates=(40.0, -75.0),
    )
    route = result.routes[0]

    assert (route.route_coordinates[0].latitude, route.route_coordinates[0].longitude) == (40.0, -75.0)
    assert (route.route_coordinates[-1].latitude, route.route_coordinates[-1].longitude) == (40.0, -75.0)
    assert len(route.route_coordinates) == 3
    assert route.route_coordinates[1].latitude == order.delivery_latitude
    assert route.route_coordinates[1].longitude == order.delivery_longitude
    assert route.distance == optimizer._compute_path_distance_m(route.route_coordinates)
    assert route.total_distance_km == pytest.approx(route.distance / 1000.0, abs=0.001)


def test_optimizer_rejects_driver_vehicle_mismatch(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicle = make_vehicle()

    with pytest.raises(ValueError, match="not assigned to a selected vehicle"):
        optimizer.optimize(
            [make_driver()],
            [vehicle],
            [make_order()],
        )


def test_indivisible_order_capacity_infeasibility_is_rejected(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicles = [make_vehicle(10), make_vehicle(2)]
    drivers = [make_driver(vehicle.id) for vehicle in vehicles]

    with pytest.raises(RuntimeError, match="No feasible optimization solution"):
        optimizer.optimize(
            drivers,
            vehicles,
            [make_order(6), make_order(6, latitude=40.1)],
        )


def test_osrm_distance_is_separate_from_solver_objective(
    make_driver,
    make_vehicle,
    make_order,
):
    from app.services.route_optimizer import RouteOptimizerService

    class DifferentRoadDistance:
        def build_road_route(self, route_coordinates):
            return SimpleNamespace(
                road_geometry=route_coordinates,
                distance_meters=999_999.0,
                duration_seconds=900.0,
            )

    vehicle = make_vehicle(10)
    optimizer_with_road_distance = RouteOptimizerService(
        routing_service=DifferentRoadDistance()
    )
    result = optimizer_with_road_distance.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
        [make_order(2)],
        depot_coordinates=(40.0, -73.0),
    )

    route = result.routes[0]
    assert route.total_distance_km == pytest.approx(route.distance / 1000.0, abs=0.001)
    assert route.road_distance_km == pytest.approx(999.999)
    assert route.total_distance_km != route.road_distance_km


def test_insufficient_fleet_capacity_raises_existing_error(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    with pytest.raises(RuntimeError, match="Insufficient vehicle capacity"):
        optimizer.optimize(
            [make_driver((vehicle := make_vehicle(4)).id)],
            [vehicle],
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


def test_optimization_request_rejects_duplicate_confirmed_order_ids():
    repeated_id = uuid4()

    with pytest.raises(ValidationError, match="order_ids must not contain duplicate"):
        OptimizationRequest(
            driver_ids=[uuid4()],
            vehicle_ids=[uuid4()],
            order_ids=[repeated_id, repeated_id],
        )


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

    vehicle = make_vehicle(4)
    result = optimizer.optimize([make_driver(vehicle.id)], [vehicle], orders)

    requested_ids = {order.id for order in orders}
    served_ids = {stop.order_id for route in result.routes for stop in route.stops}
    unserved_ids = requested_ids - served_ids

    assert served_ids == requested_ids
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

    vehicle = make_vehicle()
    result = optimizer.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
        [order],
        depot_coordinates=(40.0, -73.0),
    )

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


def test_time_window_conversion_interprets_naive_datetimes_as_utc(optimizer, make_order):
    order = make_order(
        time_window_start=datetime.fromisoformat("2026-10-08T09:00:00"),
        time_window_end=datetime.fromisoformat("2026-10-08T17:00:00"),
    )

    start_minute, end_minute = optimizer._extract_time_window(order)

    assert start_minute == int(datetime(2026, 10, 8, 9, tzinfo=timezone.utc).timestamp() // 60)
    assert end_minute == int(datetime(2026, 10, 8, 17, tzinfo=timezone.utc).timestamp() // 60)


def test_time_window_conversion_supports_midnight_rollover(optimizer, make_order):
    order = make_order(
        time_window_start=datetime.fromisoformat("2026-10-08T23:00:00+00:00"),
        time_window_end=datetime.fromisoformat("2026-10-09T01:00:00+00:00"),
    )

    start_minute, end_minute = optimizer._extract_time_window(order)

    assert end_minute - start_minute == 120


def test_time_window_conversion_rejects_partial_and_reversed_bounds(optimizer, make_order):
    partial = make_order(time_window_start=datetime(2026, 10, 8, 9, tzinfo=timezone.utc))
    reversed_window = make_order(
        time_window_start=datetime(2026, 10, 8, 17, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
    )

    with pytest.raises(ValueError, match="Both time-window bounds"):
        optimizer._extract_time_window(partial)
    with pytest.raises(ValueError, match="must be after"):
        optimizer._extract_time_window(reversed_window)


def test_time_window_optimizer_rejects_mixed_datetime_and_minute_inputs(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    datetime_order = make_order(
        time_window_start=datetime(2026, 10, 8, 9, tzinfo=timezone.utc),
        time_window_end=datetime(2026, 10, 8, 10, tzinfo=timezone.utc),
    )
    minute_order = make_order(
        time_window_start=60,
        time_window_end=120,
        latitude=40.1,
    )
    vehicle = make_vehicle(10)
    optimizer.configure(time_windows_enabled=True)

    with pytest.raises(ValueError, match="same time representation"):
        optimizer.optimize(
            [make_driver(vehicle.id)],
            [vehicle],
            [datetime_order, minute_order],
            depot_coordinates=(40.0, -73.0),
        )


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


def test_order_schema_normalizes_naive_window_datetime_to_utc():
    order = OrderCreate(
        customer_name="Test Customer",
        customer_phone="000-000-0000",
        pickup_address="Pickup address",
        delivery_address="Delivery address",
        pickup_latitude=40.0,
        pickup_longitude=-73.0,
        delivery_latitude=40.1,
        delivery_longitude=-73.1,
        demand=1,
        time_window_start=datetime.fromisoformat("2026-10-08T09:00:00"),
        time_window_end=datetime.fromisoformat("2026-10-08T17:00:00"),
    )

    assert order.time_window_start.tzinfo is timezone.utc
    assert order.time_window_end.tzinfo is timezone.utc


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


@pytest.mark.parametrize("horizon", [14, 15])
def test_hgfc_gate_boundary_is_inclusive_through_day_14(horizon):
    result = HGFCService(advisory_horizon_days=14).assess(
        HGFCRequest(forecast_demand=20.0, available_capacity=10.0, horizon_days=horizon)
    )

    assert result.gate_open is (horizon == 14)
    assert result.preparation_recommended is (horizon == 14)


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
    vehicle = make_vehicle(5)
    demands_before = [order.demand for order in orders]
    capacity_before = vehicle.capacity
    HGFCService().assess(
        HGFCRequest(forecast_demand=12.0, available_capacity=5.0, horizon_days=7)
    )
    HGFCService().assess(
        HGFCRequest(forecast_demand=0.0, available_capacity=500.0, horizon_days=14)
    )

    result = optimizer.optimize([make_driver(vehicle.id)], [vehicle], orders)

    assert [order.demand for order in orders] == demands_before
    assert vehicle.capacity == capacity_before
    assert sum(route.total_demand for route in result.routes) == sum(demands_before)


def test_forecast_cannot_make_infeasible_confirmed_orders_feasible(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicle = make_vehicle(5)
    orders = [make_order(4), make_order(4, latitude=40.1)]
    for forecast in (0.0, 10000.0):
        HGFCService().assess(
            HGFCRequest(forecast_demand=forecast, available_capacity=5.0, horizon_days=7)
        )
        with pytest.raises(RuntimeError, match="Insufficient vehicle capacity"):
            optimizer.optimize([make_driver(vehicle.id)], [vehicle], orders)


def test_optimizer_output_validates_against_response_schema(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicle = make_vehicle()
    result = optimizer.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
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

    oversized_order = Order(
        customer_name="Infeasible Customer",
        customer_phone="000-000-0000",
        pickup_address="Pickup",
        delivery_address="Delivery",
        pickup_latitude=40.0,
        pickup_longitude=-73.0,
        delivery_latitude=40.02,
        delivery_longitude=-73.02,
        demand=3,
        priority=1,
        status=OrderStatus.PENDING,
    )
    session.add(oversized_order)
    session.flush()

    route_repository = RouteRepository(session)
    with pytest.raises(HTTPException) as error:
        optimize_routes(
            payload=OptimizationRequest(
                driver_ids=[driver.id],
                vehicle_ids=[vehicle.id],
                order_ids=[order.id, oversized_order.id],
            ),
            current_dispatcher=dispatcher,
            driver_repository=DriverRepository(session),
            vehicle_repository=VehicleRepository(session),
            order_repository=OrderRepository(session),
            route_repository=route_repository,
            optimizer_service=optimizer,
        )
    assert error.value.status_code == 400
    assert route_repository.get_all() == []

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


def test_production_settings_reject_default_jwt_secret():
    with pytest.raises(ValidationError, match="SECRET_KEY must be explicitly configured"):
        Settings(environment="production", secret_key="change-me")


def test_production_settings_reject_wildcard_credentialed_cors():
    with pytest.raises(ValidationError, match="wildcard origin"):
        Settings(
            environment="production",
            secret_key="a-long-production-secret-value",
            backend_cors_origins="*",
        )
