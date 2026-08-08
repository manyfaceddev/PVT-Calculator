# PVT Lab Platform — Design Specification

Date: 2026-08-09
Status: awaiting user review
Owner: Swej Shah (PVT domain owner) with Claude (architecture + implementation)
Repo: `PVT-Calculator` (this repository). This restructure lands on `main`; all subsequent work on feature branches (no worktrees).

## 1. Purpose

A production-grade, ADNOC-internal platform for a commercial PVT laboratory: calculations, QC, analysis, and reporting across the lab's full scope of work. Reference class of software: Calsep PVTsim, whitson+. The engine computes correct physics; the lab's validated Excel workbooks serve as specifications and golden test fixtures, never as the calculator.

UI design reference: the PVT tab of `master_calc_suite_v8` (ADNOC-branded HTML mock): provenance → fluid type → study navigation, navy #00205B / action-blue #0047BB design language, QC status as a first-class surface.

## 2. Scope

### In scope (phased)
- **Phase 0** — repo restructure, core data model, units/constants layer, test infrastructure with 100% coverage gate.
- **Phase 1** — correlations layer: gas Z-factor (DAK primary, Hall-Yarborough secondary), pseudo-criticals (Sutton, SBV, Piper-McCain-Corredor, Wichert-Aziz sour correction, Erbar C7+), bubble point (Standing, Vasquez-Beggs, Glaso, Al-Marhoun), viscosity (Lee-Gonzalez-Eakin gas, Jossi-Stiel-Thodos dense gas).
- **Phase 2** — Flash Separation + Live Oil Preparation/Recombination **end-to-end**: engine, QC, Excel import of the ADRIC templates, Streamlit page in v8 styling, report export. This is the demonstrable slice.
- **Phase 3** — CCE, DV (with Amyx/Carlson flash-basis adjustment + endpoint re-anchoring), MSS, Density HPHT, Viscosity HPHT.
- **Phase 4** — CVD (Whitson-style material balance), MMP slim-tube (including a real two-line-intersection solver Excel never had).
- **Phase 5** — cross-test QC Center implementing the full PVT-check catalog; consolidated study reporting.

Implementation plans are written per phase group: the first plan (next step after this spec is approved) covers Phases 0–2; Phases 3–5 each get their own plan cycle informed by what the previous phase taught.

### Out of scope (for now, seams reserved)
- Cubic EOS (PR/SRK) flash and phase envelopes. Z-factor correlations with manual override cover current lab practice; the `correlations/` + `experiments/` split leaves a clean seam for an `eos/` package later.
- Multi-user server deployment. v1 runs locally (`streamlit run`), single user.
- Non-PVT modules of the master suite (SCAL, RCA, water chemistry, geochemistry...).
- Asphaltene/SARA/swelling studies (ARCHIVE folders exist; same experiment-package pattern will absorb them later).

## 3. Architecture principles

1. **Pure engine, thin UI.** `pvt/` never imports Streamlit or anything UI-adjacent. `ui/` contains presentation only; every number shown is computed in `pvt/`. Overlap target: zero calculation logic in `ui/`.
2. **Single responsibility, one file per concept.** One correlation per module. One experiment (lab test) per package with the `models.py / calc.py / validate.py` pattern the existing recombination module proved.
3. **Correct physics, documented deviations.** Where a source workbook is provably wrong, the engine implements the correct form and the deviation is recorded in `docs/excel-deviations.md` with cell-level proof. Each module's deviations are reviewed with Swej point by point at implementation time before the behavior is locked.
4. **Excel as I/O, not as calculator.** The app imports lab data from filled ADRIC templates (reading only the yellow input cells) and exports reports to Excel/PDF. Calculation authority lives in Python.
5. **Cross-test data flows are first-class.** Today CCE's Psat is hand-retyped into DV/MSS. In the platform a `Study` holds references, so downstream tests consume upstream results explicitly and QC can flag staleness.
6. **100% test coverage, enforced in CI.** Three test tiers (§8).

## 4. Repository layout

```
pvt/                          # pure engine
  core/
    constants.py              # standard conditions + exact conversion constants (§6)
    units.py                  # field/SI conversion layer; the ONLY place conversions live
    components.py             # Component + ComponentLibrary (Katz-Firoozabadi 52-slot table,
                              #   C36+ MW override; single shared source for all experiments)
    composition.py            # CompositionStream: mol%/wt%, normalization, MW (mol & wt routes),
                              #   ideal-mixing density, gas gravity, normalization QC
    sample.py                 # Sample, Study, CrossRef (Psat from CCE → DV/MSS etc.), sign-off
    exceptions.py             # typed errors (InputValidationError, ConvergenceError, ...)
  correlations/
    zfactor/dak.py            # Dranchuk-Abou-Kassem, Newton, correct derivative
    zfactor/hall_yarborough.py
    pseudocritical/sutton.py
    pseudocritical/sbv.py     # Stewart-Burkhardt-Voo mixing rules
    pseudocritical/piper_mccain.py   # gravity + compositional forms (published coefficients)
    pseudocritical/wichert_aziz.py
    pseudocritical/erbar.py   # C7+ characterization (from Gas_Gradient VBA)
    bubble_point/standing.py  # (exists; gains computed exponent a and range guards)
    bubble_point/vasquez_beggs.py
    bubble_point/glaso.py
    bubble_point/almarhoun.py
    viscosity/lee_gonzalez_eakin.py
    viscosity/jossi_stiel_thodos.py
  experiments/                # one package per lab test: models.py / calc.py / validate.py
    flash/                    # atmospheric flash, water-pump method (GOR, Bo, shrinkage, API,
                              #   mass-basis recombination, plus-fraction properties)
    recombination/            # exists (volumetric SF/FF); gains molar route: F_gas/F_oil split,
                              #   wellstream z_i, cylinder charging volumes, actual-GOR verify
    cce/                      # RelVol, Y-function, compressibilities, Psat pick + QC
    dv/                       # Bo_d/Rs_d/Bt_d, Bg, stage gravities, mass + molar balance
    mss/                      # stage GORs, Bo_fb/Rs_fb, separator-optimization plots
    density/                  # HPHT water-pump gravimetric with water-K correction
    viscosity/                # rolling-ball sweep, PVTsim comparison, LGE below Psat
    cvd/                      # constant-volume depletion material balance (Phase 4)
    mmp/                      # slim-tube runs, recovery curves, MMP solver (Phase 4)
  adjust/
    amyx.py                   # DL → flash-basis correction (Amyx/Dodson)
    carlson.py                # GOR-ratio alternative
    endpoint_anchor.py        # second-pass linear re-anchoring (kills negative-Rs artifact)
  qc/
    engine.py                 # QCResult, Severity(PASS/REVIEW/FAIL), ThresholdRegistry
    checks/hoffman_crump.py   # log10(K·P) vs F linearity (computed b_i from Tb/Pc/Tc)
    checks/buckley.py         # ln K vs Tc² linearity
    checks/y_function.py      # regression fit + per-point error
    checks/material_balance.py       # mass closure (flash/DV/MSS/CVD variants)
    checks/molar_balance.py          # component-level recombination vs reference
    checks/gor_backcalc.py           # GOR from MB-diagram slope
    checks/compressibility_sign.py   # Co/Cg ≥ 0; Eclipse-style total compressibility screen
    checks/composition_normalization.py
    checks/whitson_torp_cvd.py       # CVD back-calculation to residual liquid (Phase 4/5)
  io/
    excel_import/             # one reader per ADRIC template (yellow-cell maps from the digests)
    excel_export/
  reporting/
    tables.py                 # schema-driven report tables (parameter/value/unit rows)
    study_report.py
ui/                           # Streamlit only
  app.py                      # st.navigation shell
  theme.py                    # v8 design tokens (#00205B, #0047BB, tints, QC dot colors)
  pages/                      # one module per study page; session-state keys namespaced per page
  common/                     # header, metric cards, QC pills, calc-steps expander, report table
tests/
  unit/                       # mirrors pvt/ 1:1; sanity + limit tests
  golden/                     # Excel-cached fixtures, one module per source workbook
  fixtures/                   # fixture data files (frozen input/expected pairs)
docs/
  excel-deviations.md         # the bug ledger (cell-proofed), grows per module
  superpowers/specs/          # this document and successors
cli.py                        # retained; extended per phase to stay feature-par with UI
```

Existing code disposition: `pvt/recombination/` and `pvt/correlations/standing.py` are kept and refactored in place; `pvt_calc.py` (deprecated shim) is deleted; `ui/recombination.py` is rebuilt as a page under the new shell (its leaked logic — compressibility evaluation, unit conversions in callbacks — moves into `pvt/`); dead components and the stale README are replaced.

## 5. Core data model

- **`Component`** (frozen dataclass): code, name, MW, liquid density, Tb, Pc, Tc (+ optional acentric factor for the future EOS seam). **`ComponentLibrary`**: the Katz-Firoozabadi 52-slot table as the single shared instance, with per-study C36+ MW override (the only editable property, matching lab convention).
- **`CompositionStream`**: ordered mole% and/or weight% aligned to the library; provides normalization, MW by both routes, cross-check deviation, ideal-mixing liquid density, gas gravity, and its own normalization QC (±0.5 PASS / ±2 REVIEW bands from the house convention).
- **`Sample` / `Study`**: sample metadata (well, reservoir, depth, IDs, team) entered once; each experiment attaches to a Study. **`CrossRef`** models upstream results (e.g. `psat` from CCE consumed by DV/MSS) with provenance, replacing manual retyping.
- **Units**: engine computes in a fixed internal basis (psia, °R, cc, g, lbmol where the lab sheets use them); `units.py` owns every conversion; UI/CLI/import layers convert at the boundary only. Field and SI presentation both supported; the SI "sm³" basis ambiguity found in the current repo (60 °F vs 15 °C) is resolved by making the standard-condition basis an explicit, documented constant.

## 6. Constants policy

All physical/conversion constants live in `core/constants.py`, exactly once, with source comments. The lab's exact values are canonized for golden-test parity: P_std 14.73 psia (lab basis, cf. correlations' 14.696 documented separately where a source requires it), T_std 60 °F = 519.67 °R = 288.7056 K, 28316.85 cc/scf, 158987.29 cc/STB, 379.482 scf/lbmol, air MW 28.964, air density 0.0012255 g/cc @ std, R = 10.7316 psia·ft³/(lbmol·°R) (never 10.07; deviation documented), 453.59237 g/lb, 5.6146 ft³/bbl (parity flags where sheets used 5.615/5.6156). Any module needing a source workbook's variant constant for a golden test declares it locally in the test, not in the engine.

## 7. Error handling

- `validate.py` functions return human-readable message lists (UI-friendly), as today.
- `calc` entry points call their validators by default and raise `InputValidationError` listing the failures; `validate=False` opt-out exists for callers that pre-validated. This closes the "engine never calls its own validators" gap in the current module.
- Iterative solvers (`dak`, `hall_yarborough`, MMP breakpoint search) raise `ConvergenceError` with diagnostics rather than returning garbage; hard guards on division (SF=0, P=0) raise typed errors instead of ZeroDivisionError.

## 8. Testing strategy (100% coverage, enforced)

1. **Unit-sanity tier** (`tests/unit/`): analytic limits and physical behavior per module. Examples: Z → 1 as P → 0; DAK and Hall-Yarborough agree within tolerance on sweet gas; Y-function undefined at/above Psat; recovery monotone non-decreasing; unit round-trips are identity; each correlation's published worked example.
2. **Golden tier** (`tests/golden/`): exact cached values extracted from the source workbooks (already captured during the digests), e.g. flash GOR 335.13 scf/bbl / Bo 1.32600 / API 31.133; LiveOil F_gas 0.370636 / wellstream MW 127.40 / charges 150 cc + 25.38 cc; CCE RV/Y/mean-compressibility targets and fit R²; DAK fixtures (verified to 1e-6 already); PVT-check fixtures (GOR back-calc 1285.3387, slope −0.5153772, Eclipse Tc failures); MMP template (Bo 1.6665, MB error 0.185%). CVD and the MMP QC tool ship empty, so their fixtures are synthetic: published datasets (e.g. Whitson & Brulé CVD table) frozen into `tests/fixtures/`.
3. **Deviation tier**: for each ledger entry, a test asserting the *correct* engine value with a comment linking `docs/excel-deviations.md` (e.g. Piper CO2 coefficient −0.90348, not the transposed −0.09034; DV bubble-point Rs excludes stage-2 gas; CVD helper cells resolve to R and 379.482).

CI: existing GitHub Actions workflow extended with `pytest --cov=pvt --cov-fail-under=100`, ruff, and mypy on `pvt/` (UI excluded from coverage gate but smoke-imported with streamlit installed).

## 9. QC engine

`QCResult(check_id, severity, value, threshold, message, context)` with severity PASS/REVIEW/FAIL, aggregated per experiment and per study. Thresholds live in a registry seeded from the house conventions (composition totals ±0.5/2; mass balance 2/3%; molar balance 2/3%; Z deviation 2/5%; density %RSD 0.5/1; viscosity vs sim 2/5%; MMP mass balance ±5%), all overridable per study with an audit note. Graphical checks from PVT-check (Buckley, Hoffmann, Y-function, K-trends) are quantified: regression + configurable numeric tolerances, with plots rendered in the UI. The evolution-trail resurrections (CCE compressibility monotonicity, ρ×V constancy, Hall-Yarborough Z verification for DV) are included.

## 10. UI design

Streamlit multipage app via `st.navigation`; the PVT-tab tree from the v8 mock becomes the navigation model (provenance → fluid type → study). `theme.py` carries the v8 tokens (navy #00205B, action blue #0047BB, tints #e8f0fe/#f0f5ff, QC red #e53e3e / green #38a169 / amber #dd9a0a). Session-state keys namespaced per page (`recomb.v_live`), global keys (`units`, `study`) separate. Each study page: inputs (form or Excel upload), results cards, calculation-steps expander (the lab-loved feature from the current app), QC panel with severity pills, and report download. No `data-testid` CSS hacks where a supported theming path exists.

## 11. Git workflow

This restructure (Phase 0) lands directly on `main` (user decision, 2026-08-09). Every subsequent phase/feature: feature branch → PR → merge; no worktrees. Commits at each coherent step; the stashed diagram tweak (`stash@{0}`) stays untouched until the UI rebuild absorbs or obsoletes it.

## 12. Risks and mitigations

- **Fixture drift** (engine "fixed" vs workbook "as-is"): every intentional difference must exist in `docs/excel-deviations.md` before the deviating test lands; anything else failing golden parity is a bug in the port.
- **Scope breadth**: phases are strictly sequential; a phase is done only at 100% coverage with golden tests green.
- **UI/engine drift** (the current repo's CLI/UI divergence): both front-ends consume the same result dataclasses; features land engine-first.
- **Empty-template tests** (CVD/MMP): synthetic fixtures clearly labeled as such, replaced by real lab datasets when Swej supplies them.
