"""Full-sample reserve-set disagreement between HCCR (hspec) and pooled calibration.
Unit = simulation (regime, seed). Disagreement = share of test decisions (regions x origins) at a horizon where the chosen reserve set differs.
Reported for UNGATED decisions (pure effect of the calibration choice) and GATED decisions (as deployed in the paper). Resumable per simulation."""
import logging, sys, pandas as pd, numpy as np
from .study import load_config, run_sim
from .analysis import OUT, boot_ci
logging.disable(logging.CRITICAL)
P = OUT / "parts"; P.mkdir(exist_ok=True)
def one(reg, seed, cfg):
    f = P / f"dis_{reg}_{seed}.pkl"
    if f.exists(): return pd.read_pickle(f)
    (_, _, dec), _, _ = run_sim(reg, seed, cfg, "lr", keep_decisions=True); t = dec["test"]; rows = []
    for h in cfg["horizons"]:
        rawd = float((dec["S_raw"]["hspec"][h][:, t] != dec["S_raw"]["pooled"][h][:, t]).mean())
        gd = float((dec["S"]["hspec"][h][:, t] != dec["S"]["pooled"][h][:, t]).mean())
        rows.append(dict(regime=reg, seed=seed, h=h, disagree_ungated=rawd, disagree_gated=gd))
    d = pd.DataFrame(rows); pd.to_pickle(d, f); return d
def main(seeds, tag, budget_s=270):
    import time; t0 = time.time(); cfg = load_config(str(OUT.parent / "configs/study_config.json")); parts = []; done = True
    for reg in cfg["regimes"]:
        for s in seeds:
            if time.time() - t0 > budget_s and not (P / f"dis_{reg}_{s}.pkl").exists(): done = False; continue
            parts.append(one(reg, s, cfg))
    if done:
        d = pd.concat(parts); d.to_csv(OUT / f"decision_disagreement_{tag}.csv", index=False); print("complete", tag, len(d))
    else: print("partial; rerun to resume", len(parts))
if __name__ == "__main__":
    tag = sys.argv[1]; seeds = range(0, 30) if tag == "primary" else range(100, 130); main(list(seeds), tag)
