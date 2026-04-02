"""
pvt_calc.py — Core calculation functions for PVT separator recombination.
No UI logic. All inputs/outputs in stated units.
"""

from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
P_STD_PSIA = 14.696              # psia
T_STD_F    = 60.0                # °F
T_STD_R    = T_STD_F + 459.67   # Rankine = 519.67

# Conversion: scf/STB → cc/cc  (= sm³/sm³)
SCF_TO_CC        = 28_316.85     # 1 scf  = 28 316.85 cc
STB_TO_CC        = 158_987.1     # 1 STB  = 158 987.1 cc
SCF_STB_TO_CC_CC = SCF_TO_CC / STB_TO_CC   # ≈ 0.178107

# SI pressure
BARA_TO_PSIA = 14.5038           # 1 bara = 14.5038 psia
CC_TO_SM3    = 1e-6              # 1 sm³  = 1 000 000 cc

Units = Literal["field", "si"]


# ===========================================================================
# Single-stage data structures (original API — preserved)
# ===========================================================================

@dataclass
class RecombinationInputs:
    """All inputs for a single-stage separator recombination calculation."""
    V_cell:      float           # cc — recombination cell volume
    R_sep:       float           # scf/STB (field) or sm³/sm³ (SI) — separator GOR
    P_sep:       float           # psia (field) or bara (SI)
    T_sep:       float           # °F (field) or °C (SI)
    Z_sep:       float           # dimensionless — Z-factor at separator conditions
    Bo_sep:      float = 1.0     # dimensionless — oil FVF at separator conditions
    oil_fraction: float = 0.70   # fraction of cell volume to fill with separator oil
    units:       Units = "field"


@dataclass
class RecombinationResults:
    """All outputs from a single-stage separator recombination calculation."""
    V_oil_sep:       float   # cc — separator oil to charge
    V_oil_STO:       float   # cc — equivalent stock-tank oil volume
    V_gas_std_cc:    float   # cc  @ standard conditions
    V_gas_std_unit:  float   # scf (field) or sm³ (SI) @ standard conditions
    V_gas_sep:       float   # cc  @ separator conditions
    GOR_check:       float   # back-calculated GOR in original input units
    GOR_input:       float   # original input GOR for comparison
    R_cc:            float   # cc/cc — GOR in volumetric-ratio form
    P_sep_psia:      float   # internal — separator pressure in psia
    T_sep_R:         float   # internal — separator temperature in Rankine
    T_sep_F:         float   # separator temperature in °F (for display)
    units:           Units


def validate(inp: RecombinationInputs) -> list[str]:
    """Return list of error strings; empty list = OK."""
    errors: list[str] = []
    if inp.V_cell <= 0:
        errors.append("Cell volume must be > 0 cc.")
    if inp.R_sep <= 0:
        errors.append("GOR must be > 0.")
    if inp.P_sep <= 0:
        errors.append("Separator pressure must be > 0.")
    if inp.Z_sep <= 0 or inp.Z_sep > 2.0:
        errors.append("Z-factor must be in range (0, 2.0].")
    if inp.Bo_sep <= 0 or inp.Bo_sep > 5.0:
        errors.append("Bo_sep must be in range (0, 5.0].")
    if not (0.0 < inp.oil_fraction < 1.0):
        errors.append("Oil fraction must be between 0 and 1 (exclusive).")
    if inp.units == "field" and inp.T_sep < -100:
        errors.append("Separator temperature (°F) looks unrealistically low.")
    if inp.units == "si" and inp.T_sep < -73:
        errors.append("Separator temperature (°C) looks unrealistically low.")
    return errors


def calculate(inp: RecombinationInputs) -> RecombinationResults:
    """Perform single-stage separator recombination calculation."""
    if inp.units == "field":
        P_sep_psia = inp.P_sep
        T_sep_R    = inp.T_sep + 459.67
        T_sep_F    = inp.T_sep
        R_cc       = inp.R_sep * SCF_STB_TO_CC_CC
    else:
        P_sep_psia = inp.P_sep * BARA_TO_PSIA
        T_sep_F    = inp.T_sep * 9.0 / 5.0 + 32.0
        T_sep_R    = T_sep_F + 459.67
        R_cc       = inp.R_sep   # sm³/sm³ == cc/cc ratio

    V_oil_sep    = inp.oil_fraction * inp.V_cell
    V_oil_STO    = V_oil_sep / inp.Bo_sep
    V_gas_std_cc = R_cc * V_oil_STO

    if inp.units == "field":
        V_gas_std_unit = V_gas_std_cc / SCF_TO_CC
    else:
        V_gas_std_unit = V_gas_std_cc * CC_TO_SM3

    V_gas_sep = (
        V_gas_std_cc
        * (P_STD_PSIA / P_sep_psia)
        * (T_sep_R / T_STD_R)
        * inp.Z_sep
    )

    R_cc_check = V_gas_std_cc / V_oil_STO if V_oil_STO > 0 else 0.0
    GOR_check  = R_cc_check / SCF_STB_TO_CC_CC if inp.units == "field" else R_cc_check

    return RecombinationResults(
        V_oil_sep=V_oil_sep,
        V_oil_STO=V_oil_STO,
        V_gas_std_cc=V_gas_std_cc,
        V_gas_std_unit=V_gas_std_unit,
        V_gas_sep=V_gas_sep,
        GOR_check=GOR_check,
        GOR_input=inp.R_sep,
        R_cc=R_cc,
        P_sep_psia=P_sep_psia,
        T_sep_R=T_sep_R,
        T_sep_F=T_sep_F,
        units=inp.units,
    )


# ===========================================================================
# Multi-stage data structures
# ===========================================================================

@dataclass
class SeparatorStage:
    """Conditions and GOR for one separator stage."""
    R: float          # scf/STB (field) or sm³/sm³ (SI)
    P: float          # psia (field) or bara (SI)
    T: float          # °F (field) or °C (SI)
    Z: float          # dimensionless
    label: str = ""   # display label, e.g. "HP Separator"


@dataclass
class StageResult:
    """Per-stage recombination output."""
    stage_num:          int
    label:              str
    R_input:            float   # GOR in input units
    R_cc:               float   # GOR in cc/cc
    V_gas_std_cc:       float   # cc @ standard conditions
    V_gas_std_unit:     float   # scf (field) or sm³ (SI)
    V_gas_sep:          float   # cc @ this stage's separator P and T
    V_gas_recomb_cc:    float   # cc @ recombination P and T
    P_psia:             float   # internal separator pressure
    T_R:                float   # internal separator temperature (Rankine)
    T_F:                float   # separator temperature in °F (display)
    Z:                  float
    pct_of_total:       float   # % of total GOR contributed by this stage


@dataclass
class MultiStageResults:
    """Output from a multi-stage recombination calculation."""
    V_live:                float         # cc — target live fluid volume (input)
    V_oil_sep:             float         # cc — separator oil to charge
    V_oil_STO:             float         # cc — stock-tank oil equivalent
    stage_results:         list          # list[StageResult]
    total_V_gas_std_cc:    float         # cc @ std — sum over all stages
    total_V_gas_std_unit:  float         # scf or sm³ — sum over all stages
    total_V_gas_recomb_cc: float         # cc @ recombination P and T — sum over all stages
    R_total_input:         float         # total GOR in input units
    R_total_cc:            float         # total GOR in cc/cc
    GOR_check:             float         # back-calculated total GOR (input units)
    cylinder_mix_ratio:    float         # cc gas @ recomb / cc separator oil
    P_recomb_psia:         float         # recombination pressure in psia
    T_recomb_F:            float         # recombination temperature in °F
    T_recomb_R:            float         # recombination temperature in Rankine
    Z_recomb:              float
    units:                 Units


def validate_multistage(
    stages: list,
    V_live: float,
    Bo_sep: float,
    P_recomb: float,
    T_recomb: float,
    Z_recomb: float,
    units: Units,
) -> list[str]:
    """Validate multi-stage inputs. Returns list of error strings."""
    errors: list[str] = []
    if not stages:
        errors.append("At least one separator stage is required.")
    for i, s in enumerate(stages, 1):
        if s.R <= 0:
            errors.append(f"Stage {i} GOR must be > 0.")
        if s.P <= 0:
            errors.append(f"Stage {i} pressure must be > 0.")
        if s.Z <= 0 or s.Z > 2.0:
            errors.append(f"Stage {i} Z-factor must be in (0, 2.0].")
        if units == "field" and s.T < -100:
            errors.append(f"Stage {i} temperature (°F) looks unrealistically low.")
        if units == "si" and s.T < -73:
            errors.append(f"Stage {i} temperature (°C) looks unrealistically low.")
    if V_live <= 0:
        errors.append("Live fluid volume must be > 0 cc.")
    if Bo_sep <= 0 or Bo_sep > 5.0:
        errors.append("Bo_sep must be in range (0, 5.0].")
    if P_recomb <= 0:
        errors.append("Recombination pressure must be > 0.")
    if Z_recomb <= 0 or Z_recomb > 2.0:
        errors.append("Recombination Z-factor must be in (0, 2.0].")
    if units == "field" and T_recomb < -100:
        errors.append("Recombination temperature (°F) looks unrealistically low.")
    if units == "si" and T_recomb < -73:
        errors.append("Recombination temperature (°C) looks unrealistically low.")
    return errors


def calculate_multistage(
    stages: list,
    V_live: float,
    Bo_sep: float,
    P_recomb: float,
    T_recomb: float,
    Z_recomb: float,
    units: Units,
) -> MultiStageResults:
    """
    Multi-stage separator recombination with explicit recombination conditions.

    The separator oil is charged from the final (lowest-pressure) stage.
    Gas from each stage contributes a portion of the total GOR.
    The cylinder mix ratio is calculated at recombination P & T (cell charging
    conditions), which are typically different from separator conditions.

    Steps
    -----
    1. Convert recombination P, T to internal units.
    2. Compute factor_recomb = cc gas @ recomb / cc gas @ std.
    3. cylinder_mix_ratio = R_total_cc × factor_recomb / Bo_sep
       (cc gas @ recomb per cc separator oil)
    4. V_oil_sep = V_live / (1 + cylinder_mix_ratio)
       so that V_oil_sep + V_gas_recomb_total = V_live exactly.
    5. For each stage: compute gas volumes at std, separator, and recomb conditions.
    """
    # ── Convert recombination conditions ────────────────────────────────────
    if units == "field":
        P_recomb_psia = P_recomb
        T_recomb_F    = T_recomb
        T_recomb_R    = T_recomb + 459.67
    else:
        P_recomb_psia = P_recomb * BARA_TO_PSIA
        T_recomb_F    = T_recomb * 9.0 / 5.0 + 32.0
        T_recomb_R    = T_recomb_F + 459.67

    # cc gas @ recomb conditions per cc gas @ standard conditions
    factor_recomb = (P_STD_PSIA / P_recomb_psia) * (T_recomb_R / T_STD_R) * Z_recomb

    # ── First pass: accumulate total R_cc ───────────────────────────────────
    stage_raw: list[tuple] = []
    total_R_cc = 0.0
    for i, stage in enumerate(stages, 1):
        if units == "field":
            P_psia = stage.P
            T_F    = stage.T
            T_R    = T_F + 459.67
            R_cc   = stage.R * SCF_STB_TO_CC_CC
        else:
            P_psia = stage.P * BARA_TO_PSIA
            T_F    = stage.T * 9.0 / 5.0 + 32.0
            T_R    = T_F + 459.67
            R_cc   = stage.R   # sm³/sm³ == cc/cc
        total_R_cc += R_cc
        stage_raw.append((i, stage, P_psia, T_F, T_R, R_cc))

    # ── Oil volumes ──────────────────────────────────────────────────────────
    # cylinder_mix_ratio = cc gas @ recomb / cc sep oil
    cylinder_mix_ratio = total_R_cc * factor_recomb / Bo_sep
    V_oil_sep          = V_live / (1.0 + cylinder_mix_ratio)
    V_oil_STO          = V_oil_sep / Bo_sep

    # ── Per-stage gas volumes ────────────────────────────────────────────────
    stage_results: list[StageResult] = []
    for (i, stage, P_psia, T_F, T_R, R_cc) in stage_raw:
        V_gas_std_cc    = R_cc * V_oil_STO
        V_gas_std_unit  = V_gas_std_cc / SCF_TO_CC if units == "field" else V_gas_std_cc * CC_TO_SM3
        V_gas_sep       = V_gas_std_cc * (P_STD_PSIA / P_psia) * (T_R    / T_STD_R) * stage.Z
        V_gas_recomb_cc = V_gas_std_cc * factor_recomb

        stage_results.append(StageResult(
            stage_num=i,
            label=stage.label or f"Stage {i}",
            R_input=stage.R,
            R_cc=R_cc,
            V_gas_std_cc=V_gas_std_cc,
            V_gas_std_unit=V_gas_std_unit,
            V_gas_sep=V_gas_sep,
            V_gas_recomb_cc=V_gas_recomb_cc,
            P_psia=P_psia,
            T_R=T_R,
            T_F=T_F,
            Z=stage.Z,
            pct_of_total=0.0,   # filled below
        ))

    for sr in stage_results:
        sr.pct_of_total = (sr.R_cc / total_R_cc * 100.0) if total_R_cc > 0 else 0.0

    total_V_gas_std_cc    = sum(sr.V_gas_std_cc    for sr in stage_results)
    total_V_gas_std_unit  = sum(sr.V_gas_std_unit  for sr in stage_results)
    total_V_gas_recomb_cc = sum(sr.V_gas_recomb_cc for sr in stage_results)

    if units == "field":
        R_total_input = total_R_cc / SCF_STB_TO_CC_CC
        GOR_check     = (total_V_gas_std_cc / V_oil_STO) / SCF_STB_TO_CC_CC if V_oil_STO > 0 else 0.0
    else:
        R_total_input = total_R_cc
        GOR_check     = (total_V_gas_std_cc / V_oil_STO) if V_oil_STO > 0 else 0.0

    return MultiStageResults(
        V_live=V_live,
        V_oil_sep=V_oil_sep,
        V_oil_STO=V_oil_STO,
        stage_results=stage_results,
        total_V_gas_std_cc=total_V_gas_std_cc,
        total_V_gas_std_unit=total_V_gas_std_unit,
        total_V_gas_recomb_cc=total_V_gas_recomb_cc,
        R_total_input=R_total_input,
        R_total_cc=total_R_cc,
        GOR_check=GOR_check,
        cylinder_mix_ratio=cylinder_mix_ratio,
        P_recomb_psia=P_recomb_psia,
        T_recomb_F=T_recomb_F,
        T_recomb_R=T_recomb_R,
        Z_recomb=Z_recomb,
        units=units,
    )


# ===========================================================================
# Bubble Point Pressure — Standing (1947) correlation
# ===========================================================================

def standing_bubble_point(
    R_scf_stb: float,
    gamma_g: float,
    T_F: float,
    API: float,
) -> float:
    """
    Standing (1947) empirical bubble point pressure correlation.

        Pb = 18.2 × [(R / γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]

    Parameters
    ----------
    R_scf_stb : total solution GOR in scf/STB
    gamma_g   : gas specific gravity (air = 1.0)
    T_F       : reservoir temperature in °F
    API       : stock-tank oil API gravity

    Returns
    -------
    Pb in psia  (always ≥ 0; returns 0 if inputs are non-physical)

    Accuracy: ±10–15 % for typical crude oils.
    Originally derived from California crude data (Standing, 1947).
    """
    if gamma_g <= 0 or R_scf_stb <= 0:
        return 0.0
    x  = 0.00091 * T_F - 0.0125 * API
    Pb = 18.2 * ((R_scf_stb / gamma_g) ** 0.83 * 10.0 ** x - 1.4)
    return max(Pb, 0.0)
