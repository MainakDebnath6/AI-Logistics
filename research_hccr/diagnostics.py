"""Exploratory diagnostic (seeds 0-2 per regime): how often do HCCR and pooled calibration choose different reserve sets?"""
import logging, pandas as pd
from .study import load_config, run_sim
from .analysis import OUT
logging.disable(logging.CRITICAL)
def main(n_seeds=3):
    cfg = load_config(str(OUT.parent / "configs/study_config.json")); rows = []
    for reg in cfg["regimes"]:
        for seed in range(n_seeds):
            (_, _, dec), _, _ = run_sim(reg, seed, cfg, "lr", keep_decisions=True); t = dec["test"]
            for h in cfg["operational_horizons"]:
                a, b = dec["S"]["hspec"][h][:, t], dec["S"]["pooled"][h][:, t]
                rows.append(dict(regime=reg, seed=seed, h=h, frac_different=float((a != b).mean())))
    d = pd.DataFrame(rows); d.to_csv(OUT / "decision_disagreement.csv", index=False)
    print(d.groupby("regime").frac_different.mean().round(3).to_dict(), "overall", round(d.frac_different.mean(), 3))
if __name__ == "__main__": main()
