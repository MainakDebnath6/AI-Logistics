"""Transparent multi-region demand simulator (SYNTHETIC; not real observations).

demand_{r,t} = L_r*(1 + 0.0002 t + 0.12 sin(2 pi t/7 + pw_r) + 0.10 sin(2 pi t/365.25 + pa_r))
               + latent_{r,t} + eps_{r,t},   clipped at 0.
Regimes differ only in the latent / event component (see REGIMES).
"""
from __future__ import annotations
import numpy as np

REGIMES = {
    # horizon-invariant noise: calibration by horizon should NOT matter (null-control regime)
    "iid":   dict(noise=0.05, ar_phi=None, ar_sd=0.0, rw_sd=0.0, surge_p=0.0),
    # persistent latent shocks: lagged information decays with lead time -> error grows with horizon
    "ar":    dict(noise=0.05, ar_phi=0.95, ar_sd=0.10, rw_sd=0.0, surge_p=0.0),
    # unforecastable multi-day surges (heavy right tail), horizon-invariant in distribution
    "surge": dict(noise=0.05, ar_phi=None, ar_sd=0.0, rw_sd=0.0, surge_p=0.01),
    # random-walk level drift: error variance grows roughly linearly with horizon
    "drift": dict(noise=0.05, ar_phi=None, ar_sd=0.0, rw_sd=0.008, surge_p=0.0),
}

def simulate(regime: str, seed: int, T: int, levels, noise_scale: float = 1.0, ar_phi_override=None) -> np.ndarray:
    """Return array (R, T) of daily demand in load units for each region."""
    spec = dict(REGIMES[regime])
    if ar_phi_override is not None: spec["ar_phi"] = ar_phi_override   # mechanism experiment only; default path unchanged
    rid = list(REGIMES).index(regime)
    rng = np.random.default_rng(np.random.SeedSequence([seed, rid, 20261010]))
    L = np.asarray(levels, float)[:, None]
    R = L.shape[0]
    t = np.arange(T, dtype=float)[None, :]
    pw = rng.uniform(0, 2 * np.pi, (R, 1)); pa = rng.uniform(0, 2 * np.pi, (R, 1))
    det = L * (1 + 0.0002 * t + 0.12 * np.sin(2 * np.pi * t / 7 + pw) + 0.10 * np.sin(2 * np.pi * t / 365.25 + pa))
    y = det + rng.normal(0, 1, (R, T)) * spec["noise"] * L * noise_scale
    if spec["ar_phi"] is not None:
        phi = spec["ar_phi"]; sd_innov = spec["ar_sd"] * np.sqrt(1 - phi ** 2) * L[:, 0] * noise_scale
        u = np.zeros((R, T)); u[:, 0] = rng.normal(0, 1, R) * spec["ar_sd"] * L[:, 0] * noise_scale
        eps = rng.normal(0, 1, (R, T))
        for k in range(1, T):
            u[:, k] = phi * u[:, k - 1] + sd_innov * eps[:, k]
        y = y + u
    if spec["rw_sd"] > 0:
        y = y + np.cumsum(rng.normal(0, 1, (R, T)) * spec["rw_sd"] * L * noise_scale, axis=1)
    if spec["surge_p"] > 0:
        starts = rng.random((R, T)) < spec["surge_p"]
        mag = rng.uniform(0.3, 0.8, (R, T)) * L
        for r in range(R):
            for k in np.flatnonzero(starts[r]):
                y[r, k:k + 3] += mag[r, k]
    return np.maximum(y, 0.0)
