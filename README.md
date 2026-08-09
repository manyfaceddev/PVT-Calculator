# PVT Calculator

A PVT laboratory engine and Streamlit front-end for reservoir-fluid property
calculations. The full target scope is a production-grade platform covering
correlations, flash/recombination, CCE/DV/CVD/MSS, MMP, and cross-test QC for
a commercial PVT lab; see
[`docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`](docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md)
for the full design. The engine (`pvt/`) is pure Python with no UI
dependency; the lab's validated Excel workbooks are treated as specifications
and golden test fixtures, never as the calculator.

Currently implemented: **Phase 0** (repo restructure, core data model, 100%
coverage gate), **Phase 1** (full correlations layer — gas Z-factor,
pseudo-criticals, bubble point, viscosity), and **Phase 2** (Flash Separation
+ Live Oil Preparation/Recombination end to end: engine, QC checks, Excel
import of the ADRIC lab templates, a two-page Streamlit UI in v8 styling,
`.xlsx` report export, and CLI parity). Phases 3–5 (CCE/CVD/MSS/MMP,
cross-test QC) are planned — see [Phase roadmap](#phase-roadmap) below.

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
python cli.py recombine --help
python cli.py flash --help
```

Requires Python ≥ 3.12 (see `pyproject.toml`).

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
    sample.py                         # Sample, Study, CrossRef dataclasses
    exceptions.py                     # InputValidationError, ConvergenceError
  correlations/                       # Phase 1 — empirical PVT correlations
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
  superpowers/specs/                  # design spec
  superpowers/plans/                  # phase implementation plans

app.py                                # Streamlit entry point (st.navigation shell over ui/pages/)
cli.py                                # command-line interface over the same engine (recombine/flash)
pyproject.toml                        # packaging, pytest/coverage, ruff, mypy config
```

---

## Testing

```bash
pytest
```

Runs the full suite with coverage (`pyproject.toml` sets
`--cov=pvt --cov-report=term-missing --cov-fail-under=100`) — **the build
fails if `pvt/` coverage drops below 100%.** No `# pragma: no cover` is used
except on `if TYPE_CHECKING:` blocks; every other line is either exercised by
a real test or deleted (YAGNI). `cli.py` and everything under `ui/` sit
outside this gate (`--cov=pvt` only instruments the engine package) but are
still exercised by their own test suites below.

The design spec (§8) defines three test tiers, built out as each module
lands:

1. **Unit-sanity** (`tests/unit/`) — analytic limits and physical behavior
   per `pvt/core` / `pvt/qc` / `pvt/correlations` / `pvt/experiments` module
   (unit round-trips are identity, zero-sum/degenerate inputs raise
   `InputValidationError`, threshold grading boundaries, etc.).
2. **Golden** (`tests/golden/`) — exact values cached from the source Excel
   workbooks, keyed to a single reference sample (SA-372; see
   `tests/fixtures/sa372.py` / `sa372_flash.py`) across the full flash and
   recombination chains, plus the Excel importers themselves
   (`test_import_flash_v61.py`, `test_import_liveoil_v41.py`).
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

## Excel deviations ledger

[`docs/excel-deviations.md`](docs/excel-deviations.md) records every place
the Python engine deliberately differs from a source workbook — workbook +
cell proof, Excel behavior, engine behavior, and review status
(`proposed` until reviewed point-by-point, then `approved`/`parity-kept`).
14 entries exist today (D-001 through D-011, D-015 through D-018), spanning
the Phase 0 component-library canonization and validation posture through
Phase 1's correlation-formula corrections and Phase 2's standard-condition
basis / GOR-direction choices — all still `proposed`, pending a point-by-point
phase-wrap review.

---

## Phase roadmap

Per the design spec (§2):

- **Phase 0 — done.** Repo restructure into `pvt/core`, `pvt/qc`,
  `pvt/correlations`, `pvt/experiments`; canonical constants/units/component
  library; `CompositionStream`; QC severity engine; 100% coverage gate.
- **Phase 1 — done.** Correlations layer: gas Z-factor (DAK, Hall-Yarborough),
  pseudo-criticals (Sutton, SBV, Piper-McCain-Corredor, Wichert-Aziz,
  Erbar C7+), bubble point (Vasquez-Beggs, Glaso, Al-Marhoun), viscosity
  (Lee-Gonzalez-Eakin, Jossi-Stiel-Thodos).
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

---

*Standard conditions: lab basis 14.73 psia / 60°F (see `pvt/core/constants.py`
for the full canonized set and source citations). Always verify calculator
output with a qualified reservoir engineer before laboratory use.*
