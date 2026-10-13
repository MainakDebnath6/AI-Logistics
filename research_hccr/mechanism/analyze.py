"""Pre-registered analysis of the mechanism experiment (see PREREGISTRATION.md). Unit = simulation (seed). Bootstrap seed 12345, 10,000 resamples."""
import sys, numpy as np, pandas as pd
from scipy import stats
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from ..analysis import boot_ci, holm
OUT = Path(__file__).resolve().parent.parent / "results"

def D(d, phi, cond, h): return d[(d.phi == phi) & (d.condition == cond) & (d.h == h)].sort_values("seed").delta.values
def main(tag="confirm", fig_path=None):
    d = pd.read_csv(OUT / f"mechanism_{tag}_paired.csv"); rows = []; n = d.seed.nunique()
    prim = []
    for h in (14, 28):
        th = (D(d, .95, "anticipative", h) - D(d, .95, "natural", h)) - (D(d, 0.0, "anticipative", h) - D(d, 0.0, "natural", h))
        lo, hi = boot_ci(th); lo2, hi2 = boot_ci(th, alpha=0.025); p = float(stats.wilcoxon(th).pvalue)
        prim.append(dict(contrast=f"Theta_h{h}", n_sims=n, mean=th.mean(), ci95_lo=lo, ci95_hi=hi, ci975_lo=lo2, ci975_hi=hi2, p_wilcoxon=p, dz=th.mean() / th.std(ddof=1)))
    ph = holm([r["p_wilcoxon"] for r in prim]); [r.update(p_holm=float(q)) for r, q in zip(prim, ph)]
    pd.DataFrame(prim).to_csv(OUT / f"mechanism_{tag}_primary.csv", index=False)
    cells = []
    for (phi, cond, h), g in d.groupby(["phi", "condition", "h"]):
        x = g.sort_values("seed")
        for col in ("delta", "disagreement", "coverage80_hspec", "cost_hspec", "cost_pooled", "reserve_cost_hspec", "reserve_cost_pooled", "unmet_hspec", "unmet_pooled", "capacity_hspec", "capacity_pooled"):
            lo, hi = boot_ci(x[col].values); cells.append(dict(phi=phi, condition=cond, h=h, metric=col, n_sims=len(x), mean=x[col].mean(), ci_lo=lo, ci_hi=hi, deployable=bool(x.deployable.iloc[0])))
    pd.DataFrame(cells).to_csv(OUT / f"mechanism_{tag}_cells.csv", index=False)
    rd = pd.read_csv(OUT / f"mechanism_{tag}_residual_diag.csv").groupby(["phi", "h"]).mean(numeric_only=True).drop(columns="seed").reset_index(); rd.to_csv(OUT / f"mechanism_{tag}_residual_summary.csv", index=False)
    if fig_path:
        fig, ax = plt.subplots(1, 2, figsize=(3.45, 1.95), sharey=True); plt.rcParams.update({"font.size": 6})
        for a, h in zip(ax, (14, 28)):
            for phi, col, off in ((0.95, "#d62728", -0.07), (0.0, "#1f77b4", 0.07)):
                for i, (cond, mk) in enumerate((("natural", "o"), ("anticipative", "X"))):
                    v = D(d, phi, cond, h); lo, hi = boot_ci(v); a.errorbar(i + off, v.mean(), yerr=[[v.mean() - lo], [hi - v.mean()]], fmt=mk, color=col, capsize=1.5, ms=4, lw=.8,
                                                                             label=(f"$\\phi$={phi}" if i == 0 else None), mfc=("white" if cond == "anticipative" else col))
            a.axhline(0, color="k", lw=.5); a.set_xticks([0, 1]); a.set_xticklabels(["natural\n(deployable)", "anticipative\n(DIAGNOSTIC)"], fontsize=5.5); a.set_title(f"$h$={h}", fontsize=6.5); a.set_xlim(-.4, 1.4)
        ax[0].set_ylabel("$\\Delta$ = cost(pooled) $-$ cost(HCCR)", fontsize=6); ax[0].legend(frameon=False, fontsize=5.5, loc="lower right"); fig.tight_layout(pad=.3); fig.savefig(fig_path)
    print(pd.DataFrame(prim).round(4).to_string())
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
