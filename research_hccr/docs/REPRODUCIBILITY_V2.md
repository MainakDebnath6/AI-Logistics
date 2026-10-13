# Reproducibility report (priority revision)
Executed and inspected this session: pytest (28 passed); verify_claims (122 checks, exit 0); diagnostics_full primary and replication (resumable); mechanism pilot (30) and confirmatory (60) runs; analysis, comparison, make_assets; pdflatex/bibtex (6 pages).
Verified: runner natural-window costs equal frozen pipeline costs to 1e-9 (test); simulate() default path unchanged by `ar_phi_override` (test); previously reported CSV values unchanged.
Not done: real-data experiment (dataset hosts unreachable from the sandbox: DNS failure for nyc.gov and the TLC CDN); one uninterrupted `--stage all`; rerun of sensitivity/forecaster stages with the robust policy; stale-pooled-only mechanism test; second forecaster.
Environment: Python 3.12.3, numpy 2.4.4, pandas 3.0.2, scipy 1.17.1, statsmodels 0.15.0, OR-Tools 9.15.6755, single core; mechanism pilot about 8 min, confirmatory about 15 min, full-sample disagreement about 20 min.
No git repository existed; backups are file copies.
