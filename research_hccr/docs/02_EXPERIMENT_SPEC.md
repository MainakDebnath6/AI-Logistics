# 02 Proposed experiment: why does HCCR lose to pooling at h = 14, 28 under AR shocks?
**STATUS: DESIGN ONLY. No part of this experiment has been run; no results are reported.** Scaffold: `code/research_hccr/mechanism/` (design.py, power.py, plot_spec.py) with 12 unit tests (pass). The scaffold contains no data and no results.

## 1. Estimand (paper's sign convention)
Delta_{r,h} = C_pooled - C_HCCR (positive = HCCR cheaper), computed per simulation (seed), paired by common random numbers.
Because delay and information are inseparable under autocorrelation, the identifying contrast is an **interaction**:
Theta_h = [Delta_h(anticipative window) - Delta_h(natural window)] at phi=0.95 minus the same quantity at phi=0 (AR regime, h in {14, 28} estimated **separately**, no pooling across horizons; Holm over the two).
Reading: Theta_h > 0 means removing the staleness helps HCCR specifically when residuals are serially correlated.

## 2. Factors
* **A. Window timing (calibration information set).** `natural` (window ends d-h; deployable). `extra_lag L` in {7,14,28} (window ends d-h-L; deployable, strictly staler; dose-response). `anticipative` (window ends d-1; targets reach d-1+h > d for h>1; **non-deployable, diagnostic upper bound only**; `WindowSpec` refuses to construct it without `diagnostic_only=True`). At h=1 the anticipative window equals the natural one (tested), so h=1 is a built-in sanity check (Theta_1 = 0 by construction).
* **B. Latent persistence phi in {0.95 (original), 0.5, 0}** with stationary sd of the latent fixed (`ar1_latent`; tested). Held fixed: marginal latent scale, iid noise, seasonality, costs, fleet, window length W, scenario count, policies. **Cannot be held fixed:** the horizon profile of forecast-error dispersion (it depends on phi) and residual tail shape after the forecaster adapts. This confound is declared; report sd(e_28)/sd(e_1), lag-h residual autocorrelation and kurtosis per cell as covariates.
* **C. Horizon h in {1, 7, 14, 28}** (h=1 positive control for sign; primary h in {14,28}).
* Common random numbers: same underlying normal draws across cells; the unit is the simulation (seed), as in the paper. Regions and days are averaged inside it. Seeds are paired replicates, not randomised subjects.

## 3. Competing explanations and discriminating one-factor sweeps (AR, phi=0.95, natural window)
| Hypothesis | Manipulation | Expected change in Delta if TRUE | If alternative TRUE | If effect absent | Remaining ambiguity |
|---|---|---|---|---|---|
| H-delay: staleness of the h-day-old window drives the reversal | extra_lag L at h=1 (and anticipative at h=14,28) | Delta(h=1) falls toward Delta(h=28) as L rises (monotone dose-response); anticipative removes the negative sign at h=14,28 | Under quantization/sample-size alternatives, no dose-response beyond noise | Staleness is not the driver (or the AR information is not in the residual level) | Anticipative also adds information about the near-future target; only interpretable via the phi interaction |
| H-autocorr: serial dependence makes stale residuals misleading | phi in {0.95,0.5,0}; Theta interaction | Theta_h larger at phi=0.95 than 0; reversal shrinks with phi | If reversal persists at phi=0 -> not autocorrelation | Reversal not due to persistence | phi also changes dispersion growth (declared confound); no clear directional prediction for phi=0.5 beyond monotonicity |
| Alt-1 discrete quantization | Replace 27-set pool by a fine pool (e.g., capacities {1,2,4,8,16,32}, up to 2 each) | |Delta| grows at ALL horizons incl. h=1; disagreement rate rises | Delay/autocorr predict reversal remains, same sign | Quantization is not the main reason effects are small | Fine pool changes the cost surface too |
| Alt-2 finite-sample / effective n | W in {100,200,400} | Larger W shrinks the reversal at h=28 (pooled has 4x more residuals) | Under H-delay, W matters little because windows are equally stale | Sample size not the driver | Larger W also mixes older regimes |
| Alt-3 bias/tail mismatch | Centre the window residuals (subtract window mean) in both policies | Reversal shrinks if stale *bias* (not dispersion) is the problem | Delay/autocorr: little change if the problem is tail scale | Bias not the driver | Centering changes quantile estimates |
| Negative control | Shuffle residual order inside the window (`shuffle_window`) | **Delta unchanged** (same empirical set; quantiles identical, tested) | n/a | A change would indicate an implementation bug | none |
Predictions are directional only where stated; otherwise "no clear directional prediction".

## 4. Outcomes, tests, multiplicity
Primary: Theta_14, Theta_28 (paired per-simulation, percentile bootstrap 95% CI over simulations, 10,000 resamples; Holm over 2). Secondary (exploratory, uncorrected, labelled so): dose-response slope of Delta_1 in L; Delta by phi; disagreement rate; coverage; reserve cost and unmet demand separately; routing not required. Wilcoxon only as a sensitivity check on Theta, never to claim equivalence. Planned plot: `mechanism/plot_spec.py` (x = window kind x phi, y = Delta with bootstrap CI, one panel per h, non-deployable conditions drawn with a different marker). Expected pattern under H-delay+H-autocorr: anticipative marker lifts above zero only at phi=0.95 and h in {14,28}; under quantization all points hug zero at every h; under sample-size a W-dependent shift.
Threats to identification: anticipative window is leakage by design; phi confounded with dispersion; CRN pairing across phi is imperfect; single forecaster family; regions independent.
Exclusion/stopping: exclude a simulation only for solver/numerical failure (log it, report counts); no peeking; sample size fixed by the pilot rule below.

## 5. Seed count (cannot be fixed reliably from the PDF)
The PDF reports only rounded bootstrap CIs (no per-seed paired variance). Planning inference: AR Delta h=14 -0.12 [-0.15,-0.10], h=28 -0.42 [-0.56,-0.29], n=30 -> implied per-simulation sd approx 0.070 and 0.377 (imprecise: sd = half-width/1.96*sqrt(n)). Minimum practically meaningful effect for Theta is a **design choice**, not an observation: candidates 0.05, 0.10, 0.20 cost units. Test: two-sided alpha=0.05, Holm over 2 (Bonferroni approximation), power 0.80, contrast Theta (four cells, equal variance sigma^2, pairwise correlation rho): sd_Theta = 2 sigma sqrt(1-rho).
Required simulations per cell (`power.n_required_normal`):

| horizon | rho | sd_Theta | n @ 0.05 | n @ 0.10 | n @ 0.20 |
|---|---|---|---|---|---|
| h=14 | 0.0 | 0.140 | 75 | 19 | 5 |
| h=14 | 0.5 | 0.099 | 38 | 10 | 3 |
| h=14 | 0.8 | 0.063 | 15 | 4 | 1 |
| h=28 | 0.0 | 0.754 | 2162 | 541 | 136 |
| h=28 | 0.5 | 0.533 | 1081 | 271 | 68 |
| h=28 | 0.8 | 0.337 | 433 | 109 | 28 |

**Recommendation:** run a 50-simulation pilot per cell, estimate the paired sd of Theta directly, then recompute with `power.simulated_power` (bootstrap on the pilot's actual paired differences) and fix N before the confirmatory run. As a planning ceiling, budget about 300 simulations per cell for h=28 (heavy-tailed variability) and 50 for h=14; this is a budget, not a justified count. The current 30 seeds are not shown to be sufficient for these contrasts.

## 6. Data schema for the runner (to be implemented)
`sim_id, seed, regime, horizon, window_kind, extra_lag, phi, W, pool, policy, cost_total, cost_reserve, unmet, n_reserved, disagreement_rate, coverage80, deployable` (one row per simulation x condition x policy). Deployable=False for anticipative rows; these must never be aggregated into policy comparisons.

## 7. Unit tests already in place (`tests/test_mechanism.py`)
natural/extra-lag windows causal; anticipative causal only at h=1; staler windows; flag required; shuffle preserves multiset and quantiles; AR(1) stationary sd and lag-1 correlation; delta sign and pairing; textbook n=32 case; simulated power increases with n; sd-from-CI round trip.
