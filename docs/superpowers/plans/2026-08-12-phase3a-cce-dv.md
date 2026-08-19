# Phase 3a: CCE + Differential Vaporization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the CCE and DV experiment modules end-to-end (engine, QC incl. the new Psat-breakpoint check, Amyx/Carlson flash-basis adjustment, Excel importers for the filled ADRIC templates, LIMS-aligned reporting, Streamlit pages) on branch `feature/phase3-blackoil-suite`.

**Architecture:** Mirrors the proven Phase 2 patterns exactly: `pvt/experiments/<test>/` with models/calc/validate; importer per template reading only input cells; page + `_logic` module pair; golden tests pinned to the fixture workbooks' CACHED cell values (extracted from the workbook, never hand-typed from digests). Fixture workbooks are already committed under `tests/fixtures/workbooks/`: `2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`, `3_ADRIC_DV_Calc_v6.2.xlsx`, `Bubble_Dew_Point_QC_Tool_Final.xlsx`, `Diff_PVT_Adjusting.xlsx`.

**Tech Stack:** unchanged (Python 3.12, openpyxl, Streamlit; 100% branch-coverage gate on `pvt/`).

## Global Constraints

- Branch `feature/phase3-blackoil-suite`; commits pushed to the remote branch; NO AI/Claude signatures in commit messages; merge to main only via PR at feature end.
- Gate: `python3 -m pytest` green with 100% coverage on pvt/ and warning-clean; `ruff check pvt tests ui app.py cli.py`; `mypy pvt`; `python3 -c "import pvt, ui, cli"`.
- GOLDEN-INTEGRITY (hard rule): expected values in golden tests come from the fixture workbook's cached cells, read via openpyxl at documented addresses (Task-3-of-Phase-2 pattern: generate, cross-check against the digest spot values given per task, embed the generator as fixture provenance). Never alter an expectation to make a test pass; a mismatch = STOP, DONE_WITH_CONCERNS, controller adjudicates.
- WORKBOOK DEFECTS found while implementing: append a row to `docs/workbook-defect-review.md` §1 (same format) in the same commit, status `open`, do NOT block on rulings. Engine implements correct physics; deviations from a source workbook additionally get a `docs/excel-deviations.md` row (next free ID; D-019 onward).
- Known defects the ENGINE must not replicate (already ruled by the correct-physics charter, cite in code comments): CCE mean-compressibility sign flip (`Mean Compressibility!H8`), CCE bubble-point-row central-difference contamination (`F35`), DV bubble-point Rs off-by-one (`DV_Calc!J15` includes stage-2 ΔRs; engine: Rs(Psat) = Rs_fb), DV stage-gas silent mass drop beyond 8 composition slots (engine: validation error).
- Pressure policy (pending Swej ruling on psig/psia, defect D3): engine functions take ABSOLUTE psia everywhere; importers pass workbook pressure columns through UNCHANGED (matching the sheets' numbers exactly, preserving golden parity) but attach a documented `pressure_basis="as-entered (workbook mixes psig labels with absolute-pressure formulas, defect D3)"` note in the import metadata and a `# D3` comment. Report tables label the column "P (as entered)".

---

### Task 1: CCE models + validation (`pvt/experiments/cce/`)

**Files:** Create `pvt/experiments/cce/__init__.py`, `models.py`, `validate.py`; Test `tests/unit/experiments/test_cce_validate.py`

**Interfaces (produced):**
```python
@dataclass(frozen=True)
class CceStage:
    step: int; p: float; v_cell_cc: float          # pressure (abs psia policy), total cell volume

@dataclass(frozen=True)
class CceInputs:
    t_res_f: float
    psat_visual: float                              # visually observed Psat (yellow D8)
    bubble_point_step: int                          # user-picked step index (yellow D10)
    stages: tuple[CceStage, ...]                    # descending P, 2..40 stages
    rho_at_psat_g_cc: float | None = None           # density at Psat if measured

@dataclass(frozen=True)
class CceResults:
    psat_from_data: float; psat_consistency_ok: bool           # |visual - picked-row P| <= 10 psi
    v_sat_cc: float
    stages: tuple[CceStageResult, ...]              # per stage: rel_vol, density (above Psat),
                                                    # instantaneous compressibility (above Psat,
                                                    # bubble-row EXCLUDED), y_function (below Psat)
    mean_compressibility_1_psi: dict[str, float]    # keyed "res_to_psat" and pairwise ranges

def validate(inputs: CceInputs) -> list[str]
```
Validation rules (one message each): >=2 stages; P strictly descending; volumes > 0; bubble_point_step within stage range; picked-row P within 10 psi of psat_visual is a WARNING-style message prefixed "consistency:" (not blocking, mirrors the sheet's ✓/⚠ gate at `J11/K11`); t_res physical.

**Steps:** brief TDD cycle per the established pattern (failing tests incl. a happy path built from the fixture workbook's actual stage rows 16-25 read via openpyxl in the test setup; rule-per-message tests; accumulate test) → implement → gate → commit `feat(cce): models + validation`.

---

### Task 2: CCE calculation engine (`pvt/experiments/cce/calc.py`)

**Files:** Create `pvt/experiments/cce/calc.py`; Test `tests/golden/test_cce_workbook.py`; Modify `docs/excel-deviations.md` (+2 rows), `docs/workbook-defect-review.md` (no new rows expected; C1/C3 already listed)

**Formulas (from the dissected `CCE Calculation` sheet, engine-correct forms):**
- Psat from data: `psat_from_data = stages[bubble_point_step-1].p` (sheet `J9 =INDEX(B16:B55,$D$10)`).
- `v_sat = V(bubble_point_step)`; relative volume `rv_i = v_i / v_sat` (sheet col D).
- Density above/at Psat (single phase): `rho_i = rho_at_psat * v_sat / v_i` (mass conservation).
- Instantaneous compressibility above Psat, central difference over neighbors, in 1/psi ×1e6 reporting:
  `c_i = -(1/v_i) * (v_{i-1} - v_{i+1}) / (p_{i-1} - p_{i+1})` — computed ONLY where i-1 and i+1 are both above Psat (engine EXCLUDES the bubble row and its straddle; ledger row D-019: sheet `F35` straddles into two-phase, cached 85.17, engine returns None there).
- Mean compressibility (two-point form, sheet `Mean Compressibility!D4` correct variant): `c_mean = ((v_f - v_i)/((v_i+v_f)/2)) / (p_i - p_f)` ×1e6; `res_to_psat` uses first stage vs bubble row with the CORRECT operand order (ledger row D-020: sheet `H8` has flipped operands giving −12.365; engine returns +12.365-class values).
- Y-function below Psat: `y_i = (psat_from_data - p_i) / (p_i * (v_i/v_sat - 1))`.

**Goldens (fixture `2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`, cached cells; test reads them via openpyxl and compares engine output on the same imported stage table):** relative-volume col D rows 16-55 (rel 1e-9 — pure arithmetic identity), Y-function col G below-Psat rows, instantaneous compressibility col F above-Psat rows EXCLUDING row 35, `Mean Compressibility!D4` (and assert engine `res_to_psat` == ABS(cached H8) with the D-020 comment), `J9` psat-from-data, `J11/K11` consistency gate. Digest spot values for cross-check: D10 = 20 (bubble step), visual Psat D8 = 1155.73, H8 cached = −12.365, F35 cached = 85.17 (excluded).

**Steps:** TDD → implement → both ledgers → gate → commit.

---

### Task 3: CCE fit QC + resurrected checks (`pvt/qc/checks/`)

**Files:** Create `pvt/qc/checks/polynomial_fit.py`, `pvt/qc/checks/monotonic_compressibility.py`, `pvt/qc/checks/rho_v_constancy.py`; Modify `pvt/qc/engine.py` DEFAULTS (+3 keys), checks `__init__`; Test `tests/unit/qc/test_cce_checks.py`

**Interfaces:**
- `polynomial_fit.check_single_phase(stages_above, degree=3, registry=None) -> FitResult(coeffs, fitted, residual_pct, qc)` — fits computed regression (numpy-free: normal equations in pure python or `statistics`; degree-3 poly of RV vs P), grades max |deviation|% with new key `"cce_sp_fit_dev_pct" = (0.05, 0.10)`; `check_two_phase(stages_below, degree=2)` with `"cce_tp_fit_dev_pct" = (1.0, 2.0)` (thresholds proven stable across CCE v1→v5; static typed coefficients of the sheet are NOT ported — engine fits per dataset, ledger D-021).
- `monotonic_compressibility.check(...)`: instantaneous c must increase as P falls toward Psat (resurrected v1/v2 check).
- `rho_v_constancy.check(...)`: ρ·V spread above Psat graded with `"cce_rho_v_spread_pct" = (0.5, 1.0)` (proposal, flag for calibration).
- Three-state rollup mirrors v5's `C40` semantics (FAIL > REVIEW(warn) > PASS).

**Steps:** TDD (fit correctness on synthetic exact-polynomial data at rel 1e-9 + workbook-cached residual comparison loose) → implement → gate → commit.

---

### Task 4: Psat breakpoint QC (`pvt/qc/checks/psat_breakpoint.py`) — NEW from the PPV tool

**Files:** Create `pvt/qc/checks/psat_breakpoint.py`; Test `tests/golden/test_psat_breakpoint.py`; Modify `docs/workbook-defect-review.md` if the tool has defects (dissect-in-task)

**Method (fixture `Bubble_Dew_Point_QC_Tool_Final.xlsx`, single sheet; survey-confirmed formulas):** two independent least-squares lines through the above-Psat and below-Psat segments of a P-vs-QC-value series (RV or Z); intersection `p* = (b2 - b1)/(m1 - m2)` (sheet `P8=(P7-P5)/(P4-P6)` layout); parallel-trend guard (|m1−m2| below threshold → REVIEW "trends near-parallel, breakpoint ill-conditioned"). Read the workbook IN-TASK to extract the exact cell map + cached example as golden (generator-embedded provenance, cross-check the intersection value against the sheet's own cached result); new registry key `"psat_breakpoint_vs_visual_psi" = (10.0, 25.0)` (house 10-psi consistency band extended; proposal, flag).
- Public: `check(points: Sequence[tuple[float, float]], split_at: float, visual_psat: float, registry=None) -> BreakpointResult(psat_estimate, slopes, qc)` + wire into the CCE page later as a cross-check row.

**Steps:** dissect → TDD with workbook golden → implement → gate → commit. Any defect found in the PPV tool → defect-review row (status open).

---

### Task 5: CCE importer (`pvt/io/excel_import/cce_v5.py`)

**Files:** Create importer; Test `tests/golden/test_import_cce_v5.py`

**Cell map (dissected; verify each against the fixture in-task, Task-7-of-Phase-2 discipline):** sheet `CCE Calculation`: `D7` reservoir T?, `D8` visual Psat, `D10` bubble-point step, stage table rows 16-55: `A` step, `B` P, `C/D/E` volumes (verify which column is the entered V vs derived RV by reading formulas with data_only=False — derived columns are NOT imported), `Mean Compressibility` inputs if any are yellow, metadata block. Wrong-file detection; blank-cell typed errors (Phase-2 hardening pattern); negative/absurd guards. Integration golden: import → `cce.calc.calculate` → matches the workbook's cached RV/Y/compressibility columns (same assertions as Task 2 but through the import path).

---

### Task 6: CCE page + report (`ui/pages/cce_page.py` + `_logic`, `pvt/reporting/tables.py` extension)

- Page: upload/manual tabs per the flash-page pattern; stage table via `st.data_editor` (step/P/V columns, NumberColumn bounds); results: Psat panel (visual vs from-data vs breakpoint estimate), RV & Y-function charts (scatter + fitted line, Phase-2 Hoffmann-chart pattern), compressibility table, QC panel (fit checks, monotonicity, ρV, consistency, breakpoint); report download.
- `cce_tables(results, qc)` in `pvt/reporting/tables.py`; column names follow the LIMS parameter map for CCE (read `tests/fixtures/workbooks`... the LIMS format workbook is NOT in fixtures — copy `"/Users/swej/Swej/PVT Calculationssss/ARCHIVE/Report/LIMS_PVT_Routine_Report_Format_MuhammadAthif.xlsx"` to `tests/fixtures/workbooks/LIMS_Report_Format.xlsx` in this task, read its `LIMS Parameter Map` sheet, and name report rows with the LIMS short names + units for the CCE section; embed the mapping as a reviewed dict).
- Home page: flip the CCE roadmap card to live. Update `app.py` nav (icon `:material/compress:`), screen-map figure regen if trivial (else defer to 3b wrap).
- AppTests per the established set (boot, manual flow with fixture-derived numbers, invalid-resubmit stale-clear, upload flow with doctored/blank-cell errors).

---

### Task 7: DV models + validation (`pvt/experiments/dv/`)

**Interfaces:**
```python
@dataclass(frozen=True)
class DvStage:
    p: float                                        # as-entered pressure (D3 policy)
    v_oil_before_cc: float | None; v_oil_after_cc: float
    gasometer_initial_cc: float | None; gasometer_final_cc: float | None
    gasometer_p_mbar: float | None; gasometer_t_c: float | None
    z_gas: float | None = None                      # measured Z, default 1 (sheet M-col policy)
    gas_gravity_override: float | None = None       # manual γg when no composition slot

@dataclass(frozen=True)
class DvInputs:
    t_res_f: float; psat: float                     # stage 1 IS the bubble point (sheet row-23 convention)
    v_at_psat_cc: float; v_sto_cc: float
    rho_at_psat_g_cc: float; rho_sto_g_cc: float; sto_mw: float
    rs_flash_scf_stb: float; bo_flash: float        # flash anchors (Sample_Info B14/E14)
    barometric_mbar: float
    stages: tuple[DvStage, ...]                     # stage 1 = Psat row (no gas)
    stage_gas_streams: tuple[CompositionStream | None, ...]   # slot n = gas arriving at stage n+1
```
Validation: descending P; stage-1 gas fields empty; volumes positive; **gas mass accounting guard** (engine version of defect D5): any stage with liberated gas but neither a composition slot nor a gravity override → validation ERROR (sheet silently drops the mass); gasometer readings paired; flash anchors positive.

---

### Task 8: DV calculation engine (`pvt/experiments/dv/calc.py`)

**Formulas (dissected `DV_Calc`/`DV_Input`, engine-correct):**
- Gasometer std volume per stage: `v_std_cc = (g_final - g_initial) * (p_mbar / P_STD_MBAR) * (T_STD_K / (t_c + 273.15))`; scf via CC_PER_SCF. (Sheet H/K/L cols; barometric default when p_mbar None.)
- `bo_d_i = v_oil_after_i / v_sto` (col E). Stage 1: `v_at_psat/v_sto`.
- ΔRs per stage: `drs_i = v_gas_std_scf_i * CC_PER_STB / v_sto_cc`... (sheet I: `G*158987.29/B8` — scf×(cc/STB)/cc_sto = scf/STB). Rs_d flash-anchored counting down: `rs_d_i = rs_flash - Σ_{k=2..i} drs_k`; **`rs_d(psat) = rs_flash` exactly** (D-022 ledger row: sheet J15 includes I16).
- Gas gravity per stage: composition slot (`stream.gas_gravity()`) else override else error (validation already guarantees).
- `bg_i = P_STD_PSIA_CORR?` — sheet: `14.73*(T_f+459.67)*Z/(519.67*P)` rcf/scf with P as-entered (D3 policy; constants from core).
- `bt_d_i = bo_d_i + cum_gas_scf_i * CC_PER_SCF * bg_i / v_sto_cc` (col O).
- Surface (flash-basis) conversion: `rs_surface_i = rs_flash - (rs_flash - rs_d_i) * bo_flash / bo_d_psat`; `bo_surface_i = bo_d_i * bo_flash / bo_d_psat` (cols P/Q, Amyx form).
- Mass-balance oil density: `rho_i = (rho_at_psat*v_at_psat - Σ removed gas mass)/v_oil_after_i`, gas mass = `v_std_cc * γg * AIR_DENSITY_STD_G_CC` (col R).
- Mass balance closure: mass at Psat vs (residual STO mass = rho_sto*v_sto) + cum gas mass; grade with `"mass_balance_pct"` (2/3). Expose the sheet's sensitivity-ordered adjustment guidance list as `ADJUSTMENT_GUIDANCE` tuple (rows 50-59 text).

**Goldens:** fixture `3_ADRIC_DV_Calc_v6.2.xlsx` cached cells (template state: stage-1-only populated + constants — E15 Bo_d(psat) = 1.33088, B43 mass 434.3276, B46 403.6004, B47 7.61 FAIL, gasometer constants B16/E16/B18); PLUS a synthetic fully-populated dataset (published DV table from the `Fin PVT adjusted` fixture's DL sheet — real Rs_d to 1648.1/Bo_d to 1.8424 series) exercised end-to-end with internal-consistency assertions (Rs_d monotone, Bt≥Bo, closure), clearly labeled. Digest spot values in-task for cross-check.

---

### Task 9: Amyx/Carlson adjustment (`pvt/adjust/`)

**Files:** Create `pvt/adjust/__init__.py`, `amyx.py`, `carlson.py`, `endpoint_anchor.py`; Test `tests/golden/test_adjust_workbook.py`

**Formulas (dissected `Diff_PVT_Adjusting.xlsx`, committed fixture):**
- Amyx: `bo_adj = bo_d * bo_flash/bo_db` (all rows); above/at Pb `rs_adj = rs_flash`; below: `rs_adj = rs_flash - (rs_db - rs_d)*bo_flash/bo_db`.
- Carlson: `bo_adj = bo_d * rs_flash/rs_db`; `rs_adj = rs_d * rs_flash/rs_db`.
- Endpoint re-anchoring (second pass, below-Pb linear ramp over stage counter): Bo forced to 1.0 at P=0; Rs forced to 0 (Amyx only; kills the negative-Rs artifact) per the sheet's H/I-col formulas.
- Goldens: the fixture's cached first-pass AND second-pass columns for both method sheets (incl. the documented negative first-pass Rs −6.243 at P=0 reproducing, then 0 after anchoring); divergence metric `amyx_vs_carlson_dev_pct` exposed for QC.
- Wire into DV results: `dv.calc` gains `adjusted(method=...)` producing the simulator-ready table.

---

### Task 10: DV molar-balance QC + Hoffmann integration

- `pvt/qc/checks/molar_balance.py`: component-level recombination of STO + Σ stage gases vs entered reservoir fluid (sheet `Material_Balance_QC` blocks: residual moles = m/(MW·G_PER_LB) lbmol, stage moles = scf/SCF_PER_LBMOL, per-component dev% with PASS ≤2 / REVIEW ≤3 / FAIL, "new"/"N/A" states) → `MolarBalanceResult` + registry `"molar_balance_pct"` (exists).
- DV Hoffmann: reuse `hoffman_crump.check` with STO as liquid per selected stage gas (document the sheet's approximation); K-trend helper for C1..C6 vs log P.
- Tests: synthetic exact-balance dataset (dev 0) + perturbed dataset hitting each severity + template-state behaviors.

---

### Task 11: DV importer (`pvt/io/excel_import/dv_v62.py`)

Cell map (verify in-task): `Sample_Info` B/E blocks (metadata + flash anchors + Psat/rho CrossRef provenance fields — populate `Study` with CrossRefs, source_test "CCE"/"Flash"), `DV_Input` B8/E9/B15/rows 23-48 (cols B,D,E,F,G,I,J,N,O), `Component_Properties!D56` C36+ MW, `Compositions_Master` stage-gas columns H..W + STO X/Y + reservoir F/G (slot-shift convention: composition slot n feeds DV stage n+1 — encode explicitly). Dead cells NOT imported, listed in the module docstring (E10/E11 overrides, E15 back pressure, B15 field GOR — defect rows D4/D6 already in the review doc). Integration goldens through the template state.

---

### Task 12: DV page + report + 3a wrap

- `ui/pages/dv_page.py` + `_logic`: upload/manual; stage table editor; results: DV table (Bo_d/Rs_d/Bt_d/Z/Bg/γg), surface-corrected table with method selector (Amyx/Carlson/anchored) + divergence QC, mass & molar balance panels with the sensitivity guidance rendered on FAIL, Hoffmann chart; report download (`dv_tables` with LIMS DL-section names).
- Home card flip, nav icon, CLI `dv --workbook` subcommand (flash-subcommand pattern).
- Manual chapters: `docs/manual/12-cce.md` + `13-dv.md` (equation-accurate, plain-terms box, field tables per the ch-03 style; regenerate figures only if the screen-map changed); build PDF; README module list.
- Full gate + push branch; NO PR yet (3b continues on this branch).

---

## Self-review checklist
- Spec §2 Phase 3 coverage: CCE (T1-6), DV (T7-12), adjustment (T9) ✓; MSS/Density/Viscosity → plan 3b.
- New QC keys introduced: cce_sp_fit_dev_pct, cce_tp_fit_dev_pct, cce_rho_v_spread_pct, psat_breakpoint_vs_visual_psi — all flagged as proposals for Swej calibration alongside hoffman_r2.
- Every golden sourced from committed fixture workbooks' cached cells; digest values appear only as cross-check spot values inside task dispatches.
