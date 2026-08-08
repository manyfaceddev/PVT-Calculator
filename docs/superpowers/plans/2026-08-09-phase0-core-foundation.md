# Phase 0: Core Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the repo per the approved spec and build the pure-engine core (exceptions, constants, units, component library, composition streams, study model, QC engine) with test infrastructure gated at 100% coverage.

**Architecture:** Everything lands in `pvt/core/` and `pvt/qc/`, pure Python with zero UI imports. Existing recombination code moves under `pvt/experiments/`, the deprecated shim and untested legacy single-stage API are deleted, and the CI coverage gate flips to 100% as the final task.

**Tech Stack:** Python 3.12, dataclasses, pytest + pytest-cov, ruff, mypy, GitHub Actions. No new runtime dependencies beyond `streamlit` (existing) and `openpyxl` (needed by Phase 2 import; added now).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`. Work directly on `main` (user decision); commit after every task.
- `pvt/` never imports streamlit or `ui/`.
- All physical constants live in `pvt/core/constants.py` exactly once, with a source comment each. No magic numbers in calc code.
- Every deliberate difference from a source workbook gets an entry in `docs/excel-deviations.md` BEFORE the deviating test lands.
- Python 3.12 (`.python-version` already pins it). Type annotations everywhere; `mypy pvt` must pass.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Packaging and tooling baseline

**Files:**
- Create: `pyproject.toml`
- Delete: `pvt_calc.py`, `packages.txt`
- Modify: `.github/workflows/ci.yml`, `requirements.txt`, `requirements-dev.txt`
- Test: (infrastructure task; verified by running the suite)

**Interfaces:**
- Consumes: nothing.
- Produces: `pip install -e ".[dev]"` working; `pytest`, `ruff check pvt tests`, `mypy pvt` runnable locally and in CI. Coverage REPORTED but not yet gated (gate flips in Task 10).

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=69"]
build-backend = "setuptools.build_meta"

[project]
name = "pvt"
version = "0.1.0"
description = "ADRIC PVT laboratory platform engine"
requires-python = ">=3.12"
dependencies = [
    "streamlit>=1.37.1,<2",
    "openpyxl>=3.1,<4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
    "ruff>=0.5",
    "mypy>=1.10",
]

[tool.setuptools.packages.find]
include = ["pvt*", "ui*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=pvt --cov-report=term-missing"

[tool.coverage.run]
branch = true

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
warn_unused_ignores = true
disallow_untyped_defs = true
packages = ["pvt"]
```

- [ ] **Step 2: Delete the deprecated shim and Streamlit Cloud stub**

```bash
git rm pvt_calc.py packages.txt
```

- [ ] **Step 3: Point requirements files at the package** — replace the full contents of each:

`requirements.txt`:
```text
-e .
```

`requirements-dev.txt`:
```text
-e .[dev]
```

- [ ] **Step 4: Rewrite `.github/workflows/ci.yml`** — replace the full contents:

```yaml
name: CI
on:
  push:
    branches: ["main", "feature/**"]
  pull_request:
    branches: ["main"]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -e ".[dev]"
      - run: ruff check pvt tests
      - run: mypy pvt
      - run: pytest
      - run: python -c "import pvt, ui, cli"
```

- [ ] **Step 5: Run the suite locally, fix any ruff/mypy fallout mechanically**

Run: `pip install -e ".[dev]" && ruff check pvt tests && mypy pvt && pytest`
Expected: 86 tests PASS. mypy will flag `pvt/recombination/calc.py:121` (`units: str` — change to `Units`) and `pvt/recombination/models.py:83` (bare `list` — change to `list[StageResult]`); fix exactly those. Ruff may flag unused imports; remove them. Coverage report will show gaps (legacy single-stage API, Case 2 branches) — expected; do not chase 100% here.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: package as pyproject project with ruff/mypy/coverage tooling

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Remove legacy single-stage API; cover the Case 2 path

**Files:**
- Modify: `pvt/recombination/calc.py` (delete `calculate`, lines ~56–107), `pvt/recombination/validate.py` (delete `validate`), `pvt/recombination/models.py` (delete `RecombinationInputs`, `RecombinationResults`), `pvt/__init__.py` (drop their re-exports)
- Test: `tests/test_recombination_calc.py` (add Case 2 class)

**Interfaces:**
- Consumes: existing `calculate_multistage(...)` signature (unchanged).
- Produces: public API = `calculate_multistage`, `validate_multistage`, `SeparatorStage`, `StageResult`, `MultiStageResults` only. Case 2 (`oil_source="stock_tank"`) covered by tests.

- [ ] **Step 1: Write failing Case 2 tests** (append to `tests/test_recombination_calc.py`)

```python
class TestCase2StockTank:
    """Case 2: dead STO charged; stage gas + FF gas all from the separator-gas cylinder."""

    def _run(self, **overrides):
        kwargs = dict(
            v_live=1000.0, sf=1.0, ff=100.0, oil_source="stock_tank",
            p_recomb=5000.0, t_recomb=75.0, z_recomb=0.85,
            stages=[SeparatorStage(R=339.0, p=248.0, t=118.0, z=0.99)],
            units="field", p_charge=5000.0, c_o=0.0,
        )
        kwargs.update(overrides)
        return calculate_multistage(**kwargs)

    def test_volume_balance_exact(self):
        res = self._run()
        total_gas = sum(s.v_gas_recomb_cc for s in res.stage_results) + res.v_ff_gas_recomb_cc
        assert res.v_oil_sep_cc + total_gas == pytest.approx(1000.0, rel=1e-12)

    def test_ff_gas_included_in_cylinder_total(self):
        with_ff = self._run(ff=100.0)
        without_ff = self._run(ff=0.0)
        assert with_ff.total_v_gas_std_cc > without_ff.total_v_gas_std_cc

    def test_sf_ignored_in_case2(self):
        assert self._run(sf=0.8).v_oil_sto_cc == pytest.approx(self._run(sf=1.0).v_oil_sto_cc)

    def test_stage_pct_excludes_ff(self):
        res = self._run(ff=100.0)
        assert sum(s.pct_of_total for s in res.stage_results) < 100.0
```

(Adjust attribute names to the actual `MultiStageResults` fields — read `pvt/recombination/models.py` first; the FF gas volume field and `v_oil_sep_cc` exist there.)

- [ ] **Step 2: Run to verify the new tests exercise previously-dead branches**

Run: `pytest tests/test_recombination_calc.py -k Case2 -v`
Expected: PASS immediately if field names are right (logic exists, was untested). If a test FAILS, the failure is information — investigate against `calc.py` before touching anything; these are characterization tests.

- [ ] **Step 3: Delete the legacy API** — remove `calculate` from `calc.py`, `validate` from `validate.py`, `RecombinationInputs`/`RecombinationResults` from `models.py`, and their names from `pvt/__init__.py`'s re-export list and `pvt/recombination/__init__.py`.

- [ ] **Step 4: Full suite + coverage check**

Run: `pytest`
Expected: all PASS; coverage report for `pvt/recombination/` now near-100% (remaining gaps OK until Task 10).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: drop untested legacy single-stage API; cover Case 2 path

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `pvt/core/exceptions.py`

**Files:**
- Create: `pvt/core/__init__.py` (empty), `pvt/core/exceptions.py`
- Test: `tests/unit/__init__.py` (empty), `tests/unit/test_exceptions.py`

**Interfaces:**
- Produces: `PvtError(Exception)`; `InputValidationError(PvtError)` with `.errors: list[str]`, message = errors joined with "; "; `ConvergenceError(PvtError)` with `.iterations: int`, `.residual: float`.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pvt.core.exceptions import ConvergenceError, InputValidationError, PvtError

def test_input_validation_error_carries_messages():
    err = InputValidationError(["GOR must be positive", "Z out of range"])
    assert err.errors == ["GOR must be positive", "Z out of range"]
    assert "GOR must be positive; Z out of range" in str(err)
    assert isinstance(err, PvtError)

def test_convergence_error_carries_diagnostics():
    err = ConvergenceError("DAK failed", iterations=100, residual=0.5)
    assert err.iterations == 100
    assert err.residual == 0.5
    assert isinstance(err, PvtError)
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_exceptions.py -v` → FAIL (module not found).

- [ ] **Step 3: Implement**

```python
"""Typed exceptions for the pvt engine."""


class PvtError(Exception):
    """Base class for all engine errors."""


class InputValidationError(PvtError):
    """Raised when calc inputs fail validation. Carries the message list."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ConvergenceError(PvtError):
    """Raised when an iterative solver fails to converge."""

    def __init__(self, message: str, *, iterations: int, residual: float) -> None:
        self.iterations = iterations
        self.residual = residual
        super().__init__(f"{message} (iterations={iterations}, residual={residual:.3e})")
```

- [ ] **Step 4: Run to verify pass** — `pytest tests/unit/test_exceptions.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: typed engine exceptions ..."` (trailer as always).

---

### Task 4: `pvt/core/constants.py` (canonical constants, replacing `pvt/constants.py`)

**Files:**
- Create: `pvt/core/constants.py`
- Modify: `pvt/constants.py` → becomes a thin re-export (kept one phase for import stability), `pvt/recombination/calc.py` + `validate.py` imports
- Test: `tests/unit/test_constants.py` (move + extend `tests/test_constants.py`)

**Interfaces:**
- Produces (exact names, all `Final[float]` unless noted): `P_STD_PSIA = 14.73`, `P_STD_MBAR = 1015.5981`, `T_STD_F = 60.0`, `T_STD_R = 519.67`, `T_STD_K = 288.7056`, `RANKINE_OFFSET = 459.67`, `CC_PER_SCF = 28316.85`, `CC_PER_STB = 158987.29`, `SCF_PER_LBMOL = 379.482`, `FT3_PER_BBL = 5.61458`, `AIR_MW = 28.964`, `AIR_DENSITY_STD_G_CC = 0.0012255`, `R_PSIA_FT3_LBMOL_R = 10.7316`, `R_PSIA_CC_MOL_K = 1205.91`, `G_PER_LB = 453.59237`, `PSIA_PER_BARA = 14.5038`, `WATER_DENSITY_60F_G_CC = 0.9991`, `P_ATM_PSIA = 14.696`, `SCF_STB_TO_CC_CC = CC_PER_SCF / CC_PER_STB`, `Units = Literal["field", "si"]`.

- [ ] **Step 1: Write failing tests** (`tests/unit/test_constants.py`; keep every assertion from the old `tests/test_constants.py`, updated to the new import path, plus:)

```python
from pvt.core import constants as c

def test_lab_standard_conditions():
    assert c.P_STD_PSIA == 14.73
    assert c.T_STD_R == 519.67
    assert c.T_STD_K == pytest.approx(288.7056)
    assert c.P_STD_MBAR == pytest.approx(1015.5981)

def test_gas_constants_consistent():
    # R in psia·cc/(gmol·K) is R_psia_ft3 converted: 10.7316*28316.85/453.59237 ≈ 669.9? No —
    # the lab value 1205.91 is R[atm·cc/mol/K]=82.057 × 14.696; assert the identity it came from.
    assert c.R_PSIA_CC_MOL_K == pytest.approx(82.057 * 14.696, rel=1e-4)
    assert c.R_PSIA_FT3_LBMOL_R == 10.7316

def test_derived_ratio():
    assert c.SCF_STB_TO_CC_CC == pytest.approx(0.178108, rel=1e-5)

def test_air_density_matches_ideal_gas_at_lab_std():
    # rho = MW·P/(R·T) at 14.73 psia / 60F, in g/cc
    rho = c.AIR_MW * c.P_STD_PSIA / (c.R_PSIA_CC_MOL_K * c.T_STD_K)
    assert rho == pytest.approx(c.AIR_DENSITY_STD_G_CC, rel=2e-3)
```

- [ ] **Step 2: Run to verify failure** — `pytest tests/unit/test_constants.py -v` → FAIL (no module).

- [ ] **Step 3: Implement** — write `pvt/core/constants.py` with every constant above, each with a one-line source comment (e.g. `# Lab standard pressure, all ADRIC sheets (14.73 psia = 1015.5981 mbar)`; `# NIST: 1 bbl = 158987.294928 cc; lab sheets use 158987.29 — canonized for parity`). Then reduce `pvt/constants.py` to:

```python
"""Deprecated location — import from pvt.core.constants. Removed after Phase 2."""
from pvt.core.constants import *  # noqa: F401,F403
```

and switch `pvt/recombination/calc.py` / `validate.py` to `from pvt.core import constants`.

- [ ] **Step 4: Run full suite** — `pytest` → all PASS (old constants tests keep passing via new values; delete `tests/test_constants.py` after confirming `tests/unit/test_constants.py` supersedes every assertion).

- [ ] **Step 5: Commit.**

---

### Task 5: `pvt/core/units.py`

**Files:**
- Create: `pvt/core/units.py`
- Test: `tests/unit/test_units.py`

**Interfaces:**
- Produces (pure functions, all `float -> float` unless noted): `f_to_r`, `r_to_f`, `f_to_c`, `c_to_f`, `c_to_k`, `k_to_c`, `f_to_k`, `psig_to_psia(p_psig, p_atm_psia=P_ATM_PSIA)`, `psia_to_psig(...)`, `bara_to_psia`, `psia_to_bara`, `mbar_to_psia`, `scf_stb_to_cc_cc`, `cc_cc_to_scf_stb`, `scf_to_cc`, `cc_to_scf`, `stb_to_cc`, `cc_to_stb`, `api_from_density_g_cc(rho)`, `density_g_cc_from_api(api)`, `sg_from_density_g_cc(rho)` (÷ `WATER_DENSITY_60F_G_CC`).

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pvt.core import units as u

@pytest.mark.parametrize("fwd,back,value", [
    (u.f_to_r, u.r_to_f, 256.0), (u.f_to_c, u.c_to_f, 118.0),
    (u.c_to_k, u.k_to_c, 20.0), (u.bara_to_psia, u.psia_to_bara, 5.5),
    (u.scf_stb_to_cc_cc, u.cc_cc_to_scf_stb, 339.0),
    (u.scf_to_cc, u.cc_to_scf, 0.12731), (u.stb_to_cc, u.cc_to_stb, 1.0),
])
def test_round_trip(fwd, back, value):
    assert back(fwd(value)) == pytest.approx(value, rel=1e-12)

def test_known_values():
    assert u.f_to_r(60.0) == pytest.approx(519.67)
    assert u.f_to_k(60.0) == pytest.approx(288.7056, rel=1e-6)
    assert u.psig_to_psia(1156.0) == pytest.approx(1170.696)
    assert u.mbar_to_psia(1015.5981) == pytest.approx(14.73, rel=1e-6)
    assert u.api_from_density_g_cc(0.870056) == pytest.approx(31.133, abs=0.01)
    assert u.density_g_cc_from_api(31.133) == pytest.approx(0.870056, abs=1e-4)
    assert u.scf_stb_to_cc_cc(339.0) == pytest.approx(60.378, abs=0.001)  # LiveOil B25
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement** — one-liners built strictly on `pvt.core.constants` (e.g. `def mbar_to_psia(p: float) -> float: return p * constants.P_STD_PSIA / constants.P_STD_MBAR`). Docstring on `api_from_density_g_cc`: "House convention: treats g/cc at 60 °F as SG 60/60 (all ADRIC sheets do); `sg_from_density_g_cc` gives the strict conversion."

- [ ] **Step 4: Run to verify pass.**  - [ ] **Step 5: Commit.**

---

### Task 6: `pvt/core/components.py` — Katz-Firoozabadi library

**Files:**
- Create: `pvt/core/components.py`
- Test: `tests/unit/test_components.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) Component(code: str, name: str, mw: float, liquid_density_g_cc: float, tb_r: float, pc_psia: float, tc_r: float)` with property `molar_volume_cc` (= mw/density); `class ComponentLibrary` with `.get(code) -> Component` (KeyError on unknown), `.codes -> list[str]` (order preserved), `.with_c36_mw(mw: float) -> ComponentLibrary` (returns a copy with C36+ MW replaced — the only lab-editable property); module constant `KATZ_FIROOZABADI: ComponentLibrary` (52 entries).

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF

def test_library_size_and_order():
    assert len(KF.codes) == 52
    assert KF.codes[0] == "H2" and KF.codes[-1] == "C36+"

def test_known_properties():
    c1 = KF.get("C1")
    assert c1.mw == pytest.approx(16.043)
    assert c1.tc_r == pytest.approx(343.0, abs=1.0)
    assert KF.get("C7").mw == pytest.approx(100.204)
    assert KF.get("C36+").mw == pytest.approx(636.4)
    assert KF.get("Toluene").liquid_density_g_cc == pytest.approx(0.8718)

def test_molar_volume():
    c = KF.get("C6")
    assert c.molar_volume_cc == pytest.approx(c.mw / c.liquid_density_g_cc)

def test_c36_override_is_isolated_copy():
    lib2 = KF.with_c36_mw(635.0)
    assert lib2.get("C36+").mw == 635.0
    assert KF.get("C36+").mw == pytest.approx(636.4)
    assert lib2.get("C1") is KF.get("C1")

def test_unknown_code_raises():
    with pytest.raises(KeyError):
        KF.get("C99")
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement.** Data source of record: the `Component_Properties` sheet of `ADRIC_Flash_Separation_Calc_v6.1.xlsx` (canonized; LiveOil v4.1 differs in the 4th significant figure on 3 species — documented in `docs/excel-deviations.md` under "library canonization"). Full table (code, name, MW, ρ g/cc, Tb °R, Pc psia, Tc °R):

```python
_KF_ROWS: list[tuple[str, str, float, float, float, float, float]] = [
    ("H2", "Hydrogen", 2.016, 0.0711, 36.7, 188.0, 59.4),
    ("H2S", "Hydrogen sulfide", 34.0809, 0.8006, 383.1, 1300.0, 672.4),
    ("CO2", "Carbon dioxide", 44.0095, 0.818, 350.0, 1071.0, 547.6),
    ("N2", "Nitrogen", 28.0134, 0.8094, 139.3, 493.0, 227.2),
    ("C1", "Methane", 16.043, 0.3, 200.7, 666.4, 343.0),
    ("C2", "Ethane", 30.07, 0.3562, 332.2, 706.5, 549.6),
    ("C3", "Propane", 44.097, 0.507, 415.9, 616.0, 665.7),
    ("iC4", "i-Butane", 58.123, 0.5629, 470.6, 527.9, 734.1),
    ("nC4", "n-Butane", 58.123, 0.584, 490.7, 550.6, 765.3),
    ("NeoC5", "Neopentane", 72.151, 0.5967, 482.6, 464.0, 734.6),
    ("iC5", "i-Pentane", 72.151, 0.6244, 541.7, 490.4, 828.7),
    ("nC5", "n-Pentane", 72.151, 0.6311, 556.6, 488.6, 845.5),
    ("C6", "Hexanes", 86.177, 0.664, 615.4, 436.9, 913.3),
    ("MCP", "Methylcyclopentane", 84.16, 0.7536, 621.0, 548.9, 959.2),
    ("Benzene", "Benzene", 78.11, 0.8844, 636.3, 710.4, 1012.0),
    ("CycloC6", "Cyclohexane", 84.16, 0.7834, 637.2, 590.8, 996.5),
    ("C7", "Heptanes", 100.204, 0.722, 668.8, 396.8, 972.4),
    ("MCH", "Methylcyclohexane", 98.19, 0.7702, 675.0, 503.5, 1029.8),
    ("Toluene", "Toluene", 92.14, 0.8718, 690.5, 595.9, 1065.6),
    ("C8", "Octanes", 114.231, 0.745, 717.9, 360.7, 1023.9),
    ("EBenzene", "Ethylbenzene", 106.17, 0.872, 735.5, 523.5, 1111.1),
    ("MP-Xylene", "m/p-Xylene", 106.17, 0.8687, 738.4, 513.6, 1112.8),
    ("O-Xylene", "o-Xylene", 106.17, 0.8848, 751.9, 541.4, 1135.4),
    ("C9", "Nonanes", 128.258, 0.764, 763.1, 331.8, 1070.4),
    ("TMB124", "1,2,4-Trimethylbenzene", 120.195, 0.876, 807.5, 495.0, 1129.0),
    ("C10", "Decanes", 142.285, 0.778, 805.2, 305.7, 1111.8),
    ("C11", "Undecanes", 156.0, 0.789, 847.0, 285.0, 1150.0),
    ("C12", "Dodecanes", 170.0, 0.8, 885.0, 264.0, 1185.0),
    ("C13", "Tridecanes", 184.0, 0.811, 923.0, 246.0, 1220.0),
    ("C14", "Tetradecanes", 198.0, 0.822, 958.0, 230.0, 1250.0),
    ("C15", "Pentadecanes", 212.0, 0.832, 991.0, 217.0, 1280.0),
    ("C16", "Hexadecanes", 226.0, 0.839, 1020.0, 205.0, 1305.0),
    ("C17", "Heptadecanes", 240.0, 0.847, 1049.0, 193.0, 1332.0),
    ("C18", "Octadecanes", 254.0, 0.852, 1075.0, 186.0, 1354.0),
    ("C19", "Nonadecanes", 268.0, 0.857, 1101.0, 175.0, 1381.0),
    ("C20", "Eicosanes", 282.0, 0.862, 1124.0, 167.0, 1402.0),
    ("C21", "C21", 296.0, 0.867, 1146.0, 159.0, 1424.0),
    ("C22", "C22", 310.0, 0.872, 1167.0, 152.0, 1442.0),
    ("C23", "C23", 324.0, 0.877, 1187.0, 146.0, 1460.0),
    ("C24", "C24", 338.0, 0.881, 1207.0, 140.0, 1478.0),
    ("C25", "C25", 352.0, 0.885, 1226.0, 134.0, 1494.0),
    ("C26", "C26", 366.0, 0.889, 1244.0, 129.0, 1509.0),
    ("C27", "C27", 380.0, 0.893, 1262.0, 125.0, 1523.0),
    ("C28", "C28", 394.0, 0.896, 1277.0, 120.0, 1537.0),
    ("C29", "C29", 408.0, 0.899, 1294.0, 116.0, 1550.0),
    ("C30", "C30", 422.0, 0.902, 1310.0, 112.0, 1563.0),
    ("C31", "C31", 436.0, 0.906, 1323.0, 108.0, 1574.0),
    ("C32", "C32", 450.0, 0.909, 1335.0, 104.0, 1584.0),
    ("C33", "C33", 464.0, 0.912, 1349.0, 101.0, 1594.0),
    ("C34", "C34", 478.0, 0.915, 1360.0, 98.0, 1603.0),
    ("C35", "C35", 492.0, 0.917, 1373.0, 95.0, 1612.0),
    ("C36+", "C36 plus", 636.4, 0.94, 1490.0, 80.0, 1700.0),
]
```

`ComponentLibrary` wraps `dict[str, Component]` built from these rows; `with_c36_mw` uses `dataclasses.replace` on the C36+ entry.

- [ ] **Step 4: Run to verify pass.**  - [ ] **Step 5: Commit** (and add the "library canonization" entry to `docs/excel-deviations.md` — create the file now with its header if absent; ledger format defined in Task 10 Step 1; move that step here if this task runs first).

---

### Task 7: `pvt/core/composition.py`

**Files:**
- Create: `pvt/core/composition.py`
- Test: `tests/unit/test_composition.py`, `tests/fixtures/__init__.py`, `tests/fixtures/sa372.py`

**Interfaces:**
- Consumes: `ComponentLibrary`, `InputValidationError`, `AIR_MW`.
- Produces: `@dataclass(frozen=True) CompositionStream(library: ComponentLibrary, mol_pct: Mapping[str, float] | None = None, wt_pct: Mapping[str, float] | None = None)` — keys must exist in library (else `InputValidationError`); methods: `raw_mol_sum()`, `raw_wt_sum()`, `normalized_mol() -> dict[str, float]` (sums to 100), `normalized_wt()`, `mw_from_mol()` (Σzᵢ·MWᵢ/Σzᵢ), `mw_from_wt()` (100/Σ(wᵢ/MWᵢ) on normalized), `mw_consistency_pct()`, `wt_from_mol()` (derived), `liquid_density_ideal_g_cc()` (Σw/Σ(w/ρᵢ)), `gas_gravity()` (mw_from_mol/AIR_MW).

- [ ] **Step 1: Create the shared SA-372 fixture module** (`tests/fixtures/sa372.py`) with the real digested data (used again in Phase 2 golden tests):

```python
"""Sample SA-372 lab data (ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx cached values)."""

STO_MOL_PCT: dict[str, float] = {
    "C2": 0.18, "C3": 1.65, "iC4": 1.20, "nC4": 3.98, "iC5": 2.99, "nC5": 4.33,
    "C6": 7.09, "MCP": 1.24, "Benzene": 0.34, "CycloC6": 0.75, "C7": 6.12,
    "MCH": 1.34, "Toluene": 0.99, "C8": 6.19, "EBenzene": 0.65, "MP-Xylene": 1.20,
    "O-Xylene": 0.59, "C9": 5.17, "C10": 6.00, "C11": 5.60, "C12": 4.57,
    "C13": 4.03, "C14": 3.51, "C15": 3.13, "C16": 2.62, "C17": 2.20, "C18": 1.99,
    "C19": 1.89, "C20": 1.64, "C21": 1.47, "C22": 1.28, "C23": 1.13, "C24": 1.02,
    "C25": 0.90, "C26": 0.82, "C27": 0.73, "C28": 0.69, "C29": 0.63, "C30": 0.58,
    "C31": 0.52, "C32": 0.47, "C33": 0.43, "C34": 0.41, "C35": 0.36, "C36+": 4.69,
}
GAS_MOL_PCT: dict[str, float] = {
    "CO2": 4.71, "N2": 0.87, "C1": 62.51, "C2": 14.17, "C3": 9.98, "iC4": 1.77,
    "nC4": 3.25, "NeoC5": 0.01, "iC5": 0.86, "nC5": 0.88, "C6": 0.55, "MCP": 0.06,
    "Benzene": 0.02, "CycloC6": 0.06, "C7": 0.13, "MCH": 0.02, "Toluene": 0.03,
    "C8": 0.05, "EBenzene": 0.01, "MP-Xylene": 0.01, "C9": 0.03, "C10": 0.01, "C11": 0.01,
}
STO_MW_FROM_MOL = 187.05     # workbook B7 (uses C36+ MW = 635)
STO_C36_MW = 635.0
GAS_MW_FROM_MOL = 26.10      # workbook B6
STO_DENSITY_60F = 0.8196     # g/cc, input B5
```

- [ ] **Step 2: Write failing tests**

```python
import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from tests.fixtures import sa372

def _sto():
    return CompositionStream(library=KF.with_c36_mw(sa372.STO_C36_MW), mol_pct=sa372.STO_MOL_PCT)

def test_normalized_mol_sums_to_100():
    assert sum(_sto().normalized_mol().values()) == pytest.approx(100.0, abs=1e-9)

def test_raw_sum_preserved():
    assert _sto().raw_mol_sum() == pytest.approx(99.31, abs=0.01)   # workbook I66 → "REVIEW"

def test_mw_from_mol_matches_workbook():
    assert _sto().mw_from_mol() == pytest.approx(sa372.STO_MW_FROM_MOL, rel=2e-4)

def test_gas_stream_mw_and_gravity():
    gas = CompositionStream(library=KF, mol_pct=sa372.GAS_MOL_PCT)
    assert gas.mw_from_mol() == pytest.approx(sa372.GAS_MW_FROM_MOL, rel=2e-3)
    assert gas.gas_gravity() == pytest.approx(sa372.GAS_MW_FROM_MOL / 28.964, rel=2e-3)

def test_wt_from_mol_round_trips_mw():
    sto = _sto()
    derived = CompositionStream(library=sto.library, wt_pct=sto.wt_from_mol())
    assert derived.mw_from_wt() == pytest.approx(sto.mw_from_mol(), rel=1e-9)

def test_unknown_component_rejected():
    with pytest.raises(InputValidationError):
        CompositionStream(library=KF, mol_pct={"C99": 100.0})

def test_needs_at_least_one_basis():
    with pytest.raises(InputValidationError):
        CompositionStream(library=KF)
```

- [ ] **Step 3: Run to verify failure.**  - [ ] **Step 4: Implement** the dataclass with `__post_init__` validation and the methods listed in Interfaces (each 2–6 lines of arithmetic over the library lookups; guard zero-sums with `InputValidationError(["composition sums to zero"])`).

- [ ] **Step 5: Run to verify pass.**  - [ ] **Step 6: Commit.**

---

### Task 8: `pvt/core/sample.py`

**Files:**
- Create: `pvt/core/sample.py`
- Test: `tests/unit/test_sample.py`

**Interfaces:**
- Produces: `@dataclass Sample(sample_id, well, field_name, reservoir, depth_ft_md, fluid_type, cylinder, client="", project="")` (all `str` except `depth_ft_md: float | None`); `@dataclass CrossRef(value: float, source_test: str, source_field: str, note: str = "")` — units are carried in `source_field` names; `@dataclass Study(sample: Sample, reservoir_p_psig: float | None = None, reservoir_t_f: float | None = None, psat: CrossRef | None = None, density_at_psat: CrossRef | None = None, rs_flash: CrossRef | None = None, bo_flash: CrossRef | None = None)`.

- [ ] **Step 1: Write failing tests**

```python
from pvt.core.sample import CrossRef, Sample, Study

def test_cross_ref_provenance():
    psat = CrossRef(value=1156.0, source_test="CCE", source_field="psat_psig")
    study = Study(sample=Sample(sample_id="SA-372", well="WELL-X", field_name="Upper Zakum",
                                reservoir="Kharaib-2", depth_ft_md=9105.0,
                                fluid_type="Black Oil", cylinder="RF1168636"),
                  reservoir_p_psig=3939.0, reservoir_t_f=256.0, psat=psat)
    assert study.psat.value == 1156.0
    assert study.psat.source_test == "CCE"
```

- [ ] **Step 2–5:** fail → implement (plain dataclasses, no logic) → pass → commit.

---

### Task 9: `pvt/qc/engine.py`

**Files:**
- Create: `pvt/qc/__init__.py`, `pvt/qc/engine.py`
- Test: `tests/unit/test_qc_engine.py`

**Interfaces:**
- Produces: `class Severity(enum.StrEnum): PASS, REVIEW, FAIL`; `@dataclass(frozen=True) QCResult(check_id: str, severity: Severity, value: float | None, threshold: str, message: str)`; `def grade(value: float, review_at: float, fail_at: float, *, absolute: bool = True) -> Severity` (|value| ≤ review_at → PASS, ≤ fail_at → REVIEW, else FAIL); `class ThresholdRegistry` with `DEFAULTS: dict[str, tuple[float, float]]` seeded `{"composition_sum": (0.5, 2.0), "mass_balance_pct": (2.0, 3.0), "molar_balance_pct": (2.0, 3.0), "z_deviation_pct": (2.0, 5.0), "density_rsd_pct": (0.5, 1.0), "viscosity_vs_sim_pct": (2.0, 5.0), "mmp_mass_balance_pct": (5.0, 5.0), "gor_actual_vs_target_pct": (5.0, 10.0), "mw_consistency_pct": (5.0, 10.0)}`, methods `.get(check_id) -> tuple[float, float]`, `.override(check_id, review_at, fail_at, note)` recording notes in `.audit: list[str]`; `def worst(results: Iterable[QCResult]) -> Severity`.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pvt.qc.engine import QCResult, Severity, ThresholdRegistry, grade, worst

@pytest.mark.parametrize("value,expected", [
    (0.4, Severity.PASS), (-0.4, Severity.PASS),
    (1.0, Severity.REVIEW), (2.0, Severity.REVIEW), (2.1, Severity.FAIL),
])
def test_grade_bands(value, expected):
    assert grade(value, review_at=0.5, fail_at=2.0) == expected

def test_registry_defaults_and_override():
    reg = ThresholdRegistry()
    assert reg.get("mass_balance_pct") == (2.0, 3.0)
    reg.override("mass_balance_pct", 1.0, 2.0, note="tight client spec")
    assert reg.get("mass_balance_pct") == (1.0, 2.0)
    assert "tight client spec" in reg.audit[0]

def test_worst_orders_severities():
    mk = lambda s: QCResult("x", s, None, "", "")
    assert worst([mk(Severity.PASS), mk(Severity.REVIEW)]) == Severity.REVIEW
    assert worst([mk(Severity.FAIL), mk(Severity.PASS)]) == Severity.FAIL
    assert worst([]) == Severity.PASS
```

- [ ] **Step 2–5:** fail → implement → pass → commit.

---

### Task 10: Restructure moves, deviations ledger, README, 100% gate

**Files:**
- Create: `docs/excel-deviations.md`, `pvt/experiments/__init__.py`, `pvt/correlations/bubble_point/__init__.py`
- Move: `pvt/recombination/` → `pvt/experiments/recombination/`; `pvt/correlations/standing.py` → `pvt/correlations/bubble_point/standing.py`
- Modify: `pvt/__init__.py`, `cli.py`, `ui/recombination.py`, `ui/components.py`, all test imports, `README.md` (rewrite), `pyproject.toml` (add `--cov-fail-under=100`)

**Interfaces:**
- Produces: `from pvt import calculate_multistage, ...` continues to work (re-exports updated to new paths — external import surface unchanged). Coverage gate at 100% active in CI.

- [ ] **Step 1: Create `docs/excel-deviations.md`** with header and the first entries:

```markdown
# Excel Deviations Ledger

Every place the Python engine deliberately differs from a source workbook.
Each entry needs: workbook + cell proof, what Excel does, what the engine does, status
(`proposed` until reviewed point-by-point with Swej, then `approved`/`parity-kept`).

| ID | Workbook / cell | Excel behavior | Engine behavior | Status |
|----|-----------------|----------------|-----------------|--------|
| D-001 | Library canonization: LiveOil v4.1 vs Flash v6.1 `Component_Properties` (C7 100.205 vs 100.204; H2S 34.082 vs 34.0809; C36+ default 635 vs 636.4) | Two variants in circulation | One canonical table (Flash v6.1 values); C36+ MW is a per-study override | proposed |
| D-002 | Engine-wide | Sheets never call their validators; silent div/0 possible (e.g. recomb calc.py P_recomb=0) | `calc` raises `InputValidationError` unless `validate=False` | proposed |
```

- [ ] **Step 2: Perform the moves with `git mv`**, then fix imports:

```bash
mkdir -p pvt/experiments pvt/correlations/bubble_point
git mv pvt/recombination pvt/experiments/recombination
git mv pvt/correlations/standing.py pvt/correlations/bubble_point/standing.py
```

Update `pvt/__init__.py` re-export paths, `pvt/correlations/__init__.py`, new `pvt/correlations/bubble_point/__init__.py` (`from .standing import standing_bubble_point`), `cli.py`, `ui/recombination.py`, `ui/components.py` (change its deep import `from pvt.recombination.models import ...` to `from pvt import ...`), and every `tests/` import.

- [ ] **Step 3: Run full suite** — `pytest` → all PASS.

- [ ] **Step 4: Flip the gate** — in `pyproject.toml` set `addopts = "--cov=pvt --cov-report=term-missing --cov-fail-under=100"`. Run `pytest`. If any line is uncovered, either cover it with a real test or delete it (YAGNI) — no `# pragma: no cover` except on `if TYPE_CHECKING:` blocks.

- [ ] **Step 5: Rewrite `README.md`** — sections: what the platform is (one paragraph, spec link), quick start (`pip install -e ".[dev]"`, `streamlit run app.py`, `python cli.py --help`), repo layout (current tree), testing (`pytest`, the three tiers, 100% gate), the deviations ledger, phase roadmap.

- [ ] **Step 6: Commit** — `git add -A && git commit -m "refactor: move to experiments/ layout; deviations ledger; 100% coverage gate ..."`.

---

## Self-review checklist (run after writing, before executing)

- Spec §4 layout vs tasks: `core/` (Tasks 3–8), `qc/engine` (Task 9), moves (Task 10) — covered. `io/`, `reporting/`, `ui` rework are Phase 2. Correlations are Phase 1.
- Interfaces consumed by Phase 1/2 plans: `constants`, `units`, `Component/Library`, `CompositionStream`, `QCResult/grade/ThresholdRegistry`, exceptions — all defined here with exact names.
