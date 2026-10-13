# Final quality gate: honest status

| # | Gate | Status |
|---|---|---|
| 1 | Contribution differs from closest prior work | **Partially.** Not a new algorithm (stated). Distinction is only the controlled ablation/causal-delay/firewall study; Wei et al. could not be read in full. |
| 2 | Algorithm fully specified and implemented | Yes (Alg. 1, Eq. 1, code). |
| 3 | Numerical claims traceable to executed experiments | Yes: tables are generated from `results/*.csv`; text numbers were checked against them by hand (re-check after any rerun). |
| 4 | Same evaluation conditions for every baseline | Yes (shared forecasts, scenarios, splits, seeds). |
| 5 | Ablations isolate one component | Yes, with gating applied identically to all variants. |
| 6 | Forecast vs operational reported separately | Yes. |
| 7 | Confirmed-order feasibility preserved | By construction + 13 tests; routing stage takes no forecast input. |
| 8 | No leakage | Tested (forecasts, windows, decisions); validation used only for buffer and gate. |
| 9 | Reproducible | Yes: frozen config, seeds, one command; deterministic spot-check passed. |
| 10 | <= 6 pages in required format | 6 pages (last page: 2 references) in generic IEEEtran conference format. **The target venue's template/CFP has not been checked.** |
| 11 | Every citation verified | **No, not fully.** Unverified: Wei et al. author list (cited "et al."); Mahmutogullari et al. author list ("others"); Gendreau et al. volume/pages omitted and author list only partly confirmed; Kannan et al. and Wen et al./Chevillon verified only through other papers' bibliographies; Armayau et al. is 2026 not 2025. |
| 12 | Honest limitations | Yes (Sec. VI). |

## Unmet publication requirements / blockers
* Simulation only; no real-data validation. The synthetic cost ratio drives headline savings (sensitivity: 1.8 to 34.4).
* No re-implementation of Jia et al., Kannan et al. or Wei et al.; no superiority claim over them.
* Routing evidence: 240 instances/policy, first-solution solver, 1 s limit.
* Explanation of the long-horizon reversal (stale, autocorrelated residual window) is an untested hypothesis.
* The predecessor PDF's Table II could not be reproduced; the manuscript should not be reused with those numbers.
* Complete citation verification, venue template check, and a proofread are needed before submission. Acceptance is not predicted.

* Sensitivity and forecaster-ablation CSVs were generated before the robust policy was added and contain six policies; the robust cover appears in the main and routing experiments only.
* Stages were run in resumable chunks; one uninterrupted `--stage all` invocation was not re-executed end to end.
* `verify_claims.py` checks the numbers quoted in the text; tables are generated from CSVs by script.
