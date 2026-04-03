"""
pvt/recombination/calc.py — Core calculation logic for separator recombination.

All inputs and outputs are in the units stated in the model docstrings.
No UI or I/O logic here.

Two oil-source cases are supported:
  Case 1 — "separator": oil charged from the separator (Bo_sep corrects to STO).
  Case 2 — "stock_tank": oil charged directly from the stock tank (STO, fully
            degassed). The stock tank GOR (R_STO) is added to the separator GOR
            to account for gas that flashed from the separator oil on its way to
            the stock tank.  All gas (separator + STO flash) is assumed to come
            from the separator gas cylinder (the common lab simplification).

For both cases the technician charges oil at a lower "oil charging pressure"
(P_charge_oil) and room temperature, then pumps gas in to reach P_recomb.
Oil is slightly compressible, so the charging volume at P_charge differs
from the volume the oil occupies at P_recomb.  The correction uses the
isothermal oil compressibility c_o (default 10 × 10⁻⁶ psi⁻¹):

    V_oil_charge = V_oil_at_recomb × [1 + c_o × (P_recomb − P_charge)]

Because P_charge < P_recomb the oil is at lower pressure when charged and
therefore occupies a slightly LARGER volume than it will at final conditions.
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
    stages:       list[SeparatorStage],
    V_live:       float,
    Bo_sep:       float,
    P_recomb:     float,
    T_recomb:     float,
    Z_recomb:     float,
    units:        str,
    oil_source:   str   = "separator",  # "separator" | "stock_tank"
    R_STO:        float = 0.0,          # stock tank GOR (input units); Case 2 only
    P_charge_oil: float = 2014.7,       # absolute oil charging pressure (same units as P_recomb)
    c_o:          float = 10.0e-6,      # oil isothermal compressibility (psi⁻¹)
) -> MultiStageResults:
    """
    Multi-stage separator recombination with explicit recombination conditions.

    Case 1 — oil_source="separator"
    --------------------------------
    The separator oil is charged from the final (lowest-pressure) stage.
    Gas from each stage contributes its portion of the total GOR.
    Bo_sep converts separator oil volume to STO equivalent.

    Case 2 — oil_source="stock_tank"
    ---------------------------------
    Stock tank oil (STO, fully degassed) is the oil source.  Bo_sep is set to
    1.0 internally (the STO is the volume reference; no FVF correction needed).
    R_STO is the gas/oil ratio of gas that flashed from the separator oil as it
    travelled from the last separator to the stock tank.  All gas (separator
    stages + STO flash) is treated as coming from the separator gas cylinder
    (the standard lab simplification).

    Charging pressure correction (both cases)
    ------------------------------------------
    The technician fills the cell with oil at P_charge_oil (lower pressure) and
    room temperature.  At this lower pressure the oil is slightly less
    compressed than at P_recomb, so the charging volume is:

        V_oil_charge = V_oil_sep × [1 + c_o × (P_recomb − P_charge)]

    This is slightly LARGER than V_oil_sep when P_charge < P_recomb.

    Steps
    -----
    1. Convert recombination and charging P, T to internal units.
    2. factor_recomb = cc gas @ recomb per cc gas @ std.
    3. Total effective R_cc = Σ(sep stage R_cc) + R_STO_cc [Case 2 adds STO term].
    4. cylinder_mix_ratio = R_total_eff_cc × factor_recomb / Bo_sep_eff.
    5. V_oil_sep = V_live / (1 + cylinder_mix_ratio)
       → guarantees V_oil_sep + V_gas_recomb_total = V_live exactly.
    6. V_oil_charge = V_oil_sep × (1 + c_o × ΔP).
    7. Per-stage: compute gas volumes at std, separator, and recomb conditions.
    8. STO flash gas volumes [Case 2]: computed at last-stage separator conditions.
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

    # ── Oil charging pressure → psia ─────────────────────────────────────────
    if units == "field":
        P_charge_psia = P_charge_oil
    else:
        P_charge_psia = P_charge_oil * BARA_TO_PSIA

    # ── Stock tank GOR (Case 2) → cc/cc ──────────────────────────────────────
    if oil_source == "stock_tank":
        R_STO_cc = R_STO * SCF_STB_TO_CC_CC if units == "field" else R_STO
    else:
        R_STO_cc = 0.0
        R_STO    = 0.0

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
            R_cc   = stage.R   # sm³/sm³ == cc/cc

        total_R_cc += R_cc
        stage_raw.append((i, stage, P_psia, T_F, T_R, R_cc))

    # ── Effective total R (separator stages + STO flash for Case 2) ───────────
    total_R_cc_eff = total_R_cc + R_STO_cc

    # ── Bo correction ─────────────────────────────────────────────────────────
    # Case 1: Bo_sep converts separator oil volume → STO equivalent.
    # Case 2: STO is already the volume reference; no FVF correction needed.
    Bo_sep_eff = Bo_sep if oil_source == "separator" else 1.0

    # ── Oil volumes (live-fluid-volume driven) ────────────────────────────────
    cylinder_mix_ratio = total_R_cc_eff * factor_recomb / Bo_sep_eff
    V_oil_sep          = V_live / (1.0 + cylinder_mix_ratio)
    V_oil_STO          = V_oil_sep / Bo_sep_eff

    # ── Oil charging volume (compressibility correction) ──────────────────────
    # At P_charge < P_recomb the oil is at lower pressure and occupies a
    # slightly LARGER volume.  This is what the technician actually measures.
    delta_P      = P_recomb_psia - P_charge_psia
    V_oil_charge = V_oil_sep * (1.0 + c_o * delta_P)

    # ── Shrinkage factor (Case 2 informational) ───────────────────────────────
    # Defined per user convention: R_sep_total × SF = R_STO  →  SF = R_STO / R_sep
    shrinkage_factor = (
        R_STO_cc / total_R_cc
        if (oil_source == "stock_tank" and total_R_cc > 0)
        else 0.0
    )

    # ── Per-stage separator gas volumes ───────────────────────────────────────
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

    # pct_of_total uses effective total (including STO flash) as denominator
    for sr in stage_results:
        sr.pct_of_total = (
            sr.R_cc / total_R_cc_eff * 100.0
            if total_R_cc_eff > 0 else 0.0
        )

    total_V_gas_std_cc    = sum(sr.V_gas_std_cc    for sr in stage_results)
    total_V_gas_std_unit  = sum(sr.V_gas_std_unit  for sr in stage_results)
    total_V_gas_recomb_cc = sum(sr.V_gas_recomb_cc for sr in stage_results)

    # ── STO flash gas volumes (Case 2 only) ───────────────────────────────────
    # Treated as separator gas for cylinder volume calculations (lab convention).
    # Computed at last separator stage conditions (closest to stock tank P, T).
    if oil_source == "stock_tank" and R_STO_cc > 0:
        last_i, last_stage, last_P_psia, last_T_F, last_T_R, _ = stage_raw[-1]
        V_STO_gas_std_cc    = R_STO_cc * V_oil_STO
        V_STO_gas_std_unit  = (
            V_STO_gas_std_cc / SCF_TO_CC if units == "field"
            else V_STO_gas_std_cc * CC_TO_SM3
        )
        V_STO_gas_recomb_cc = V_STO_gas_std_cc * factor_recomb

        # Add STO flash gas to the running totals (all goes into the cell)
        total_V_gas_std_cc    += V_STO_gas_std_cc
        total_V_gas_std_unit  += V_STO_gas_std_unit
        total_V_gas_recomb_cc += V_STO_gas_recomb_cc
    else:
        V_STO_gas_std_cc    = 0.0
        V_STO_gas_std_unit  = 0.0
        V_STO_gas_recomb_cc = 0.0

    # ── GOR summary ───────────────────────────────────────────────────────────
    # R_total_input / R_total_cc reflect separator stages only.
    # GOR_check back-calculates from ALL gas in the cell (sep + STO flash).
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
        oil_source=oil_source,
        P_charge_oil_psia=P_charge_psia,
        V_oil_charge=V_oil_charge,
        c_o=c_o,
        R_STO_input=R_STO,
        R_STO_cc=R_STO_cc,
        shrinkage_factor=shrinkage_factor,
        V_STO_gas_std_cc=V_STO_gas_std_cc,
        V_STO_gas_std_unit=V_STO_gas_std_unit,
        V_STO_gas_recomb_cc=V_STO_gas_recomb_cc,
        units=units,
    )
