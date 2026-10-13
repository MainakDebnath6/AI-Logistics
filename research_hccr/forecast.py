"""Forecasters. Every forecast for origin o uses only observations y[..o] (and models fitted on data <= refit date <= o).

F[h] has shape (R, T): F[h][r, o] = prediction (made at origin o) of y[r, o+h]; NaN where unavailable.
"""
from __future__ import annotations
import numpy as np

def _design(T: int, h: int, y: np.ndarray, origins: np.ndarray) -> np.ndarray:
    """Direct-horizon seasonal-LR features for one region at given origins (target = o+h)."""
    tgt = origins + h
    cols = [np.ones(len(origins)), tgt / 365.0]
    for k in (1, 2, 3):
        cols += [np.sin(2 * np.pi * k * tgt / 7.0), np.cos(2 * np.pi * k * tgt / 7.0)]
    for k in (1, 2):
        cols += [np.sin(2 * np.pi * k * tgt / 365.25), np.cos(2 * np.pi * k * tgt / 365.25)]
    cols.append(y[origins])                                              # last observed value
    csum = np.concatenate([[0.0], np.cumsum(y)])
    cols.append((csum[origins + 1] - csum[origins - 6]) / 7.0)           # trailing 7-day mean (incl. origin)
    return np.column_stack(cols)

def forecast_seasonal_lr(y: np.ndarray, horizons, t_first: int, refit_every: int = 7):
    R, T = y.shape
    out = {h: np.full((R, T), np.nan) for h in horizons}
    for r in range(R):
        for h in horizons:
            origins_all = np.arange(7, T - h)
            X = _design(T, h, y[r], origins_all); Y = y[r, origins_all + h]
            for f in range(t_first, T - h, refit_every):
                m = origins_all + h <= f                                   # targets observed by refit date f
                beta, *_ = np.linalg.lstsq(X[m], Y[m], rcond=None)
                hi = min(f + refit_every, T - h)
                sel = (origins_all >= f) & (origins_all < hi)
                out[h][r, origins_all[sel]] = np.maximum(X[sel] @ beta, 0.0)
    return out

def forecast_naive_week(y: np.ndarray, horizons, t_first: int):
    """Previous-week repeat: target tau uses y[tau - 7k], k = ceil(h/7), which is <= origin."""
    R, T = y.shape
    out = {h: np.full((R, T), np.nan) for h in horizons}
    for h in horizons:
        k = int(np.ceil(h / 7)); o = np.arange(t_first, T - h)
        out[h][:, o] = y[:, o + h - 7 * k]
    return out

def forecast_holt_winters(y: np.ndarray, horizons, t_first: int, param_refit_every: int = 28):
    """Additive weekly Holt-Winters. Smoothing parameters re-estimated (statsmodels) at past dates only;
    states updated daily with data up to the origin."""
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    import warnings
    R, T = y.shape
    out = {h: np.full((R, T), np.nan) for h in horizons}
    m = 7
    for r in range(R):
        params = {}
        for f in range(t_first, T, param_refit_every):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = ExponentialSmoothing(y[r, max(0, f - 364):f + 1], trend="add", seasonal="add",
                                           seasonal_periods=m, initialization_method="estimated").fit()
            p = fit.params
            params[f] = (float(p["smoothing_level"]), float(p["smoothing_trend"]), float(p["smoothing_seasonal"]))
        fdates = sorted(params)
        level = y[r, :m].mean(); trend = (y[r, m:2 * m].mean() - level) / m
        seas = y[r, :m] - level
        cur = None
        for t in range(T):
            # parameters are those estimated at the latest refit date <= t (no future info)
            cand = [f for f in fdates if f <= t]
            if cand: cur = params[cand[-1]]
            if t >= m:
                a, b, g = cur if cur is not None else (0.3, 0.05, 0.2)
                s_i = t % m; pl = level
                level = a * (y[r, t] - seas[s_i]) + (1 - a) * (level + trend)
                trend = b * (level - pl) + (1 - b) * trend
                seas[s_i] = g * (y[r, t] - level) + (1 - g) * seas[s_i]
            if t >= t_first:
                for h in horizons:
                    if t + h < T:
                        out[h][r, t] = max(level + h * trend + seas[(t + h) % m], 0.0)
    return out
