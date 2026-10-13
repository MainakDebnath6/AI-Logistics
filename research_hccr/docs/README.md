# Horizon-calibrated advance fleet reservation: simulation study (reproducibility README)

Everything here is **simulation-based**. No real order data were used.

## Layout
* `paper/` main.tex, references.bib, main.pdf (5 pages, IEEEtran conference), assets/ (figure + table fragments generated from results).
* `code/research_hccr/` the research module (simulator, forecasters, causal calibration, policies, routing stage, statistics, tests, frozen config, result CSVs).
* `docs/` AUDIT_REPORT.md (uploaded package audit), NOVELTY_AUDIT.md, FINAL_CHECKLIST.md, original_hashes.txt, seed sweep.

## Install
Place `code/research_hccr/` at the root of the AI-Logistics repository (next to `backend/`, `experiments/`); it imports the repo's unmodified `RouteOptimizerService`. No existing repo file is changed.
`pip install ortools scikit-learn statsmodels pandas scipy numpy matplotlib pytest` plus the backend requirements (`pydantic`, `sqlalchemy`, `fastapi`, `passlib`, `bcrypt`, `psycopg[binary]`, ...).
Versions used: Python 3.12.3, numpy 2.4.4, pandas 3.0.2, scipy 1.17.1, statsmodels 0.15.0, OR-Tools 9.15.6755.

## Run
```
python -m pytest research_hccr/tests -q            # 13 invariant tests (no look-ahead, accounting, firewall)
python -m research_hccr.run_study --stage all      # main | models | sensitivity | routing; resumable (results/parts/)
python -m research_hccr.analysis                   # paired statistics -> results/*.csv
python -m research_hccr.comparison paper/assets    # consolidated comparison table
python -m research_hccr.diagnostics                # HCCR-vs-pooled decision disagreement
python -m research_hccr.replication                # independent-seed replication (seeds 100-129)
python -m research_hccr.verify_claims              # checks every number quoted in the paper text vs the CSVs
python -m research_hccr.make_assets paper/assets   # figure + LaTeX table fragments
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```
Single-core wall time was roughly 5 min (main), 15-20 min (sensitivity), 15 min (Holt-Winters ablation), 3 min (routing). Config: `configs/study_config.json` (frozen before any test result was inspected). Seeds: 0-29 per regime (main), 0-9 (forecaster ablation, routing), 0-14 (sensitivity).
Determinism check: regenerating regime=drift, seed=7 matched the stored CSV to 1.8e-15.

## Key result files (`results/`)
operational_main.csv, intervals_main.csv, paired_comparisons_main.csv, paired_by_horizon_main.csv, policy_levels_main.csv, gate_open_rate.csv, forecast_calibration_summary.csv, operational_models.csv, forecast_model_ablation.csv, forecast_model_paired.csv, operational_sensitivity.csv, sensitivity_summary.csv, routing_instances.csv, routing_summary.csv, routing_paired_vs_reactive.csv, routing_capacity_vs_feasibility.csv, config_used.json.

## Method states (kept separate)
reserved (forecast-driven, cost paid) -> activated (dispatcher rule using confirmed demand only) -> routed (existing CVRP on confirmed orders).

## Priority revision additions
python -m research_hccr.diagnostics_full primary|replication     # full-sample reserve-set disagreement
python -m research_hccr.mechanism.runner pilot 200 230           # planning pilot only
python -m research_hccr.mechanism.runner confirm 300 360         # pre-registered confirmatory run
python -m research_hccr.mechanism.analyze confirm paper/assets/fig_mechanism.pdf
See revision/ for MECHANISM_REPORT, LITERATURE_AUDIT, CLAIM_AUDIT_V2, HOSTILE_REVIEWS_V2, CHANGELOG_V2, REPRODUCIBILITY_V2.
