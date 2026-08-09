# Chapter 1: Introduction

## 1.1 What This Platform Is

The PVT Lab Platform (packaged as `pvt`, described in `pyproject.toml` as the
"ADRIC PVT laboratory platform engine") is a production-grade, ADNOC-internal
system for a commercial PVT laboratory: calculations, quality control,
analysis, and reporting across the lab's full scope of work. The design
specification names its reference class explicitly: Calsep PVTsim,
Whitson+ (`docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`,
Section 1).

Two front ends sit on top of one calculation engine:

- A Streamlit web application (`app.py`, pages under `ui/pages/`), titled
  "ADRIC PVT Platform" in its page configuration, for interactive lab use.
- A command-line interface (`cli.py`) exposing the same engine for scripted
  or headless runs.

Both consume the same typed result dataclasses, so a number produced by the
web app and the same input run through the CLI are computed by identical
code paths: there is exactly one place addition, a correlation, or a QC
threshold is implemented.

## 1.2 Design Philosophy

The design spec (Section 3) lays out the principles the codebase is built
to, and the repository visibly follows them:

**Correct physics, documented deviations.** Where a source ADRIC workbook is
provably wrong, the engine implements the physically correct form rather
than reproducing the bug, and the deviation is recorded in
`docs/excel-deviations.md` with cell-level proof: which workbook, which
cell, what Excel does, what the engine does instead, and a review status
(`proposed` until reviewed point by point with the PVT domain owner, then
`approved` or `parity-kept`). As of this writing the ledger holds entries
D-001 through D-011 and D-015 through D-018 (18 entries), spanning the
component-library canonization, the validation posture, correlation-formula
corrections (a transposed CO2 coefficient, an inverted exponent, a missing
`10^` step, a hardcoded gas-constant literal), and Phase 2's
standard-condition-basis and GOR-direction choices. One entry, D-018 (the
LiveOil v4.1 GOR-basis divide direction), is marked "NEEDS SWEJ RULING"
rather than merely `proposed`: it is a case where the engine's chosen
convention could not be verified against the workbook's own golden values,
because the workbook's shrinkage factor happened to be 1.0.

**Excel workbooks as golden ground truth, never as the calculator.** The
lab's validated Excel workbooks are treated as specifications and as golden
test fixtures. The platform imports lab data from filled ADRIC templates by
reading only the yellow input cells (never a formula-computed cell) and
recomputes every derived quantity in Python; it exports reports back to
Excel. Calculation authority lives entirely in Python.

**Deviations-ledger discipline.** Every deliberate difference from a
workbook must exist in `docs/excel-deviations.md` before a deviating test
is allowed to land; any other golden-parity failure is treated as a bug in
the port, not a sanctioned difference. Each module's deviations are meant to
be reviewed with the PVT domain owner point by point before the behavior is
considered locked (spec Section 12).

**Pure engine, thin UI.** `pvt/` never imports Streamlit or anything
UI-adjacent; `ui/` contains presentation only, and every number the UI
displays is computed inside `pvt/`. This is verifiable directly: nothing
under `pvt/` imports `streamlit`, and the Streamlit `AppTest` smoke tests in
`tests/ui/` exist specifically to keep that boundary honest.

**Single responsibility, one file per concept.** One correlation per module
(e.g. `pvt/correlations/bubble_point/standing.py` holds only Standing's
1947 correlation), and one lab experiment per package following a
`models.py` / `calc.py` / `validate.py` pattern.

**Cross-test data flows as first-class objects.** Today a value like Psat
gets hand-retyped from one workbook into the next. The platform's `Study`
dataclass is designed to hold `CrossRef` references instead, so a downstream
test consumes an upstream result explicitly and QC can flag when that
reference has gone stale (spec Section 3, item 5; see Chapter 3 for the
current shape of `Study`/`CrossRef`).

**100% test coverage, enforced.** `pyproject.toml` wires
`--cov=pvt --cov-fail-under=100` with branch coverage into every `pytest`
run; see Chapter 2 for the mechanics.

## 1.3 Architecture Overview

The engine/UI split is a directory split. `pvt/` is pure Python with no UI
dependency; `ui/` is Streamlit-only presentation. The package map below is
drawn directly from the current repository tree (not the design spec's
target-state layout, which includes several packages (`adjust/`, most of
the QC `checks/` catalog, `reporting/study_report.py`) planned for later
phases and not yet present).

```text
pvt/                              # pure engine, no Streamlit/UI imports
  __init__.py                     # flat re-export surface: from pvt import ...
  constants.py                    # legacy shim -> pvt.core.constants (removed after Phase 2)
  core/
    constants.py                  # canonical physical constants + conversion factors
    units.py                      # field/SI conversion functions (only place conversions live)
    components.py                 # Component, ComponentLibrary (Katz-Firoozabadi, 52 slots)
    composition.py                # CompositionStream: mol%/wt%, normalization, MW, density
    plus_fractions.py             # C7+/C11+/C20+/C36+ plus-fraction properties
    sample.py                     # Sample, Study, CrossRef dataclasses
    exceptions.py                 # PvtError, InputValidationError, ConvergenceError
  correlations/                   # Phase 1: empirical PVT correlations
    bubble_point/                 # standing, vasquez_beggs, glaso, almarhoun
    pseudocritical/               # sutton, sbv, piper_mccain, wichert_aziz, erbar
    viscosity/                    # lee_gonzalez_eakin, jossi_stiel_thodos, critical_volumes
    zfactor/                      # dak (Dranchuk-Abou-Kassem), hall_yarborough
  experiments/                    # one package per lab test
    flash/                        # atmospheric flash separation (models/calc/validate/recombine)
    recombination/                # separator recombination: volumetric (SF/FF) + molar routes
      compressibility.py          #   effective_c_o: oil compressibility, constant/polynomial
      molar.py, loading.py        #   molar composition split + cylinder loading plan
  io/
    excel_import/                 # one reader per ADRIC template -> typed dataclasses
      flash_v61.py                #   ADRIC_Flash_Separation_Calc_v6.1.xlsx
      liveoil_v41.py               #   ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx
  qc/
    engine.py                     # QCResult, Severity, ThresholdRegistry, grade(), worst()
    checks/                       # composition_normalization, mw_consistency, hoffman_crump
  reporting/
    tables.py                     # ReportTable/ReportRow builders (flash_tables, recombination_tables)
    excel_export.py               # write_report: ADRIC-styled single-sheet .xlsx (or BytesIO)

ui/                                # Streamlit presentation only, no calculation logic
  theme.py                         # v8 design tokens + inject() CSS
  common/components.py             # page_header, metric_card, qc_pill, qc_panel, calc_steps, ...
  pages/
    flash_page.py, flash_page_logic.py               # Flash Separation (SSF)
    recombination_page.py, recombination_page_logic.py  # Recombination / Live Oil

tests/
  unit/                            # mirrors pvt/core + pvt/qc + pvt/experiments, 1:1
  golden/                          # workbook-cached golden-value tests (SA-372 sample)
  fixtures/                        # frozen workbook-derived fixture data + the two .xlsx templates
  ui/                              # Streamlit AppTest smoke tests (outside the pvt coverage gate)

docs/
  excel-deviations.md              # the deviations ledger
  workbook-defect-review.md        # formula-level defect catalog awaiting domain-owner ruling
  superpowers/specs/               # design spec(s)
  superpowers/plans/                # phase implementation plans

app.py                              # Streamlit entry point (st.navigation shell over ui/pages/)
cli.py                               # command-line interface over the same engine
```

Note one deliberate deviation from the design spec's own target layout: the
spec's Section 4 shows `app.py` and `theme.py` living under `ui/`; in the
repository as built, `app.py` sits at the repository root (it is the
project's actual Streamlit entry point, referenced by
`streamlit run app.py`) and `ui/theme.py` remains under `ui/`. The spec's
`pvt/core` also does not list `plus_fractions.py`, which exists in the
current tree implementing the "plus-fraction properties" capability the
spec's `experiments/flash` description calls for; it was implemented as a
shared `pvt.core` primitive (consumed via `CompositionStream`) rather than
nested inside `pvt/experiments/flash/`, since plus-fraction cuts apply to
any composition stream, not only a flash result. `pvt/qc/checks/` currently
implements three of the many check modules the spec's target layout lists
(`composition_normalization`, `mw_consistency`, `hoffman_crump`); the rest
(`buckley`, `y_function`, `material_balance`, `molar_balance`,
`gor_backcalc`, `compressibility_sign`, `whitson_torp_cvd`) are reserved
names for later phases. An `adjust/` package (Amyx/Carlson DL-to-flash-basis
correction, endpoint re-anchoring) does not exist yet either; it belongs to
Phase 3.

## 1.4 Current Scope

Per the design spec's phased scope (Section 2) and confirmed against what is
actually implemented in the repository:

- **Phase 0 (done).** Repository restructure; the core data model
  (`Component`/`ComponentLibrary`, `CompositionStream`, `Sample`/`Study`/
  `CrossRef`); the units/constants layer; typed exceptions; test
  infrastructure with the 100% branch-coverage gate on `pvt/`.
- **Phase 1 (done).** The correlations layer: gas Z-factor (Dranchuk-Abou-
  Kassem primary, Hall-Yarborough secondary), pseudo-criticals (Sutton, SBV,
  Piper-McCain-Corredor, Wichert-Aziz sour correction, Erbar C7+
  characterization), bubble point (Standing, Vasquez-Beggs, Glaso,
  Al-Marhoun), viscosity (Lee-Gonzalez-Eakin gas, Jossi-Stiel-Thodos dense
  gas).
- **Phase 2 (done, pending phase-wrap review).** Flash Separation and Live
  Oil Preparation/Recombination end to end: engine (volumetric SF/FF and
  molar composition-split recombination flows, an oil-compressibility
  model), QC checks (composition normalization, MW consistency,
  Hoffman-Crump crossplot), Excel import of both ADRIC templates
  (`flash_v61`, `liveoil_v41`), a two-page Streamlit UI in "v8" styling,
  `.xlsx` report export, and CLI parity (`cli.py recombine` /
  `cli.py flash`). This is the platform's first demonstrable end-to-end
  slice (spec Section 2).

This is what a user of the platform today can actually do: run flash
separation and recombination calculations, either by uploading a filled
ADRIC workbook or by typing values into a form; get graded QC results
against house thresholds; and export or print a report. Everything else
described below is roadmap.

### Phase roadmap (design spec, Section 2)

- **Phase 3, planned.** Constant Composition Expansion (CCE); Differential
  Vaporization (DV), including the Amyx/Carlson flash-basis adjustment and
  endpoint re-anchoring; Multi-Stage Separation (MSS); Density HPHT;
  Viscosity HPHT.
- **Phase 4, planned.** Constant Volume Depletion (CVD, Whitson-style
  material balance); MMP slim-tube analysis, including a real two-line-
  intersection solver the source Excel workbooks never had.
- **Phase 5, planned.** A cross-test QC Center implementing the full
  PVT-check catalog, and consolidated study-level reporting.

Explicitly out of scope for now, with the seams reserved rather than closed
off: cubic equation-of-state (PR/SRK) flash and phase envelopes (the
`correlations/` + `experiments/` split leaves room for a future `eos/`
package); multi-user server deployment (v1 runs locally via
`streamlit run`, single user); the master suite's non-PVT modules (SCAL,
RCA, water chemistry, geochemistry); and asphaltene/SARA/swelling studies
(spec Section 2).
