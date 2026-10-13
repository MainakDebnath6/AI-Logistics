"""Independent replication of the primary contrast (HCCR vs pooled, gated, mean over h in {1,7,14}) on NEW seeds 100-129.
Hypothesis and configuration are the frozen ones; nothing is tuned. Resumable per regime."""
import logging, pandas as pd, numpy as np
from scipy import stats
from .study import load_config, run_sim
from .analysis import OUT, CFG, OPH, boot_ci
logging.disable(logging.CRITICAL)
SEEDS = range(100, 130); P = OUT / "parts"; P.mkdir(exist_ok=True)
def main():
    cfg = load_config(str(OUT.parent / "configs/study_config.json")); rows = []
    for reg in cfg["regimes"]:
        f = P / f"rep_{reg}.pkl"
        if not f.exists():
            ops = []
            for s in SEEDS:
                (r, _, _), _, _ = run_sim(reg, s, cfg, "lr"); ops += r
            pd.to_pickle(pd.DataFrame(ops), f)
        rows.append(pd.read_pickle(f))
    df = pd.concat(rows); df.to_csv(OUT / "replication_operational.csv", index=False); out = []
    def cost(p, v, hs, reg): return df[(df.policy == p) & (df.variant == v) & df.h.isin(hs) & (df.regime == reg)].groupby("seed").cost_total.mean().sort_index()
    for reg in cfg["regimes"]:
        for hlab, hs in (("h1-7-14", OPH), ("h1", [1]), ("h14", [14]), ("h28", [28])):
            h, po = cost("hspec", "gated", hs, reg), cost("pooled", "gated", hs, reg); d = (po - h).values; lo, hi = boot_ci(d)
            p = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
            out.append(dict(regime=reg, horizons=hlab, n=len(d), mean_delta=d.mean(), ci_lo=lo, ci_hi=hi, p_wilcoxon=p, pct_of_hccr=100 * d.mean() / h.mean()))
    t = pd.DataFrame(out); t.to_csv(OUT / "replication_B.csv", index=False); print(t.round(3).to_string())
if __name__ == "__main__": main()
