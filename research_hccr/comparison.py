"""Consolidated quantitative comparison from raw CSVs. Unit for CIs: (regime, seed) simulation; regions/days averaged within it."""
from __future__ import annotations
import numpy as np, pandas as pd
from .analysis import OUT, CFG, OPH, boot_ci

POL = ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"]
NAME = {"reactive": "Reactive CVRP", "point": "Point-forecast", "buffer": "Fixed buffer (val.)", "pooled": "Pooled residuals",
        "hspec": "HCCR (horizon-spec.)", "robust": "Robust quantile cover", "robust_ungated": "Robust cover, no gate (ref.)", "oracle": "Oracle (unattainable)"}

def _units(df, pol, hs, col):
    var = "gated"
    if pol == "robust_ungated": pol, var = "robust", "ungated"
    s = df[(df.policy == pol) & (df.variant == var) & (df.h.isin(hs))]
    return s.groupby(["regime", "seed"])[col].mean()

def build():
    df = pd.read_csv(OUT / "operational_main.csv"); rt = pd.read_csv(OUT / "routing_instances.csv")
    iv = pd.read_csv(OUT / "intervals_main.csv"); rows = []
    scopes = [("aggregate", "h1-7-14", OPH, CFG["regimes"])] + [("per-regime", f"h1-7-14", OPH, [r]) for r in CFG["regimes"]] + \
             [("per-horizon", f"h{h}", [h], CFG["regimes"]) for h in CFG["horizons"]]
    for scope, hlab, hs, regs in scopes:
        for p in POL + (["robust_ungated"] if scope == "aggregate" else []):
            rec = dict(scope=scope, regimes="all" if len(regs) > 1 else regs[0], horizons=hlab, policy=p)
            for col in ["cost_total", "cost_reserve", "unmet", "shortage_day_rate", "n_reserved"]:
                u = _units(df, p, hs, col); u = u[u.index.get_level_values(0).isin(regs)]
                lo, hi = boot_ci(u.values); rec.update({col: u.mean(), col + "_lo": lo, col + "_hi": hi})
            rec["n_units"] = len(u)
            wp = iv[(iv.h.isin(hs)) & (iv.regime.isin(regs))]; rec["wape"] = float(wp.wape.mean())   # shared LR forecast
            if p == "robust_ungated": rows.append(rec); continue
            if scope == "aggregate" or scope == "per-regime" or (scope == "per-horizon" and hs == [7]):
                r_ = rt[(rt.policy == p) & (rt.regime.isin(regs))]
                f = r_.groupby(["regime", "seed"]).feasible.mean(); lo, hi = boot_ci(f.values)
                rec.update(route_feas=float(f.mean()), route_feas_lo=lo, route_feas_hi=hi, route_n_instances=len(r_),
                           route_runtime_s=float(r_.runtime_s.mean()))
            rows.append(rec)
    t = pd.DataFrame(rows); t.to_csv(OUT / "comparison_table.csv", index=False)
    # forecaster variants on identical seeds (0-9): same HCCR reservation objective, different forecast
    mod = pd.read_csv(OUT / "operational_models.csv"); lr = df[df.seed < CFG["n_seeds_forecast_models"]]
    ivm = pd.concat([iv[iv.seed < CFG["n_seeds_forecast_models"]], pd.read_csv(OUT / "intervals_models.csv")])
    fr = []
    for m in ("lr", "hw", "naive"):
        d = pd.concat([lr, mod]); d = d[d.model == m]
        u = _units(d, "hspec", OPH, "cost_total"); lo, hi = boot_ci(u.values)
        w = ivm[(ivm.model == m) & ivm.h.isin(OPH)].wape.mean()
        base = _units(d, "reactive", OPH, "cost_total")
        fr.append(dict(forecaster=m, n_units=len(u), cost=u.mean(), lo=lo, hi=hi, wape=float(w), reactive_cost=base.mean()))
    pd.DataFrame(fr).to_csv(OUT / "comparison_forecasters.csv", index=False)
    return t

def latex_rows(out_dir):
    t = pd.read_csv(OUT / "comparison_table.csv"); a = t[t.scope == "aggregate"].set_index("policy")
    rows = []
    for p in POL[:6] + ["robust_ungated", "oracle"]:
        r = a.loc[p]
        rt_ = "-- " if pd.isna(r.get("route_feas", np.nan)) else f"{100*r.route_feas:.1f} [{100*r.route_feas_lo:.0f}, {100*r.route_feas_hi:.0f}]"
        rows.append(f"{NAME[p]} & {r.cost_total:.2f} [{r.cost_total_lo:.2f}, {r.cost_total_hi:.2f}] & {r.cost_reserve:.2f} & {r.unmet:.2f} & {r.shortage_day_rate:.2f} & {r.n_reserved:.2f} & {rt_} \\\\")
    open(out_dir / "tab_comparison_rows.tex", "w").write("\n".join(rows))
    f = pd.read_csv(OUT / "comparison_forecasters.csv"); nm = {"lr": "Seasonal LR", "hw": "Holt--Winters", "naive": "Weekly naive"}
    open(out_dir / "tab_comparison_fc_rows.tex", "w").write("\n".join(
        f"HCCR + {nm[r.forecaster]} & {100*r.wape:.1f} & {r.cost:.2f} [{r.lo:.2f}, {r.hi:.2f}] & {r.reactive_cost:.2f} \\\\" for r in f.itertuples()))

if __name__ == "__main__":
    import sys; from pathlib import Path
    build(); latex_rows(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
    print("comparison ok")
