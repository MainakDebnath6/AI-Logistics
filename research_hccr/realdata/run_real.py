"""Real-data check (see PREREGISTRATION_REAL.md). Reuses the frozen forecaster, residual protocol, reserve pool and policy decision rules."""
from __future__ import annotations
import json, sys, logging
from pathlib import Path
import numpy as np, pandas as pd
from ..study import load_config, build_forecasts, capacity
from ..calibrate import residuals
from ..reserve import ReservePool
from ..policies import BASE_POLICIES, decide_range, choose_buffers, realized, interval_metrics
from ..analysis import OUT, boot_ci
logging.disable(logging.CRITICAL)
DATA = Path(__file__).resolve().parent / "data"
BANDS = {"night": range(0, 6), "morning": range(6, 11), "midday": range(11, 16), "evening": range(16, 24)}
SPLIT = dict(T=731, t_calibration_start=365, t_validation_start=540, t_test_start=600, t_test_last_origin=702, calibration_window=150)
PI_GRID = [1.0, 2.0, 4.0, 9.0, 19.0]; PRIMARY_PI = 4.0; BLOCK = 28

def load_segments():
    h = pd.read_csv(DATA / "hour.csv"); h["dteday"] = pd.to_datetime(h["dteday"]); idx = pd.date_range("2011-01-01", "2012-12-31")
    seg = np.vstack([h[h.hr.isin(v)].groupby("dteday").cnt.sum().reindex(idx).fillna(0).values for v in BANDS.values()]).astype(float)
    scale = 100.0 / seg[:, :SPLIT["t_calibration_start"]].mean(axis=1)          # uses the initial-fit period ONLY
    return seg * scale[:, None], scale, idx

def block_boot_mean(x, block=BLOCK, n=10000, seed=12345):
    rng = np.random.default_rng(seed); x = np.asarray(x, float); L = len(x); nb = int(np.ceil(L / block)); starts = np.arange(L - block + 1)
    m = np.empty(n)
    for i in range(n):
        s = rng.choice(starts, nb); m[i] = np.concatenate([x[a:a + block] for a in s])[:L].mean()
    return float(np.quantile(m, .025)), float(np.quantile(m, .975))

def main():
    cfg = load_config(str(OUT.parent / "configs/study_config.json")); cfg.update(SPLIT); y, scale, idx = load_segments(); cfg["region_levels"] = [100.0] * y.shape[0]; cfg["n_regions"] = y.shape[0]
    F = build_forecasts(y, cfg, "lr"); res = residuals(y, F); A = capacity(y, cfg); hs = cfg["horizons"]
    val = list(range(cfg["t_validation_start"], cfg["t_test_start"])); test = list(range(cfg["t_test_start"], cfg["t_test_last_origin"] + 1)); rows = []; orow = []
    assert y.shape[1] == 731 and max(test) + max(hs) <= 730
    for pi in PI_GRID:
        c = dict(cfg, shortage_penalty=pi); pool = ReservePool(c["reserve_vehicle_capacities"], c["reserve_vehicle_max_count"], c["reserve_cost_fixed"], c["reserve_cost_per_unit"], c["reserve_cost_scale"])
        buf = choose_buffers(y, F, res, pool, A, pi, hs, val, c); S = decide_range(y, F, res, pool, A, pi, hs, test, c, buf_frac=buf)
        for h in hs:
            tot = {p: realized(S[p][h], y, A, pool, pi, test, h) for p in BASE_POLICIES}
            per_origin = {p: tot[p][2].mean(axis=0) for p in BASE_POLICIES}
            d = per_origin["pooled"] - per_origin["hspec"]; lo, hi = block_boot_mean(d)
            dis = float((S["hspec"][h][:, test] != S["pooled"][h][:, test]).mean())
            hccr_cost = float(per_origin["hspec"].mean())
            for p in BASE_POLICIES:
                rows.append(dict(pi=pi, h=h, policy=p, total_cost=float(per_origin[p].mean()), reserve_cost=float(tot[p][0].mean()), unmet=float(tot[p][1].mean()), n_reserved=float(tot[p][3].mean()), shortage_day_rate=float((tot[p][1] > 0).mean())))
            orow.append(dict(pi=pi, h=h, delta=float(d.mean()), ci_lo=lo, ci_hi=hi, pct_of_hccr=100 * float(d.mean()) / hccr_cost, disagreement=dis, buffer_fraction=buf[h], n_origins=len(test)))
    pd.DataFrame(rows).to_csv(OUT / "realdata_policies.csv", index=False); o = pd.DataFrame(orow); o.to_csv(OUT / "realdata_delta.csv", index=False)
    iv = pd.DataFrame(interval_metrics(y, F, res, hs, test, cfg)); iv.to_csv(OUT / "realdata_forecast_calibration.csv", index=False)
    meta = dict(source="UCI Bike Sharing (CC BY 4.0), mirror udacity/deep-learning", download_date="2026-10-12", n_days=731, segments=list(BANDS), scale=[float(s) for s in scale], split=SPLIT, primary_pi=PRIMARY_PI, block=BLOCK, n_test_origins=len(test))
    (OUT / "realdata_meta.json").write_text(json.dumps(meta, indent=2)); pd.set_option("display.width", 200)
    print(o.round(3).to_string()); print(iv.round(3).to_string())
if __name__ == "__main__": main()
