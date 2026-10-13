"""Design logic for the proposed mechanism experiment.  Sign convention (as in the paper): delta = C_pooled - C_HCCR; delta>0 => HCCR cheaper.

Calibration-window variants (residual e_{o,h} = y_{o+h} - yhat_{o,h} becomes observable at day o+h):
  natural      : origins o in [d-h-W+1, d-h]                    (deployable; the paper's protocol)
  extra_lag(L) : origins o in [d-h-L-W+1, d-h-L]                (deployable; strictly staler than natural; dose-response in delay)
  anticipative : origins o in [d-W, d-1]; targets reach d-1+h>d (NOT deployable; uses future demand; diagnostic upper bound only)
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class WindowSpec:
    kind: str = "natural"          # natural | extra_lag | anticipative
    extra_lag: int = 0
    diagnostic_only: bool = False  # must be True for anticipative windows

    def __post_init__(self):
        if self.kind not in ("natural", "extra_lag", "anticipative"): raise ValueError(self.kind)
        if self.kind == "anticipative" and not self.diagnostic_only:
            raise ValueError("anticipative windows use future demand: set diagnostic_only=True and never report them as a policy")
        if self.kind == "natural" and self.extra_lag != 0: raise ValueError("natural window has no extra lag")
        if self.extra_lag < 0: raise ValueError("extra_lag must be >= 0")

def window_origins(spec: WindowSpec, d: int, h: int, W: int, first: int) -> np.ndarray:
    """Origins whose residuals form the calibration window at decision day d for horizon h."""
    if spec.kind == "anticipative": hi = d - 1
    else: hi = d - h - (spec.extra_lag if spec.kind == "extra_lag" else 0)
    lo = max(first, hi - W + 1)
    return np.arange(lo, hi + 1) if hi >= lo else np.empty(0, int)

def is_causal(spec: WindowSpec, d: int, h: int, W: int, first: int) -> bool:
    o = window_origins(spec, d, h, W, first)
    return bool(len(o) == 0 or (o + h).max() <= d)

def shuffle_window(e: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Negative control: destroy serial order inside the window. The empirical distribution (hence quantiles/scenarios as a SET)
    is unchanged, so any effect of autocorrelation must act through staleness/dependence on the target, not set composition."""
    return rng.permutation(e)

def ar1_latent(T: int, phi: float, stationary_sd: float, rng: np.random.Generator) -> np.ndarray:
    """AR(1) latent shock with FIXED stationary sd for any phi in [0,1) (phi=0 -> iid). Marginal scale of the latent is held fixed;
    the horizon profile of forecast-error dispersion is NOT held fixed (it depends on phi) - a declared confound."""
    innov_sd = stationary_sd * np.sqrt(1.0 - phi ** 2)
    u = np.empty(T); u[0] = rng.normal(0, stationary_sd)
    z = rng.normal(0, 1, T)
    for t in range(1, T): u[t] = phi * u[t - 1] + innov_sd * z[t]
    return u

def delta(cost_pooled: np.ndarray, cost_hccr: np.ndarray) -> np.ndarray:
    """Paired per-simulation difference (same seeds, demand, costs, fleet, forecasts)."""
    a, b = np.asarray(cost_pooled, float), np.asarray(cost_hccr, float)
    if a.shape != b.shape: raise ValueError("paired arrays must align by simulation")
    return a - b

def effect_of_removing_delay(delta_natural: np.ndarray, delta_anticipative: np.ndarray) -> np.ndarray:
    """PRIMARY estimand per simulation (h in {14,28}, AR): (delta under anticipative diagnostic) - (delta under natural)."""
    return np.asarray(delta_anticipative, float) - np.asarray(delta_natural, float)
