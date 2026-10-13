"""Discrete reserve-vehicle selection (reservation state only; activation is a separate, confirmed-demand-driven step)."""
from __future__ import annotations
import itertools
import numpy as np

class ReservePool:
    def __init__(self, caps, max_count, c_fixed, c_unit, cost_scale=1.0):
        self.caps_by_type = list(caps)
        combos = list(itertools.product(range(max_count + 1), repeat=len(caps)))
        cap = np.array([sum(n * q for n, q in zip(c, caps)) for c in combos], float)
        nveh = np.array([sum(c) for c in combos], int)
        cost = np.array([cost_scale * sum(n * (c_fixed + c_unit * q) for n, q in zip(c, caps)) for c in combos], float)
        order = np.lexsort((cap, cost))                    # ascending cost; ties broken by smaller capacity
        self.counts = [combos[i] for i in order]
        self.cap, self.nveh, self.cost = cap[order], nveh[order], cost[order]
        self.empty = int(np.flatnonzero(self.nveh == 0)[0])

    def choose_cost_aware(self, A: float, scen: np.ndarray, pi: float) -> int:
        """argmin_S  c(S) + pi * mean_b (D_b - A - cap(S))_+   (expected unmet demand under scenarios)."""
        short = np.maximum(scen[None, :] - (A + self.cap[:, None]), 0.0).mean(axis=1)
        return int(np.argmin(self.cost + pi * short))

    def choose_cover(self, A: float, target: float) -> int:
        """Cheapest S with A + cap(S) >= target; if none exists, the maximum-capacity set (buffer policy)."""
        ok = A + self.cap >= target
        if ok.any():
            idx = np.flatnonzero(ok); return int(idx[np.argmin(self.cost[idx])])
        return int(np.argmax(self.cap))

    def realized(self, S: np.ndarray, y: np.ndarray, A: np.ndarray, pi: float):
        """Realized reservation cost, unmet demand, total cost. Unmet demand = (y - A - cap(S))_+ (aggregate-capacity level)."""
        unmet = np.maximum(y - A - self.cap[S], 0.0)
        return self.cost[S], unmet, self.cost[S] + pi * unmet
