# Phase 2: Flash + Recombination End-to-End Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first complete vertical slice: atmospheric Flash Separation and Live-Oil Preparation/Recombination — engine, QC checks, Excel import of the filled ADRIC templates, Streamlit UI in the v8 design language, and Excel report export.

**Architecture:** `pvt/experiments/flash/` (new) and `pvt/experiments/recombination/` (gains the molar route beside the existing volumetric SF/FF route). QC checks live in `pvt/qc/checks/`, importers in `pvt/io/excel_import/`, report building in `pvt/reporting/`. The Streamlit app becomes an `st.navigation` shell with per-study pages; all numbers rendered come from engine result objects.

**Tech Stack:** Python 3.12, openpyxl (read + write), Streamlit ≥1.37 with `streamlit.testing.v1.AppTest` for UI tests.

## Global Constraints

- Phases 0–1 complete. Coverage gate `--cov=pvt --cov-fail-under=100` stays green after every task (UI is outside the gate but must import cleanly and pass AppTest smoke tests).
- Golden values below are cached values from `ADRIC_Flash_Separation_Calc_v6.1.xlsx` and `ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx` (sample SA-372) — cite `# GOLDEN:` with cell refs.
- New deviations D-011…D-014 defined in tasks below; ledger entry lands in the same commit, status `proposed` until the Phase-2 wrap review with Swej.
- v8 design tokens: navy `#00205B`, action blue `#0047BB`, selected tint `#e8f0fe`, hover fill `#f0f5ff`, page bg `#f0f2f5`, QC red `#e53e3e` / green `#38a169` / amber `#dd9a0a`.
- Commit trailer: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`

---

### Task 1: Flash models + validation (`pvt/experiments/flash/`)

**Files:**
- Create: `pvt/experiments/flash/__init__.py`, `models.py`, `validate.py`
- Test: `tests/unit/experiments/test_flash_validate.py` (+ `tests/unit/experiments/__init__.py`)

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class FlashVolumetrics:
    pump_initial_cc: float
    pump_final_cc: float
    v_sto_cc: float
    oil_tare_g: float
    oil_gross_g: float
    gasometer_initial_cc: float
    gasometer_final_cc: float
    gas_temp_c: float
    gas_abs_pressure_mbar: float
    gas_gravity: float
    pump_constant: float = 1.0
    vcf: float = 1.0
    gasometer_factor: float = 1.0

@dataclass(frozen=True)
class FlashResults:
    v_press_cc: float; m_oil_g: float; v_gas_meas_cc: float; v_gas_std_cc: float
    gas_density_std_g_cc: float; m_gas_g: float; gor_cc_cc: float; gor_scf_bbl: float
    bo_flash: float; shrinkage: float; oil_density_60f_g_cc: float; api: float

def validate(inputs: FlashVolumetrics) -> list[str]
```

- `validate` rules (each producing one message): pump_final > pump_initial; gasometer_final ≥ gasometer_initial; v_sto_cc > 0; oil_gross_g > oil_tare_g; 0.5 < gas_gravity < 3.0; 500 < gas_abs_pressure_mbar < 1500; −10 < gas_temp_c < 60; factors > 0.

- [ ] **Step 1: Write failing tests** — one happy-path (SA-372 numbers, empty list) and one test per rule (`assert any("gravity" in e for e in errors)` style), plus a multi-error accumulation test.

```python
import dataclasses
from pvt.experiments.flash.models import FlashVolumetrics
from pvt.experiments.flash.validate import validate

SA372 = FlashVolumetrics(
    pump_initial_cc=50.0, pump_final_cc=70.8945, v_sto_cc=15.7576,
    oil_tare_g=100.0, oil_gross_g=113.71,
    gasometer_initial_cc=500.0, gasometer_final_cc=1458.2037,
    gas_temp_c=20.0, gas_abs_pressure_mbar=1012.25, gas_gravity=1.146,
)

def test_happy_path():
    assert validate(SA372) == []

def test_reversed_pump_flagged():
    bad = dataclasses.replace(SA372, pump_final_cc=40.0)
    assert any("pump" in e.lower() for e in validate(bad))

def test_errors_accumulate():
    bad = dataclasses.replace(SA372, pump_final_cc=40.0, gas_gravity=5.0, v_sto_cc=0.0)
    assert len(validate(bad)) == 3
```

- [ ] **Step 2–5:** fail → implement → pass → commit.

---

### Task 2: Flash calculation chain (`flash/calc.py`)

**Files:**
- Create: `pvt/experiments/flash/calc.py`
- Modify: `docs/excel-deviations.md` (D-011: workbook computes P_base = barometric + back-pressure in B25 but never uses it; engine takes the measured absolute pressure input only)
- Test: `tests/golden/test_flash_sa372.py` (+ `tests/golden/__init__.py`)

**Interfaces:**
- Consumes: `FlashVolumetrics`, `validate`, `constants`, `units`, `InputValidationError`.
- Produces: `def calculate(inputs: FlashVolumetrics, *, validate_inputs: bool = True) -> FlashResults` (raises `InputValidationError` listing messages when validation fails and `validate_inputs` is True).

- [ ] **Step 1: Write failing golden tests**

```python
import pytest
from pvt.experiments.flash.calc import calculate
from tests.unit.experiments.test_flash_validate import SA372

# GOLDEN: ADRIC_Flash_Separation_Calc_v6.1.xlsx, Volumetrics_Master (cached values)
def test_sa372_flash_chain():
    r = calculate(SA372)
    assert r.v_press_cc == pytest.approx(20.8945, abs=1e-4)          # B13
    assert r.m_oil_g == pytest.approx(13.71, abs=1e-9)               # B16
    assert r.v_gas_meas_cc == pytest.approx(958.2037, abs=1e-4)      # B19
    assert r.v_gas_std_cc == pytest.approx(940.5655, abs=0.001)      # B27
    assert r.gas_density_std_g_cc == pytest.approx(0.001404423, rel=1e-6)  # B28
    assert r.m_gas_g == pytest.approx(1.32095, abs=1e-5)             # B29
    assert r.gor_cc_cc == pytest.approx(59.6896, abs=0.001)          # B31
    assert r.gor_scf_bbl == pytest.approx(335.13, abs=0.01)          # B32
    assert r.bo_flash == pytest.approx(1.32600, abs=1e-5)            # B33
    assert r.shrinkage == pytest.approx(0.754151, abs=1e-6)          # B34
    assert r.oil_density_60f_g_cc == pytest.approx(0.870056, abs=1e-6)  # B36
    assert r.api == pytest.approx(31.133, abs=0.001)                 # B37

def test_invalid_inputs_raise():
    import dataclasses
    from pvt.core.exceptions import InputValidationError
    with pytest.raises(InputValidationError):
        calculate(dataclasses.replace(SA372, v_sto_cc=0.0))
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Implement**

```python
"""Atmospheric flash separation, water-pump method (ADRIC Flash v6.1 methodology)."""
from pvt.core import constants as c
from pvt.core import units as u
from pvt.core.exceptions import InputValidationError
from pvt.experiments.flash.models import FlashResults, FlashVolumetrics
from pvt.experiments.flash.validate import validate


def calculate(inputs: FlashVolumetrics, *, validate_inputs: bool = True) -> FlashResults:
    if validate_inputs and (errors := validate(inputs)):
        raise InputValidationError(errors)
    i = inputs
    v_press = (i.pump_final_cc - i.pump_initial_cc) * i.pump_constant * i.vcf
    m_oil = i.oil_gross_g - i.oil_tare_g
    v_gas_meas = (i.gasometer_final_cc - i.gasometer_initial_cc) * i.gasometer_factor
    # Ideal-gas (Z=1) correction to lab standard conditions; measured absolute pressure
    # is the input (workbook's unused B25 composite: ledger D-011).
    v_gas_std = v_gas_meas * (i.gas_abs_pressure_mbar / c.P_STD_MBAR) * (
        c.T_STD_K / (i.gas_temp_c + 273.15))
    gas_density = i.gas_gravity * c.AIR_DENSITY_STD_G_CC
    gor_cc = v_gas_std / i.v_sto_cc
    rho_sto = m_oil / i.v_sto_cc
    return FlashResults(
        v_press_cc=v_press, m_oil_g=m_oil, v_gas_meas_cc=v_gas_meas,
        v_gas_std_cc=v_gas_std, gas_density_std_g_cc=gas_density,
        m_gas_g=v_gas_std * gas_density, gor_cc_cc=gor_cc,
        gor_scf_bbl=gor_cc * c.FT3_PER_BBL, bo_flash=v_press / i.v_sto_cc,
        shrinkage=i.v_sto_cc / v_press, oil_density_60f_g_cc=rho_sto,
        api=u.api_from_density_g_cc(rho_sto),
    )
```

- [ ] **Step 4: Run to verify pass** (note `gas_density_std_g_cc` golden uses gravity × 0.0012255, matching the sheet's yellow B22 = our constant). Add ledger D-011.

- [ ] **Step 5: Commit.**

---

### Task 3: Mass-basis recombination + plus fractions (`flash/recombine.py`, `core/plus_fractions.py`)

**Files:**
- Create: `pvt/experiments/flash/recombine.py`, `pvt/core/plus_fractions.py`
- Test: `tests/golden/test_flash_recombination_sa372.py`, `tests/fixtures/sa372_flash.py`

**Interfaces:**
- Produces:
  - `pvt/core/plus_fractions.py`: `@dataclass(frozen=True) PlusFraction(mol_pct, wt_pct, mw, density_g_cc)`; `def plus_fraction(stream: CompositionStream, cut: str) -> PlusFraction` with positional boundaries on the 52-slot order: `"C7+"` from `C7` (MCP/Benzene/CycloC6 excluded, MCH/Toluene included), `"C11+"` from `C11`, `"C20+"` from `C20`, `"C36+"` = C36+ only. MW mole-weighted; density = Σwt/Σ(wt/ρᵢ).
  - `flash/recombine.py`: `@dataclass(frozen=True) MassRecombination(wf_gas, wf_oil, wellstream: CompositionStream, mw_whole_sample)`; `def recombine_mass(m_oil_g: float, m_gas_g: float, oil_stream: CompositionStream, gas_stream: CompositionStream) -> MassRecombination` — wellstream wt% = wf_gas·gas_wtᵢ + wf_oil·oil_wtᵢ (normalized wt bases), mol% back-calculated from wt/MW renormalized; `mw_whole_sample = 100/Σ(wtᵢ/MWᵢ)`.

- [ ] **Step 1: Create `tests/fixtures/sa372_flash.py`** with the flash workbook's GC inputs (both streams, mol% AND wt%, the 52-row table from the digest — transcribe the full nonzero dict exactly as digested: gas C1 47.656/23.242 ... oil C36+ 4.912/16.456; ~50 lines).

- [ ] **Step 2: Write failing golden tests**

```python
import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.plus_fractions import plus_fraction
from pvt.experiments.flash.recombine import recombine_mass
from tests.fixtures import sa372_flash as fx

def _streams():
    oil = CompositionStream(library=KF, mol_pct=fx.OIL_MOL_PCT, wt_pct=fx.OIL_WT_PCT)
    gas = CompositionStream(library=KF, mol_pct=fx.GAS_MOL_PCT, wt_pct=fx.GAS_WT_PCT)
    return oil, gas

def test_golden_wf_and_mw():
    oil, gas = _streams()
    r = recombine_mass(13.71, 1.32095, oil, gas)
    assert r.wf_gas == pytest.approx(0.0878821, rel=1e-5)        # Recombination!B18
    assert r.mw_whole_sample == pytest.approx(135.0426, rel=1e-4)  # B21 (Convention A)

def test_golden_c7_plus_of_recombined():
    oil, gas = _streams()
    ws = recombine_mass(13.71, 1.32095, oil, gas).wellstream
    pf = plus_fraction(ws, "C7+")
    # GOLDEN: Plus_Properties_Report, Recombined column
    assert pf.mol_pct == pytest.approx(51.119, abs=0.05)
    assert pf.wt_pct == pytest.approx(84.236, abs=0.05)
    assert pf.mw == pytest.approx(222.53, abs=0.3)
    assert pf.density_g_cc == pytest.approx(0.84661, abs=5e-4)

def test_mol_and_wt_mw_routes_agree():
    oil, gas = _streams()
    ws = recombine_mass(13.71, 1.32095, oil, gas).wellstream
    assert ws.mw_from_mol() == pytest.approx(ws.mw_from_wt(), rel=1e-9)

def test_cut_boundaries():
    oil, _ = _streams()
    c7 = plus_fraction(oil, "C7+")
    # MCP/Benzene/CycloC6 are NOT in C7+ (positional convention, flash workbook rows 57+)
    assert c7.mol_pct == pytest.approx(79.873, abs=0.05)  # GOLDEN: flashed-liquid C7+
```

- [ ] **Step 3–5:** fail → implement → pass → commit.

---

### Task 4: Molar recombination route (`recombination/molar.py`)

**Files:**
- Create: `pvt/experiments/recombination/molar.py`
- Modify: `docs/excel-deviations.md` (D-012: LiveOil B8 GOR-basis toggle appears inverted vs convention — engine implements the conventional direction, REQUIRES Swej confirmation; goldens unaffected because the workbook's B_st = 1.0)
- Test: `tests/golden/test_molar_recombination_sa372.py`

**Interfaces:**
- Produces:

```python
class GorBasis(StrEnum):
    SEPARATOR = "separator"      # scf per separator barrel: divided by shrinkage to STO basis
    STOCK_TANK = "stock_tank"    # already scf/STB: used as-is

@dataclass(frozen=True)
class MolarSplit:
    gor_scf_stb_effective: float; gor_cc_cc: float
    n_gas_per_cc_sto: float; n_oil_per_cc_sto: float
    f_gas: float; f_oil: float; w_gas: float; w_oil: float; mw_wellstream: float

def molar_split(gor: float, basis: GorBasis, shrinkage: float, sto_density_g_cc: float,
                sto_mw: float, gas_mw: float, z_std: float = 0.99) -> MolarSplit
def wellstream(split: MolarSplit, sto: CompositionStream, gas: CompositionStream) -> CompositionStream
def k_values(gas: CompositionStream, liquid: CompositionStream) -> dict[str, float]  # y/x, x>0 only
```

Formulas (LiveOil Recombination sheet): `gor_cc = gor_eff · SCF_STB_TO_CC_CC`; `n_gas = P_STD_PSIA·gor_cc/(z_std·R_PSIA_CC_MOL_K·T_STD_K)`; `n_oil = ρ_sto/MW_sto`; `f_gas = n_gas/(n_gas+n_oil)`; `w_gas = f_gas·MW_gas/(f_gas·MW_gas + f_oil·MW_sto)`; `mw = f_gas·MW_gas + f_oil·MW_sto`; wellstream `zᵢ = f_gas·yᵢ + f_oil·xᵢ` on normalized mol bases.

- [ ] **Step 1: Write failing golden tests**

```python
import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.experiments.recombination.molar import GorBasis, molar_split, wellstream
from tests.fixtures import sa372

# GOLDEN: ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx, Recombination sheet
def _split():
    return molar_split(339.0, GorBasis.STOCK_TANK, 1.0,
                       sto_density_g_cc=0.8196, sto_mw=187.05, gas_mw=26.10, z_std=0.99)

def test_golden_molar_split():
    s = _split()
    assert s.gor_cc_cc == pytest.approx(60.378, abs=0.001)            # B25
    assert s.n_gas_per_cc_sto == pytest.approx(0.00258036, rel=1e-4)  # B26
    assert s.n_oil_per_cc_sto == pytest.approx(0.00438162, rel=1e-4)  # B27
    assert s.f_gas == pytest.approx(0.370636, abs=1e-5)               # B29
    assert s.w_gas == pytest.approx(0.075937, abs=1e-5)               # B31
    assert s.mw_wellstream == pytest.approx(127.40, abs=0.01)         # B33

def test_golden_wellstream_composition():
    lib = KF.with_c36_mw(635.0)
    sto = CompositionStream(library=lib, mol_pct=sa372.STO_MOL_PCT)
    gas = CompositionStream(library=lib, mol_pct=sa372.GAS_MOL_PCT)
    ws = wellstream(_split(), sto, gas)
    z = ws.normalized_mol()
    assert z["C1"] == pytest.approx(23.17, abs=0.02)                  # J-col, C1 row
    assert z["C36+"] == pytest.approx(2.97, abs=0.01)
    assert sum(z.values()) == pytest.approx(100.0, abs=1e-9)

def test_separator_basis_direction():
    # D-012: conventional direction — separator GOR (scf/sep-bbl) / shrinkage -> STO basis.
    sep = molar_split(339.0, GorBasis.SEPARATOR, 0.8, 0.8196, 187.05, 26.10)
    st = molar_split(339.0, GorBasis.STOCK_TANK, 0.8, 0.8196, 187.05, 26.10)
    assert sep.gor_scf_stb_effective == pytest.approx(339.0 / 0.8)
    assert st.gor_scf_stb_effective == pytest.approx(339.0)
```

- [ ] **Step 2–5:** fail → implement → pass → commit with ledger D-012 (status `proposed — needs Swej ruling`; the workbook divides in the STOCK_TANK branch instead).

---

### Task 5: Cylinder loading volumes + GOR verification (`recombination/loading.py`)

**Files:**
- Create: `pvt/experiments/recombination/loading.py`
- Test: `tests/golden/test_loading_sa372.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True)
class LoadingInputs:
    cylinder_volume_cc: float; target_oil_cc: float
    oil_load_p_psig: float; oil_load_t_f: float
    gas_load_p_psig: float; gas_load_t_f: float; z_gas_load: float
    sto_density_at_load_g_cc: float

@dataclass(frozen=True)
class LoadingPlan:
    v_oil_charge_cc: float; v_sto_equivalent_cc: float; n_oil_mol: float
    n_gas_mol: float; v_gas_std_cc: float; std_cc_per_cc_at_load: float
    v_gas_charge_cc: float; total_charge_cc: float; fits: bool; utilization_pct: float

def plan_loading(inputs: LoadingInputs, split: MolarSplit, sto_density_60f: float,
                 sto_mw: float, z_std: float = 0.99) -> LoadingPlan
def verify_actual_gor(actual_oil_cc: float, actual_gas_cc: float, inputs: LoadingInputs,
                      sto_density_60f: float, target_gor_scf_stb: float,
                      z_std: float = 0.99, registry: ThresholdRegistry | None = None
                      ) -> tuple[float, float, QCResult]   # (actual_gor, dev_pct, qc)
```

Formulas (Loading_Volumes sheet): `v_sto_equiv = target_oil · ρ_load/ρ_60F`; `n_oil = v_sto_equiv·ρ_60F/MW`; `n_gas = split.n_gas_per_cc_sto · v_sto_equiv`; `v_gas_std = n_gas·z_std·R_PSIA_CC_MOL_K·T_STD_K/P_STD_PSIA`; `factor = P_load_psia·z_std·T_STD_K/(z_load·T_load_K·P_STD_PSIA)` with `P_load_psia = psig + 14.73` (lab basis, note vs `P_ATM_PSIA` in the docstring), `T_load_K = u.f_to_k(t_f)`; `v_gas_charge = v_gas_std/factor`; fits gate `total ≤ 0.95·cylinder`. Verification: `n_actual = actual_gas·P_load/(z_load·R·T_load)`; `v_std = n·z_std·R·T_STD_K/P_STD`; `sto_actual = actual_oil·ρ_load/ρ_60`; `gor = (v_std/sto_actual)·CC_PER_STB/CC_PER_SCF`; deviation vs target graded with registry key `"gor_actual_vs_target_pct"` (5/10).

- [ ] **Step 1: Write failing golden tests**

```python
import pytest
from pvt.experiments.recombination.loading import LoadingInputs, plan_loading, verify_actual_gor
from pvt.qc.engine import Severity
from tests.golden.test_molar_recombination_sa372 import _split

INPUTS = LoadingInputs(cylinder_volume_cc=1000.0, target_oil_cc=150.0,
                       oil_load_p_psig=2000.0, oil_load_t_f=75.0,
                       gas_load_p_psig=5000.0, gas_load_t_f=75.0, z_gas_load=0.85,
                       sto_density_at_load_g_cc=0.885)

# GOLDEN: ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx, Loading_Volumes sheet
def test_golden_loading_plan():
    p = plan_loading(INPUTS, _split(), sto_density_60f=0.8196, sto_mw=187.05, z_std=0.99)
    assert p.v_oil_charge_cc == 150.0                                   # B22
    assert p.v_sto_equivalent_cc == pytest.approx(161.97, abs=0.01)     # B23
    assert p.n_oil_mol == pytest.approx(0.709687, rel=1e-4)             # B25
    assert p.n_gas_mol == pytest.approx(0.417938, rel=1e-4)             # B29
    assert p.v_gas_std_cc == pytest.approx(9779.46, abs=0.5)            # B30
    assert p.std_cc_per_cc_at_load == pytest.approx(385.39, abs=0.05)   # B31
    assert p.v_gas_charge_cc == pytest.approx(25.38, abs=0.01)          # B32
    assert p.fits is True and p.utilization_pct == pytest.approx(17.5, abs=0.1)

def test_golden_actual_gor_fails_gate():
    gor, dev, qc = verify_actual_gor(108.96, 27.47, INPUTS, 0.8196,
                                     target_gor_scf_stb=339.0, z_std=0.99)
    assert gor == pytest.approx(505.2, abs=0.5)                         # B47
    assert dev == pytest.approx(49.03, abs=0.1)                         # B49
    assert qc.severity == Severity.FAIL                                 # B50 "FAIL >10%"
```

- [ ] **Step 2–5:** fail → implement → pass → commit.

---

### Task 6: QC checks for the slice (`pvt/qc/checks/`)

**Files:**
- Create: `pvt/qc/checks/__init__.py`, `composition_normalization.py`, `mw_consistency.py`, `hoffman_crump.py`
- Test: `tests/unit/qc/test_checks.py` (+ `tests/unit/qc/__init__.py`)

**Interfaces:**
- Produces:
  - `composition_normalization.check(stream: CompositionStream, basis: Literal["mol","wt"], registry: ThresholdRegistry | None = None) -> QCResult` — grades `|raw_sum − 100|` with key `"composition_sum"`.
  - `mw_consistency.check(stream, registry=None) -> QCResult` — grades `mw_consistency_pct()` with key `"mw_consistency_pct"`.
  - `hoffman_crump.py`: `@dataclass(frozen=True) HoffmanPoint(code, k, f_factor, log10_kp)`; `@dataclass(frozen=True) HoffmanResult(points: list[HoffmanPoint], slope, intercept, r_squared, qc: QCResult)`; `def check(gas: CompositionStream, liquid: CompositionStream, p_psia: float, t_f: float, registry=None) -> HoffmanResult` — per component present in both streams with x>0 and y>0: `K=y/x`, `b = log10(Pc/14.7)/(1/Tb − 1/Tc)`, `F = b(1/Tb − 1/T_R)`, `y-val = log10(K·p_psia)`; least-squares line, R²; registry key `"hoffman_r2"` added to `DEFAULTS` as `(0.98, 0.95)` graded on `1 − r²` bands — mark in the docstring: *default thresholds proposed by engineering judgment (the sheets are visual-only); configurable, pending Swej calibration.* Note the 14.7 inside b is the Hoffman convention constant (not `P_STD_PSIA`) — named local `_HOFFMAN_P_ATM = 14.7` with comment.

- [ ] **Step 1: Write failing tests**

```python
import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.qc.checks import composition_normalization, hoffman_crump, mw_consistency
from pvt.qc.engine import Severity
from tests.fixtures import sa372

def test_normalization_review_band():
    sto = CompositionStream(library=KF.with_c36_mw(635.0), mol_pct=sa372.STO_MOL_PCT)
    qc = composition_normalization.check(sto, "mol")
    assert qc.severity == Severity.REVIEW        # GOLDEN: raw sum 99.31 -> "REVIEW" (I67)

def test_hoffman_b_factor_matches_reference():
    # GOLDEN(loose): PVT-check Hoffman sheet, C1 at Tsep=55.4F: b=805.4586 with ITS table;
    # KF library Tb/Pc/Tc differ in the 3rd digit -> 1% tolerance.
    res = hoffman_crump.check(
        CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0}),
        CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0}),
        p_psia=355.0, t_f=55.4)
    c1 = next(p for p in res.points if p.code == "C1")
    b_c1 = c1.f_factor / (1 / KF.get("C1").tb_r - 1 / (55.4 + 459.67))
    assert b_c1 == pytest.approx(805.4586, rel=0.01)

def test_hoffman_r2_perfect_for_two_points():
    res = hoffman_crump.check(
        CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0}),
        CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0}),
        p_psia=355.0, t_f=55.4)
    assert res.r_squared == pytest.approx(1.0, abs=1e-12)   # 2 points define the line
    assert res.qc.severity == Severity.PASS

def test_mw_consistency_grades():
    sto = CompositionStream(library=KF.with_c36_mw(635.0), mol_pct=sa372.STO_MOL_PCT)
    derived = CompositionStream(library=sto.library, mol_pct=sa372.STO_MOL_PCT,
                                wt_pct=sto.wt_from_mol())
    assert mw_consistency.check(derived).severity == Severity.PASS
```

- [ ] **Step 2–5:** fail → implement → pass → commit.

---

### Task 7: Excel importer, Flash template (`pvt/io/excel_import/flash_v61.py`)

**Files:**
- Create: `pvt/io/__init__.py`, `pvt/io/excel_import/__init__.py`, `pvt/io/excel_import/flash_v61.py`
- Create: `tests/fixtures/workbooks/` (copies of the two filled ADRIC templates)
- Test: `tests/golden/test_import_flash_v61.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) FlashImport(volumetrics: FlashVolumetrics, oil_stream: CompositionStream, gas_stream: CompositionStream, sample: Sample)`; `def read(path: str | Path) -> FlashImport`. Reads ONLY input cells (yellow-cell map from the dissection): metadata A-block (`B5:B8`, `E5:E8`, `H5:H8`), volumetrics (`B11,E11,B12,E12,B14,B15,E15,B17,B18,E18,B20,E17,E20,B21,E21`), compositions rows 41–92 cols E–H against the component order rows, with `openpyxl.load_workbook(path, data_only=True, read_only=True)`. Unknown layout (missing sheet `Volumetrics_Master` or shifted header) raises `InputValidationError`.

- [ ] **Step 1: Copy the filled templates into the repo as fixtures**

```bash
mkdir -p tests/fixtures/workbooks
cp "/Users/swej/Swej/PVT Calculationssss/2_Flahs, Recomb Live Oil/ADRIC_Flash_Separation_Calc_v6.1.xlsx" tests/fixtures/workbooks/
cp "/Users/swej/Swej/PVT Calculationssss/2_Flahs, Recomb Live Oil/ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx" tests/fixtures/workbooks/
git add tests/fixtures/workbooks
```

- [ ] **Step 2: Write failing integration test — import → calculate → golden**

```python
import pytest
from pathlib import Path
from pvt.experiments.flash.calc import calculate
from pvt.io.excel_import.flash_v61 import read

WB = Path("tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx")

def test_import_then_calculate_reproduces_workbook():
    imp = read(WB)
    r = calculate(imp.volumetrics)
    assert r.gor_scf_bbl == pytest.approx(335.13, abs=0.01)
    assert r.bo_flash == pytest.approx(1.32600, abs=1e-5)
    assert r.api == pytest.approx(31.133, abs=0.001)
    assert imp.sample.sample_id == "SA-372"
    assert imp.oil_stream.raw_mol_sum() == pytest.approx(100.0, abs=0.5)

def test_wrong_file_rejected():
    from pvt.core.exceptions import InputValidationError
    with pytest.raises(InputValidationError):
        read(Path("tests/fixtures/workbooks/ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx"))
```

- [ ] **Step 3–5:** fail → implement (cell map as a module-level dict; loop rows 41–92 matching col B codes to library codes via a small alias map, e.g. `"Cyclohexane"→"CycloC6"`) → pass → commit.

---

### Task 8: Excel importer, LiveOil template (`excel_import/liveoil_v41.py`)

**Files:**
- Create: `pvt/io/excel_import/liveoil_v41.py`
- Test: `tests/golden/test_import_liveoil_v41.py`

**Interfaces:**
- Produces: `@dataclass(frozen=True) LiveOilImport(gor: float, gor_basis: GorBasis, shrinkage: float, z_std: float, sto_density_60f: float, c36_mw: float, sto_stream, gas_stream, loading: LoadingInputs, sample: Sample)`; `def read(path) -> LiveOilImport`. Cell map: `Recombination!B5` (GOR), `B6` (basis dropdown text), `B7` (shrinkage), `B12` (z_std), `STO_Composition!B5` (ρ), `D65` (C36+ MW), compositions col I rows 15–65 both sheets, `Loading_Volumes!B5:B13` + amber/teal cells (`B7,B8,B12,B9,B10,B11`), `Sample_Info` block.

- [ ] **Step 1: Write failing integration test**

```python
import pytest
from pathlib import Path
from pvt.experiments.recombination.molar import molar_split, wellstream
from pvt.io.excel_import.liveoil_v41 import read

WB = Path("tests/fixtures/workbooks/ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx")

def test_import_then_recombine_reproduces_workbook():
    imp = read(WB)
    assert imp.gor == 339.0 and imp.z_std == 0.99
    split = molar_split(imp.gor, imp.gor_basis, imp.shrinkage, imp.sto_density_60f,
                        imp.sto_stream.mw_from_mol(), imp.gas_stream.mw_from_mol(),
                        z_std=imp.z_std)
    assert split.f_gas == pytest.approx(0.370636, abs=1e-4)
    ws = wellstream(split, imp.sto_stream, imp.gas_stream)
    assert ws.normalized_mol()["C1"] == pytest.approx(23.17, abs=0.05)
```

- [ ] **Step 2–5:** fail → implement → pass → commit. (Basis-cell text "Separator"/"Stock Tank" maps to `GorBasis` **through the D-012 convention decision** — until Swej rules, map sheet text verbatim to the enum and pass `shrinkage=1.0` through untouched, which reproduces the workbook because its B7=1; leave a `# D-012` comment at the mapping site.)

---

### Task 9: Report tables + Excel export (`pvt/reporting/`)

**Files:**
- Create: `pvt/reporting/__init__.py`, `pvt/reporting/tables.py`, `pvt/reporting/excel_export.py`
- Test: `tests/unit/test_reporting.py`

**Interfaces:**
- Produces:
  - `tables.py`: `@dataclass(frozen=True) ReportRow(label: str, value: str, unit: str = "")`; `@dataclass(frozen=True) ReportTable(title: str, rows: list[ReportRow])`; `def flash_tables(results: FlashResults, recomb: MassRecombination, qc: list[QCResult]) -> list[ReportTable]` (sections: Flash Results, Whole Sample, QC Summary — QC rows show `check_id`, severity, message); `def recombination_tables(split: MolarSplit, plan: LoadingPlan, qc: list[QCResult]) -> list[ReportTable]`.
  - `excel_export.py`: `def write_report(path: str | Path, tables: list[ReportTable], *, title: str, sample: Sample) -> None` — openpyxl workbook, one sheet, ADRIC-style header (navy fill `00205B`, white bold), section titles bold, three-column rows, severity cells filled green/amber/red (`38A169`/`DD9A0A`/`E53E3E`).

- [ ] **Step 1: Write failing tests**

```python
import openpyxl
import pytest
from pvt.core.sample import Sample
from pvt.qc.engine import QCResult, Severity
from pvt.reporting.excel_export import write_report
from pvt.reporting.tables import ReportRow, ReportTable

def test_round_trip_report(tmp_path):
    tables = [ReportTable("Flash Results", [ReportRow("GOR", "335.13", "scf/bbl"),
                                            ReportRow("Bo", "1.3260", "vol/vol")]),
              ReportTable("QC Summary", [ReportRow("composition_sum", "REVIEW", "")])]
    out = tmp_path / "report.xlsx"
    write_report(out, tables, title="Flash Separation Report",
                 sample=Sample(sample_id="SA-372", well="WELL-X", field_name="Upper Zakum",
                               reservoir="Kharaib-2", depth_ft_md=9105.0,
                               fluid_type="Black Oil", cylinder="RF1168636"))
    ws = openpyxl.load_workbook(out).active
    text = [[c.value for c in row] for row in ws.iter_rows()]
    flat = [str(v) for row in text for v in row if v is not None]
    assert "Flash Separation Report" in flat and "SA-372" in flat
    assert "GOR" in flat and "335.13" in flat and "scf/bbl" in flat
```

Plus a `flash_tables` unit test asserting section titles and that every `QCResult` passed in appears as a row.

- [ ] **Step 2–5:** fail → implement → pass → commit.

---

### Task 10: Streamlit shell, theme, common components

**Files:**
- Create: `ui/theme.py`, `ui/common/__init__.py`, `ui/common/components.py`, `ui/pages/__init__.py`
- Rewrite: `app.py` (repo root)
- Delete: `ui/styles.py`, `ui/components.py`, `ui/recombination.py` (superseded; the stashed ASCII-diagram tweak `stash@{0}` becomes obsolete — flag to Swej in the wrap task before dropping)
- Test: `tests/ui/test_shell.py` (+ `tests/ui/__init__.py`; NOT under the pvt coverage gate)

**Interfaces:**
- Produces:
  - `ui/theme.py`: `TOKENS: dict[str, str]` (`navy #00205B`, `blue #0047BB`, `tint #e8f0fe`, `hover #f0f5ff`, `bg #f0f2f5`, `qc_red #e53e3e`, `qc_green #38a169`, `qc_amber #dd9a0a`); `def inject() -> None` (one `st.markdown` CSS block: headings navy, buttons blue, metric-card class).
  - `ui/common/components.py`: `def page_header(title: str, subtitle: str) -> None`; `def metric_card(label: str, value: str, unit: str = "") -> None`; `def qc_pill(result: QCResult) -> None` (colored dot + check id + message); `def qc_panel(results: list[QCResult]) -> None`; `def calc_steps(steps: list[tuple[str, str]]) -> None` (expander of label/formula-rendered rows); `def report_download(tables, sample, filename: str) -> None` (builds xlsx in `BytesIO` via `write_report`, `st.download_button`).
  - `app.py`: `st.navigation` with two `st.Page` entries — "Flash Separation (SSF)" → `ui/pages/flash_page.py`, "Recombination / Live Oil" → `ui/pages/recombination_page.py`; `st.set_page_config(page_title="ADRIC PVT Platform", layout="wide")`; `theme.inject()`.

- [ ] **Step 1: Write failing AppTest smoke test**

```python
from streamlit.testing.v1 import AppTest

def test_shell_boots_without_exception():
    at = AppTest.from_file("app.py").run()
    assert not at.exception
```

- [ ] **Step 2–5:** fail (pages missing) → implement shell + theme + components with placeholder-free minimal pages created in Tasks 11–12 (create empty page modules rendering `page_header` only so the shell boots) → pass → commit.

---

### Task 11: Flash page (`ui/pages/flash_page.py`)

**Files:**
- Create: `ui/pages/flash_page.py`
- Test: `tests/ui/test_flash_page.py`

**Interfaces:**
- Consumes: `flash_v61.read`, `flash.calc.calculate`, `recombine_mass`, QC checks, `flash_tables`, common components.
- Produces: page with two input modes — `st.file_uploader` ("Upload filled ADRIC Flash v6.1 template") and a manual `st.form` mirroring `FlashVolumetrics` fields (number inputs with the validate.py ranges as min/max, session keys prefixed `flash.`) — then: metric cards (GOR scf/bbl, Bo, shrinkage, density, API), composition QC pills, Hoffmann plot (`st.scatter_chart` of F vs log10(K·P)), calc-steps expander (V_press → m_oil → V_gas_std → GOR → Bo chain with numbers), and `report_download`.

- [ ] **Step 1: Write failing AppTest**

```python
from streamlit.testing.v1 import AppTest

def test_flash_page_manual_flow():
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    assert not at.exception
    # fill the manual form with SA-372 numbers and submit
    inputs = {"flash.pump_initial_cc": 50.0, "flash.pump_final_cc": 70.8945,
              "flash.v_sto_cc": 15.7576, "flash.oil_tare_g": 100.0,
              "flash.oil_gross_g": 113.71, "flash.gasometer_initial_cc": 500.0,
              "flash.gasometer_final_cc": 1458.2037, "flash.gas_temp_c": 20.0,
              "flash.gas_abs_pressure_mbar": 1012.25, "flash.gas_gravity": 1.146}
    for key, val in inputs.items():
        at.number_input(key=key).set_value(val)
    at.button[0].click()
    at.run()
    assert not at.exception
    assert any("335.1" in str(m.value) for m in at.markdown)   # GOR card rendered
```

- [ ] **Step 2–5:** fail → implement → pass → commit. (Composition entry in manual mode: `st.data_editor` seeded with the 52 component codes and zero mol%/wt% columns; upload mode fills everything from the importer.)

---

### Task 12: Recombination page rebuild + CLI + phase wrap

**Files:**
- Create: `ui/pages/recombination_page.py`
- Modify: `cli.py` (add `flash` subcommand; align recombination flags with the surviving engine API), `README.md` (pages + import + report sections), `docs/excel-deviations.md` (final statuses)
- Test: `tests/ui/test_recombination_page.py`, `tests/unit/test_cli.py`

**Interfaces:**
- Produces:
  - Recombination page with two tabs: **Volumetric (SF/FF)** — ports the existing `calculate_multistage` UI flow (Case 1/Case 2 selector, single separator stage, charging pressure + compressibility (the `_compute_compressibility` logic moves INTO `pvt/experiments/recombination/compressibility.py` as `def effective_c_o(model: Literal["constant","polynomial"], value_or_coeffs, p_ref_psia) -> float` with unit tests — closing the old UI-leak); **Molar (composition)** — GOR/basis/density/MW inputs or LiveOil template upload → split, wellstream table, loading plan, actual-GOR verify, QC pills, report download.
  - `cli.py flash --workbook <path>` → prints the flash report tables as fixed-width text; `cli.py recombine ...` retains existing behavior on the new import paths.
- Test contract: AppTest boots both tabs without exception and reproduces `f_gas ≈ 0.370636` from typed molar inputs; CLI test runs `flash` on the fixture workbook via `subprocess` or direct `main([...])` call asserting "335.13" in captured output.

- [ ] **Step 1: Write failing tests** (AppTest as Task 11 pattern; CLI:)

```python
from cli import main

def test_cli_flash_on_fixture(capsys):
    main(["flash", "--workbook", "tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx"])
    out = capsys.readouterr().out
    assert "335.13" in out and "SA-372" in out
```

- [ ] **Step 2: Implement page + `compressibility.py` move + CLI.**

- [ ] **Step 3: Full suite green at 100% gate; AppTest suite green.**

- [ ] **Step 4: Phase wrap — deviations review with Swej.** Present ledger D-001…D-014 point by point with proofs (this is a conversation, not code): D-012 (GOR-basis direction) needs an explicit ruling; also ask to drop `stash@{0}` (obsolete ASCII-diagram tweak on the deleted `ui/recombination.py`). Flip reviewed entries to `approved`/`parity-kept`.

- [ ] **Step 5: Commit + update README + tag** `git tag v0.2.0-flash-recomb`.

---

## Self-review checklist

- Spec §2 Phase 2 vs tasks: engine (1–5), QC (6), Excel import (7–8), report export (9), UI in v8 styling (10–12), CLI parity (12) — covered. Cross-test `CrossRef` wiring has no consumer until CCE lands (Phase 3) — deliberately not exercised here beyond `Sample` in imports/reports.
- Type consistency: `MolarSplit` fields used in Tasks 4/5/8/12 match; `QCResult`/`Severity`/`ThresholdRegistry` per Phase 0 Task 9; `FlashVolumetrics` fields identical in Tasks 1/2/7/11.
- Golden numbers all cite workbook cells captured in the dissection reports; tolerances account for the canonical-vs-workbook component-table differences (D-001).
