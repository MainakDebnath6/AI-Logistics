"""Rolling-origin residual calibration. At decision time d, only residuals whose TARGET is already observed
(o' + h <= d) are eligible. Windows are the most recent W eligible residuals."""
from __future__ import annotations
import numpy as np

def residuals(y: np.ndarray, F: dict) -> dict:
    """e[h][r, o] = y[r, o+h] - F[h][r, o] (NaN where undefined). Indexed by ORIGIN o; available at time o+h."""
    R, T = y.shape; out = {}
    for h, f in F.items():
        e = np.full((R, T), np.nan); e[:, :T - h] = y[:, h:] - f[:, :T - h]; out[h] = e
    return out

def window_h(e_h_r: np.ndarray, h: int, d: int, W: int, first: int) -> np.ndarray:
    """Horizon-specific eligible residuals at decision time d (origin o' in [first, d-h])."""
    hi = d - h
    lo = max(first, hi - W + 1)
    if hi < lo: return np.empty(0)
    w = e_h_r[lo:hi + 1]
    return w[~np.isnan(w)]

def window_pooled(res: dict, r: int, horizons, d: int, W: int, first: int) -> np.ndarray:
    return np.concatenate([window_h(res[h][r], h, d, W, first) for h in horizons])
