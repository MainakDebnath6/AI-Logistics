# Final execution report
Repository: https://github.com/MainakDebnath6/AI-Logistics (cloned; master = 535c193). Work is on LOCAL branches `research-final` (commit d0cb0de) and `research-final-checkpoint` (unchanged start). **Nothing was pushed or deployed.**

## A. Research
* Baseline reproduced: the research artifacts regenerate bit-identically; 144 quoted-number checks pass (`verify_claims.py`).
* New experiments (all pre-registered with SHA-256 before running): (1) anticipative-window mechanism test, 60 simulations; (2) **relative-freshness test, 45 simulations** (new in this round); (3) **real-data descriptive check**, one dataset.
* Experiment 2 (deployable): staling ONLY the pooled policy shifts the HCCR-vs-pooled contrast by Psi_14 = +0.097 [0.065, 0.131] and Psi_28 = +0.096 [0.061, 0.131] (Holm p < 0.001; at the 0.10 minimum meaningful effect). At phi = 0.95 it removes nearly all of the h = 14 reversal (-0.125 -> -0.019) but only about a fifth of the h = 28 reversal (-0.508 -> -0.406); no effect at phi = 0. Freshness is a real but incomplete mechanism; the persistence/dispersion confound is unresolved.
* Real data: UCI Bike Sharing (CC BY 4.0; GitHub mirror, official host unreachable; integrity-checked; SHA-256 recorded). Four hour-of-day segments (NOT regions), 103 test origins, no routing. |Delta| <= 0.33% of HCCR cost in all 20 (horizon x pi) cells (threshold 1%), inconsistent sign, disagreement 2.9-16.5%. Horizon-specific intervals did NOT improve coverage on this data (0.757 vs 0.762 at h=1); forecasts are weak (WAPE 20-27%). A consistency check, not validation: one city, supply-censored counts, shortened window (W=150).
* Not reproduced / corrected: earlier "fixes coverage" and "under 10% disagreement" claims (corrected previously); predecessor manuscript's Table II (not reproducible).
* Not done: ER-SAA/ScenPO/Wei re-implementations (primary-source detail insufficient for a faithful, matched implementation without changing the question; ER-SAA also uses in-sample/leave-one-out residuals under i.i.d. or mixing assumptions, unlike our rolling-origin protocol, so any implementation would be an adaptation, not a reproduction); stale-HCCR/two-forecaster extensions; slack-aware reserve objective (routing-aware evidence remains the existing 240-instance study: aggregate capacity sufficient but unroutable in 10-21% of cases).

## B. Software
* **Dashboard chart defect found and fixed.** Root cause: experiment artifacts store infeasible scenarios as route_distance_km = 0.0 (leads 12, 24, 48, 60 d are infeasible, demand > capacity), so zero-height bars hid four of six scenarios; the frontend plotted them faithfully. Fix: API `_null_failed_route_distances` returns null + status `infeasible_not_measured` (input not mutated, other files untouched); frontend builder nulls failed distances (also for legacy zero-valued artifacts) and labels "Lead Nd (infeasible)"; a page note states failed routes are not zero and data are synthetic. 3 new tests (2 backend, 1 frontend).
* Files changed in the app: backend/app/api/analytics.py, backend/tests/test_research_analytics.py, frontend/src/pages/ResearchAnalytics.jsx, frontend/src/services/researchAnalyticsData.js, frontend/src/services/researchAnalyticsData.test.js. Added: research_hccr/ (module, tests, configs, results), research_paper/ (source + PDF).
* Not changed: routing service and its interface (the firewall invariant is intact and tested), models, migrations, deployment config, secrets.
* Deployment: NOT deployed. Steps needed: push `research-final`, open a PR, let Render/Vercel build, then load Research Analytics and confirm leads 12/24/48/60 show "(infeasible)" with the note. Live site inspection was not possible (host not reachable from the sandbox).
* Noted, not fixed: 7 pre-existing frontend ESLint errors (react-hooks rules) and 1 backend test failing only because of the sandbox's bcrypt version; a stray repository directory named "earch analytics dashboard and API" (filename artifact) exists upstream.

## D. Manuscript
`research_paper/main.pdf` (+ `main.tex`, `references.bib`, `assets/`): 6 pages including references, IEEEtran conference format, abstract 197 words. Changes this round: abstract, evidence/scope/contribution wording; two new subsections (relative-freshness test; descriptive real-data check); sensitivity table removed from the paper (kept in CSV and text) to stay within six pages; limitations updated. Earlier versions kept as main_v1..v5 in the delivered paper folder.

## E. Remaining limitations (smallest action to resolve)
1. No real logistics/order/fleet data; routing never validated on real data -> obtain an order+vehicle dataset.
2. Mechanism incomplete: ~80% of the h = 28 reversal unexplained; persistence confounded with dispersion growth -> experiment varying dispersion independently; second forecaster family.
3. Real-data check is one city, supply-censored, shortened window, weak forecaster -> a longer multi-region demand series.
4. No published baseline re-implemented -> full-text study of Jia et al. and Wei et al. (institutional access) then an adapted, clearly labelled comparison.
5. Citations: Wei et al. author list missing; Wen et al. and Chevillon taken from secondary reference lists.
6. Dashboard fix not deployed; no end-to-end/login/OSRM test performed (no services or credentials).

## F. Honest assessment
Scientific validity: findings are internally consistent, pre-registered, replicated and honestly hedged; effect sizes are small and the evidence is largely synthetic. Reproducibility: strong (frozen config, seeds, hashes, 144 checks). Novelty: modest (pooled vs horizon-specific ~ unscaled vs scaled ER-SAA residuals; novelty is protocol, diagnostics and the mechanism tests). Operational relevance: not demonstrated. Software: one real defect fixed with tests; deployment and end-to-end unverified. Manuscript: concise, within limit. This is a careful diagnostic paper suited to a workshop-level venue; it is not shown to be stronger than that.
