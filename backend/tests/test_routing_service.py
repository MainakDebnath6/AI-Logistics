from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest
from app.schemas.optimization import RouteCoordinate
from app.services.routing_service import RoadRoutingError, RoutingService


DEPOT = RouteCoordinate(latitude=22.5726, longitude=88.3639)
STOP = RouteCoordinate(latitude=22.5826, longitude=88.3739)


def osrm_payload(geometry=None, waypoints=None, code="Ok"):
    return {
        "code": code,
        "waypoints": waypoints
        if waypoints is not None
        else [
            {"waypoint_index": 0, "location": [88.3639, 22.5726], "distance": 0},
            {"waypoint_index": 1, "location": [88.3739, 22.5826], "distance": 0},
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
        (osrm_payload(code="NoRoute"), "could not route"),
        (osrm_payload(geometry=[]), "no detailed road geometry"),
        ({"code": "Ok", "routes": ["malformed"]}, "malformed route object"),
        (osrm_payload(geometry=[[88.3639, 22.5726], [22.5826, 88.3739]]), "does not match"),
        (
            osrm_payload(
                waypoints=[
                    {"waypoint_index": 1, "location": [88.3639, 22.5726], "distance": 0},
                    {"waypoint_index": 0, "location": [88.3739, 22.5826], "distance": 0},
                ]
            ),
            "waypoint order",
        ),
        (
            osrm_payload(
                waypoints=[
                    {"waypoint_index": 0, "location": [22.5726, 88.3639], "distance": 0},
                    {"waypoint_index": 1, "location": [88.3739, 22.5826], "distance": 0},
                ]
            ),
            "geometry start",
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