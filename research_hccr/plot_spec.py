"""Main figure: interaction plot of delta = C_pooled - C_HCCR. Expects a CSV produced by the (future) experiment runner with schema:
 columns: sim_id, seed, regime, horizon, window_kind[natural|extra_lag|anticipative], extra_lag, phi, delta, deployable[bool]
Nothing is generated here; the function raises if the file is absent."""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

def boot_ci(x, n=10000, seed=1):
    rng = np.random.default_rng(seed); x = np.asarray(x, float); m = x[rng.integers(0, len(x), (n, len(x)))].mean(1)
    return np.quantile(m, .025), np.quantile(m, .975)

def interaction_plot(csv_path, out_pdf):
    d = pd.read_csv(csv_path)                    # FileNotFoundError if no experiment has been run: intentional
    need = {"seed", "regime", "horizon", "window_kind", "extra_lag", "phi", "delta", "deployable"}
    if not need <= set(d.columns): raise ValueError(f"missing columns: {need - set(d.columns)}")
    hs = sorted(d.horizon.unique()); fig, axes = plt.subplots(1, len(hs), figsize=(7.1, 2.2), sharey=True)
    for ax, h in zip(np.atleast_1d(axes), hs):
        for (kind, phi), g in d[d.horizon == h].groupby(["window_kind", "phi"]):
            m = g.groupby("seed").delta.mean(); lo, hi = boot_ci(m.values)
            dep = bool(g.deployable.iloc[0]); ax.errorbar([f"{kind}\nphi={phi}"], [m.mean()], yerr=[[m.mean() - lo], [hi - m.mean()]],
                                                         fmt="o" if dep else "x", capsize=2, label=("deployable" if dep else "DIAGNOSTIC (non-deployable)"))
        ax.axhline(0, color="k", lw=.6); ax.set_title(f"h={h}", fontsize=7); ax.tick_params(labelsize=5)
    axes[0].set_ylabel("C_pooled - C_HCCR  (>0: HCCR cheaper)"); fig.tight_layout(); fig.savefig(out_pdf)
