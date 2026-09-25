# Workbook Defect Review — for Swej's point-by-point ruling

Compiled 2026-08-09 from the full formula-level dissection of every workbook. Three categories:
**[FIX-SHEET]** = a defect in a production ADRIC workbook the lab uses today — worth fixing in Excel regardless of the platform.
**[ENGINE]** = already handled in the Python engine with a `docs/excel-deviations.md` ledger row (ID given).
**[RULING]** = needs Swej's decision.

Statuses here are `open` until reviewed together; ledger rows flip `proposed → approved` per your call.

---

## 1. Your ADRIC production workbooks

### ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx
| # | Cell / area | Defect | Evidence | Category |
|---|---|---|---|---|
| L1 | `Recombination!B8` | GOR-type toggle divides the **Stock Tank** GOR by shrinkage; convention divides the **Separator** GOR (scf/sep-bbl ÷ SF → STO basis). Masked today because B7 = 1.0. | Formula `=IF(B6="Stock Tank",B5/B7,B5)` | **[RULING — D-018]** |
| L2 | `Gas_Composition` col J | The gas **Wt%** inputs are inconsistent with the Mol% inputs by up to 1067% (N2: 0.08 entered vs 0.93 computed; C1: 21.43 vs 38.42). Sheet's own QC = FAIL as shipped. Wt%-side wellstream numbers inherit this; Mol%-side deliverable unaffected. | Cross-check col N; `B8`="FAIL" | [FIX-SHEET] — re-enter gas Wt% from the GC report |
| L3 | `Loading_Volumes!B13` | BSW input is dead — referenced by no formula; no volume correction applied anywhere. | Formula scan: zero references | [FIX-SHEET] or delete the cell |
| L4 | Hoffman b-factor | Uses 14.7 psia while everything else uses 14.73. | `N`-col formula | [ENGINE — kept 14.7 as the Hoffman convention constant, documented] |

### ADRIC_Flash_Separation_Calc_v6.1.xlsx
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| F1 | `Volumetrics_Master!B25` | P_base (= barometric + back-pressure) computed but never used; V_gas_std uses the separately-entered B21. Two pressure conventions coexist silently. | Dependency scan | **[ENGINE — D-017]**; [FIX-SHEET] delete B25 or wire it |
| F2 | Gas side | Z = 1 assumed in every gas conversion (typical ~0.997 at std). ~0.2–0.3% systematic bias, standard lab-sheet practice but undocumented. | `B27` formula | [RULING — accept as convention, or add Z correlations sheet-side/platform-side] |

### 2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| C1 | `Mean Compressibility!H8` | Reservoir→Psat mean compressibility has flipped operand order → returns **−12.365** (negative) while D9 computes the same range correctly as +12.365. The negative value propagates to `Report Tab!K49`. | Both formulas present; sign differs | [FIX-SHEET] |
| C2 | `CCE Calculation!Q16:T55` | "PVTsim" comparison columns are formulas copying the measured columns (`=D16` etc.) — the comparison is vacuous until real PVTsim output is pasted. | Cell formulas | [FIX-SHEET] — paste real sim data or clear |
| C3 | `F35` (bubble-point row) | Instantaneous compressibility at the Psat row uses a central difference straddling into two-phase volume growth → spurious 85.17 displayed and charted. | Stencil spans rows 34–36 | [FIX-SHEET] blank it; engine excludes it |
| C4 | Y-function | Never used to determine Psat (user picks the step; fit is QC-only). Confirmed deliberate across v1→v5. | Version evolution | [ENGINE — same design kept; noted, not a bug] |
| C5 | (v1/v2 heritage) | Compressibility-monotonicity and ρ×V-constancy checks existed in v1/v2, dropped in v5's layout compaction. | QC Protocol rows 42–87 in v2 | [ENGINE — resurrected in the platform's QC set] |

### Bubble_Dew_Point_QC_Tool_Final.xlsx
| # | Cell / area | Defect | Evidence | Category |
|---|---|---|---|---|
| BD1 | `F14:F25` region label + `P4:P7` SUMPRODUCT masks | "Above"/"Below" region membership is decided by RAW ROW INDEX vs. the `K6`/`K7` row-COUNT cells (`A<=$K$6`), never by comparing a row's own pressure against a split-pressure value (no such cell exists). The sheet's own instructions (`L28`: "Enter 4-6 points above and 4-6 points below the expected breakpoint") implicitly require the user to pre-sort entries into two contiguous, correctly-ordered row blocks, but nothing validates that convention was followed. A data-entry ordering mistake (e.g. an "above" row typed with a lower pressure than a "below" row) silently misclassifies that row into the wrong segment's fit, with no error or warning surfaced anywhere on the sheet. | `F14` formula `=IF(A14<=$K$6,"Above Point",...)`; `P4` mask `($B$14:$B$25=1)*($A$14:$A$25<=$K$6)` | [FIX-SHEET] — add a row-order/monotonicity validation; or [RULING] whether the row-order convention is acceptable given the sheet's own usage instructions |
| BD2 | `K10` vs `P10` | Two independently-coded "enough points" gates disagree: `P10` requires >=2 points in EACH region (`OR($K$6<2,$K$7<2)`), while `K10` only checks the TOTAL pressure/QC-value count across both regions is >=4 (`COUNT(C14:C25)<4`), ignoring the per-region split and the `Use` flag entirely. A dataset with, say, 1 above-point and 5 below-points (`K6`=1) passes `K10`'s "OK" gate (total count 6>=4) while `P10` simultaneously shows "Need >=2 points in each region" — a contradictory verdict/note pair shown side by side (`I10`/`O10` area). | `K10` formula `=IF(OR(COUNT(C14:C25)<4,COUNT(E14:E25)<4),"Need data",...)` vs `P10` formula `=IF(OR($K$6<2,$K$7<2),"Need >=2 points in each region",...)` | [FIX-SHEET] — unify the two gates on the per-region test |
| BD3 | `K10` vs `P10` | The parallel-trend guard uses TWO different absolute slope-difference thresholds, three orders of magnitude apart: `P10`'s note fires at `ABS(P4-P6)<0.000000001` (1e-9) while `K10`'s verdict fires at `ABS(P4-P6)<0.000001` (1e-6). For a slope difference landing between the two (plausible — this fixture's own slopes are ~1e-5), `K10` shows "OK" while `P10` simultaneously shows "Parallel trends – review points". Neither is scale-invariant: an absolute slope tolerance means something different for a relative-volume Y-axis (~1.0) than for a liquid-dropout-% Y-axis (~50). | `K10`/`P10` formulas (see BD2 row for exact text) | [FIX-SHEET] — unify to one, ideally relative, threshold; [RULING] pick the house convention (the platform's `psat_breakpoint` check uses a relative `1e-3*max(|slope|)` guard instead of resurrecting either sheet constant — see `docs/excel-deviations.md` D-023) |

### 3_ADRIC_DV_Calc_v6.2.xlsx
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| D1 | `DV_Calc!J15` | Bubble-point Rs formula `=$B$7-SUM($I15:I$16)` includes stage-2's ΔRs → Rs at Psat understated once depletion data is entered. Rows 16+ are correct. | Formula range | [FIX-SHEET] — change to `=$B$7` |
| D2 | `Report!E7` | Fluid Type links `=Sample_Info!B10` which is empty (value lives in B9) → Report shows 0. | Link + empty cell | [FIX-SHEET] |
| D3 | Stage pressures | Psat entered in **psig** (1156) flows unconverted into the `P (psia)` column and the Bg formula, which needs absolute pressure. | No +14.7 anywhere | [RULING — treat all stage P as psia, or add conversion; engine uses absolute consistently] |
| D4 | `DV_Input!E10/E11` | STO density/MW "override" cells are referenced by nothing — editing them does nothing (DV_Calc pulls Sample_Info directly). | Zero references | [FIX-SHEET] delete or wire |
| D5 | Stage-gas slots | Only 8 composition slots; DV stages beyond row 31 need manual gas gravity or their gas mass silently drops out of the mass balance. | `L`-col = 0 path | [FIX-SHEET] add guard; engine raises a validation error instead |
| D6 | `DV_Input!E15` | Back pressure never added to gasometer pressure (P_meas pinned to barometric). Same in MSS. | Formula scan | [FIX-SHEET] or delete input |

### ADRIC_MSS_Calc_FINAL_MSS_v4_corrected 2.xlsx
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| M1 | `Report!E7` | Same empty-link Fluid Type bug as DV (points at `Sample_Info!B10`). | Link | [FIX-SHEET] |
| M2 | `MSS_Input!O24:O27` | Gas Z column collected but never used (std-volume correction assumes Z=1). | Formula scan | [RULING — accept convention or wire Z] |
| M3 | `Material_Balance_QC` rows 146–149 | K-value trend block divides by the **reservoir** composition column (empty in the template) instead of STO → charts permanently blank. | Formula refs | [FIX-SHEET] |
| M4 | Cross-test | No QC compares measured cumulative GOR (269) against the flash Rs_fb (521) entered in Sample_Info. | — | [ENGINE — cross-test QC planned Phase 5; sheet could add one cell] |

### 1_Density_HPHT_Calc_v3_Single.xlsx and 5_Viscosity_HPHT_Calc_v2.xlsx
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| V1 | Density `F21`, Viscosity `D41` | `=_xludf.STDEV.S(...)` — a machine-written unknown-function artifact. Evaluates #NAME? → IFERROR → blank, so **Std Dev, %RSD, and the QC verdict have never computed** in either sheet. | Cached None; `_xludf.` prefix | [FIX-SHEET] — replace with `=STDEV.S(...)` |
| V2 | Density `E5:E8` | Working P, sample T, pump ref P, pump T are referenced by **no formula** — physics enters only via the two manually-typed water densities. | Formula scan | [RULING — platform computes ρw(P,T) from IAPWS instead; sheet should at least label these as metadata] |
| V3 | Density `C21` | Average includes runs whose status is "Out of range". | AVERAGE over all G | [FIX-SHEET] — AVERAGEIF on Valid |
| V4 | Viscosity `F40` | `VLOOKUP(E6,...,FALSE)` requires reservoir P to exactly equal a table pressure; otherwise blank. | Exact-match flag | [FIX-SHEET] — interpolate; engine interpolates |
| V5 | Viscosity `H40` | Stock-tank row found by hardcoded `MATCH(15,...)`. | Formula | [FIX-SHEET] |

### CVD_Calc_WaterPump_v3_WhitsonStyle_AdditionalQC.xlsx (template, ships empty)
| # | Cell | Defect | Evidence | Category |
|---|---|---|---|---|
| X1 | `CVD_Calc!E7`, `E9` | Labeled "R" and "scf_per_lbmol" but formulas are `=B16`/`=B14` (missing sheet qualifier) → they resolve to **stage pressures** on the same sheet, poisoning every n_gas and n_p calculation. | Cached 0s; formula text | **[FIX-SHEET — Critical before any lab use]** |
| X2 | `Plots!A5:F24`, `Report!B5:B8` | Reference `CVD_Calc!B9:R28` but the stage table lives at rows 13–32 → off-by-4: header junk charted, stages 16–19 dropped, Report Pdew/T broken (`#VALUE!`/0 cached). | Cached junk strings | **[FIX-SHEET — Critical]** |
| X3 | `Additional_QC` rows 9–28 | Hall-Yarborough variant uses Tr instead of reciprocal t, omits ·t in the A-term, and reports the reduced density y as "Z_calc". | Formulas | **[ENGINE — D-006]**; [FIX-SHEET] |
| X4 | `Additional_QC!C50` | K_est = `10^(B34+C34/B6)/F50` with Hoffman b/Tb table values → 10^470 overflow (#NUM! cached). | Cached errors | [FIX-SHEET]; engine implements correct Hoffmann |
| X5 | Yellow constant cells | '200', '379.482', '10.7316' stored as **text**; Excel coerces silently. | Cell types | [FIX-SHEET] hygiene |

### MMP slim-tube tools
| # | Where | Defect | Evidence | Category |
|---|---|---|---|---|
| S1 | QC tool + template | Recovery exceeds 100% (102.9%): "PV" (111.14 cc) already includes dead volume (4.71 cc) yet recovery never subtracts it; the raw-logger file's own (dead) formula does subtract. Double-count trap between C9 and C10 inputs. | Both formulas compared | [RULING — define the house recovery basis; engine has an explicit flag] |
| S2 | `Run n!D127/D128` | Empty runs show mass-balance "100%" error and "REVIEW" (no blank guard) → MMP Summary inherits garbage rows. | Cached values | [FIX-SHEET] |
| S3 | Template ` Data` | Gas uses forward differences, oil backward → GOR series leads oil by one sample. | `P4=I5-I4` vs `N5=H5-H4` | [FIX-SHEET] |
| S4 | `Reporting` | VLOOKUP TRUE = stair-step, not interpolation; first row #N/A. | Formulas | [FIX-SHEET]; engine interpolates |
| S5 | MMP itself | Never computed anywhere — engineer eyeballs two lines and types the answer. | No formula | [ENGINE — real two-line-intersection solver planned Phase 4] |

## 2. Third-party reference tools (FYI — not yours to fix)
- **Z factor calculation.xls**: transposed Piper CO2 coefficient −0.09034 vs published −0.90348 (D-003); wrong Newton derivative that still converges (D-005); C7+ MW summed unweighted (D-004).
- **Bubble point correlations.xls**: Standing exponent left as user input (D-007); Vasquez-Beggs exponent multiplied instead of divided → #NUM! (D-008); Glaso ×14.5 stray factor + final 10^x never applied (D-009); Lasater is only the last step (chart factor is an input).
- **PVT-check.xls**: gas constant entered as 10.07 instead of 10.732 (cancels in its CVD checks, still wrong); molar volume appears as 379 / 379.4 / 379.5 in different cells; file A's wellstream-gravity formula used z instead of y (fixed in file B).

## 3. Rulings needed (summary)
1. **D-018** — GOR-basis direction (L1). Engine currently: conventional (Separator ÷ SF).
2. **hoffman_r2 bands** — R² ≥ 0.98 PASS / ≥ 0.95 REVIEW (engineering-judgment defaults).
3. **Z = 1 conventions** (F2, M2) — keep as lab convention or upgrade.
4. **DV psig/psia** (D3) and **MMP recovery basis** (S1) — define the house convention.
5. **Ledger statuses** — flip D-001…D-018 `proposed → approved` (or amend) as we walk through.
6. **stash@{0}** — drop the obsolete July-15 UI diagram tweak?
7. **Bubble_Dew_Point_QC_Tool_Final.xlsx gates** (BD1-BD3) — row-order region split with no ordering validation, and two pairs of mutually-inconsistent point-count/parallel-trend gates (`K10` vs `P10`). The platform's `pvt.qc.checks.psat_breakpoint` sidesteps all three (threshold split instead of row-order; single relative parallel-guard) — confirm that resolution, or have the sheet itself fixed to match.
