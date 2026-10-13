"""One-command reproduction:  python -m research_hccr.run_study --stage all   (from the repository root).

Stages: main | models | sensitivity | routing | stats   (each writes CSV/JSON under research_hccr/results/).
"""
from __future__ import annotations
import argparse, copy, json, logging, time
from pathlib import Path
import numpy as np, pandas as pd

logging.disable(logging.CRITICAL)
HERE = Path(__file__).resolve().parent
OUT = HERE / "results"; OUT.mkdir(exist_ok=True)

from .study import load_config, run_sim, evaluate, make_pool
from .simulate import simulate

PARTS = OUT / "parts"; PARTS.mkdir(exist_ok=True)

def _part(stage, regime, fn, only=None):
    """Compute one (stage, regime) chunk once; reuse the checkpoint on re-runs (resumable)."""
    p = PARTS / f"{stage}_{regime}.pkl"
    if only and regime not in only: return None
    if p.exists(): return pd.read_pickle(p)
    res = fn(); pd.to_pickle(res, p); print(stage, regime, "computed", flush=True); return res

def _collect(stage, cfg, name_map):
    out = {k: [] for k in name_map}
    for regime in cfg["regimes"]:
        p = PARTS / f"{stage}_{regime}.pkl"
        if not p.exists(): return False
        res = pd.read_pickle(p)
        for k in name_map: out[k].append(res[k])
    for k, fname in name_map.items(): pd.concat(out[k]).to_csv(OUT / fname, index=False)
    return True

def stage_main(cfg, only=None):
    def one(regime):
        ops, ints = [], []
        for seed in range(cfg["n_seeds_main"]):
            (rows, iv, _), _, _ = run_sim(regime, seed, cfg, "lr"); ops += rows; ints += iv
        return dict(ops=pd.DataFrame(ops), ints=pd.DataFrame(ints))
    for r in cfg["regimes"]: _part("main", r, lambda r=r: one(r), only)
    _collect("main", cfg, dict(ops="operational_main.csv", ints="intervals_main.csv"))

def _seed_parts(stage, cfg, n, one, only=None):
    """Resumable at (regime, seed) granularity. one(regime, seed) -> dict of DataFrames."""
    for regime in cfg["regimes"]:
        if only and regime not in only: continue
        for seed in range(n):
            p = PARTS / f"{stage}_{regime}_{seed}.pkl"
            if not p.exists():
                pd.to_pickle(one(regime, seed), p)
        print(stage, regime, "complete", flush=True)

def _collect_seeds(stage, cfg, n, name_map):
    out = {k: [] for k in name_map}
    for regime in cfg["regimes"]:
        for seed in range(n):
            p = PARTS / f"{stage}_{regime}_{seed}.pkl"
            if not p.exists(): return False
            res = pd.read_pickle(p)
            for k in name_map: out[k].append(res[k])
    for k, fname in name_map.items(): pd.concat(out[k]).to_csv(OUT / fname, index=False)
    return True

def stage_models(cfg, only=None):
    n = cfg["n_seeds_forecast_models"]
    def one(regime, seed):
        ops, ints = [], []
        for model in ("naive", "hw"):
            (rows, iv, _), _, _ = run_sim(regime, seed, cfg, model); ops += rows; ints += iv
        return dict(ops=pd.DataFrame(ops), ints=pd.DataFrame(ints))
    _seed_parts("models", cfg, n, one, only)
    _collect_seeds("models", cfg, n, dict(ops="operational_models.csv", ints="intervals_models.csv"))

def stage_sensitivity(cfg, only=None):
    from .study import build_forecasts
    sens = cfg["sensitivity"]; n = 15
    def one(regime, seed):
        ops = []
        y = simulate(regime, seed, cfg["T"], cfg["region_levels"]); F = build_forecasts(y, cfg, "lr")
        for param, vals in sens.items():
            for v in vals:
                c = copy.deepcopy(cfg); c[param] = v
                rows, _, _ = evaluate(y, F, c, dict(regime=regime, seed=seed, model="lr", noise_scale=1.0, param=param, value=v)); ops += rows
        for ns in (0.5, 2.0):
            (rows, _, _), _, _ = run_sim(regime, seed, cfg, "lr", noise_scale=ns, tag_extra=dict(param="noise_scale", value=ns)); ops += rows
        return dict(ops=pd.DataFrame(ops))
    _seed_parts("sens", cfg, n, one, only)
    _collect_seeds("sens", cfg, n, dict(ops="operational_sensitivity.csv"))

def stage_routing(cfg, only=None):
    from . import routing_eval as RE
    rc = cfg["routing"]; pool = make_pool(cfg)
    policies = ["reactive", "point", "buffer", "pooled", "hspec", "robust", "oracle"]; H = rc["horizon"]
    def one(regime, seed):
        out = []; cache = {}
        (_, _, dec), y, _ = run_sim(regime, seed, cfg, "lr", keep_decisions=True)
        rng = np.random.default_rng(np.random.SeedSequence([seed, 99, list(cfg["regimes"]).index(regime)]))
        test = dec["test"]; R = y.shape[0]
        picks = [(int(rng.integers(R)), int(rng.choice(test))) for _ in range(rc["instances_per_seed"])]   # random, outcome-blind
        for k, (r, o) in enumerate(picks):
            D = int(round(y[r, o + H])); A = int(dec["A"][r])
            sizes, coords = RE.make_orders(D, np.random.default_rng(np.random.SeedSequence([seed, k, 7])), rc)
            base = RE.base_fleet_caps(A, rc["base_vehicle_max_capacity"])
            for p in policies:
                s = int(dec["S"][p][H][r, o]); counts = pool.counts[s]
                reserved = [q for n_, q in zip(counts, cfg["reserve_vehicle_capacities"]) for _ in range(n_)]
                active = RE.activate_reserved(base, reserved, D); fleet = base + active
                key = tuple(sorted(fleet)) + (k,)
                if key not in cache:
                    cache[key] = RE.solve_confirmed_orders(sizes, coords, fleet, rc, key=f"{regime}-{seed}-{k}")
                res = cache[key]
                out.append(dict(regime=regime, seed=seed, instance=k, region=r, origin=o, confirmed_demand=D, base_capacity=A,
                                policy=p, n_reserved=int(sum(counts)), reserve_cost=float(pool.cost[s]),
                                n_activated=len(active), fleet_capacity=int(sum(fleet)),
                                aggregate_unmet=float(max(D - A - pool.cap[s], 0.0)),
                                feasible=res["feasible"], distance_km=res["distance_km"], runtime_s=res["runtime_s"],
                                served=res["served"], requested=res["requested"], reason=res["reason"]))
        return dict(ops=pd.DataFrame(out))
    _seed_parts("routing", cfg, rc["n_seeds"], one, only)
    _collect_seeds("routing", cfg, rc["n_seeds"], dict(ops="routing_instances.csv"))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", default="all"); ap.add_argument("--config", default=str(HERE / "configs/study_config.json")); ap.add_argument("--regime", default=None)
    a = ap.parse_args(); cfg = load_config(a.config)
    (OUT / "config_used.json").write_text(json.dumps(cfg, indent=2))
    t0 = time.time()
    for name, fn in (("main", stage_main), ("models", stage_models), ("sensitivity", stage_sensitivity), ("routing", stage_routing)):
        if a.stage in ("all", name):
            fn(cfg, only=[a.regime] if a.regime else None); print(f"[{name}] {time.time()-t0:.0f}s elapsed", flush=True)
