"""Paired power analysis. Inputs must come from PAIRED per-simulation differences (pilot) - none are supplied here."""
from __future__ import annotations
import numpy as np
from scipy import stats

def n_required_normal(sd_paired: float, min_effect: float, alpha: float = 0.05, power: float = 0.8, n_tests: int = 1) -> int:
    """Closed-form paired z approximation: n = ((z_{1-a/(2m)} + z_{power}) * sd / delta)^2 (Bonferroni over n_tests; conservative vs Holm)."""
    za = stats.norm.ppf(1 - alpha / (2 * n_tests)); zb = stats.norm.ppf(power)
    return int(np.ceil(((za + zb) * sd_paired / min_effect) ** 2))

def simulated_power(pilot_diffs: np.ndarray, min_effect: float, n: int, alpha: float = 0.05, n_boot: int = 2000,
                    n_rep: int = 1000, seed: int = 0) -> float:
    """Simulation-based power from a PILOT sample of paired differences: shift the pilot to mean=min_effect, resample n pairs
    with replacement, and record how often the percentile-bootstrap CI excludes 0 (uses real paired variance/shape, not a normal model)."""
    rng = np.random.default_rng(seed); d0 = np.asarray(pilot_diffs, float); d0 = d0 - d0.mean() + min_effect; hits = 0
    for _ in range(n_rep):
        d = rng.choice(d0, size=n, replace=True)
        m = d[rng.integers(0, n, (n_boot, n))].mean(axis=1)
        hits += (np.quantile(m, alpha / 2) > 0) or (np.quantile(m, 1 - alpha / 2) < 0)
    return hits / n_rep

def sd_from_reported_ci(ci_lo: float, ci_hi: float, n: int) -> float:
    """PLANNING ONLY: back out a paired-difference sd from a reported 95% CI (SE ~ half-width/1.96, sd = SE*sqrt(n)).
    Rounded, bootstrap CIs make this imprecise; replace by the pilot's actual sd as soon as raw paired data exist."""
    return (ci_hi - ci_lo) / 2 / 1.96 * np.sqrt(n)
