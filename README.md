# PVT Calculator

[![CI](https://github.com/manyfaceddev/PVT-Calculator/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/manyfaceddev/PVT-Calculator/actions/workflows/ci.yml)

An ADNOC-internal PVT laboratory platform: a pure-Python calculation engine
plus a Streamlit front-end for reservoir-fluid property calculations,
built for a commercial PVT lab's full scope of work (reference class of
software: Calsep PVTsim, whitson+). The engine (`pvt/`) has no UI
dependency; the lab's validated Excel workbooks are treated as
specifications and golden test fixtures, never as the calculator. Full
design: [`docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`](docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md).

---

## Quick start

```bash
pip install -e ".[dev]"

# Streamlit app (Flash Separation + Recombination / Live Oil pages)
streamlit run app.py

# Command-line interface (same engine, no UI) — two subcommands:

# `recombine`: multi-stage separator recombination from typed inputs
python cli.py recombine --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 \
              --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820

# `flash`: import a filled ADRIC Flash v6.1 workbook and print its report
python cli.py flash --workbook path/to/ADRIC_Flash_Separation_Calc_v6.1.xlsx

python cli.py --help

# Full test suite (100% branch-coverage gate on pvt/)
pytest
```

Requires Python >= 3.12 (see `pyproject.toml`). `launch.sh` starts the
Streamlit app bound to `0.0.0.0:8501` for LAN access; `run_pvt.sh` is a
virtualenv-aware wrapper around `cli.py`.

---

## What works today

**Phase 0 — foundation.** Repo restructured into `pvt/core`, `pvt/qc`,
`pvt/correlations`, `pvt/experiments`; canonical physical constants and
unit conversions; `Component`/`ComponentLibrary` (Katz-Firoozabadi 52-slot
table); `CompositionStream`; `Sample`/`Study` data model; QC severity
engine; 100% branch-coverage gate on `pvt/`, enforced in CI.

**Phase 1 — correlations library, 13 correlations.** Gas Z-factor
(Dranchuk-Abou-Kassem, Hall-Yarborough), pseudo-criticals (Sutton, SBV,
Piper-McCain-Corredor, Wichert-Aziz sour correction, Erbar C7+), bubble
point (Standing, Vasquez-Beggs, Glaso, Al-Marhoun), viscosity
(Lee-Gonzalez-Eakin gas, Jossi-Stiel-Thodos dense gas).

**Phase 2 — Flash Separation + Recombination, end to end.** Atmospheric
flash separation and Live Oil Preparation/Recombination (volumetric SF/FF
multi-stage flow and a molar composition-split flow, with an oil
compressibility model for cylinder charging volumes), QC checks
(composition normalization, MW consistency, Hoffman-Crump), Excel import
of both ADRIC lab templates (Flash v6.1, LiveOil v4.1), a two-page
Streamlit UI in v8 styling, ADRIC-styled `.xlsx` report export, and CLI
parity (`cli.py recombine` / `cli.py flash`).

Phases 3-5 (CCE/DV/MSS/Density/Viscosity HPHT, CVD/MMP, cross-test QC
Center) are planned — see [Phase roadmap](#phase-roadmap) below and
`docs/manual/11-deviations-and-roadmap.md` for what the dissected ADRIC
workbooks already tell us about each of those modules.

---

## Repo layout

```
pvt/                                  # pure engine — no Streamlit/UI imports
  __init__.py                         # flat re-export surface: from pvt import ...
  constants.py                        # legacy shim → pvt.core.constants (removed after Phase 2)
  core/
    constants.py                      # canonical physical constants + unit-conversion factors
    units.py                          # field/SI conversion functions
    components.py                     # Component, ComponentLibrary (Katz-Firoozabadi 52-slot table)
    composition.py                    # CompositionStream — mol%/wt%, normalization, MW, density
    plus_fractions.py                 # C7+/C11+/C20+/C36+ cut properties from a composition stream
    sample.py                         # Sample, Study, CrossRef dataclasses
    exceptions.py                     # InputValidationError, ConvergenceError
  correlations/                       # Phase 1 — empirical PVT correlations (13 total)
    bubble_point/                     # Standing, Vasquez-Beggs, Glaso, Al-Marhoun
    pseudocritical/                   # Sutton, SBV, Piper-McCain-Corredor, Wichert-Aziz, Erbar C7+
    viscosity/                        # Lee-Gonzalez-Eakin, Jossi-Stiel-Thodos, critical volumes
    zfactor/                          # Dranchuk-Abou-Kassem, Hall-Yarborough
  experiments/
    flash/                            # atmospheric flash separation (models/calc/validate/recombine)
    recombination/                    # separator recombination — two flows:
      models.py, calc.py, validate.py #   volumetric SF/FF (Carlsen & Whitson multi-stage)
      compressibility.py              #   effective_c_o — oil compressibility, constant/polynomial
      molar.py, loading.py            #   molar composition split + cylinder loading plan (LiveOil v4.1)
  io/
    excel_import/                     # ADRIC workbook importers -> typed dataclasses
      flash_v61.py                    #   ADRIC_Flash_Separation_Calc_v6.1.xlsx
      liveoil_v41.py                  #   ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx
  qc/
    engine.py                         # QCResult, Severity, ThresholdRegistry, grade(), worst()
    checks/                           # composition_normalization, mw_consistency, hoffman_crump
  reporting/
    tables.py                         # ReportTable/ReportRow builders (flash_tables, recombination_tables)
    excel_export.py                   # write_report — ADRIC-styled single-sheet .xlsx (or BytesIO)

ui/                                   # Streamlit presentation only — no calculation logic
  theme.py                            # design tokens (v8 palette) + inject() CSS
  common/
    components.py                     # shared components (page_header, metric_card, qc_pill,
                                       #   qc_panel, calc_steps, report_download, ...)
  pages/
    flash_page.py                     # Flash Separation (SSF) — upload workbook or manual entry
    flash_page_logic.py               #   pure helpers (composition editor, upload spooling)
    recombination_page.py             # Recombination / Live Oil — Volumetric (SF/FF) + Molar tabs
    recombination_page_logic.py       #   pure helpers (report tables, upload spooling)

tests/
  unit/                               # mirrors pvt/core + pvt/qc + pvt/experiments, 1:1
    correlations/                     # one test module per Phase 1 correlation
    experiments/                      # flash validate, molar recombination, compressibility
    qc/                               # QC check modules
  golden/                             # workbook-cached golden-value tests (SA-372 sample)
  fixtures/                           # frozen workbook-derived fixture data (sa372.py, sa372_flash.py)
    workbooks/                        # the two filled ADRIC .xlsx templates used by golden/import tests
  ui/                                 # Streamlit AppTest smoke tests (outside the pvt coverage gate)
  test_recombination_calc.py          # recombination calculation tests (volumetric flow)
  test_recombination_validate.py      # recombination input-validation tests

docs/
  excel-deviations.md                 # ledger of every deliberate engine/workbook difference
  workbook-defect-review.md           # formula-level defect review of the full ADRIC workbook set
  reference/gasprop_functions.bas     # reference VBA kernel used to cross-check the Python port
  manual/                             # this manual's source chapters + build output (see below)
  superpowers/specs/                  # design spec
  superpowers/plans/                  # phase implementation plans

scripts/
  build_manual.sh                     # pandoc build: docs/manual/*.md -> PVT-Platform-Manual.pdf

app.py                                # Streamlit entry point (st.navigation shell over ui/pages/)
cli.py                                # command-line interface over the same engine (recombine/flash)
launch.sh                             # LAN launcher for the Streamlit app (0.0.0.0:8501)
run_pvt.sh                            # virtualenv-aware wrapper around cli.py
pyproject.toml                        # packaging, pytest/coverage, ruff, mypy config
```

---

## Documentation

The full manual lives in `docs/manual/` as one chapter per file, compiled
to a single PDF by `scripts/build_manual.sh`:

- `docs/manual/00-title.md` — title page and abstract
- `docs/manual/01-introduction.md` through `docs/manual/02-installation.md` —
  platform purpose and architecture, and installation/running the platform
- `docs/manual/03-application-guide.md` — the at-the-bench guide to the
  Streamlit app: what screen to open, which field each reading goes into,
  and what the results mean
- `docs/manual/04-core-concepts.md` through `docs/manual/10-reporting.md` —
  the core data model, the correlations library, the flash/recombination
  workflow, Excel import, QC, and reporting, one chapter per topic
- `docs/manual/11-deviations-and-roadmap.md` — the deviations-ledger
  discipline, every current D-001..D-018 entry summarized, the open
  rulings, and the Phase 3-5 roadmap read against the dissected workbooks

Compiled output: `docs/manual/PVT-Platform-Manual.pdf` (see
[Building the manual](#building-the-manual) below). Two supporting
documents referenced throughout the manual live alongside the ledger:

- [`docs/excel-deviations.md`](docs/excel-deviations.md) — the deviations
  ledger itself (cell-level proof for every engine/workbook difference)
- [`docs/workbook-defect-review.md`](docs/workbook-defect-review.md) — the
  formula-level defect review of every ADRIC production workbook, compiled
  for point-by-point ruling with the PVT domain owner

---

## Testing

```bash
pytest
```

Runs the full suite with coverage (`pyproject.toml` sets
`--cov=pvt --cov-report=term-missing --cov-fail-under=100`, with
`[tool.coverage.run] branch = true`) — **the build fails if `pvt/` branch
coverage drops below 100%.** No `# pragma: no cover` is used except on
`if TYPE_CHECKING:` blocks; every other line and branch is either
exercised by a real test or deleted (YAGNI). `cli.py` and everything under
`ui/` sit outside this gate (`--cov=pvt` only instruments the engine
package) but are still exercised by their own test suites below.

Three test tiers, built out as each module lands:

1. **Unit-sanity** (`tests/unit/`) — analytic limits and physical behavior
   per `pvt/core` / `pvt/qc` / `pvt/correlations` / `pvt/experiments` module
   (unit round-trips are identity, zero-sum/degenerate inputs raise
   `InputValidationError`, threshold grading boundaries, etc.).
2. **Golden** (`tests/golden/`) — exact values cached from the source Excel
   workbooks, keyed to a single reference sample (SA-372; see
   `tests/fixtures/sa372.py` / `sa372_flash.py`) across the full flash and
   recombination chains, plus the Excel importers themselves
   (`test_import_flash_v61.py`, `test_import_liveoil_v41.py`). Every golden
   assertion anchors to a value cached in the source workbook, not to a
   recomputed one, so the test fails if the engine's output ever silently
   drifts from what the lab's own spreadsheet produced.
3. **Deviation** — one test per `docs/excel-deviations.md` entry, asserting
   the engine's correct value where it deliberately departs from a
   workbook.

`tests/ui/` additionally runs Streamlit `AppTest` smoke tests against
`app.py` and each `ui/pages/*.py` module — both tabs of each page boot
without exception, and at least one manual-entry flow per page is driven
end to end through the real engine and checked against a golden figure
(e.g. Flash's GOR card, Recombination's Gas Mole Fraction card).

Also run before committing:

```bash
python3 -m pytest                          # full suite + 100% pvt coverage gate
python3 -m ruff check pvt tests ui app.py cli.py
python3 -m mypy pvt
python3 -c "import pvt, ui, cli"           # import-smoke, matches the CI step
```

---

## Deviations-ledger discipline

Every place the Python engine deliberately differs from a source workbook
is recorded in `docs/excel-deviations.md` with cell-level proof before its
test lands — anything else failing golden parity is a bug in the port, not
a deviation. Each entry stays `proposed` until it is reviewed
point-by-point with the PVT domain owner, at which point it flips to
`approved` (the engine's form is correct) or `parity-kept` (the workbook's
form is kept deliberately); see `docs/manual/11-deviations-and-roadmap.md`
for the full current ledger and the open rulings.

---

## Phase roadmap

Per the design spec (§2):

- **Phase 0 — done.** Repo restructure into `pvt/core`, `pvt/qc`,
  `pvt/correlations`, `pvt/experiments`; canonical constants/units/component
  library; `CompositionStream`; QC severity engine; 100% coverage gate.
- **Phase 1 — done.** Correlations layer: gas Z-factor (DAK, Hall-Yarborough),
  pseudo-criticals (Sutton, SBV, Piper-McCain-Corredor, Wichert-Aziz,
  Erbar C7+), bubble point (Standing, Vasquez-Beggs, Glaso, Al-Marhoun),
  viscosity (Lee-Gonzalez-Eakin, Jossi-Stiel-Thodos).
- **Phase 2 — done, pending phase-wrap review.** Flash Separation + Live Oil
  Preparation/Recombination end-to-end: engine (volumetric SF/FF and molar
  composition-split flows, oil-compressibility model), QC checks
  (composition normalization, MW consistency, Hoffman-Crump), Excel import of
  both ADRIC templates, a two-page Streamlit UI in v8 styling
  (`ui/pages/flash_page.py`, `ui/pages/recombination_page.py`), `.xlsx`
  report export, and CLI parity (`cli.py recombine` / `cli.py flash`).
- **Phase 3 — planned.** CCE, DV (with Amyx/Carlson flash-basis adjustment),
  MSS, Density HPHT, Viscosity HPHT.
- **Phase 4 — planned.** CVD (Whitson-style material balance), MMP slim-tube.
- **Phase 5 — planned.** Cross-test QC Center; consolidated study reporting.

| Phase | Status | Scope |
|-------|--------|-------|
| 0 | done | Repo restructure, core data model, units/constants, 100% coverage gate |
| 1 | done | Correlations library (Z-factor, pseudo-criticals, bubble point, viscosity) |
| 2 | done, pending phase-wrap review | Flash + Recombination end-to-end, QC, Excel import/export, UI, CLI |
| 3 | planned | CCE, DV, MSS, Density HPHT, Viscosity HPHT |
| 4 | planned | CVD (material balance), MMP slim-tube |
| 5 | planned | Cross-test QC Center, consolidated study reporting |

---

## Building the manual

```bash
bash scripts/build_manual.sh
```

Concatenates `docs/manual/00-title.md` and chapters `01` through `11` (in
numeric order) through Pandoc into `docs/manual/PVT-Platform-Manual.pdf`
(table of contents, 2.5cm margins, LaTeX `report` class). Requires
`pandoc` and a `pdflatex`-providing LaTeX distribution on `PATH`; the
script fails loudly if either is missing or a chapter file is absent.

---

## Offline installation (locked-down PC)

For a target machine with no internet access, `scripts/make_offline_bundle.sh`
builds a self-contained folder (streamlit, openpyxl, and their full
transitive dependency closure as downloaded wheels, plus the source tree)
that installs entirely from local files with `pip install --no-index`:

```bash
# Run on a machine WITH internet access:
bash scripts/make_offline_bundle.sh win_amd64   # or omit the tag for this machine

# Copy dist/pvt-offline-<platform>/ to the target PC, then follow its
# INSTALL.txt: python -m venv, activate, pip install --no-index
# --find-links wheels ..., streamlit run app.py (or python cli.py ...).
```

See [`docs/manual/02-installation.md`, Section 2.7](docs/manual/02-installation.md#27-offline-installation-locked-down-pc)
for the full walkthrough, including the CLI-only path (needs only `pvt` +
`openpyxl`, no Streamlit at all).

---

*Standard conditions: lab basis 14.73 psia / 60°F (see `pvt/core/constants.py`
for the full canonized set and source citations). Always verify calculator
output with a qualified reservoir engineer before laboratory use.*
