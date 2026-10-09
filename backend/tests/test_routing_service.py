from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from app.core.config import Settings
from app.schemas.optimization import RouteCoordinate
from app.services.route_optimizer import RouteOptimizerService
from app.services.routing_service import RoadRouteResult, RoadRoutingError, RoutingService


DEPOT = RouteCoordinate(latitude=22.5726, longitude=88.3639)
STOP = RouteCoordinate(latitude=22.5826, longitude=88.3739)


def test_osrm_timeout_setting_is_bounded():
    assert Settings(OSRM_TIMEOUT_SECONDS=30.0).OSRM_TIMEOUT_SECONDS == 30.0
    with pytest.raises(ValueError):
        Settings(OSRM_TIMEOUT_SECONDS=30.1)


def osrm_payload(geometry=None, waypoints=None, code="Ok"):
    return {
        "code": code,
        "waypoints": waypoints
        if waypoints is not None
        else [
            {"location": [88.3639, 22.5726], "distance": 0},
            {"location": [88.3739, 22.5826], "distance": 0},
        ],
        "routes": [
            {
                "distance": 2400,
                "duration": 360,
                "geometry": {
                    "type": "LineString",
                    "coordinates": geometry
                    if geometry is not None
                    else [[88.3639, 22.5726], [88.3680, 22.5770], [88.3739, 22.5826]],
                },
            }
        ],
    }


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


def test_osrm_geometry_is_detailed_ordered_and_uses_lon_lat_request(monkeypatch):
    captured = {}

    def fake_urlopen(url, timeout):
        captured.update(url=url, timeout=timeout)
        return FakeResponse(osrm_payload())

    monkeypatch.setattr("app.services.routing_service.urlopen", fake_urlopen)
    result = RoutingService().build_road_route([DEPOT, STOP])

    assert "/88.3639000,22.5726000;88.3739000,22.5826000?" in captured["url"]
    assert "overview=full" in captured["url"]
    assert "geometries=geojson" in captured["url"]
    assert [(point.latitude, point.longitude) for point in result.road_geometry] == [
        (22.5726, 88.3639),
        (22.5770, 88.3680),
        (22.5826, 88.3739),
    ]


def test_osrm_waypoint_array_order_validates_intermediate_geometry(monkeypatch):
    payload = {
        "code": "Ok",
        "waypoints": [
            {"location": [88.3639, 22.5726], "distance": 0},
            {"location": [88.3680, 22.5770], "distance": 0},
            {"location": [88.3739, 22.5826], "distance": 0},
        ],
        "routes": [
            {
                "distance": 2400,
                "duration": 360,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [88.3639, 22.5726],
                        [88.3680, 22.5770],
                        [88.3739, 22.5826],
                    ],
                },
            }
        ],
    }
    monkeypatch.setattr(
        "app.services.routing_service.urlopen",
        lambda *_args, **_kwargs: FakeResponse(payload),
    )
    middle = RouteCoordinate(latitude=22.5770, longitude=88.3680)

    result = RoutingService().build_road_route([DEPOT, middle, STOP])

    assert len(result.road_geometry) == 3
    assert (result.road_geometry[1].latitude, result.road_geometry[1].longitude) == (
        middle.latitude,
        middle.longitude,
    )


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        (TimeoutError("request timed out"), "timed out"),
        (HTTPError("https://osrm.test", 503, "unavailable", {}, None), "HTTP 503"),
    ],
)
def test_osrm_transport_failures_are_reported(monkeypatch, failure, message):
    def fail_request(*_args, **_kwargs):
        raise failure

    monkeypatch.setattr("app.services.routing_service.urlopen", fail_request)
    with pytest.raises(RoadRoutingError, match=message):
        RoutingService().build_road_route([DEPOT, STOP])


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (b"not-json", "malformed JSON"),
        (osrm_payload(code="NoRoute"), "no drivable route"),
        (osrm_payload(code="NoSegment"), "could not match"),
        (osrm_payload(geometry=[]), "no detailed road geometry"),
        ({"code": "Ok", "routes": ["malformed"]}, "malformed route object"),
        (
            {
                **osrm_payload(),
                "routes": [
                    {
                        **osrm_payload()["routes"][0],
                        "geometry": {
                            "type": "Point",
                            "coordinates": [88.3639, 22.5726],
                        },
                    }
                ],
            },
            "not a GeoJSON LineString",
        ),
        (osrm_payload(geometry=[[88.3639, 22.5726], [22.5826, 88.3739]]), "does not match"),
        (
            osrm_payload(
                waypoints=[
                    {"location": [22.5726, 88.3639], "distance": 0},
                    {"location": [88.3739, 22.5826], "distance": 0},
                ]
            ),
            "does not correspond to the requested coordinate",
        ),
        (osrm_payload(geometry=[[88.3639, 22.5726], [float("nan"), 22.5826]]), "invalid longitude/latitude"),
    ],
)
def test_osrm_invalid_or_mismatched_response_is_rejected(monkeypatch, body, message):
    monkeypatch.setattr("app.services.routing_service.urlopen", lambda *_args, **_kwargs: FakeResponse(body))
    with pytest.raises(RoadRoutingError, match=message):
        RoutingService().build_road_route([DEPOT, STOP])


@pytest.mark.parametrize(
    "coordinates",
    [
        [DEPOT],
        [DEPOT, SimpleNamespace(latitude=91, longitude=88)],
        [DEPOT, SimpleNamespace(latitude=22, longitude=float("inf"))],
    ],
)
def test_missing_or_invalid_input_coordinates_are_rejected(monkeypatch, coordinates):
    monkeypatch.setattr(
        "app.services.routing_service.urlopen",
        lambda *_args, **_kwargs: pytest.fail("invalid inputs must not call OSRM"),
    )
    with pytest.raises(RoadRoutingError, match="coordinate"):
        RoutingService().build_road_route(coordinates)


def test_optimizer_does_not_publish_straight_line_fallback_as_road_route(
    optimizer,
    make_driver,
    make_vehicle,
    make_order,
):
    vehicle = make_vehicle()
    result = optimizer.optimize(
        [make_driver(vehicle.id)],
        [vehicle],
        [make_order()],
        depot_coordinates=(22.5726, 88.3639),
    )
    route = result.routes[0]

    assert route.road_route_status == "failed"
    assert route.road_route_error
    assert route.road_geometry == []
    assert route.total_duration_minutes is None
    assert len(route.route_coordinates) >= 2
    response_payload = result.model_dump(mode="json")
    assert response_payload["routes"][0]["road_route_status"] == "failed"
    assert response_payload["routes"][0]["road_geometry"] == []
    assert response_payload["routes"][0]["total_duration_minutes"] is None


def test_single_order_route_passes_depot_delivery_depot_once_to_road_router(
    make_driver,
    make_vehicle,
    make_order,
):
    class CapturingRoutingService:
        received = None

        def build_road_route(self, route_coordinates):
            self.received = list(route_coordinates)
            return RoadRouteResult(
                road_geometry=list(route_coordinates),
                distance_meters=2400,
                duration_seconds=360,
            )

    depot = (22.5726, 88.3639)
    vehicle = make_vehicle(10)
    order = make_order(2, latitude=22.5800, longitude=88.3700)
    routing = CapturingRoutingService()
    service = RouteOptimizerService(routing_service=routing)
    service._settings = Settings(
        DEFAULT_DEPOT_LATITUDE=depot[0],
        DEFAULT_DEPOT_LONGITUDE=depot[1],
    )

    result = service.optimize([make_driver(vehicle.id)], [vehicle], [order])

    expected = [
        (depot[0], depot[1]),
        (order.delivery_latitude, order.delivery_longitude),
        (depot[0], depot[1]),
    ]
    actual = [(point.latitude, point.longitude) for point in routing.received]
    route = result.routes[0]
    assert actual == expected
    assert route.total_orders == 1
    assert route.stops[0].order_id == order.id
    assert route.road_route_status == "available"
    assert route.road_distance_km == pytest.approx(2.4)
    assert route.total_duration_minutes == pytest.approx(6.0)