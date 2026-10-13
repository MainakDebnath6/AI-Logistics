# Audit of the uploaded AI-Logistics research package

All findings below were obtained by extracting the archives into a scratch directory and executing the code.
**The uploaded files were never modified** (SHA-256 of each upload is in `original_hashes.txt`).

## 1. What the uploads contain
| Upload | Finding |
|---|---|
| `AI-Logistics-master.zip` | Full application repo (FastAPI backend, React frontend, Alembic/PostgreSQL schema, `experiments/`, `data/raw/synthetic_demand.csv`, 83 backend tests). |
| `AI-Logistics-Research-Package.zip` | The repo's `experiments/` folder, `synthetic_demand.csv`, and result CSV/JSON files, flattened. **Identical to the repo copy after normalising CRLF line endings** (all five scripts, seven CSVs, all JSON artifacts). No independent experiment. |
| `Forecast_Aware_Logistics_Route_Optimization2.pdf` | The 2-column manuscript (reports MAPE 8.02 % / 3.24 %, "HGFCI proposed, not wired"). |

Dataset: `synthetic_demand.csv`, 730 rows, 2024-01-01..2025-12-30, single column `demand` (mean 114.9, sd 21.3, min 62.4, max 168.8, no zeros, no duplicate dates), flag `data_type = synthetic`. It is **aggregate daily demand — not regional and not order-level**. `data-1791525942039.csv` and the PostgreSQL schema were treated as application artefacts, not research observations.

## 2. Reproduction of the shipped artifacts
`python -m experiments.run_all` was run in an isolated copy (Python 3.12, OR-Tools, scikit-learn, statsmodels installed fresh).
* Synthetic data regenerated: max |difference| = 0.
* `forecast_models`, `feature_ablation`, `horizon_sensitivity`, `hgfc_advisory`: **bit-identical**.
* `cvrp_benchmark`, `reactive_vs_hgfc`: identical except solver wall-clock time (<= 2 ms).
* `forecast_raw_predictions`: identical (only NaN string formatting differs).
* Repo tests: 82 passed, 1 failed. The failure is environmental (`passlib` + newer `bcrypt` in my sandbox, "password longer than 72 bytes"); it is unrelated to the research code.

So the repo's *own* results are reproducible. Splits: 670 train / 60 test, seed 20261008, rolling-origin horizons 1/7/14/30/60.

## 3. Discrepancies and defects (none overwritten; all reported)
1. **PDF Table II does not reproduce.** PDF: naive 21.29 %, Holt-Winters 12.48 %, seasonal LR 8.02 % (60-day MAPE). Repo code/seed: naive 10.93 %, HW 13.96 %, LR 4.11 %. I swept 40 seeds with the repo's own implementation: LR 60-day MAPE spans 2.95-6.20 % and naive 7.86-13.75 %. **8.02 % (LR) and 21.29 % (naive) are outside the range the repo's code can produce**, so the PDF numbers came from an unrecorded different setup (the PDF itself says the seed was not recorded). Treat them as unverified.
2. **The "error grows with horizon" claim is a design artifact.** PDF: MAPE 3.24 % (7 d) -> 8.02 % (60 d). That pattern is consistent with reading prefixes of one 60-day forecast from a single origin. Under the repo's own rolling-origin evaluation (`horizon_sensitivity.csv`), seasonal-LR MAE is essentially flat in horizon: 4.58 / 4.71 / 4.79 / 4.55 at h = 7 / 14 / 30 / 60 (MAPE 4.14-4.32 %). On this data-generating process there is no horizon effect to justify a 14-day gate.
3. **The manuscript's status claims are out of date.** The PDF says HGFCI is "proposed, not wired in". The repo contains `backend/app/services/hgfc_service.py` and schemas (an advisory-only capacity-risk service) and an `experiments/reactive_vs_hgfc` artifact.
4. **`reactive_vs_hgfc` is not a comparison.** Both arms reuse the same confirmed-order solve, so every difference is zero by construction.
5. **Failed routes recorded as zeros.** `cvrp_benchmark.csv` stores infeasible instances (4 of 6 scenarios; demand > fleet capacity of 100) with distance 0 and service level 0, and averages them in. This violates the rule never to substitute zero distance/cost for failed routes. Only 2 of 6 scenarios are feasible (distances 868.0 and 865.7 km); the other four are stored as 0.0 distance / 0 % service.
6. **Different experimental setups** are mixed in the PDF (Table II vs Table III use different seeds, acknowledged by the authors).
7. **Aggregate-capacity feasibility is not routing feasibility.** My probe found demand 125 with exactly 125 units of fleet capacity returns "No feasible optimization solution" from the repo's CVRP service (first-solution heuristic, indivisible orders). Capacity-level shortfall therefore understates routing infeasibility; the new study reports both.

## 4. Consequence for the research design
The shipped data cannot support the proposed research question (single aggregate series; no regions; no orders; no horizon-dependent error). I therefore built a transparent multi-region simulator (`research_hccr/simulate.py`) with four pre-declared regimes, one of which deliberately has horizon-invariant error as a null control. All results are simulation-based.
