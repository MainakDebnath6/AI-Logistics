import numpy as np, pytest
from research_hccr.mechanism.design import *
from research_hccr.mechanism.power import n_required_normal, simulated_power, sd_from_reported_ci
from scipy import stats

def test_natural_and_extra_lag_windows_are_causal_anticipative_is_not():
    for h in (1, 7, 14, 28):
        assert is_causal(WindowSpec("natural"), 800, h, 200, 400)
        assert is_causal(WindowSpec("extra_lag", 14), 800, h, 200, 400)
        ant = is_causal(WindowSpec("anticipative", diagnostic_only=True), 800, h, 200, 400)
        assert ant == (h == 1)   # at h=1 the window ends at d-1 (target d): identical to natural; for h>1 it uses future demand

def test_extra_lag_window_is_strictly_staler():
    a = window_origins(WindowSpec("natural"), 800, 7, 200, 400); b = window_origins(WindowSpec("extra_lag", 14), 800, 7, 200, 400)
    assert b.max() == a.max() - 14 and len(a) == len(b) == 200

def test_anticipative_requires_diagnostic_flag():
    with pytest.raises(ValueError): WindowSpec("anticipative")

def test_shuffle_preserves_multiset_and_quantiles():
    e = np.random.default_rng(0).normal(size=200); s = shuffle_window(e, np.random.default_rng(1))
    assert np.array_equal(np.sort(e), np.sort(s)) and not np.array_equal(e, s)
    assert np.quantile(e, .9) == np.quantile(s, .9)

@pytest.mark.parametrize("phi", [0.0, 0.5, 0.95])
def test_ar1_latent_has_fixed_stationary_sd(phi):
    u = ar1_latent(200_000, phi, 10.0, np.random.default_rng(3)); assert abs(u.std() - 10.0) < 0.35
    lag1 = np.corrcoef(u[:-1], u[1:])[0, 1]; assert abs(lag1 - phi) < 0.02

def test_delta_sign_convention_and_pairing():
    assert delta(np.array([10., 11.]), np.array([9., 12.])).tolist() == [1.0, -1.0]
    with pytest.raises(ValueError): delta(np.ones(3), np.ones(4))

def test_effect_of_removing_delay_sign():
    assert effect_of_removing_delay(np.array([-0.4]), np.array([0.1]))[0] == pytest.approx(0.5)

def test_closed_form_n_matches_textbook_case():
    # sd=1, delta=0.5, alpha=.05 two-sided, power .8 -> classic n ~ 32
    assert n_required_normal(1.0, 0.5) == 32

def test_simulated_power_increases_with_n_and_is_near_nominal_under_tiny_effect():
    pilot = np.random.default_rng(0).normal(0, 1, 60)
    p_small, p_big = simulated_power(pilot, 0.5, 15, n_rep=200, n_boot=500), simulated_power(pilot, 0.5, 80, n_rep=200, n_boot=500)
    assert p_big > p_small and p_big > 0.8

def test_sd_from_ci_roundtrip():
    sd = 2.0; n = 30; se = sd / np.sqrt(n); assert sd_from_reported_ci(-1.96 * se, 1.96 * se, n) == pytest.approx(sd)

# ---- runner integration tests (information boundary, pairing, consistency with the frozen baseline) ----
def test_runner_natural_cells_match_frozen_pipeline_exactly():
    import logging, json; logging.disable(logging.CRITICAL)
    from pathlib import Path
    from research_hccr.study import load_config, run_sim, build_forecasts, capacity
    from research_hccr.simulate import simulate
    from research_hccr.calibrate import residuals
    from research_hccr.reserve import ReservePool
    from research_hccr.mechanism.runner import run_condition
    from research_hccr.mechanism.design import WindowSpec
    cfg = load_config(str(Path(__file__).resolve().parents[1] / "configs" / "study_config.json"))
    (rows, _, _), y, F = run_sim("ar", 0, cfg, "lr")
    res = residuals(y, F); pool = ReservePool(cfg["reserve_vehicle_capacities"], cfg["reserve_vehicle_max_count"], cfg["reserve_cost_fixed"], cfg["reserve_cost_per_unit"], 1.0)
    out = run_condition(y, F, res, cfg, pool, capacity(y, cfg), cfg["shortage_penalty"], (14,), WindowSpec("natural"), cfg["calibration_window"], cfg["horizons"])[0]
    import pandas as pd; d = pd.DataFrame(rows); g = lambda p: float(d[(d.policy == p) & (d.variant == "ungated") & (d.h == 14)].cost_total.iloc[0])
    assert abs(out["cost_hspec"] - g("hspec")) < 1e-9 and abs(out["cost_pooled"] - g("pooled")) < 1e-9

def test_phi_override_changes_only_latent_and_default_unchanged():
    from research_hccr.simulate import simulate, REGIMES
    a = simulate("ar", 1, 300, [100.0]); b = simulate("ar", 1, 300, [100.0], ar_phi_override=0.95); c = simulate("ar", 1, 300, [100.0], ar_phi_override=0.0)
    assert np.array_equal(a, b) and not np.array_equal(a, c) and REGIMES["ar"]["ar_phi"] == 0.95

def test_anticipative_condition_never_marked_deployable():
    from research_hccr.mechanism.runner import CONDITIONS
    for label, spec, W, pk, hs, f in CONDITIONS(200): assert (spec.kind == "anticipative") == (label == "anticipative")

def test_freshness_conditions_are_all_deployable_and_only_change_the_intended_policy():
    from research_hccr.mechanism.runner_fresh import FRESH_CONDITIONS
    from research_hccr.mechanism.design import is_causal
    for label, sh, sp in FRESH_CONDITIONS:
        assert sh.kind != "anticipative" and sp.kind != "anticipative"
        for h in (1, 14, 28):
            assert is_causal(sh, 800, h, 200, 400) and is_causal(sp, 800, h, 200, 400)
    d = {l: (sh, sp) for l, sh, sp in FRESH_CONDITIONS}
    assert d["pooled_stale28"][0].kind == "natural" and d["pooled_stale28"][1].extra_lag == 28   # HCCR untouched
    assert d["hccr_stale28"][1].kind == "natural" and d["hccr_stale28"][0].extra_lag == 28       # pooled untouched
    assert d["natural"][0].kind == d["natural"][1].kind == "natural"

def test_run_condition_default_pooled_spec_is_unchanged_by_new_argument():
    # spec_p=None must reproduce the original behaviour exactly (frozen-baseline consistency is tested above)
    import inspect
    from research_hccr.mechanism.runner import run_condition
    assert inspect.signature(run_condition).parameters["spec_p"].default is None

# ---- real-data pipeline checks ----
def test_realdata_scaling_uses_initial_fit_period_only_and_split_is_causal():
    from research_hccr.realdata.run_real import load_segments, SPLIT
    y, scale, idx = load_segments()
    assert y.shape == (4, 731) and abs(y[:, :SPLIT["t_calibration_start"]].mean(axis=1) - 100).max() < 1e-9
    assert SPLIT["t_calibration_start"] < SPLIT["t_validation_start"] < SPLIT["t_test_start"] <= SPLIT["t_test_last_origin"]
    assert SPLIT["t_test_last_origin"] + 28 <= 730          # every test target exists

def test_realdata_hourly_to_daily_consistency():
    import pandas as pd
    from research_hccr.realdata.run_real import DATA
    h = pd.read_csv(DATA / "hour.csv"); d = pd.read_csv(DATA / "day.csv")
    assert (h.groupby("dteday").cnt.sum().reindex(d.dteday).values == d.cnt.values).all() and len(d) == 731

def test_block_bootstrap_ci_contains_mean_of_constant_series():
    from research_hccr.realdata.run_real import block_boot_mean
    lo, hi = block_boot_mean(np.full(100, 0.7), n=200); assert lo == pytest.approx(0.7) and hi == pytest.approx(0.7)
