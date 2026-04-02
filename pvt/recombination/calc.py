"""
pvt/recombination/calc.py — Core calculation logic for separator recombination.

All inputs and outputs are in the units stated in the model docstrings.
No UI or I/O logic here.
"""

from pvt.constants import (
    P_STD_PSIA, T_STD_R,
    SCF_TO_CC, CC_TO_SM3, SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
)
from pvt.recombination.models import (
    RecombinationInputs, RecombinationResults,
    SeparatorStage, StageResult, MultiStageResults,
)


# ===========================================================================
# Single-stage  (simple / legacy)
# ===========================================================================

def calculate(inp: RecombinationInputs) -> RecombinationResults:
    """
    Single-stage separator recombination.

    Uses cell volume + oil fraction to determine charge volumes.
    For the preferred workflow (live-fluid-volume driven), use
    calculate_multistage with n=1 stage instead.
    """
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
# Multi-stage  (primary API)
# ===========================================================================

def calculate_multistage(
    stages:   list[SeparatorStage],
    V_live:   float,
    Bo_sep:   float,
    P_recomb: float,
    T_recomb: float,
    Z_recomb: float,
    units:    str,
) -> MultiStageResults:
    """
    Multi-stage separator recombination with explicit recombination conditions.

    The separator oil is charged from the final (lowest-pressure) stage.
    Gas from each stage contributes its portion of the total GOR.
    The cylinder mix ratio is calculated at recombination P & T — the actual
    cell-charging conditions, which differ from separator conditions.

    Steps
    -----
    1. Convert recombination P, T to internal units.
    2. factor_recomb = cc gas @ recomb per cc gas @ std.
    3. cylinder_mix_ratio = R_total_cc × factor_recomb / Bo_sep
    4. V_oil_sep = V_live / (1 + cylinder_mix_ratio)
       → guarantees V_oil_sep + V_gas_recomb_total = V_live exactly.
    5. Per stage: compute gas volumes at std, separator, and recomb conditions.
    """
    # ── Recombination conditions → internal units ────────────────────────────
    if units == "field":
        P_recomb_psia = P_recomb
        T_recomb_F    = T_recomb
        T_recomb_R    = T_recomb + 459.67
    else:
        P_recomb_psia = P_recomb * BARA_TO_PSIA
        T_recomb_F    = T_recomb * 9.0 / 5.0 + 32.0
        T_recomb_R    = T_recomb_F + 459.67

    # cc gas @ recomb per cc gas @ standard conditions
    factor_recomb = (P_STD_PSIA / P_recomb_psia) * (T_recomb_R / T_STD_R) * Z_recomb

    # ── First pass: per-stage unit conversions + total R_cc ─────────────────
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

    # ── Oil volumes (live-fluid-volume driven) ───────────────────────────────
    cylinder_mix_ratio = total_R_cc * factor_recomb / Bo_sep
    V_oil_sep          = V_live / (1.0 + cylinder_mix_ratio)
    V_oil_STO          = V_oil_sep / Bo_sep

    # ── Per-stage gas volumes ────────────────────────────────────────────────
    stage_results: list[StageResult] = []

    for (i, stage, P_psia, T_F, T_R, R_cc) in stage_raw:
        V_gas_std_cc    = R_cc * V_oil_STO
        V_gas_std_unit  = (
            V_gas_std_cc / SCF_TO_CC if units == "field"
            else V_gas_std_cc * CC_TO_SM3
        )
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
        GOR_check     = (
            (total_V_gas_std_cc / V_oil_STO) / SCF_STB_TO_CC_CC
            if V_oil_STO > 0 else 0.0
        )
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
