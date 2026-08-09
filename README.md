# PVT Calculator

A PVT laboratory engine and Streamlit front-end for reservoir-fluid property
calculations. The full target scope is a production-grade platform covering
correlations, flash/recombination, CCE/DV/CVD/MSS, MMP, and cross-test QC for
a commercial PVT lab; see
[`docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`](docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md)
for the full design. The engine (`pvt/`) is pure Python with no UI
dependency; the lab's validated Excel workbooks are treated as specifications
and golden test fixtures, never as the calculator.

Currently implemented: **Phase 0** (repo restructure, core data model,
100% coverage gate) plus the pre-existing separator-recombination module and
the Standing bubble-point correlation. Phases 1–5 (full correlations layer,
additional experiment modules, Excel I/O, reporting, cross-test QC) are
planned — see [Phase roadmap](#phase-roadmap) below.

---

## Quick start

```bash
pip install -e ".[dev]"

# Streamlit app (separator recombination module)
streamlit run app.py

# Command-line interface (same engine, no UI)
python cli.py --help
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
  correlations/
    bubble_point/
      standing.py                     # Standing (1947) bubble-point correlation
  experiments/
    recombination/                    # separator fluid recombination (models/calc/validate)
  qc/
    engine.py                         # QCResult, Severity, ThresholdRegistry, grade(), worst()

ui/                                   # Streamlit presentation only — no calculation logic
  theme.py                            # design tokens (v8 palette) + inject() CSS
  common/
    components.py                     # shared components (page_header, metric_card, qc_pill, ...)
  pages/
    flash_page.py                     # Flash Separation (SSF) page
    recombination_page.py             # Recombination / Live Oil page

tests/
  unit/                               # mirrors pvt/core + pvt/qc, 1:1
  fixtures/                           # frozen workbook-derived fixture data (e.g. sa372.py)
  test_correlations.py                # Standing bubble-point tests
  test_recombination_calc.py          # recombination calculation tests
  test_recombination_validate.py      # recombination input-validation tests

docs/
  excel-deviations.md                 # ledger of every deliberate engine/workbook difference
  superpowers/specs/                  # design spec
  superpowers/plans/                  # phase implementation plans

app.py                                # Streamlit entry point (st.navigation shell over ui/pages/)
cli.py                                # command-line interface over the same engine
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
a real test or deleted (YAGNI).

The design spec (§8) defines three test tiers, built out as each module
lands:

1. **Unit-sanity** (`tests/unit/`) — analytic limits and physical behavior
   per `pvt/core` / `pvt/qc` module (unit round-trips are identity,
   zero-sum/degenerate inputs raise `InputValidationError`, threshold
   grading boundaries, etc.).
2. **Golden** — exact values cached from the source Excel workbooks (see
   `tests/fixtures/sa372.py` for the current SA-372 sample data, consumed
   by `tests/unit/test_composition.py`). A dedicated `tests/golden/` tier
   lands as Phase 1/2 correlation and experiment modules are ported.
3. **Deviation** — one test per `docs/excel-deviations.md` entry, asserting
   the engine's correct value where it deliberately departs from a
   workbook.

Also run before committing:

```bash
python3 -m ruff check pvt tests
python3 -m mypy pvt
```

---

## Excel deviations ledger

[`docs/excel-deviations.md`](docs/excel-deviations.md) records every place
the Python engine deliberately differs from a source workbook — workbook +
cell proof, Excel behavior, engine behavior, and review status
(`proposed` until reviewed point-by-point, then `approved`/`parity-kept`).
Two entries exist today: canonization of the Katz-Firoozabadi component
library onto one table (D-001), and the engine's `InputValidationError` on
bad calc inputs where the source sheets have no validation at all (D-002).

---

## Phase roadmap

Per the design spec (§2):

- **Phase 0 — done.** Repo restructure into `pvt/core`, `pvt/qc`,
  `pvt/correlations`, `pvt/experiments`; canonical constants/units/component
  library; `CompositionStream`; QC severity engine; 100% coverage gate.
- **Phase 1 — planned.** Correlations layer: gas Z-factor (DAK, Hall-Yarborough),
  pseudo-criticals (Sutton, SBV, Piper-McCain-Corredor, Wichert-Aziz,
  Erbar C7+), bubble point (Vasquez-Beggs, Glaso, Al-Marhoun), viscosity
  (Lee-Gonzalez-Eakin, Jossi-Stiel-Thodos).
- **Phase 2 — planned.** Flash Separation + Live Oil Preparation/Recombination
  end-to-end: engine, QC, Excel import of ADRIC templates, Streamlit page in
  v8 styling, report export.
- **Phase 3 — planned.** CCE, DV (with Amyx/Carlson flash-basis adjustment),
  MSS, Density HPHT, Viscosity HPHT.
- **Phase 4 — planned.** CVD (Whitson-style material balance), MMP slim-tube.
- **Phase 5 — planned.** Cross-test QC Center; consolidated study reporting.

---

*Standard conditions: lab basis 14.73 psia / 60°F (see `pvt/core/constants.py`
for the full canonized set and source citations). Always verify calculator
output with a qualified reservoir engineer before laboratory use.*
