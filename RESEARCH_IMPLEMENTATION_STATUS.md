# Research Implementation Status

Status reflects the code and generated outputs in this repository as of 2026-10-08. The repository contains no paper source file and no real dated demand dataset; paper-number comparisons and empirical claims cannot be verified here.

## Implemented

- Deterministic synthetic dataset generator and checked-in CSV: 730 consecutive dates from 2024-01-01, seed 20261008, chronological 670/60 split, weekly period 7, annual period 365.25, Gaussian sigma 5, nonnegative clipping. Every row is marked `synthetic`.
- Forecast experiment models: previous-week seasonal naive, weekly additive Holt-Winters, and Seasonal LR with trend, weekly/annual Fourier terms, causal lag inputs, and trailing rolling features.
- Expanding-window rolling-origin evaluation for 7/14/30/60-day horizons. Zero actuals are excluded from MAPE and explicitly counted; MAE/RMSE include all targets. Raw daily actual/prediction rows and configuration are written to CSV/JSON.
- Seasonal LR feature ablations remove the specified feature columns and share the same dataset, split, and training target rows; they use one fixed 60-day origin and are descriptive, not inferential.
- HGFCI service/API is advisory only: horizon gate, Delta, Rho where defined, and nonnegative risk. At zero capacity, Rho is null and absolute risk remains defined. The default gate is inclusive through day 14.
- Confirmed-order routing now uses an explicit configured/request depot and delivery nodes. OR-Tools capacity uses confirmed integer order demand and actual vehicle capacity. Selected drivers must match their mapped selected vehicles. Requested confirmed orders are mandatory; duplicate IDs are rejected and responses report served/requested IDs separately.
- Optimized distance is the deterministic Haversine solver objective and route coordinates reconstruct depot → deliveries → depot. Optional OSRM geometry, duration, and road distance are returned separately and do not change optimized distance.
- Time-window datetimes normalize to UTC; naive datetimes are explicitly interpreted as UTC. OR-Tools uses relative integer minutes from the earliest window. Partial, reversed, and mixed datetime/numeric windows are rejected. The feature remains opt-in.
- Successful optimizer results persist atomically as route summary plus JSON result. Route history schema/API and an additive Alembic migration are present.
- Explicit development/demo seed command requires an explicit non-production environment and externally supplied passwords; it is deterministic and insert-if-absent.
- Production settings reject placeholder JWT secrets and wildcard credentialed CORS; configured origins are used by FastAPI.

## Generated Synthetic Results

Command executed: `python -m experiments.run_all` using seed 20261008. Outputs are in `experiments/results/`.

- 60-day single-origin model comparison: previous-week naive MAE 12.7530, RMSE 15.0234, MAPE 10.9278%; Holt-Winters MAE 16.5458, RMSE 19.6759, MAPE 13.9633%; Seasonal LR MAE 4.5456, RMSE 5.7411, MAPE 4.1076%. This 60-day comparison has one forecast origin.
- Seasonal LR rolling-origin horizon MAE: 7 days 4.5776 (54 origins), 14 days 4.7066 (47 origins), 30 days 4.7896 (31 origins), 60 days 4.5456 (1 origin). Window targets overlap across origins; rows are not independent samples.
- Seasonal LR 60-day fixed-origin feature ablation MAE: full 4.5456; remove weekly 4.4040; remove annual 6.0569; remove lags 4.5126; remove rolling 5.1157; remove weekly and annual 9.4039. These are descriptive synthetic outcomes; no paired significance test is reported.
- The advisory experiment evaluates six evenly spaced holdout lead times against an assumed synthetic daily capacity of 100 units. One within-gate scenario produced a positive shortfall signal. This capacity is an experiment assumption, not fleet data.
- The six-scenario synthetic CVRP benchmark used 4 vehicles at 25 units each, explicit depot coordinates, deterministic Haversine distances, and OR-Tools `PATH_CHEAPEST_ARC` with a one-solution limit. Mean service level was 33.33%, utilization 31.5%, route distance 288.947 km, shortfall 16.5 units, and route count 1.333. These are benchmark outputs for the generated scenarios, not operational fleet performance.
- The reactive/HGFCI artifact records the same CVRP solution in both arms: all paired operational differences are zero by construction. This is not an operational-benefit test. One advisory warning occurred among six sampled forecast lead times.

## Unsupported / Not Validated

- **Real-world forecasting:** No real order-history time series, provenance, demand aggregation policy, or operational units are supplied. Synthetic accuracy must not be presented as real-world accuracy.
- **Sigma-based calibrated HGFCI:** Sigma 5 is implemented as generator noise standard deviation. There is no forecast-error calibration data or paper-defined uncertainty multiplier that justifies a calibrated risk band.
- **Operational reactive-vs-prepared-fleet benefit:** No candidate fleet, availability schedule, intervention policy, or preparation lead-time data exist. Therefore no operational intervention is applied to CVRP inputs and no benefit comparison is claimed. The paired artifact reuses the identical CVRP result to check non-interference only. Delivery cost is unavailable because no cost model exists.
- **Inferential statistics:** Horizon windows overlap and ablation has one holdout origin; no significance claims are supported by these runs.
- **PostgreSQL runtime validation:** Migration upgrade/downgrade SQL generation was checked offline. No live PostgreSQL database was available, so an actual database upgrade/downgrade and API persistence transaction were not executed against PostgreSQL.
- **Paper comparison:** No paper file is present in this checkout, so discrepancies against any published numeric claims cannot be calculated.

## Reproduction

```bash
python -m experiments.run_all
python -m pytest
```

The runner regenerates the synthetic CSV before evaluating forecast, ablation, horizon, CVRP, and advisory outputs. See `data/README.md` and `experiments/README.md` for complete definitions and limitations.
