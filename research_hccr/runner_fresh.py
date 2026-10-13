"""Relative-freshness experiment (PREREGISTRATION_FRESHNESS.md). All conditions are deployable; only the calibration window ages differ."""
from __future__ import annotations
import sys, time
import pandas as pd
from ..study import load_config, build_forecasts, capacity
from ..simulate import simulate
from ..calibrate import residuals
from ..reserve import ReservePool
from .design import WindowSpec
from .runner import run_condition, residual_diagnostics, OUT, PARTS
NAT = WindowSpec("natural")
# (label, spec for HCCR window, spec for pooled windows)
FRESH_CONDITIONS = [("natural", NAT, NAT), ("pooled_stale14", NAT, WindowSpec("extra_lag", 14)), ("pooled_stale28", NAT, WindowSpec("extra_lag", 28)),
                    ("hccr_stale28", WindowSpec("extra_lag", 28), NAT)]
HS = (1, 14, 28)

def run_sim_fresh(seed, cfg, phis=(0.95, 0.0)):
    pool = ReservePool(cfg["reserve_vehicle_capacities"], cfg["reserve_vehicle_max_count"], cfg["reserve_cost_fixed"], cfg["reserve_cost_per_unit"], cfg["reserve_cost_scale"])
    rows = []
    for phi in phis:
        y = simulate("ar", seed, cfg["T"], cfg["region_levels"], 1.0, ar_phi_override=phi)
        F = build_forecasts(y, cfg, "lr"); res = residuals(y, F); A = capacity(y, cfg)
        for label, sh, sp in FRESH_CONDITIONS:
            for r in run_condition(y, F, res, cfg, pool, A, cfg["shortage_penalty"], HS, sh, cfg["calibration_window"], cfg["horizons"], spec_p=sp):
                rows.append(dict(seed=seed, regime="ar", phi=phi, condition=label, deployable=True, **r))
    return pd.DataFrame(rows)

def run_batch(seeds, tag, budget_s=270):
    cfg = load_config(str(OUT.parent / "configs/study_config.json")); PARTS.mkdir(exist_ok=True); t0 = time.time(); done = True
    for s in seeds:
        f = PARTS / f"fresh_{tag}_{s}.pkl"
        if f.exists(): continue
        if time.time() - t0 > budget_s: done = False; continue
        pd.to_pickle(run_sim_fresh(s, cfg), f)
    if done:
        pd.concat([pd.read_pickle(PARTS / f"fresh_{tag}_{s}.pkl") for s in seeds]).to_csv(OUT / f"freshness_{tag}_paired.csv", index=False); print("complete", tag, len(seeds))
    else: print("partial; rerun", sum((PARTS / f"fresh_{tag}_{s}.pkl").exists() for s in seeds), "/", len(seeds))
if __name__ == "__main__":
    run_batch(list(range(int(sys.argv[2]), int(sys.argv[3]))), sys.argv[1])
