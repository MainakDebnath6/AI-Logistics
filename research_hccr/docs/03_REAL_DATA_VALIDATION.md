# 03 Real-data validation methods (PROPOSED; not performed)
**Nothing here has been run. No data were downloaded or analysed. All result slots are placeholders.**

## A. Selected dataset and verification status
**Primary candidate: NYC Taxi & Limousine Commission (TLC) Trip Record Data**, official page https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page (retrieved during this task).
Verified from that page: yellow and green taxi trip records with pickup/drop-off date-times and locations; For-Hire Vehicle (FHV) records with dispatching base and pickup date, time and **taxi-zone location ID**; files distributed as PARQUET; a Taxi Zone map/lookup is provided; the data were supplied to TLC by technology providers and **TLC makes no representation as to accuracy**; from 2025 a `cbd_congestion_fee` column reflects congestion pricing (a structural change to report, not hide). Yellow-taxi data dictionary (March 2025) confirms `PULocationID` = TLC taxi zone where the meter was engaged.
**Not verified (must be checked at freeze time):** exact temporal coverage per trip type, the license/terms of use (NYC Open Data terms are presumed but were not retrieved), and the current schema (the page warns of possible parquet schema changes).
*Why this dataset:* real, public, daily-aggregable zone-level pickup counts over many years, with natural regime shifts (the 2020 collapse, 2025 congestion pricing) that stress calibration. *Why not M5 retail sales:* no spatial fleet interpretation; it was not verified in this task and is kept only as a secondary candidate for forecast-calibration-only checks.
**What it cannot support:** TLC trips are not CVRP orders (no delivery coordinates beyond zones, no vehicle capacities, no order indivisibility). The routing stage and routing-feasibility claims therefore **cannot be validated** with this data; the real-data study evaluates forecasting, calibration, reserve-set choice, reservation cost and shortfall only. The firewall invariants remain code-level tests.

## B. Region definition (no future information)
Demand unit = completed pickups per day (trips), **not** vehicle load units. Regions = the K=4..8 highest-volume taxi zones (or borough-level zone groups) ranked by **initial-training-period** pickup totals only; zones with missing days > 5% of the training period are excluded; remaining missing days are left missing for evaluation and imputed only with the training-period same-weekday median for model fitting. Daily aggregation by pickup date (local time). A documented scaling maps trips to model units so that the mean regional training demand equals 100 units (a pure rescaling that keeps the paper's reserve pool Q in {10,20,40} comparable); this is a data-interface adaptation, and capacity A_r keeps the rule kappa x training mean.

## C. Strictly causal temporal protocol
Date boundaries are **derived by rule after inspecting coverage, not invented**: take the most recent contiguous block of at least 1,100 complete days ending at the last complete month at freeze time (to mirror 400 / 300 / 100 / >=300 for initial training / calibration / validation / test, with the last 28 days reserved for targets). Do not silently exclude shifted months; if a structural break (e.g., Jan 2025 pricing) lies in the block, report results with and without it, both pre-declared. Rolling-origin: for origin d and horizon h the forecast uses y up to d; the residual of origin o becomes eligible at day o+h; calibration windows are the last W=200 eligible residuals (paper protocol); models refit weekly on targets already observed; validation window selects only the buffer and the gate and is then frozen; the test period is evaluated once. Overlapping targets across horizons are not treated as independent samples: the unit of replication is the **region-block (or bootstrap over weeks)**, never days. Leakage checks reuse the non-anticipativity tests (perturb data after d; non-oracle decisions must not change).

## D. Costs and shortage penalty (normalised, scenario-based)
No monetary cost can be derived from TLC data. Use a dimensionless objective: reservation cost per unit capacity c_bar = 1 (relative), shortage penalty pi expressed through the **critical fractile** alpha = pi / (pi + c_bar) in the grid {0.5, 0.67, 0.8, 0.9, 0.95} (i.e., pi/c_bar in {1, 2, 4, 9, 19}). This grid is a design rationale (it spans indifference to strongly shortage-averse reserving), **not** an empirical estimate. The primary alpha=0.8 is fixed before any test evaluation; results are reported across the whole grid. Results are labelled "scenario-based normalised cost", never "real operational cost".

## E. Transferability of the seven policies
| Policy | Transfer | Note |
|---|---|---|
| Reactive | Unchanged | no reservation |
| Point forecast | Unchanged | demand-unit rescaling only |
| Validation-tuned buffer | Unchanged | grid as fraction of region level; tuned on validation only |
| Pooled residuals | Unchanged | |
| HCCR | Unchanged | |
| Robust quantile cover (q=0.95, untuned) | Unchanged | keep asymmetry statement |
| Oracle | Unchanged (unattainable) | uses realised test demand |
| Confirmed-order CVRP routing stage | **Not evaluable** | no orders/capacities/coordinates; do not manufacture them |

## F. Publication-ready subsection (LaTeX, extended-version text)
```latex
\subsection{Real-data validation (proposed protocol)}
We will repeat the horizon-specific versus pooled comparison on public NYC TLC trip records~\cite{tlc}, aggregated to daily pickups for the highest-volume taxi zones ranked on the initial-training period only. Demand units are trips, rescaled so that mean regional training demand equals 100 model units; no vehicle capacities, orders or routes exist in these data, so routing feasibility is \emph{not} evaluated. Splits follow the causal protocol of Sec.~III: the first block is used for initial fitting, the second for rolling residual calibration (a residual becomes eligible only at day $o{+}h$), the third for selecting the buffer and gate, and the final block is evaluated once. Costs are normalised: reservation cost per unit capacity is 1 and the shortage penalty is varied through the critical fractile $\alpha\in\{0.5,0.67,0.8,0.9,0.95\}$, with $\alpha{=}0.8$ fixed as primary before testing. Uncertainty is bootstrapped over region-blocks, not days. We report $\Delta=C_{\mathrm{pooled}}-C_{\mathrm{HCCR}}$ = {{HCCR_VS_POOLED_EFFECT}} {{CONFIDENCE_INTERVAL}} on {{REAL_DATASET_RESULT}}; routing results: {{ROUTING_RESULT_IF_AVAILABLE}} (not available for this dataset).
```
(Requires adding a TLC bibliography entry after the license/coverage are verified.) It does not fit in the six-page paper without removing content; use it in an extended version.
