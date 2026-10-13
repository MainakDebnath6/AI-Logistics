# Mechanism experiment report (pre-registered; executed)
Pre-registration: `code/research_hccr/mechanism/PREREGISTRATION.md`, SHA-256 `5a86d4ba799fe0efdc7361c3c4ef34cf711004b2351eaa8746b36a2d055da788`, hashed before any mechanism run. Runner reproduces the frozen pipeline's natural-window ungated costs exactly (test `test_runner_natural_cells_match_frozen_pipeline_exactly`).
Data: pilot = 30 simulations (seeds 200-229, planning only, not pooled); confirmatory = 60 fresh simulations (seeds 300-359); AR regime; no exclusions or solver failures.

## Primary contrasts (as pre-registered)
| contrast   |   n_sims |   mean |   ci95_lo |   ci95_hi |   ci975_lo |   ci975_hi |   p_wilcoxon |     dz |   p_holm |
|:-----------|---------:|-------:|----------:|----------:|-----------:|-----------:|-------------:|-------:|---------:|
| Theta_h14  |       60 | 0.0319 |    0.0086 |    0.0546 |     0.0052 |     0.0582 |       0.0058 | 0.3517 |   0.0058 |
| Theta_h28  |       60 | 0.3229 |    0.282  |    0.3651 |     0.2754 |     0.3708 |       0      | 1.9521 |   0      |
Theta_28 is large and robust (d_z 1.95). Theta_14 is statistically detectable but **below the pre-registered 0.10 minimum meaningful effect**.

## Prediction scorecard (predictions fixed before running)
| Prediction | Outcome |
|---|---|
| Theta_14, Theta_28 > 0 (delay + persistence) | **Held** for Theta_28; Theta_14 positive but below MPE |
| Dose-response: Delta_1 falls toward Delta_28 as extra lag L rises (deployable) | **Failed** (see dose table) |
| Fine pool: |Delta| larger and disagreement higher at all h | **Partly**: disagreement much higher; |Delta| not clearly larger; reversal persists |
| W=400 shrinks the h=28 reversal | **Held** (and W=100 enlarges it) |
| Shuffle negative control unchanged | Verified in unit tests (identical multiset/quantiles); not run as a separate experiment |
| h=1 anticipative == natural (sanity) | **Mis-specified**: true for HCCR, false for pooled (its h'>1 windows leak). Theta_1 != 0 by construction |

## Dose-response at h=1 (deployable extra lag applied to BOTH policies)
| extra lag L | phi | Delta_1 [95% CI] |
|---|---|---|
| 0 | 0.95 | +0.294 [+0.258, +0.330] |
| 0 | 0.0 | +0.006 [-0.000, +0.013] |
| 7 | 0.95 | +0.301 [+0.266, +0.338] |
| 7 | 0.0 | +0.006 [-0.000, +0.012] |
| 14 | 0.95 | +0.305 [+0.268, +0.344] |
| 14 | 0.0 | +0.001 [-0.005, +0.007] |
| 28 | 0.95 | +0.314 [+0.275, +0.355] |
| 28 | 0.0 | +0.002 [-0.005, +0.009] |

## Sweeps (phi=0.95, natural window)
| condition | h | Delta [95% CI] | disagreement |
|---|---|---|---|
| W100 | 14 | -0.186 [-0.208, -0.163] | 0.076 |
| W100 | 28 | -0.726 [-0.812, -0.641] | 0.204 |
| W400 | 14 | -0.078 [-0.101, -0.054] | 0.064 |
| W400 | 28 | -0.303 [-0.364, -0.244] | 0.164 |
| finepool | 14 | -0.142 [-0.162, -0.123] | 0.570 |
| finepool | 28 | -0.466 [-0.537, -0.395] | 0.748 |

## Cell means (Delta, disagreement, coverage)
| metric | window | phi | h | mean [95% CI] |
|---|---|---|---|---|
| delta | natural | 0.95 | 1 | +0.294 [+0.258, +0.330] |
| delta | natural | 0.95 | 14 | -0.121 [-0.145, -0.098] |
| delta | natural | 0.95 | 28 | -0.445 [-0.515, -0.373] |
| delta | natural | 0.0 | 1 | +0.006 [-0.000, +0.013] |
| delta | natural | 0.0 | 14 | -0.004 [-0.011, +0.003] |
| delta | natural | 0.0 | 28 | -0.008 [-0.016, -0.001] |
| delta | anticipative | 0.95 | 1 | +0.229 [+0.198, +0.261] |
| delta | anticipative | 0.95 | 14 | -0.096 [-0.119, -0.073] |
| delta | anticipative | 0.95 | 28 | -0.112 [-0.173, -0.054] |
| delta | anticipative | 0.0 | 1 | -0.026 [-0.036, -0.017] |
| delta | anticipative | 0.0 | 14 | -0.011 [-0.020, -0.003] |
| delta | anticipative | 0.0 | 28 | +0.002 [-0.008, +0.011] |
| disagreement | natural | 0.95 | 1 | +0.145 [+0.135, +0.154] |
| disagreement | natural | 0.95 | 14 | +0.068 [+0.063, +0.073] |
| disagreement | natural | 0.95 | 28 | +0.182 [+0.170, +0.195] |
| disagreement | natural | 0.0 | 1 | +0.009 [+0.008, +0.010] |
| disagreement | natural | 0.0 | 14 | +0.008 [+0.007, +0.008] |
| disagreement | natural | 0.0 | 28 | +0.013 [+0.012, +0.014] |
| disagreement | anticipative | 0.95 | 1 | +0.143 [+0.134, +0.153] |
| disagreement | anticipative | 0.95 | 14 | +0.069 [+0.065, +0.074] |
| disagreement | anticipative | 0.95 | 28 | +0.179 [+0.168, +0.191] |
| disagreement | anticipative | 0.0 | 1 | +0.017 [+0.016, +0.018] |
| disagreement | anticipative | 0.0 | 14 | +0.013 [+0.012, +0.014] |
| disagreement | anticipative | 0.0 | 28 | +0.023 [+0.022, +0.024] |
| coverage80_hspec | natural | 0.95 | 1 | +0.791 [+0.789, +0.794] |
| coverage80_hspec | natural | 0.95 | 14 | +0.762 [+0.756, +0.768] |
| coverage80_hspec | natural | 0.95 | 28 | +0.728 [+0.720, +0.736] |
| coverage80_hspec | natural | 0.0 | 1 | +0.793 [+0.791, +0.795] |
| coverage80_hspec | natural | 0.0 | 14 | +0.793 [+0.791, +0.796] |
| coverage80_hspec | natural | 0.0 | 28 | +0.791 [+0.789, +0.794] |
| coverage80_hspec | anticipative | 0.95 | 1 | +0.791 [+0.789, +0.794] |
| coverage80_hspec | anticipative | 0.95 | 14 | +0.776 [+0.771, +0.781] |
| coverage80_hspec | anticipative | 0.95 | 28 | +0.759 [+0.753, +0.765] |
| coverage80_hspec | anticipative | 0.0 | 1 | +0.793 [+0.791, +0.795] |
| coverage80_hspec | anticipative | 0.0 | 14 | +0.793 [+0.791, +0.795] |
| coverage80_hspec | anticipative | 0.0 | 28 | +0.792 [+0.790, +0.794] |

## Residual diagnostics (means over simulations)
|   phi |   h |   resid_autocorr_lag_h |   resid_autocorr_lag1 |   resid_sd |
|------:|----:|-----------------------:|----------------------:|-----------:|
|  0    |   1 |                  0.016 |                 0.016 |     11.04  |
|  0    |   7 |                  0.033 |                 0.011 |     11.046 |
|  0    |  14 |                  0.038 |                 0.012 |     11.05  |
|  0    |  28 |                  0.034 |                 0.016 |     11.075 |
|  0.95 |   1 |                 -0.023 |                -0.023 |      6.722 |
|  0.95 |   7 |                  0.174 |                 0.64  |      9.372 |
|  0.95 |  14 |                  0.256 |                 0.756 |     11.149 |
|  0.95 |  28 |                  0.285 |                 0.819 |     12.892 |
phi=0.95: lag-h residual autocorrelation 0.26-0.29 at h=14,28 and residual sd rising 6.7 -> 12.9 with h; phi=0: autocorrelation ~0.03 and flat sd ~11. Marginal residual scale matches only near h=14: **persistence is confounded with horizon-dependent dispersion** (declared in the pre-registration).

## Interpretation (only what the data support)
1. The h=28 reversal requires persistent residuals (phi=0 gives Delta ~ 0 at all h), subject to the dispersion confound.
2. Giving both policies fresh (non-deployable) calibration data removes most (0.445 -> 0.112) but not all of the reversal.
3. Adding staleness to both policies does not erode HCCR's h=1 advantage; staleness per se is therefore **not** the mechanism. The data fit *relative* freshness (pooled windows include fresh short-horizon residuals), **not tested directly** (next experiment: stale the pooled policy only).
4. Effective sample size matters (W sweep); quantisation explains low disagreement, not the reversal.
5. Disagreement is unchanged by anticipation (0.179 vs 0.182 at h=28) although cost changes sharply: disagreement rate is a poor proxy for cost impact.

## Deviations from the pre-registration (disclosed)
* Holm correction was applied to Wilcoxon p-values of Theta (the pre-registration named Holm but not the test); 95% and 97.5% (Bonferroni) bootstrap CIs are both in `mechanism_confirm_primary.csv`.
* The h=1 sanity statement was wrong for the pooled policy (above).
* N=60 exceeds the rule's minimum (closed-form 8 at h=14 and 24 at h=28 for MPE 0.10 using pilot sd 0.086 and 0.157); chosen because the observed Theta_14 (~0.03) is below the MPE. Detecting 0.03 at 80% power with Bonferroni alpha would need about 77 simulations at the confirmatory sd (0.091); N=60 was adequate in practice (CI excludes 0) but this was not guaranteed in advance.
* Anticipative window rows are non-deployable and excluded from every policy comparison in the paper.
Limitations: one regime family, one forecaster, regions independent, fine pool changes the cost surface.
