"""Build paper figures and LaTeX table fragments directly from results/*.csv (no hand-typed numbers)."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent; R = HERE / "results"
OUT = Path(__import__("sys").argv[1]) if len(__import__("sys").argv) > 1 else HERE / "paper_assets"
OUT.mkdir(parents=True, exist_ok=True)
REG = ["iid", "ar", "surge", "drift"]; RN = {"iid": "IID", "ar": "AR", "surge": "Surge", "drift": "Drift"}
plt.rcParams.update({"font.size": 7, "axes.labelsize": 7, "legend.fontsize": 6, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
                     "font.family": "serif", "axes.linewidth": 0.6, "pdf.fonttype": 42})

def fmt(x, d=2): return f"{x:.{d}f}"
def ci(m, lo, hi, d=2): return f"{m:+.{d}f} [{lo:+.{d}f}, {hi:+.{d}f}]"

# ---------------- Figure: calibration coverage + per-horizon advantage ----------------
cal = pd.read_csv(R / "forecast_calibration_summary.csv"); ph = pd.read_csv(R / "paired_by_horizon_main.csv")
fig, ax0 = plt.subplots(1, 1, figsize=(3.45, 1.9)); ax = [ax0]
cols = {"iid": "#7f7f7f", "ar": "#d62728", "surge": "#2ca02c", "drift": "#1f77b4"}
for r in REG:
    c = cal[cal.regime == r].sort_values("h")
    ax[0].plot(c.h, c.cov_hspec, "-o", ms=2.5, color=cols[r], lw=1, label=f"{RN[r]}")
    ax[0].plot(c.h, c.cov_pooled, "--s", ms=2.5, color=cols[r], lw=0.9, alpha=0.8)
ax[0].axhline(0.8, color="k", lw=0.6, ls=":"); ax[0].text(15.5, 0.808, "nominal 0.80", fontsize=5.5)
ax[0].set_xlabel("forecast horizon $h$ (days)"); ax[0].set_ylabel("empirical 80% coverage"); ax[0].set_xticks([1, 7, 14, 28]); ax[0].set_ylim(0.64, 1.0)
ax[0].set_title("solid = horizon-specific, dashed = pooled", fontsize=6.5); ax[0].legend(ncol=4, loc="upper right", frameon=False, handlelength=1.2, columnspacing=0.7)
fig.tight_layout(pad=0.4); fig.savefig(OUT / "fig_results.pdf"); plt.close(fig)

# ---------------- Table: policy levels (+ routing if present) ----------------
lv = pd.read_csv(R / "policy_levels_main.csv"); names = {"reactive": "Reactive CVRP", "point": "Point-forecast", "buffer": "Fixed buffer (val.)",
                                                          "pooled": "Pooled residuals", "hspec": "HCCR (horizon-spec.)", "robust": "Robust quantile cover", "oracle": "Oracle (unattainable)"}
rt = pd.read_csv(R / "routing_summary.csv").set_index("policy") if (R / "routing_summary.csv").exists() else None
rows = []
for p in names:
    g = lv[lv.policy == p]
    row = f"{names[p]} & {fmt(g.cost_total.mean())} & {fmt(g.cost_reserve.mean())} & {fmt(g.unmet.mean())} & {fmt(g.shortage_day_rate.mean(),2)} & {fmt(g.n_reserved.mean())}"
    if rt is not None:
        row += f" & {100*rt.loc[p,'feasibility_rate']:.1f}"
    rows.append(row + r" \\")
(OUT / "tab_policies_rows.tex").write_text("\n".join(rows))

# ---------------- Table: ablation / paired comparisons ----------------
pc = pd.read_csv(R / "paired_comparisons_main.csv"); pc = pc[pc.horizons == "h1-7-14"]
lab = {"vs_pooled(B)": "B: pooled residuals", "vs_point(C)": "C: point forecast", "vs_buffer(D)": "D: fixed buffer",
       "vs_ungated(E)": "E: no horizon gate", "vs_reactive": "Reactive CVRP", "oracle_gap": "Oracle (gap)"}
rows = []
for k, v in lab.items():
    cells = []
    for r in REG:
        x = pc[(pc.comparison == k) & (pc.regime == r)].iloc[0]
        star = "" if (pd.isna(x.p_holm)) else ("$^{\\ast}$" if x.p_holm < 0.05 else "")
        cells.append(ci(x.mean_delta, x.ci_lo, x.ci_hi) + star)
    rows.append(f"{v} & " + " & ".join(cells) + r" \\")
(OUT / "tab_ablation_rows.tex").write_text("\n".join(rows))
# per-horizon rows for pooled
rows = []
for h in sorted(ph.h.unique()):
    cells = []
    for r in REG:
        x = ph[(ph.comparison == "vs_pooled") & (ph.regime == r) & (ph.h == h)].iloc[0]
        cells.append(ci(x.mean_delta, x.ci_lo, x.ci_hi))
    rows.append(f"B at $h={h}$ & " + " & ".join(cells) + r" \\")
(OUT / "tab_ablation_byh_rows.tex").write_text("\n".join(rows))

# ---------------- Table: forecast models ----------------
if (R / "forecast_model_ablation.csv").exists():
    fm = pd.read_csv(R / "forecast_model_ablation.csv"); mn = {"naive": "Weekly naive", "hw": "Holt--Winters", "lr": "Seasonal LR"}
    rows = []
    for m in ("naive", "hw", "lr"):
        cells = []
        for r in REG:
            x = fm[(fm.model == m) & (fm.regime == r)].iloc[0]; cells.append(f"{100*x.wape:.1f} / {x.cost_hspec:.2f}")
        rows.append(f"{mn[m]} & " + " & ".join(cells) + r" \\")
    (OUT / "tab_models_rows.tex").write_text("\n".join(rows))

# ---------------- Table: sensitivity ----------------
if (R / "sensitivity_summary.csv").exists():
    s = pd.read_csv(R / "sensitivity_summary.csv"); s = s[s.regime == "ALL"]
    pn = {"shortage_penalty": "$\\pi{=}", "reserve_cost_scale": "cost scale $\\times", "capacity_pressure_kappa": "$\\kappa{=}", "noise_scale": "noise $\\times"}
    rows = []
    order = [("primary", 0.0)] + [(p, v) for p in ("shortage_penalty", "reserve_cost_scale", "capacity_pressure_kappa", "noise_scale")
                                  for v in sorted(s[s.param == p].value.unique())]
    keep = {("primary", 0.0), ("shortage_penalty", 1.0), ("shortage_penalty", 4.0), ("capacity_pressure_kappa", 1.2), ("noise_scale", 2.0)}
    for p, v in order:
        if (p, v) not in keep: continue
        g = s[(s.param == p) & (s.value == v)]
        if g.empty: continue
        cells = []
        for comp in ("reactive", "point", "pooled", "ungated"):
            x = g[g.comparator == comp].iloc[0]; cells.append(ci(x.mean_delta, x.ci_lo, x.ci_hi))
        lbl = "primary" if p == "primary" else f"{pn[p]}{v:g}$"
        rows.append(f"{lbl} & {g.iloc[0].cost_hspec:.2f} & " + " & ".join(cells) + r" \\")
    (OUT / "tab_sens_rows.tex").write_text("\n".join(rows))
if (R / "replication_B.csv").exists():
    rp = pd.read_csv(R / "replication_B.csv"); pcm = pd.read_csv(R / "paired_comparisons_main.csv"); pcm = pcm[(pcm.horizons == "h1-7-14") & (pcm.comparison == "vs_pooled(B)")]
    rows = []
    for r in REG:
        o = pcm[pcm.regime == r].iloc[0]; n = rp[(rp.regime == r) & (rp.horizons == "h1-7-14")].iloc[0]
        h1 = rp[(rp.regime == r) & (rp.horizons == "h1")].iloc[0]; h28 = rp[(rp.regime == r) & (rp.horizons == "h28")].iloc[0]
        rows.append(f"{RN[r]} & {ci(o.mean_delta,o.ci_lo,o.ci_hi,3)} & {ci(n.mean_delta,n.ci_lo,n.ci_hi,3)} & {100*o.mean_delta/o.cost_a:+.2f} / {n.pct_of_hccr:+.2f} & {h1.mean_delta:+.2f} / {h28.mean_delta:+.2f} \\\\")
    (OUT / "tab_rep_rows.tex").write_text("\n".join(rows))
print("assets written to", OUT)
