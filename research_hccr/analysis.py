"""Paired statistics. Unit of replication = simulation seed (all regions/test days averaged within seed).
Difference convention: delta = cost(comparator) - cost(HCCR); delta > 0 means HCCR is cheaper."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent; OUT = HERE / "results"
CFG = json.load(open(HERE / "configs/study_config.json"))
OPH = CFG["operational_horizons"]

def boot_ci(d, n=CFG["bootstrap_resamples"], seed=CFG["bootstrap_seed"], alpha=0.05):
    rng = np.random.default_rng(seed); d = np.asarray(d, float)
    m = d[rng.integers(0, len(d), (n, len(d)))].mean(1)
    return float(np.quantile(m, alpha / 2)), float(np.quantile(m, 1 - alpha / 2))

def holm(p):
    p = np.asarray(p, float); o = np.argsort(p); adj = np.empty_like(p); run = 0.0
    for rank, i in enumerate(o):
        run = max(run, (len(p) - rank) * p[i]); adj[i] = min(1.0, run)
    return adj

def seed_cost(df, policy, variant, hs, metric="cost_total"):
    s = df[(df.policy == policy) & (df.variant == variant) & (df.h.isin(hs))]
    return s.groupby(["regime", "seed"])[metric].mean()

def paired(df, a, b, hs, metric="cost_total"):
    """a, b = (policy, variant). returns per-regime stats of delta = cost(b) - cost(a)."""
    ca, cb = seed_cost(df, *a, hs, metric), seed_cost(df, *b, hs, metric); rows = []
    for regime in CFG["regimes"]:
        d = (cb - ca).xs(regime, level="regime").sort_index().values
        lo, hi = boot_ci(d)
        try: p = float(stats.wilcoxon(d).pvalue) if np.any(d != 0) else 1.0
        except ValueError: p = 1.0
        ref = seed_cost(df, "reactive", "gated", hs, metric).xs(regime, level="regime").mean()
        rows.append(dict(regime=regime, n=len(d), mean_delta=float(d.mean()), ci_lo=lo, ci_hi=hi, p_wilcoxon=p,
                         dz=float(d.mean() / d.std(ddof=1)) if d.std(ddof=1) > 0 else float("nan"),
                         pct_of_reactive=float(100 * d.mean() / ref), cost_a=float(ca.xs(regime, level="regime").mean()),
                         cost_b=float(cb.xs(regime, level="regime").mean())))
    return rows

def main_tables():
    df = pd.read_csv(OUT / "operational_main.csv")
    H = ("hspec", "gated")
    comps = {"vs_reactive": ("reactive", "gated"), "vs_pooled(B)": ("pooled", "gated"), "vs_point(C)": ("point", "gated"),
             "vs_buffer(D)": ("buffer", "gated"), "vs_ungated(E)": ("hspec", "ungated"), "oracle_gap": ("oracle", "gated")}
    rows = []
    for hs_name, hs in (("h1-7-14", OPH), ("h28", [28])):
        for name, b in comps.items():
            for r in paired(df, H, b, hs): rows.append(dict(horizons=hs_name, comparison=name, **r))
    t = pd.DataFrame(rows)
    # Holm over the 5 confirmatory comparisons x 4 regimes (primary horizons); oracle gap is descriptive
    conf = t[(t.horizons == "h1-7-14") & (t.comparison != "oracle_gap")].copy(); conf["p_holm"] = holm(conf.p_wilcoxon.values)
    t = t.merge(conf[["horizons", "comparison", "regime", "p_holm"]], how="left", on=["horizons", "comparison", "regime"])
    t.to_csv(OUT / "paired_comparisons_main.csv", index=False)
    # absolute levels
    lv = []
    for p in ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"]:
        for regime in CFG["regimes"]:
            s = df[(df.policy == p) & (df.variant == "gated") & (df.h.isin(OPH)) & (df.regime == regime)].groupby("seed")[
                ["cost_total", "cost_reserve", "unmet", "n_reserved", "shortage_day_rate"]].mean()
            lv.append(dict(policy=p, regime=regime, **{k: float(s[k].mean()) for k in s}, **{k + "_sd": float(s[k].std(ddof=1)) for k in s}))
    pd.DataFrame(lv).to_csv(OUT / "policy_levels_main.csv", index=False)
    # per-horizon deltas HCCR vs pooled and vs reactive
    ph = []
    for h in CFG["horizons"]:
        for name, b in (("vs_pooled", ("pooled", "gated")), ("vs_reactive", ("reactive", "gated")), ("vs_point", ("point", "gated"))):
            for r in paired(df, H, b, [h]): ph.append(dict(h=h, comparison=name, **r))
    pd.DataFrame(ph).to_csv(OUT / "paired_by_horizon_main.csv", index=False)
    # gate usage
    g = df[(df.variant == "gated") & (df.policy.isin(["hspec", "pooled", "point", "buffer", "robust"]))].groupby(["regime", "policy", "h"]).gate_open.mean().reset_index()
    g.to_csv(OUT / "gate_open_rate.csv", index=False)
    return t

def interval_table():
    iv = pd.read_csv(OUT / "intervals_main.csv")
    g = iv.groupby(["regime", "h"])[["mae", "wape", "cov_hspec", "cov_pooled", "width_hspec", "width_pooled"]].mean().reset_index()
    sd = iv.groupby(["regime", "h"])[["cov_hspec", "cov_pooled"]].std(ddof=1).add_suffix("_sd").reset_index()
    g = g.merge(sd, on=["regime", "h"]); g.to_csv(OUT / "forecast_calibration_summary.csv", index=False); return g

def models_table():
    main = pd.read_csv(OUT / "operational_main.csv"); mod = pd.read_csv(OUT / "operational_models.csv")
    ns = CFG["n_seeds_forecast_models"]; main = main[main.seed < ns]
    allm = pd.concat([main, mod]); rows = []
    for model in ("naive", "hw", "lr"):
        for regime in CFG["regimes"]:
            s = allm[(allm.model == model) & (allm.regime == regime) & (allm.policy == "hspec") & (allm.variant == "gated") & (allm.h.isin(OPH))]
            r_ = allm[(allm.model == model) & (allm.regime == regime) & (allm.policy == "reactive") & (allm.variant == "gated") & (allm.h.isin(OPH))]
            rows.append(dict(model=model, regime=regime, cost_hspec=float(s.groupby("seed").cost_total.mean().mean()),
                             cost_reactive=float(r_.groupby("seed").cost_total.mean().mean())))
    ivm = pd.concat([pd.read_csv(OUT / "intervals_main.csv").query("seed < @ns"), pd.read_csv(OUT / "intervals_models.csv")])
    f = ivm[ivm.h.isin(OPH)].groupby(["model", "regime"])[["mae", "wape"]].mean().reset_index()
    t = pd.DataFrame(rows).merge(f, on=["model", "regime"]); t.to_csv(OUT / "forecast_model_ablation.csv", index=False)
    # paired: HCCR(lr) vs HCCR(model), per regime
    d_rows = []
    for regime in CFG["regimes"]:
        c = {m: allm[(allm.model == m) & (allm.regime == regime) & (allm.policy == "hspec") & (allm.variant == "gated") & (allm.h.isin(OPH))].groupby("seed").cost_total.mean().sort_index() for m in ("naive", "hw", "lr")}
        for m in ("naive", "hw"):
            d = (c[m] - c["lr"]).values; lo, hi = boot_ci(d)
            d_rows.append(dict(regime=regime, comparison=f"{m}-lr", n=len(d), mean_delta=float(d.mean()), ci_lo=lo, ci_hi=hi))
    pd.DataFrame(d_rows).to_csv(OUT / "forecast_model_paired.csv", index=False)
    return t

def sensitivity_table():
    s = pd.read_csv(OUT / "operational_sensitivity.csv"); main = pd.read_csv(OUT / "operational_main.csv")
    main = main[main.seed < 15].assign(param="primary", value=0.0)
    allx = pd.concat([s, main]); rows = []
    for (param, value), g in allx.groupby(["param", "value"]):
        for regime in CFG["regimes"] + ["ALL"]:
            gg = g if regime == "ALL" else g[g.regime == regime]
            def c(pol, var="gated"):
                return gg[(gg.policy == pol) & (gg.variant == var) & (gg.h.isin(OPH))].groupby(["regime", "seed"]).cost_total.mean().sort_index()
            h, po, re_, pt, ug = c("hspec"), c("pooled"), c("reactive"), c("point"), c("hspec", "ungated")
            for nm, other in (("pooled", po), ("reactive", re_), ("point", pt), ("ungated", ug)):
                d = (other - h).values; lo, hi = boot_ci(d)
                rows.append(dict(param=param, value=value, regime=regime, comparator=nm, n=len(d), mean_delta=float(d.mean()), ci_lo=lo, ci_hi=hi,
                                 cost_hspec=float(h.mean()), cost_reactive=float(re_.mean())))
    t = pd.DataFrame(rows); t.to_csv(OUT / "sensitivity_summary.csv", index=False); return t

def routing_table():
    r = pd.read_csv(OUT / "routing_instances.csv"); rows = []
    for p in ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"]:
        g = r[r.policy == p]
        by_seed = g.groupby(["regime", "seed"]).feasible.mean()
        lo, hi = boot_ci(by_seed.values)
        rows.append(dict(policy=p, n_instances=len(g), feasibility_rate=float(g.feasible.mean()), feas_ci_lo=lo, feas_ci_hi=hi,
                         agg_unmet_instances=float((g.aggregate_unmet > 0).mean()),
                         mean_reserve_cost=float(g.reserve_cost.mean()), mean_n_activated=float(g.n_activated.mean()),
                         mean_distance_feasible_km=float(g[g.feasible].distance_km.mean()), runtime_s=float(g.runtime_s.mean())))
    t = pd.DataFrame(rows)
    # matched distance: instances feasible under ALL policies
    pv = r.pivot_table(index=["regime", "seed", "instance"], columns="policy", values="feasible", aggfunc="first")
    allf = pv.all(axis=1); idx = allf[allf].index
    dm = r.set_index(["regime", "seed", "instance"]).loc[idx].reset_index().groupby("policy").distance_km.mean()
    t["matched_distance_km"] = t.policy.map(dm); t["n_matched"] = len(idx)
    # aggregate-capacity-feasible but routing-infeasible
    gap = r[(r.aggregate_unmet == 0) & (~r.feasible) & (r.confirmed_demand <= r.fleet_capacity)]
    t.attrs["gap"] = len(gap)
    t.to_csv(OUT / "routing_summary.csv", index=False)
    gaps = pd.DataFrame(dict(policy=r.policy, agg_ok=(r.confirmed_demand <= r.fleet_capacity), feasible=r.feasible)).groupby("policy").apply(
        lambda g: pd.Series(dict(n_agg_ok=int(g.agg_ok.sum()), routing_infeasible_despite_agg_ok=int((g.agg_ok & ~g.feasible).sum()))), include_groups=False)
    gaps.to_csv(OUT / "routing_capacity_vs_feasibility.csv")
    # paired feasibility difference vs reactive
    rows2 = []
    for p in ["point", "buffer", "pooled", "hspec", "robust", "oracle"]:
        a = r[r.policy == p].set_index(["regime", "seed", "instance"]).feasible.astype(float)
        b = r[r.policy == "reactive"].set_index(["regime", "seed", "instance"]).feasible.astype(float)
        d = (a - b).groupby(["regime", "seed"]).mean().values; lo, hi = boot_ci(d)
        rows2.append(dict(policy=p, mean_feas_gain_vs_reactive=float(d.mean()), ci_lo=lo, ci_hi=hi))
    pd.DataFrame(rows2).to_csv(OUT / "routing_paired_vs_reactive.csv", index=False)
    return t

if __name__ == "__main__":
    import sys
    for fn in (main_tables, interval_table, models_table, sensitivity_table, routing_table):
        try: fn(); print(fn.__name__, "ok")
        except FileNotFoundError as e: print(fn.__name__, "skipped:", e.filename)
