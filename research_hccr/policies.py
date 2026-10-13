"""Reserve policies evaluated under identical forecasts, scenarios, costs and splits.

Reserve decision at origin d for horizon h (target day d+h, region r) uses only information available at d:
forecast F[h][r,d] and residuals whose targets are <= d. Confirmed demand y[r,d+h] is used ONLY for evaluation
(and by the oracle, which is a labelled unattainable reference).
"""
from __future__ import annotations
import numpy as np
from .calibrate import residuals, window_h, window_pooled
from .reserve import ReservePool

BASE_POLICIES = ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"]
MIN_RESIDUALS = 30

def _decide(pool: ReservePool, policy: str, *, A, yhat, y_true, win_h, win_pool, buf_target, pi):
    if policy == "reactive": return pool.empty
    if policy == "oracle":   return pool.choose_cost_aware(A, np.array([y_true]), pi)
    if policy == "point":    return pool.choose_cost_aware(A, np.array([yhat]), pi)
    if policy == "buffer":   return pool.choose_cover(A, buf_target)
    if policy == "pooled":   return pool.choose_cost_aware(A, np.maximum(0.0, yhat + win_pool), pi) if len(win_pool) >= MIN_RESIDUALS else pool.empty
    if policy == "robust":   # conservative: cover point forecast + 95th percentile of horizon-specific residuals (no cost model)
        return pool.choose_cover(A, yhat + float(np.quantile(win_h, 0.95))) if len(win_h) >= MIN_RESIDUALS else pool.empty
    if policy == "hspec":    return pool.choose_cost_aware(A, np.maximum(0.0, yhat + win_h), pi) if len(win_h) >= MIN_RESIDUALS else pool.empty
    raise ValueError(policy)

def decide_range(y, F, res, pool, A, pi, horizons, origins, cfg, buf_frac=None, extra_buffer_fracs=None):
    """Return S[policy][h] int arrays (R,T) filled at the given origins; plus buffer-by-fraction decisions if requested."""
    R, T = y.shape; W = cfg["calibration_window"]; first = cfg["t_calibration_start"]; L = np.asarray(cfg["region_levels"])
    S = {p: {h: np.full((R, T), -1, int) for h in horizons} for p in BASE_POLICIES}
    for r in range(R):
        for h in horizons:
            for d in origins:
                yh = F[h][r, d]
                if np.isnan(yh): continue
                wh = window_h(res[h][r], h, d, W, first)
                wp = window_pooled(res, r, horizons, d, W, first)
                bf = 0.0 if buf_frac is None else buf_frac[h]
                for p in BASE_POLICIES:
                    S[p][h][r, d] = _decide(pool, p, A=A[r], yhat=yh, y_true=y[r, d + h], win_h=wh, win_pool=wp,
                                            buf_target=yh + bf * L[r], pi=pi)
    return S

def realized(S_p_h, y, A, pool, pi, origins, h):
    """Per-(region,origin) realized reserve cost, unmet, total, vehicles count; arrays shape (R, len(origins))."""
    R = y.shape[0]; o = np.asarray(origins)
    Sidx = S_p_h[:, o]
    yt = y[:, o + h]; At = np.repeat(A[:, None], len(o), axis=1)
    rc, un, tot = pool.realized(Sidx, yt, At, pi)
    return rc, un, tot, pool.nveh[Sidx]

def choose_buffers(y, F, res, pool, A, pi, horizons, val_origins, cfg):
    """Per-horizon buffer fraction minimising VALIDATION total cost over the pre-specified grid."""
    L = np.asarray(cfg["region_levels"]); best = {}
    for h in horizons:
        costs = []
        for bf in cfg["buffer_grid_fraction_of_level"]:
            tot = []
            for r in range(y.shape[0]):
                for d in val_origins:
                    yh = F[h][r, d]
                    if np.isnan(yh): continue
                    s = pool.choose_cover(A[r], yh + bf * L[r])
                    tot.append(pool.cost[s] + pi * max(y[r, d + h] - A[r] - pool.cap[s], 0.0))
            costs.append(np.mean(tot))
        best[h] = float(cfg["buffer_grid_fraction_of_level"][int(np.argmin(costs))])
    return best

def gate_flags(y, S_val, A, pool, pi, horizons, val_origins):
    """Gate for policy p at horizon h is open iff its VALIDATION mean total cost is below the reactive policy's."""
    flags = {}
    for p in BASE_POLICIES:
        flags[p] = {}
        for h in horizons:
            c_p = realized(S_val[p][h], y, A, pool, pi, val_origins, h)[2].mean()
            c_r = realized(S_val["reactive"][h], y, A, pool, pi, val_origins, h)[2].mean()
            flags[p][h] = bool(c_p < c_r) if p not in ("reactive", "oracle") else True
    return flags

def interval_metrics(y, F, res, horizons, origins, cfg, q=0.8):
    """Interval coverage/width (horizon-specific vs pooled residual quantiles) and point accuracy on given origins."""
    W = cfg["calibration_window"]; first = cfg["t_calibration_start"]; R = y.shape[0]
    lo_q, hi_q = (1 - q) / 2, 1 - (1 - q) / 2
    rows = []
    for h in horizons:
        cov = {"hspec": [], "pooled": []}; wid = {"hspec": [], "pooled": []}; ae = []; yy = []
        for r in range(R):
            for d in origins:
                yh = F[h][r, d]
                if np.isnan(yh): continue
                yt = y[r, d + h]; ae.append(abs(yt - yh)); yy.append(yt)
                for name, w in (("hspec", window_h(res[h][r], h, d, W, first)), ("pooled", window_pooled(res, r, horizons, d, W, first))):
                    if len(w) < MIN_RESIDUALS: continue
                    lo, hi = yh + np.quantile(w, lo_q), yh + np.quantile(w, hi_q)
                    cov[name].append(lo <= yt <= hi); wid[name].append(hi - lo)
        rows.append(dict(h=h, mae=float(np.mean(ae)), wape=float(np.sum(ae) / np.sum(yy)),
                         cov_hspec=float(np.mean(cov["hspec"])), cov_pooled=float(np.mean(cov["pooled"])),
                         width_hspec=float(np.mean(wid["hspec"])), width_pooled=float(np.mean(wid["pooled"]))))
    return rows
