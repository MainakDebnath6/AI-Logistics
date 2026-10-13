"""Pre-registered analysis (PREREGISTRATION_FRESHNESS.md). Unit = simulation. Bootstrap seed 12345, 10,000 resamples; Holm over the 2 primary contrasts."""
import sys, numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from ..analysis import boot_ci, holm
OUT = Path(__file__).resolve().parent.parent / "results"
def D(d, phi, cond, h): return d[(d.phi == phi) & (d.condition == cond) & (d.h == h)].sort_values("seed").delta.values
def main(tag="confirm", fig=None):
    d = pd.read_csv(OUT / f"freshness_{tag}_paired.csv"); n = d.seed.nunique(); prim = []
    for h in (14, 28):
        psi = (D(d, .95, "pooled_stale28", h) - D(d, .95, "natural", h)) - (D(d, 0.0, "pooled_stale28", h) - D(d, 0.0, "natural", h))
        lo, hi = boot_ci(psi); prim.append(dict(contrast=f"Psi_h{h}", n_sims=n, mean=psi.mean(), ci95_lo=lo, ci95_hi=hi, p_wilcoxon=float(stats.wilcoxon(psi).pvalue), dz=psi.mean() / psi.std(ddof=1)))
    for r, q in zip(prim, holm([r["p_wilcoxon"] for r in prim])): r["p_holm"] = float(q)
    pd.DataFrame(prim).to_csv(OUT / f"freshness_{tag}_primary.csv", index=False)
    cells = []
    for (phi, cond, h), g in d.groupby(["phi", "condition", "h"]):
        g = g.sort_values("seed")
        for col in ("delta", "disagreement", "cost_hspec", "cost_pooled", "reserve_cost_hspec", "reserve_cost_pooled", "unmet_hspec", "unmet_pooled"):
            lo, hi = boot_ci(g[col].values); cells.append(dict(phi=phi, condition=cond, h=h, metric=col, n_sims=len(g), mean=g[col].mean(), ci_lo=lo, ci_hi=hi))
    pd.DataFrame(cells).to_csv(OUT / f"freshness_{tag}_cells.csv", index=False)
    # secondary: per-policy cost change under staling (mechanism: who gets worse?)
    sec = []
    for phi in (0.95, 0.0):
        for h in (1, 14, 28):
            for cond, pol in (("pooled_stale28", "pooled"), ("hccr_stale28", "hspec")):
                dc = d[(d.phi == phi) & (d.condition == cond) & (d.h == h)].sort_values("seed")[f"cost_{pol}"].values - d[(d.phi == phi) & (d.condition == "natural") & (d.h == h)].sort_values("seed")[f"cost_{pol}"].values
                lo, hi = boot_ci(dc); sec.append(dict(phi=phi, h=h, intervention=cond, policy_staled=pol, cost_change_mean=dc.mean(), ci_lo=lo, ci_hi=hi))
    pd.DataFrame(sec).to_csv(OUT / f"freshness_{tag}_policy_cost_change.csv", index=False)
    if fig:
        fg, ax = plt.subplots(1, 2, figsize=(3.45, 1.9), sharey=True); plt.rcParams.update({"font.size": 6})
        for a, h in zip(ax, (14, 28)):
            for phi, col, off in ((0.95, "#d62728", -.06), (0.0, "#1f77b4", .06)):
                for i, cond in enumerate(("natural", "pooled_stale14", "pooled_stale28")):
                    v = D(d, phi, cond, h); lo, hi = boot_ci(v); a.errorbar(i + off, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt="o", color=col, capsize=1.5, ms=3.5, lw=.8, label=(f"$\\phi$={phi}" if i == 0 else None))
            a.axhline(0, color="k", lw=.5); a.set_xticks([0, 1, 2]); a.set_xticklabels(["natural", "pooled\n+14d", "pooled\n+28d"], fontsize=5.5); a.set_title(f"$h$={h}", fontsize=6.5); a.set_xlim(-.4, 2.4)
        ax[0].set_ylabel("$\\Delta$ = cost(pooled) $-$ cost(HCCR)", fontsize=6); ax[0].legend(frameon=False, fontsize=5.5, loc="lower right"); fg.tight_layout(pad=.3); fg.savefig(fig)
    print(pd.DataFrame(prim).round(4).to_string())
if __name__ == "__main__": main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
