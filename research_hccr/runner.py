"""Mechanism-experiment runner (AR regime). Reuses the frozen simulator, forecaster, residuals, reserve pool and cost-aware objective.
Policies are the paper's ungated 'pooled' and 'hspec' (HCCR) decision rules; ONLY the calibration window (and, in sweeps, W / pool) is varied."""
from __future__ import annotations
import json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from ..study import load_config, build_forecasts, capacity
from ..simulate import simulate
from ..calibrate import residuals
from ..reserve import ReservePool
from .design import WindowSpec, window_origins
MIN_RES = 30
HERE = Path(__file__).resolve().parent; OUT = HERE.parent / "results"; PARTS = OUT / "parts"

def _win(e_arr, spec, d, h, W, first):
    o = window_origins(spec, d, h, W, first); v = e_arr[o] if len(o) else np.empty(0); return v[~np.isnan(v)]

def run_condition(y, F, res, cfg, pool, A, pi, hs, spec, W, hs_all, spec_p=None):
    """Returns per-horizon dict of metrics for pooled and hspec under one calibration condition."""
    first = cfg["t_calibration_start"]; test = np.arange(cfg["t_test_start"], cfg["t_test_last_origin"] + 1); R = y.shape[0]; out = []
    for h in hs:
        Sh = np.empty((R, len(test)), int); Sp = np.empty_like(Sh); cov = []
        for r in range(R):
            for k, d in enumerate(test):
                yh = F[h][r, d]; eh = _win(res[h][r], spec, d, h, W, first)
                ep = np.concatenate([_win(res[hp][r], (spec_p or spec), d, hp, W, first) for hp in hs_all])
                Sh[r, k] = pool.choose_cost_aware(A[r], np.maximum(0, yh + eh), pi) if len(eh) >= MIN_RES else pool.empty
                Sp[r, k] = pool.choose_cost_aware(A[r], np.maximum(0, yh + ep), pi) if len(ep) >= MIN_RES else pool.empty
                if len(eh) >= MIN_RES: cov.append(yh + np.quantile(eh, .1) <= y[r, d + h] <= yh + np.quantile(eh, .9))
        yt = y[:, test + h]; At = np.repeat(A[:, None], len(test), axis=1); row = dict(h=h, disagreement=float((Sh != Sp).mean()), coverage80_hspec=float(np.mean(cov)))
        for name, S in (("hspec", Sh), ("pooled", Sp)):
            rc, un, tot = pool.realized(S, yt, At, pi)
            row.update({f"cost_{name}": float(tot.mean()), f"reserve_cost_{name}": float(rc.mean()), f"unmet_{name}": float(un.mean()), f"capacity_{name}": float(pool.cap[S].mean())})
        row["delta"] = row["cost_pooled"] - row["cost_hspec"]; out.append(row)
    return out

def residual_diagnostics(res, hs, first):
    rows = []
    for h in hs:
        ac, sd, r1 = [], [], []
        for r in range(res[h].shape[0]):
            e = res[h][r][first:]; e = e[~np.isnan(e)]
            ac.append(np.corrcoef(e[:-h], e[h:])[0, 1]); r1.append(np.corrcoef(e[:-1], e[1:])[0, 1]); sd.append(e.std())
        rows.append(dict(h=h, resid_autocorr_lag_h=float(np.mean(ac)), resid_autocorr_lag1=float(np.mean(r1)), resid_sd=float(np.mean(sd))))
    return rows

CONDITIONS = lambda W0: [  # (label, WindowSpec, W, pool_key, horizons, factor)
    ("natural", WindowSpec("natural"), W0, "base", (1, 14, 28), "main"),
    ("anticipative", WindowSpec("anticipative", diagnostic_only=True), W0, "base", (1, 14, 28), "main"),
    ("lag7", WindowSpec("extra_lag", 7), W0, "base", (1,), "dose"), ("lag14", WindowSpec("extra_lag", 14), W0, "base", (1,), "dose"),
    ("lag28", WindowSpec("extra_lag", 28), W0, "base", (1,), "dose"),
    ("W100", WindowSpec("natural"), 100, "base", (14, 28), "sweep"), ("W400", WindowSpec("natural"), 400, "base", (14, 28), "sweep"),
    ("finepool", WindowSpec("natural"), W0, "fine", (14, 28), "sweep")]

def run_sim_mech(seed, cfg, phis=(0.95, 0.0), only_main=False):
    pool_base = ReservePool(cfg["reserve_vehicle_capacities"], cfg["reserve_vehicle_max_count"], cfg["reserve_cost_fixed"], cfg["reserve_cost_per_unit"], cfg["reserve_cost_scale"])
    pool_fine = ReservePool([1, 2, 4, 8, 16, 32], 1, 0.0, 0.7, 1.0); pools = {"base": pool_base, "fine": pool_fine}
    rows, diag = [], []; hs_all = cfg["horizons"]
    for phi in phis:
        y = simulate("ar", seed, cfg["T"], cfg["region_levels"], 1.0, ar_phi_override=phi)
        F = build_forecasts(y, cfg, "lr"); res = residuals(y, F); A = capacity(y, cfg); pi = cfg["shortage_penalty"]
        diag += [dict(seed=seed, phi=phi, **r) for r in residual_diagnostics(res, hs_all, cfg["t_calibration_start"])]
        for label, spec, W, pk, hs, factor in CONDITIONS(cfg["calibration_window"]):
            if only_main and factor != "main": continue
            if phi == 0.0 and factor == "sweep": continue
            for r in run_condition(y, F, res, cfg, pools[pk], A, pi, hs, spec, W, hs_all):
                rows.append(dict(seed=seed, regime="ar", phi=phi, condition=label, factor=factor, window_kind=spec.kind, extra_lag=spec.extra_lag, W=W,
                                 pool=pk, deployable=(spec.kind != "anticipative"), **r))
    return pd.DataFrame(rows), pd.DataFrame(diag)

def run_batch(seeds, tag, budget_s=270, only_main=False):
    cfg = load_config(str(OUT.parent / "configs/study_config.json")); PARTS.mkdir(exist_ok=True); t0 = time.time(); done = True
    for s in seeds:
        f = PARTS / f"mech_{tag}_{s}.pkl"
        if f.exists(): continue
        if time.time() - t0 > budget_s: done = False; continue
        pd.to_pickle(run_sim_mech(s, cfg, only_main=only_main), f)
    if done:
        a = [pd.read_pickle(PARTS / f"mech_{tag}_{s}.pkl") for s in seeds]
        pd.concat([x[0] for x in a]).to_csv(OUT / f"mechanism_{tag}_paired.csv", index=False); pd.concat([x[1] for x in a]).to_csv(OUT / f"mechanism_{tag}_residual_diag.csv", index=False)
        print("complete", tag, len(seeds))
    else: print("partial; rerun", sum((PARTS / f"mech_{tag}_{s}.pkl").exists() for s in seeds), "/", len(seeds))

if __name__ == "__main__":
    tag = sys.argv[1]; a, b = int(sys.argv[2]), int(sys.argv[3]); run_batch(list(range(a, b)), tag)
