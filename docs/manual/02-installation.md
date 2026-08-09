# Chapter 2: Installation and Running the Platform

## 2.1 Requirements

The engine requires Python 3.12 or later. `pyproject.toml` pins this
explicitly:

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.37.1,<2",
    "openpyxl>=3.1,<4",
]
```

Runtime dependencies are deliberately minimal: `streamlit` powers the web
UI and `openpyxl` powers Excel import/export. Nothing under `pvt/` itself
requires a numerical library beyond the Python standard library (`math`,
`dataclasses`, `enum`).

Development dependencies, declared under the `dev` extra, add the test and
lint toolchain:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
]
```

## 2.2 Installation

Install the package in editable mode with the `dev` extra so the test and
lint tools come along:

```bash
pip install -e ".[dev]"
```

`[tool.setuptools.packages.find]` in `pyproject.toml` restricts what
`setuptools` discovers to `pvt*` and `ui*`; `app.py` and `cli.py` are
top-level scripts, not part of an installed package, and are simply run
from a checkout of the repository.

## 2.3 Running the Web Application

Launch the Streamlit app from the repository root:

```bash
streamlit run app.py
```

`app.py` also supports being launched directly, in which case it
re-execs itself through Streamlit:

```bash
python app.py
```

`app.py` is a thin `st.navigation` shell: it calls `st.set_page_config`,
injects the theme via `ui.theme.inject()`, and registers two pages, each
implemented as its own module under `ui/pages/`:

| Page title (navigation) | Module | What it does |
|---|---|---|
| Flash Separation (SSF) | `ui/pages/flash_page.py` | Two entry modes: upload a filled `ADRIC_Flash_Separation_Calc_v6.1.xlsx` workbook, or fill a manual-entry form mirroring `FlashVolumetrics`'s fields plus an optional composition editor seeded with the 52 Katz-Firoozabadi component codes; both then render metric cards, QC pills, the Hoffmann-Crump crossplot, a calculation-steps expander, and a report download. |
| Recombination / Live Oil | `ui/pages/recombination_page.py` | Two tabs: **Volumetric (SF/FF)**, a form-driven Carlsen & Whitson multi-stage recombination flow with oil-charging pressure/compressibility; and **Molar (composition)**, manual GOR/basis/shrinkage/density/MW inputs or an uploaded `ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx` workbook, driving the molar composition split and cylinder loading plan. |

A local theme file, `.streamlit/config.toml`, sets the "v8" palette
(primary color `#0047BB`) that `ui/theme.py` builds on. Both filled ADRIC
template workbooks used for manual testing/demo purposes are checked into
`tests/fixtures/workbooks/`.

## 2.4 The Command-Line Interface

`cli.py` exposes the same engine as the web app through two subcommands,
`recombine` and `flash` (`cli.py`'s `build_parser()`):

```bash
python cli.py --help
python cli.py recombine --help
python cli.py flash --help
```

### `recombine`: multi-stage separator recombination

Takes typed inputs directly on the command line (no workbook needed). The
required Stage 1 arguments are `--gor`, `--p_sep`, `--t_sep`, `--z_sep`,
plus the recombination-side `--v_live`, `--p_recomb`, `--t_recomb`
(`--z_recomb` defaults to `1.0`, `--sf` defaults to `1.00`, `--stages`
defaults to `1` and accepts `1`, `2`, or `3`). Stage 2/3 conditions
(`--gor2/--p2/--t2/--z2`, `--gor3/--p3/--t3/--z3`) become required only when
`--stages` selects them. An optional Standing bubble-point estimate
activates when both `--api` and `--sg_gas` are supplied (`--t_res` overrides
the temperature used, defaulting to the Stage 1 temperature). `--units`
selects `field` (psia/°F/scf/STB, the default) or `si`
(bara/°C/sm³/sm³).

```bash
# Single stage (field units)
python cli.py recombine --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 \
              --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820

# Two-stage with a Standing Pb estimate
python cli.py recombine --gor 850 --p_sep 800 --t_sep 140 --z_sep 0.865 \
              --stages 2 --gor2 50 --p2 65 --t2 100 --z2 0.977 \
              --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820 \
              --api 42 --sg_gas 0.72

# SI units
python cli.py recombine --units si --gor 151.4 --p_sep 55.8 --t_sep 62.8 --z_sep 0.865 \
              --v_live 300 --p_recomb 346.7 --t_recomb 93.3 --z_recomb 0.820
```

`recombine` validates inputs with `validate_multistage` and prints one
error per line to stderr (exit code 1) if validation fails, rather than
running a calculation on bad input.

### `flash`: import a filled ADRIC Flash v6.1 workbook

Takes exactly one argument, `--workbook`, and runs the full import →
calculate → mass-basis recombine → QC → report chain:

```bash
python cli.py flash --workbook path/to/ADRIC_Flash_Separation_Calc_v6.1.xlsx
```

`flash` imports through `pvt.io.excel_import.flash_v61.read`, runs
`pvt.experiments.flash.calc.calculate`, recombines the oil/gas streams by
mass (`pvt.experiments.flash.recombine.recombine_mass`), grades composition
normalization and MW consistency QC checks, and prints the resulting report
tables as fixed-width text via `pvt.reporting.tables.flash_tables`. A
malformed workbook or unreadable file path is reported with `error:` lines
on stderr and exit code 1, rather than a Python traceback.

Both subcommands share the same fixed-width report formatting helpers
(`_format_report_tables`, `_row`, `_section`, `_rule` in `cli.py`).

## 2.5 Running the Tests

```bash
pytest
```

`pyproject.toml`'s `[tool.pytest.ini_options]` fixes `testpaths = ["tests"]`
and sets:

```toml
addopts = "--cov=pvt --cov-report=term-missing --cov-fail-under=100"

[tool.coverage.run]
branch = true
```

This is the platform's central quality gate: `pytest` fails the build if
branch coverage of the `pvt/` package drops below 100%. Coverage is scoped
to `pvt/` only; `cli.py` and everything under `ui/` sit outside the
`--cov=pvt` gate, but both are still exercised by their own dedicated test
suites (`tests/unit/test_cli.py`; the Streamlit `AppTest` smoke tests under
`tests/ui/`).

The suite is organized in three tiers, matching the design spec's testing
strategy (Section 8):

1. **Unit-sanity** (`tests/unit/`), mirroring `pvt/core`, `pvt/qc`,
   `pvt/correlations`, and `pvt/experiments` 1:1: analytic limits and
   physical-behavior checks (unit round-trips are identity, degenerate
   inputs raise `InputValidationError`, threshold-grading boundaries land
   correctly, and so on).
2. **Golden** (`tests/golden/`), keyed to a single reference sample
   (SA-372; see `tests/fixtures/sa372.py` / `sa372_flash.py`): exact values
   cached from the source ADRIC workbooks, run across the full flash and
   recombination chains, plus the Excel importers themselves.
3. **Deviation**, one test per `docs/excel-deviations.md` entry, asserting
   the engine's correct value at the exact point it deliberately departs
   from a source workbook.

### CI and the lint/type-check gate

`.github/workflows/ci.yml` runs on every push to `main`/`feature/**` and on
every pull request into `main`, on `ubuntu-latest` with Python 3.12:

```yaml
- run: pip install -e ".[dev]"
- run: ruff check pvt tests ui app.py cli.py
- run: mypy pvt
- run: pytest
- run: python -c "import pvt, ui, cli"
```

There is no `pytest -W error` flag or `filterwarnings` configuration in
this repository (none was found in `pyproject.toml` or elsewhere); the
platform's actual warning discipline is enforced at the linter/type-checker
layer instead: `ruff check` and `mypy pvt` are both required, zero-issue CI
steps (`[tool.mypy]` additionally sets `disallow_untyped_defs = true` and
`warn_unused_ignores = true`, so an unnecessary `# type: ignore` is itself a
failure). Runtime `warnings.warn(...)` calls that do exist in the engine
(range-guard warnings in `standing.py`, `vasquez_beggs.py`, and `erbar.py`,
for out-of-correlation-range inputs) are deliberate, documented behavior
with dedicated tests that assert on the warning text, not something the
test suite silences or is meant to be clean of. The final import-smoke step
(`python -c "import pvt, ui, cli"`) guards the pure-engine/thin-UI boundary
directly: it fails if `ui` cannot be imported (e.g. a missing Streamlit
dependency) as much as if `pvt` cannot.

Before committing, run the same sequence locally:

```bash
python3 -m pytest                          # full suite + 100% pvt coverage gate
python3 -m ruff check pvt tests ui app.py cli.py
python3 -m mypy pvt
python3 -c "import pvt, ui, cli"           # import-smoke, matches the CI step
```

## 2.6 Repo Layout Reference

| Path | Contents |
|---|---|
| `pvt/` | Pure calculation engine. No Streamlit or UI import anywhere in this tree. |
| `pvt/core/` | Constants, unit conversions, `Component`/`ComponentLibrary`, `CompositionStream`, plus-fraction properties, `Sample`/`Study`/`CrossRef`, typed exceptions. |
| `pvt/correlations/` | Phase 1 empirical correlations: `bubble_point/`, `pseudocritical/`, `viscosity/`, `zfactor/`. |
| `pvt/experiments/` | One package per lab test (`flash/`, `recombination/`), each following a `models.py` / `calc.py` / `validate.py` pattern. |
| `pvt/io/excel_import/` | `flash_v61.py`, `liveoil_v41.py`: one reader per ADRIC template. |
| `pvt/qc/` | `engine.py` (severity grading, threshold registry) and `checks/` (individual QC check modules). |
| `pvt/reporting/` | `tables.py` (schema-driven report tables) and `excel_export.py` (ADRIC-styled `.xlsx` writer). |
| `ui/` | Streamlit presentation layer: `theme.py`, `common/components.py`, `pages/`. |
| `tests/unit/` | Mirrors `pvt/core` + `pvt/qc` + `pvt/experiments` + `pvt/correlations`, 1:1. |
| `tests/golden/` | Workbook-cached golden-value tests keyed to the SA-372 reference sample. |
| `tests/fixtures/` | Frozen fixture data (`sa372.py`, `sa372_flash.py`) and the two filled `.xlsx` templates under `workbooks/`. |
| `tests/ui/` | Streamlit `AppTest` smoke tests, outside the `pvt` coverage gate. |
| `docs/excel-deviations.md` | The deviations ledger. |
| `docs/workbook-defect-review.md` | Formula-level workbook defect catalog awaiting a point-by-point ruling. |
| `docs/superpowers/specs/` | Design specification(s). |
| `docs/superpowers/plans/` | Phase implementation plans. |
| `app.py` | Streamlit entry point (root of the repository, not under `ui/`). |
| `cli.py` | Command-line interface (`recombine`, `flash` subcommands). |
| `pyproject.toml` | Packaging, `pytest`/coverage, `ruff`, and `mypy` configuration. |
| `.github/workflows/ci.yml` | CI pipeline: `ruff check`, `mypy`, `pytest`, import-smoke. |

## 2.7 Offline Installation (Locked-Down PC)

Some target machines have no internet access at all (a company PC on a
locked-down network) and cannot assume Python has Streamlit already
installed, or that PyPI is even reachable. `scripts/make_offline_bundle.sh`
builds a self-contained folder that installs the whole platform, including
the `streamlit` and `openpyxl` packages and their full transitive
dependency closure, using `pip install --no-index` (no network access
required at install time).

Run the script on any machine that does have internet access. It downloads
wheels from PyPI, so it is not itself offline; only the resulting bundle
is:

```bash
bash scripts/make_offline_bundle.sh                        # bundle for this machine
bash scripts/make_offline_bundle.sh win_amd64               # bundle targeting a Windows PC
bash scripts/make_offline_bundle.sh manylinux2014_x86_64 --dev   # + pytest/ruff/mypy
```

The optional first argument is a pip wheel platform tag for the *target*
PC (`win_amd64`, `manylinux2014_x86_64`, `macosx_11_0_arm64`, and so on);
omit it to build for the machine the script is running on. `--dev`
additionally downloads the `[dev]` extra (`pytest`, `pytest-cov`, `ruff`,
`mypy`); it is left out by default since a locked-down PC normally only
needs to run the application, not the test/lint toolchain. The script
fails loudly (missing tooling, a failed download, an empty result) and
prints the bundle's final path and size on success. It writes
`dist/pvt-offline-<platform>/`:

| Path | Contents |
|---|---|
| `wheels/` | Every runtime dependency (`streamlit`, `openpyxl`, their full transitive closure, plus `setuptools`/`wheel` needed to build the project from source), as downloaded `.whl` files. |
| `src/` | The full source tree at `git archive HEAD` (the repository at the built commit, with no `.git` directory or other build/test cruft). |
| `INSTALL.txt` | Exact install steps for the target PC, both Windows and POSIX. |

Copy that folder to the target PC (USB stick, internal network share,
whatever the site allows) and follow `INSTALL.txt`:

```bash
python -m venv .venv

# Windows (cmd.exe / PowerShell)
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install --no-index --find-links wheels setuptools wheel
cd src
pip install --no-index --no-build-isolation --find-links ../wheels -e .
streamlit run app.py
```

or the CLI, from the same activated environment and `src/` directory:

```bash
python cli.py recombine --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 \
              --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820
```

Every install command above passes `--no-index`, so pip refuses to
contact PyPI at all: a dependency missing from `wheels/` fails loudly with
a "no matching distribution found" error instead of silently depending on
the target PC happening to have internet after all.

### Running without Streamlit at all

The command-line interface does not need Streamlit. Tracing `cli.py`'s
actual import closure (`cli.py` itself plus everything reachable through
`pvt.core`, `pvt.correlations`, `pvt.experiments`, `pvt.qc`,
`pvt.reporting`, and, for the `flash` subcommand, `pvt.io.excel_import`)
shows exactly one third-party package: `openpyxl`. Everything else is the
Python standard library (`math`, `dataclasses`, `enum`, `argparse`, and so
on). So `python cli.py recombine ...` and
`python cli.py flash --workbook ...` both run on a machine with only the
`pvt` package and `openpyxl` installed; no Streamlit anywhere.

The GUI (`streamlit run app.py`) does need the `streamlit` package, but
that only means the ordinary Python library bundled in `wheels/` above,
installed into a per-user virtual environment like any other pip package.
It needs no admin rights, and it is not a system service or background
daemon: `streamlit run` starts a local web server for the duration of
your session and nothing more.

A zero-install, browser-only build (compiling the app to WebAssembly with
a tool such as stlite, so a target PC would not need a Python interpreter
at all) is a roadmap evaluation item, not something this platform
supports today.
