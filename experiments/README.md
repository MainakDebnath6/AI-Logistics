# Reproducible Experiments

Install the repository's root `requirements.txt`, then run from the repository root:

```bash
python -m experiments.run_all
```

The command regenerates `data/raw/synthetic_demand.csv` before evaluating any model, so forecast, ablation, horizon, advisory, and routing experiments use the same dataset. Output CSV and JSON files are written under `experiments/results/`; each row includes seed and split sizes, while each JSON also records method details.

## Data and split

The dataset is synthetic only. The fixed default seed is `20261008`; the series contains 730 daily dates, starts `2024-01-01`, uses a 670-day training prefix and 60-day chronological holdout, and is generated as documented in `data/README.md`. No rows are shuffled.

## Forecast models

- Previous-week naive repeats the latest observed seven values in weekday order.
- Holt-Winters is additive with weekly seasonality and deterministic grid search over smoothing gains 0.2, 0.5, and 0.8.
- Seasonal LR uses a linear trend, weekly Fourier harmonics 1-3, annual harmonics 1-2, lags 1/7/14/28/365, and trailing means 7/28/365 when included by the ablation.

Rolling-origin horizon evaluation uses expanding history and all valid forecast origins in the 60-day holdout. A target observation is only added to history after its date. Horizon origin counts are 54, 47, 31, and 1 for horizons 7, 14, 30, and 60 days respectively. The 60-day model-comparison row consequently has only one origin; it should not be interpreted as independent repeated evidence. MAPE excludes zero actuals from its denominator and reports both total and nonzero observation counts. MAE and RMSE include all targets.

Feature ablation removes the stated Fourier, lag, or rolling columns from the LR design matrix. All variants use the same training targets (starting at index 365 with the full history available), dataset, split, and one fixed 60-day holdout origin; no inferential test is claimed.

## Routing and HGFCI

Routing experiments use real OR-Tools with explicit synthetic depot/delivery coordinates and deterministic Haversine distance; external OSRM is disabled. The benchmark uses `PATH_CHEAPEST_ARC`, a one-solution limit, fixed order/vehicle order, and records generated order/driver/vehicle IDs, integer confirmed demands, coordinates, depot, capacities, feasibility, service, utilization, route distance, and solver runtime. Route distance uses the solver arcs; it is not a post-hoc distance over OSRM geometry.

The HGFCI artifact evaluates the implemented horizon gate and capacity formulas against an explicitly assumed synthetic daily capacity. The paired routing artifact reuses the same single CVRP solve for both arms because no candidate-fleet preparation policy or additional-vehicle availability data exists. It is an advisory non-interference check, not an operational-benefit experiment. No preparation action, changed capacity, extra vehicle, or cost benefit is fabricated. Delivery cost remains unavailable.

## Limitations

The generated series is not measured logistics data. Synthetic forecast accuracy does not establish real-world model performance. No real dispatch-time capacity policy, candidate fleet, cost model, or dated demand history is present. Therefore an empirical capacity-risk calibration and a causal reactive-versus-prepared-fleet comparison are unsupported by current data. See `RESEARCH_IMPLEMENTATION_STATUS.md` for implementation state and generated metrics.