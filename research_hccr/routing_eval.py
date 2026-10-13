"""Confirmed-order CVRP stage. Reuses the repository's RouteOptimizerService (OR-Tools) UNCHANGED.

Firewall: nothing in this module accepts a forecast. Inputs are (confirmed orders, active fleet capacities).
States kept separate:  reserved (paid, forecast-driven)  ->  activated (confirmed-demand-driven)  ->  routed.
"""
from __future__ import annotations
import itertools, sys, inspect
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5
import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "backend") not in sys.path:
    sys.path.insert(0, str(REPO / "backend"))
from app.models.order import OrderStatus                      # noqa: E402
from app.services.route_optimizer import RouteOptimizerService  # noqa: E402

class _Offline:
    def build_road_route(self, route_coordinates): return None

def make_orders(D_units: int, rng, rcfg):
    """Split confirmed integer demand D into orders (sizes in order_size_range, summing exactly to D)."""
    lo, hi = rcfg["order_size_range"]; sizes = []; rem = int(D_units)
    while rem > 0:
        s = int(min(rem, rng.integers(lo, hi + 1))); sizes.append(s); rem -= s
    if len(sizes) > 1 and sizes[-1] < 1: sizes.pop()
    box = rcfg["region_box_deg"]; dlat, dlon = rcfg["depot"]
    coords = [(dlat + rng.uniform(-box, box), dlon + rng.uniform(-box, box)) for _ in sizes]
    return sizes, coords

def base_fleet_caps(A: int, max_cap: int):
    n = int(np.ceil(A / max_cap)); base, extra = divmod(int(A), n)
    return [base + (1 if i < extra else 0) for i in range(n)]

def activate_reserved(base_caps, reserved_caps, D_confirmed):
    """Dispatcher activation rule using CONFIRMED demand only: smallest-capacity reserved subset that covers D
    (ties: fewer vehicles); if none covers, activate all reserved. Forecasts play no role here."""
    total = sum(base_caps); best = None
    for k in range(len(reserved_caps) + 1):
        for comb in itertools.combinations(range(len(reserved_caps)), k):
            cap = total + sum(reserved_caps[i] for i in comb)
            if cap >= D_confirmed:
                key = (cap, k)
                if best is None or key < best[0]: best = (key, comb)
    idx = best[1] if best else tuple(range(len(reserved_caps)))
    return [reserved_caps[i] for i in idx]

def solve_confirmed_orders(sizes, coords, fleet_caps, rcfg, key: str = "inst"):
    """Route exactly the confirmed orders with the existing CVRP optimizer and the actual vehicle capacities."""
    vehicles = [SimpleNamespace(id=uuid5(NAMESPACE_URL, f"{key}:v{i}"), capacity=int(c), registration_number=f"V{i}")
                for i, c in enumerate(fleet_caps)]
    drivers = [SimpleNamespace(id=uuid5(NAMESPACE_URL, f"{key}:d{i}"), vehicle_id=v.id,
                               user=SimpleNamespace(full_name=f"d{i}")) for i, v in enumerate(vehicles)]
    orders = [SimpleNamespace(id=uuid5(NAMESPACE_URL, f"{key}:o{i}"), customer_name=f"c{i}", pickup_address="depot",
                              delivery_address=f"a{i}", pickup_latitude=la, pickup_longitude=lo,
                              delivery_latitude=la, delivery_longitude=lo, demand=int(s), priority=1,
                              status=OrderStatus.PENDING, time_window_start=None, time_window_end=None)
              for i, (s, (la, lo)) in enumerate(zip(sizes, coords))]
    opt = RouteOptimizerService(routing_service=_Offline())
    opt.configure(optimization_timeout_seconds=rcfg["solver_timeout_seconds"],
                  optimization_solution_limit=rcfg["solver_solution_limit"])
    t0 = perf_counter()
    try:
        res = opt.optimize(drivers, vehicles, orders, depot_coordinates=tuple(rcfg["depot"]))
    except RuntimeError as e:
        if "Insufficient vehicle capacity" in str(e) or "No feasible" in str(e):
            return dict(feasible=False, distance_km=float("nan"), runtime_s=perf_counter() - t0, served=0,
                        requested=len(sizes), n_routes=0, reason=str(e)[:60])
        raise
    served = sum(r.total_orders for r in res.routes)
    return dict(feasible=True, distance_km=float(res.total_distance_km), runtime_s=perf_counter() - t0,
                served=int(served), requested=len(sizes), n_routes=int(res.total_routes), reason="")

assert "forecast" not in " ".join(inspect.signature(solve_confirmed_orders).parameters), "firewall violated"
