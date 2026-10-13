# 00 Claim ledger (source of truth: compiled paper `main.pdf`, 6 pages)
Locations are by section; PDF page numbers moved during editing. Status labels: SUP = supported by evidence shown in the paper; PLA = plausible, insufficiently demonstrated; EXP = exploratory; UNV = unverifiable from the PDF alone (needs artifacts).

| # | Claim | Location | Evidence shown | Assessment | Action |
|---|---|---|---|---|---|
| 1 | HCCR and pooling choose different reserve sets in "under 10% of decisions on average per regime" | Abstract; Intro; Sec. V-B | Text only: 0.3% IID, 2.8% Drift, 4.4% Surge, 9.4% AR; 3 seeds/regime, gated decisions, h in {1,7,14} | **EXP / UNV from PDF.** "Under 10%" is a regime average (max 9.4%); per-seed and per-horizon rates are not in the PDF and could exceed 10%. | Keep "on average per regime" and "exploratory"; report per-horizon rates in the extended version. |
| 2 | Reversal at h=14,28 in AR is an observed result; cause untested | Abstract; Sec. V-C | Table III by-horizon rows (+0.29, -0.12, -0.42); replication h1/h28 columns | SUP for the observation; mechanism PLA (explicitly labelled untested). | Abstract says "cause is untested". Mechanism experiment designed in 02 (not run). |
| 3 | Coverage and cost are distinct | Intro; Sec. V-A | Fig. 2a coverage; Table III | SUP | none |
| 4 | Paired CIs interpreted correctly | Sec. IV-C; V | Holm over 20 tests; marginal-CI sentence rewritten; Tables IV-VI declared uncorrected | SUP (checked earlier) | none |
| 5 | Replication varies in magnitude | Sec. V-C, Table (replication) | AR 0.53% vs 0.88%; Drift 0.29% vs 1.08% (wide CI) | SUP; discussed honestly | none |
| 6 | Seven-policy comparison fair | Sec. IV-C; Table II | Same inputs; robust cover q=0.95 untuned (asymmetry stated); gate applied identically | SUP with stated asymmetry | none |
| 7 | Routing feasibility vs aggregate capacity | Sec. V-B | Oracle 60.4% < buffer 69.6%; 240 instances/policy at h=7 | SUP for the sample; small, first-solution solver | none |
| 8 | Related-work claims match sources | Sec. II; Table I | Abstract-level for Wei, Armayau, Beatrici, Patel, Ghosal; Jia read in part | **UNV / partly flawed.** Paper said Jia "read in full" while Intro said abstract-level: contradictory and overstated. | **Fixed** to "read in part". Remaining entries are abstract-level and labelled so. |
| 9 | Abstract agrees with results | Abstract | 0.1-0.5%, 1.1%, 2.2%, -0.8%, -2.5% all traced (verify_claims.py: 78+ checks) | SUP. Earlier version's "at most 0.5% at 1,7,14" was ambiguous and was already corrected. | none |
| 10 | Conclusion within synthetic scope | Sec. VI | "Validation on real order histories is the necessary next step" | SUP | none |
| 11 | Word "causal" | Title (old), Methods | Means non-anticipative, not causal inference | **Ambiguous.** | Title/abstract reworded; definition added in Sec. III. |
| 12 | Surge gain (+0.01) | Sec. V-C | Holm-significant but hypothesis predicts none | EXP | Labelled exploratory in paper. |
| 13 | "13 automated invariant tests" | Intro; Sec. III | Repo tests | UNV from PDF (verified against repo: 25 tests pass incl. 12 mechanism-scaffold tests added later) | Count in paper refers to the 13 original tests. |
