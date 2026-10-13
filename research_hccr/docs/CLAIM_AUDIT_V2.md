# Claim audit, priority items (outcomes)
| Item | Finding | Action |
|---|---|---|
| A. "fixes coverage" | **Unsupported.** HCCR coverage 0.725-0.794 over all regimes/horizons; AR/Drift still under-cover at h=28 (0.725/0.735); pooled is closer at h=7 in AR (0.788 vs 0.777) and Drift (0.805 vs 0.783) | Conclusion, abstract, intro, results reworded to "moves coverage toward nominal / improved, not corrected" |
| B. Disagreement from 3 seeds | **Recomputed on all 30 primary + 30 replication simulations per regime** (`decision_disagreement_*.csv`, unit = simulation). Regime means over h in {1,7,14}: IID 0.4%, Drift 3.6%, Surge 3.8%, AR 8.3% [7.4, 9.1]; replication AR 9.0%. **Not uniformly <10%**: AR h=1 14.0%, h=28 17.4%; one simulation 15.7% | Abstract/intro/results/contribution 2 rewritten; "under 10%" removed as a blanket claim |
| C. Long-horizon reversal | Pre-registered mechanism test run (60 fresh simulations). Reversal needs persistent residuals and is largely removed by fresh data, but staleness per se is not the mechanism (dose-response failed) | Mechanism reported as partly resolved; hypothesis labelled untested where it is |
| D. Statistical reporting | Units, Holm family (20 tests), bootstrap CIs, uncorrected tables labelled; mechanism Holm applied to Wilcoxon p (disclosed) | none further |
| E. Policy fairness | Robust cover untuned (stated); oracle unattainable (stated); gate identical across policies | none |
| F. Firewall | 13 core tests + runner/pairing tests; oracle exempt; software invariant, not proof | wording unchanged |
| New: Jia "read in full" | Overstated | corrected to "read in part" (paper and audit) |
| New: ER-SAA equivalence | Pooled/HCCR = unscaled/horizon-scaled ER-SAA residuals | Related work and contribution boundary narrowed |
| New: pre-registration error | h=1 sanity check wrong for pooled policy | disclosed in paper and report |
| New: `verify_claims.py` | 122 checks, exit 0 | - |
