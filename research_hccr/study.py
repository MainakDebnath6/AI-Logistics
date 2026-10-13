"""Per-simulation driver: simulate -> forecast -> calibrate -> decide -> evaluate (strictly chronological)."""
from __future__ import annotations
import copy, json
import numpy as np
from .simulate import simulate
from .forecast import forecast_seasonal_lr, forecast_naive_week, forecast_holt_winters
from .calibrate import residuals
from .reserve import ReservePool
from .policies import (BASE_POLICIES, decide_range, realized, choose_buffers, gate_flags, interval_metrics)

def load_config(path):
    with open(path) as f: return json.load(f)

def make_pool(cfg):
    return ReservePool(cfg["reserve_vehicle_capacities"], cfg["reserve_vehicle_max_count"],
                       cfg["reserve_cost_fixed"], cfg["reserve_cost_per_unit"], cfg["reserve_cost_scale"])

def build_forecasts(y, cfg, model):
    hs = cfg["horizons"]; t0 = cfg["t_calibration_start"]
    if model == "lr":    return forecast_seasonal_lr(y, hs, t0, cfg["refit_every_days"])
    if model == "naive": return forecast_naive_week(y, hs, t0)
    if model == "hw":    return forecast_holt_winters(y, hs, t0, cfg["hw_param_refit_every_days"])
    raise ValueError(model)

def capacity(y, cfg):
    return np.ceil(
        cfg["capacity_pressure_kappa"]
        * y[:, :cfg["t_calibration_start"]].mean(axis=1)
    ).astype(int)

def evaluate(y, F, cfg, tag, keep_decisions=False):
    """Run all policies for one (y, F, cost-config). Returns operational rows, interval rows, optional decisions."""
    pool = make_pool(cfg); pi = cfg["shortage_penalty"]; hs = cfg["horizons"]
    A = capacity(y, cfg); res = residuals(y, F)
    val = list(range(cfg["t_validation_start"], cfg["t_test_start"]))
    test = list(range(cfg["t_test_start"], cfg["t_test_last_origin"] + 1))
    buf = choose_buffers(y, F, res, pool, A, pi, hs, val, cfg)
    S_val = decide_range(y, F, res, pool, A, pi, hs, val, cfg, buf_frac=buf)
    gates = gate_flags(y, S_val, A, pool, pi, hs, val)
    S_test = decide_range(y, F, res, pool, A, pi, hs, test, cfg, buf_frac=buf)
    rows = []
    for p in BASE_POLICIES:
        for h in hs:
            for variant in ("ungated", "gated"):
                S = S_test[p][h]
                if variant == "gated" and not gates[p][h]:
                    S = np.where(S >= 0, pool.empty, S)
                rc, un, tot, nv = realized(S, y, A, pool, pi, test, h)
                rows.append(dict(**tag, h=h, policy=p, variant=variant, gate_open=gates[p][h],
                                 cost_total=float(tot.mean()), cost_reserve=float(rc.mean()), unmet=float(un.mean()),
                                 n_reserved=float(nv.mean()), shortage_day_rate=float((un > 0).mean())))
    intervals = [dict(**tag, **r) for r in interval_metrics(y, F, res, hs, test, cfg)]
    dec = None
    if keep_decisions:
        validation_costs = {
            p: {
                h: float(realized(S_val[p][h], y, A, pool, pi, val, h)[2].mean())
                for h in hs
            }
            for p in BASE_POLICIES
        }
        dec = dict(S_raw={p: {h: S_test[p][h] for h in hs} for p in BASE_POLICIES}, A=A, y=y, test=np.array(test), buf=buf, gates=gates,
                   validation_costs=validation_costs,
                   S={p: {h: np.where(S_test[p][h] >= 0, np.where(gates[p][h], S_test[p][h], pool.empty), -1) for h in hs} for p in BASE_POLICIES})
    return rows, intervals, dec

def run_sim(regime, seed, cfg, model="lr", noise_scale=1.0, tag_extra=None, keep_decisions=False):
    y = simulate(regime, seed, cfg["T"], cfg["region_levels"], noise_scale)
    F = build_forecasts(y, cfg, model)
    tag = dict(regime=regime, seed=seed, model=model, noise_scale=noise_scale, **(tag_extra or {}))
    return evaluate(y, F, cfg, tag, keep_decisions), y, F
