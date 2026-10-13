"""Invariant tests: no look-ahead, reserve/capacity accounting, and the confirmed-order feasibility firewall."""
import copy, inspect, json, logging
from pathlib import Path
import numpy as np
import pytest

logging.disable(logging.CRITICAL)
CFG = json.load(open(Path(__file__).resolve().parents[1] / "configs" / "study_config.json"))

from research_hccr.simulate import simulate
from research_hccr.forecast import forecast_seasonal_lr, forecast_naive_week, forecast_holt_winters
from research_hccr.calibrate import residuals, window_h, window_pooled
from research_hccr.reserve import ReservePool
from research_hccr.policies import decide_range, BASE_POLICIES
from research_hccr.study import capacity
from research_hccr import routing_eval as RE

SMALL = dict(CFG, T=620, t_calibration_start=400, t_validation_start=500, t_test_start=550,
             t_test_last_origin=560, horizons=[1, 7], calibration_window=100)

def test_base_capacity_uses_paper_ceiling_on_fit_period_only():
    config = dict(CFG, capacity_pressure_kappa=1.05, t_calibration_start=2)
    demand = np.array([[1.0, 1.0, 10_000.0]])

    assert capacity(demand, config).tolist() == [2]

def pool(): return ReservePool(CFG["reserve_vehicle_capacities"], CFG["reserve_vehicle_max_count"], 4.0, 0.5, 1.0)

@pytest.mark.parametrize("fc", ["lr", "naive", "hw"])
def test_forecasts_do_not_use_future_observations(fc):
    y = simulate("ar", 3, 620, CFG["region_levels"]); o = 520
    f = {"lr": lambda a: forecast_seasonal_lr(a, [1, 7], 400, 7), "naive": lambda a: forecast_naive_week(a, [1, 7], 400),
         "hw": lambda a: forecast_holt_winters(a, [1, 7], 400, 28)}[fc]
    base = f(y); y2 = y.copy(); y2[:, o + 1:] += 1e4     # corrupt everything after the origin
    pert = f(y2)
    for h in (1, 7):
        np.testing.assert_allclose(base[h][:, :o + 1], pert[h][:, :o + 1], equal_nan=True)

def test_calibration_window_only_contains_realised_targets():
    h, d, W, first = 7, 600, 100, 400
    e = np.arange(1100, dtype=float)                       # value == origin index
    w = window_h(e, h, d, W, first)
    assert w.max() + h <= d and w.min() >= first and len(w) == W

def test_policy_decisions_independent_of_future_demand():
    cfg = SMALL; y = simulate("surge", 5, cfg["T"], cfg["region_levels"])
    A = np.round(1.05 * y[:, :400].mean(1)); d = 555
    def run(yy):
        F = forecast_seasonal_lr(yy, cfg["horizons"], 400, 7); res = residuals(yy, F)
        return decide_range(yy, F, res, pool(), A, 2.0, cfg["horizons"], [d], cfg, buf_frac={1: .1, 7: .1})
    base = run(y); y2 = y.copy(); y2[:, d + 1:] *= 3.0     # change every observation after the decision time
    pert = run(y2)
    for p in BASE_POLICIES:
        for h in cfg["horizons"]:
            same = np.array_equal(base[p][h][:, d], pert[p][h][:, d])
            if p == "oracle": assert not same           # oracle MUST depend on the future (labelled unattainable)
            else: assert same, (p, h)

def test_cost_aware_selection_limits():
    P = pool(); A = 100.0; scen = np.full(50, 130.0)
    assert P.nveh[P.choose_cost_aware(A, scen, pi=1e6)] >= 1 and A + P.cap[P.choose_cost_aware(A, scen, 1e6)] >= 130
    assert P.choose_cost_aware(A, scen, pi=1e-6) == P.empty
    assert P.choose_cost_aware(A, np.full(50, 90.0), pi=1e6) == P.empty          # no demand risk -> no reservation

def test_cost_aware_is_exact_minimiser():
    P = pool(); rng = np.random.default_rng(0)
    for _ in range(20):
        scen = np.maximum(0, rng.normal(110, 15, 80)); A = 100.0; pi = 2.0
        s = P.choose_cost_aware(A, scen, pi)
        obj = [P.cost[i] + pi * np.maximum(scen - A - P.cap[i], 0).mean() for i in range(len(P.cap))]
        assert np.isclose(obj[s], min(obj))

def test_capacity_accounting():
    P = pool(); S = np.array([P.empty, int(np.argmax(P.cap))]); y = np.array([150.0, 150.0]); A = np.array([100.0, 100.0])
    rc, un, tot = P.realized(S, y, A, pi=2.0)
    assert un[0] == 50.0 and un[1] == max(150 - 100 - P.cap[S[1]], 0) and np.allclose(tot, rc + 2.0 * un)
    assert rc[0] == 0.0

def test_buffer_cover_never_returns_under_capacity_when_cover_exists():
    P = pool(); s = P.choose_cover(100.0, 130.0); assert 100 + P.cap[s] >= 130

def test_activation_uses_confirmed_demand_only_and_never_exceeds_reserved():
    base = RE.base_fleet_caps(105, 30); res = [10, 20, 40]
    assert RE.activate_reserved(base, res, 90) == []                        # confirmed demand fits -> nothing activated
    act = RE.activate_reserved(base, res, 125); assert sum(base) + sum(act) >= 125 and set(act) <= set(res)
    assert RE.activate_reserved(base, res, 10_000) == res                    # cannot exceed what was reserved

def test_firewall_solver_has_no_forecast_input_and_is_invariant():
    assert not any("forecast" in p.lower() for p in inspect.signature(RE.solve_confirmed_orders).parameters)
    rc = CFG["routing"]; rng = np.random.default_rng(7); sizes, coords = RE.make_orders(98, rng, rc)
    fleet = RE.base_fleet_caps(105, 30)
    a = RE.solve_confirmed_orders(sizes, coords, fleet, rc, key="fw"); b = RE.solve_confirmed_orders(sizes, coords, fleet, rc, key="fw")
    # same confirmed orders + same active fleet -> identical routing result, regardless of any (unseen) forecast
    assert a["feasible"] and (a["distance_km"], a["served"], a["n_routes"]) == (b["distance_km"], b["served"], b["n_routes"])
    assert sum(sizes) == 98 and a["served"] == a["requested"] == len(sizes)

def test_confirmed_demand_conserved_by_order_split():
    rc = CFG["routing"]
    for D in (1, 7, 99, 143):
        sizes, _ = RE.make_orders(D, np.random.default_rng(D), rc); assert sum(sizes) == D and min(sizes) >= 1

def test_robust_policy_covers_forecast_plus_quantile_when_possible():
    P = pool(); A = 100.0; s = P.choose_cover(A, 100.0 + 25.0)
    assert A + P.cap[s] >= 125.0 and P.choose_cover(A, 1e9) == int(np.argmax(P.cap))
