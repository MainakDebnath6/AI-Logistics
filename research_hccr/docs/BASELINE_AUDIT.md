# Baseline audit (what is implemented, what is not)

| Method | Status | Evidence / note |
|---|---|---|
| Reactive CVRP (no reservation) | **Implemented** | policy `reactive`; routing via unmodified repo OR-Tools service |
| Point-forecast reservation | **Implemented** | `point` (Eq. 1 with one scenario) |
| Validation-tuned fixed buffer | **Implemented** | `buffer`, per-horizon buffer from fixed grid on validation only |
| Pooled empirical residual scenarios | **Implemented** | `pooled` (conceptually ER-SAA-like; not Kannan et al.'s method) |
| HCCR (horizon-specific residuals) | **Implemented** | `hspec` |
| Conservative robust quantile cover | **Implemented (new)** | `robust` = cover y-hat + 95th pct of horizon residuals; own definition, not a published method |
| Naive weekly / Holt-Winters + same reservation | **Implemented** | forecaster ablation (10 seeds), `comparison` uses seeds 0-9 |
| Perfect-information oracle | **Implemented** (unattainable) | `oracle` |
| Wei et al. 2024 joint rental+routing | **Not implemented; infeasible to reproduce faithfully** | full text/algorithm details not obtained; different (VRPTW, metaheuristic) problem |
| Jia et al. 2025 ScenPO | **Not implemented** | needs learned multi-horizon quantile model + two-stage stochastic program; not recoverable within this simulator without changing the question |
| Kannan et al. ER-SAA | **Not implemented** | only known via Jia et al.'s description |
| Conformal / DRO (Patel, Ghosal) | **Not implemented** | different guarantees/problem class; no coverage claim is made |
| Decision-focused learning (Elmachtoub-Grigas) | **Not implemented** | out of scope |

Regression check: adding `robust` left all 5,760 pre-existing operational rows and 1,440 routing instances bit-identical (max abs diff 0).
Not rerun with the new policy (documented limitation): forecaster ablation and sensitivity CSVs (they contain the six earlier policies only).
Runtime: routing solver runtime is recorded per instance (`route_runtime_s` in `comparison_table.csv`); reservation-decision runtime was not measured reliably and is not reported.
