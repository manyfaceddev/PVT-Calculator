"""
pvt/recombination/calc.py — Core calculation logic for separator recombination.

All inputs and outputs are in the units stated in the model docstrings.
No UI or I/O logic here.

Nomenclature follows Carlsen & Whitson (IPTC-19775, 2020) and the Whitson manual.
See models.py for full definitions of SF and FF.

Two oil-source cases are supported:
  Case 1 — "separator": oil is charged from the separator stage.
            SF (Shrinkage Factor) converts separator oil volume → STO equivalent.

  Case 2 — "stock_tank": stock-tank oil (STO, fully degassed) is charged.
            FF (Flash Factor) accounts for gas that flashed from the separator
            oil on its way to the stock tank.  All gas (separator stages + flash)
            comes from the separator gas cylinder (standard lab simplification).

Total producing GOR (Carlsen & Whitson eq.):
    Rp = Rp,sep / SF + FF

where:
  Rp,sep — GOR at separator in scf per STB separator oil (metered)
  SF     — Separator-Oil Shrinkage Factor = V_STO / V_sep_oil
  FF     — Flash Factor = scf flash gas per STB STO (solution GOR of sep oil)
  Rp     — total producing GOR in scf per STB STO

In this code the per-stage GOR input (SeparatorStage.R) is already in scf/STB STO
(i.e. Rp,sep / SF — the shrinkage-corrected value).  FF is supplied separately
as the additional stock-tank flash (Case 2 only).  The total producing GOR is:
    Rp_cc = sum(R_stage_cc) + FF_cc   [all per cc STO]

No oil isothermal compressibility (c_o) is required.  The recombination volumes
are determined entirely from the GOR and recombination conditions:
    factor = (P_std / P_recomb) × (T_recomb_R / T_std_R) × Z_recomb
    V_oil_STO = V_live / (1 + Rp_cc × factor)
    V_gas_recomb = V_live − V_oil_STO
"""

from pvt.constants import (
    P_STD_PSIA, T_STD_R,
    SCF_TO_CC, CC_TO_SM3, SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
)
import math
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
    stages:     list[SeparatorStage],
    V_live:     float,
    SF:         float,          # Separator-Oil Shrinkage Factor = V_STO/V_sep_oil (0 < SF ≤ 1)
    P_recomb:   float,
    T_recomb:   float,
    Z_recomb:   float,
    units:      str,
    oil_source: str   = "separator",  # "separator" | "stock_tank"
    FF:         float = 0.0,          # Flash Factor (scf/STB STO or sm³/sm³); Case 2 only
    p_charge:   float = 14.7,         # Oil charging pressure (psia or bara)
    c_o:        float = 0.0,          # Oil compressibility (1/psia or 1/bara)
) -> MultiStageResults:
    """
    Multi-stage separator recombination with explicit recombination conditions.

    Uses the Carlsen & Whitson (2020) framework:
        Rp = sum(R_stage) + FF        [Rp = total producing GOR per STB STO]

    Case 1 — oil_source="separator"
    --------------------------------
    Separator oil is charged.  SF converts V_sep_oil → V_STO for the gas
    volume calculation.  No flash gas (FF = 0).

    Case 2 — oil_source="stock_tank"
    ---------------------------------
    Stock-tank oil (STO, fully degassed) is charged.  FF is the flash factor —
    gas that came out of solution between the last separator and the stock tank.
    All gas (separator stages + flash) is loaded from the separator gas cylinder.

    Steps
    -----
    1. Convert recombination P, T to internal units.
    2. factor_recomb = (P_std/P_recomb) × (T_recomb_R/T_std_R) × Z  [cc gas recomb / cc gas std]
    3. Rp_cc = sum(R_stage_cc) + FF_cc        [total GOR, cc/cc per STO]
    4. cylinder_mix_ratio = Rp_cc × factor_recomb / (1/SF)  [Case 1] or × 1  [Case 2]
       Equivalently: mix_ratio = Rp_cc × factor_recomb × Bo_sep_eff
       where Bo_sep_eff = 1/SF for Case 1, 1.0 for Case 2.
    5. V_oil_STO = V_live / (1 + cylinder_mix_ratio)  — guarantees exact volume balance.
    6. V_oil_sep = V_oil_STO / SF  [Case 1, volume at recomb P]
       V_oil_sep = V_oil_STO       [Case 2, STO at recomb P]
    7. V_oil_charge = V_oil_sep × exp(c_o × (p_charge - P_recomb))  [volume at charge P]
    8. Per-stage: gas volumes at std, separator, and recombination conditions.
    9. Flash gas volumes [Case 2]: all attributed to separator gas cylinder.
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

    # factor_recomb: cc gas @ recomb per cc gas @ standard conditions
    factor_recomb = (P_STD_PSIA / P_recomb_psia) * (T_recomb_R / T_STD_R) * Z_recomb

    # ── Charging pressure and compressibility → internal units ──────────────
    p_charge_psia = p_charge if units == "field" else p_charge * BARA_TO_PSIA
    c_o_psia      = c_o      if units == "field" else c_o / BARA_TO_PSIA

    # ── Flash Factor (Case 2) → cc/cc ────────────────────────────────────────
    if oil_source == "stock_tank":
        FF_cc = FF * SCF_STB_TO_CC_CC if units == "field" else FF
    else:
        FF_cc = 0.0
        FF    = 0.0

    # ── First pass: per-stage unit conversions + total separator R_cc ────────
    stage_raw: list[tuple] = []   # (i, stage, P_psia, T_F, T_R, R_cc)
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
            R_cc   = stage.R   # sm³/sm³ ≡ cc/cc

        total_R_cc += R_cc
        stage_raw.append((i, stage, P_psia, T_F, T_R, R_cc))

    # ── Total producing GOR: Rp = sum(R_stage) + FF  [per STO] ───────────────
    Rp_total_cc = total_R_cc + FF_cc

    # ── Oil volume conversion factor ──────────────────────────────────────────
    # Case 1: gas volumes are referenced to STO, but we charge sep oil.
    #         V_sep_oil = V_STO / SF  →  mix_ratio uses Bo_sep_eff = 1/SF
    # Case 2: we charge STO directly; Bo_sep_eff = 1.0.
    Bo_sep_eff = (1.0 / SF) if oil_source == "separator" else 1.0

    # ── Oil volumes (live-fluid-volume driven) ────────────────────────────────
    # cylinder_mix_ratio = cc gas @ recomb per cc oil charged into the cell.
    # For Case 1: oil charged = V_oil_sep = V_oil_STO × Bo_sep_eff
    cylinder_mix_ratio = Rp_total_cc * factor_recomb / Bo_sep_eff
    V_oil_sep          = V_live / (1.0 + cylinder_mix_ratio)
    V_oil_STO          = V_oil_sep * SF if oil_source == "separator" else V_oil_sep

    # ── Oil volume at charging pressure ───────────────────────────────────────
    V_oil_charge = V_oil_sep * math.exp(c_o_psia * (p_charge_psia - P_recomb_psia))

    # ── Per-stage separator gas volumes ───────────────────────────────────────
    stage_results: list[StageResult] = []

    for (i, stage, P_psia, T_F, T_R, R_cc) in stage_raw:
        V_gas_std_cc    = R_cc * V_oil_STO
        V_gas_std_unit  = (
            V_gas_std_cc / SCF_TO_CC if units == "field"
            else V_gas_std_cc * CC_TO_SM3
        )
        V_gas_sep       = V_gas_std_cc * (P_STD_PSIA / P_psia) * (T_R / T_STD_R) * stage.Z
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

    # pct_of_total uses Rp (including FF) as denominator
    for sr in stage_results:
        sr.pct_of_total = (
            sr.R_cc / Rp_total_cc * 100.0
            if Rp_total_cc > 0 else 0.0
        )

    total_V_gas_std_cc    = sum(sr.V_gas_std_cc    for sr in stage_results)
    total_V_gas_std_unit  = sum(sr.V_gas_std_unit  for sr in stage_results)
    total_V_gas_recomb_cc = sum(sr.V_gas_recomb_cc for sr in stage_results)

    # ── Flash gas volumes (Case 2 only) ───────────────────────────────────────
    # All flash gas is loaded from the separator cylinder (standard lab practice).
    if oil_source == "stock_tank" and FF_cc > 0:
        V_FF_gas_std_cc    = FF_cc * V_oil_STO
        V_FF_gas_std_unit  = (
            V_FF_gas_std_cc / SCF_TO_CC if units == "field"
            else V_FF_gas_std_cc * CC_TO_SM3
        )
        V_FF_gas_recomb_cc = V_FF_gas_std_cc * factor_recomb

        total_V_gas_std_cc    += V_FF_gas_std_cc
        total_V_gas_std_unit  += V_FF_gas_std_unit
        total_V_gas_recomb_cc += V_FF_gas_recomb_cc
    else:
        V_FF_gas_std_cc    = 0.0
        V_FF_gas_std_unit  = 0.0
        V_FF_gas_recomb_cc = 0.0

    # ── GOR summary ───────────────────────────────────────────────────────────
    # R_total_input / R_total_cc: separator stages only.
    # GOR_check: back-calculates Rp from all gas in the cell (sep + flash).
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
        V_oil_charge=V_oil_charge,
        V_oil_STO=V_oil_STO,
        stage_results=stage_results,
        total_V_gas_std_cc=total_V_gas_std_cc,
        total_V_gas_std_unit=total_V_gas_std_unit,
        total_V_gas_recomb_cc=total_V_gas_recomb_cc,
        R_total_input=R_total_input,
        R_total_cc=total_R_cc,
        Rp_total_cc=Rp_total_cc,
        GOR_check=GOR_check,
        cylinder_mix_ratio=cylinder_mix_ratio,
        P_recomb_psia=P_recomb_psia,
        T_recomb_F=T_recomb_F,
        T_recomb_R=T_recomb_R,
        Z_recomb=Z_recomb,
        factor_recomb=factor_recomb,
        oil_source=oil_source,
        SF=SF,
        FF_input=FF,
        FF_cc=FF_cc,
        V_FF_gas_std_cc=V_FF_gas_std_cc,
        V_FF_gas_std_unit=V_FF_gas_std_unit,
        V_FF_gas_recomb_cc=V_FF_gas_recomb_cc,
        units=units,
    )
