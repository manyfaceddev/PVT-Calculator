"""
pvt/recombination/models.py — Input / output data models for separator
recombination calculations.  Pure dataclasses; no calculation logic.

Nomenclature follows Carlsen & Whitson (IPTC-19775, 2020) and the Whitson manual:

  SF   — Separator-Oil Shrinkage Factor = V_STO / V_sep_oil  (range 0.65–0.99)
           Equivalent to 1/Bo_sep where Bo_sep = oil FVF at separator conditions.

  FF   — Separator-Oil Flash Factor = scf flash gas liberated per STB_STO
           (gas that comes out of solution when separator oil is brought to
           stock-tank / standard conditions). This is the solution GOR of the
           separator oil (Rs_sep), expressed per STB STO.

  Rp,sep — Measured separator GOR in scf per STB separator oil (metered).
           In our convention the per-stage GOR input (SeparatorStage.R) is in
           scf/STB where the STB denominator is stock-tank oil (STO), i.e.
           R = Rp,sep / SF (already shrinkage-corrected). See calc.py for details.

  Rp   — Total producing GOR at stock-tank conditions:
           Rp = sum(R_stage) + FF        [both terms per STB STO]
         In Whitson notation with raw measured GOR per sep barrel:
           Rp = Rp,sep / SF + FF         [Carlsen & Whitson eq.]
"""

from dataclasses import dataclass
from pvt.constants import Units


# ===========================================================================
# Multi-stage models  (primary API)
# ===========================================================================

@dataclass
class SeparatorStage:
    """Conditions and GOR for one separator stage.

    R is the stage GOR in the input unit system:
      - field: scf/STB  (STB = stock-tank barrel, i.e. STO-referenced)
      - SI:    sm³/sm³  (both volumes at standard conditions)
    """
    R:     float        # scf/STB STO (field) or sm³/sm³ (SI)
    P:     float        # psia (field) or bara (SI)
    T:     float        # °F (field) or °C (SI)
    Z:     float        # gas compressibility factor (dimensionless)
    label: str = ""     # display label, e.g. "HP Separator"


@dataclass
class StageResult:
    """Per-stage output from a recombination calculation."""
    stage_num:          int
    label:              str
    R_input:            float   # GOR in input units (scf/STB STO or sm³/sm³)
    R_cc:               float   # GOR in cc gas_std / cc STO
    V_gas_std_cc:       float   # cc @ standard conditions
    V_gas_std_unit:     float   # scf (field) or sm³ (SI) @ standard conditions
    V_gas_sep:          float   # cc @ separator P and T
    V_gas_recomb_cc:    float   # cc @ recombination P and T
    P_psia:             float   # separator pressure in psia (internal)
    T_R:                float   # separator temperature in Rankine (internal)
    T_F:                float   # separator temperature in °F (display)
    Z:                  float
    pct_of_total:       float   # % of total producing GOR (Rp) from this stage


@dataclass
class MultiStageResults:
    """Full output from a multi-stage separator recombination calculation.

    Key industry-standard quantities:
      SF              — Separator-Oil Shrinkage Factor (V_STO / V_sep_oil)
      FF_input/FF_cc  — Flash Factor (gas liberated per STB STO, i.e. Rs_sep)
      Rp_total_cc     — Total producing GOR at STO basis (cc gas_std / cc STO)
    """
    # ── Inputs echoed back ───────────────────────────────────────────────────
    V_live:                float   # cc — target live fluid volume
    # ── Oil volumes ──────────────────────────────────────────────────────────
    V_oil_sep:             float   # cc — oil volume at recombination pressure
    V_oil_charge:          float   # cc — oil volume at charging pressure
    V_oil_STO:             float   # cc — stock-tank oil equivalent
    # ── Gas volumes (separator stages + flash) ───────────────────────────────
    stage_results:         list    # list[StageResult]
    total_V_gas_std_cc:    float   # cc @ std — all gas (sep stages + flash)
    total_V_gas_std_unit:  float   # scf or sm³ — all gas
    total_V_gas_recomb_cc: float   # cc @ recombination P & T — all gas
    # ── GOR summary ──────────────────────────────────────────────────────────
    R_total_input:         float   # sum of separator-stage GOR in input units (per STO)
    R_total_cc:            float   # sum of separator-stage GOR in cc/cc (per STO)
    Rp_total_cc:           float   # total producing GOR = R_total_cc + FF_cc (cc/cc, per STO)
    GOR_check:             float   # back-calculated total GOR (input units) — for verification
    # ── Cylinder mix ratio ───────────────────────────────────────────────────
    cylinder_mix_ratio:    float   # cc gas @ recomb P&T per cc oil at recomb P
    # ── Recombination conditions ─────────────────────────────────────────────
    P_recomb_psia:         float
    T_recomb_F:            float
    T_recomb_R:            float
    Z_recomb:              float
    factor_recomb:         float   # (P_std/P_recomb)·(T_recomb_R/T_std_R)·Z — cc gas recomb / cc gas std
    # ── Oil source & shrinkage ────────────────────────────────────────────────
    oil_source:            str     # "separator" | "stock_tank"
    SF:                    float   # Separator-Oil Shrinkage Factor = V_STO/V_sep_oil = 1/Bo_sep
    # ── Flash Factor / Stock-tank gas (Case 2 only; 0.0 for Case 1) ─────────
    FF_input:              float   # Flash Factor in input units (scf/STB STO or sm³/sm³)
    FF_cc:                 float   # Flash Factor in cc gas_std / cc STO
    V_FF_gas_std_cc:       float   # flash gas volume @ std conditions (cc)
    V_FF_gas_std_unit:     float   # flash gas volume @ std (scf or sm³)
    V_FF_gas_recomb_cc:    float   # flash gas volume @ recomb P&T (cc)
    # ── Metadata ─────────────────────────────────────────────────────────────
    units:                 Units


# ===========================================================================
# Single-stage models  (legacy / simple API)
# ===========================================================================

@dataclass
class RecombinationInputs:
    """All inputs for a single-stage separator recombination."""
    V_cell:       float           # cc — recombination cell volume
    R_sep:        float           # scf/STB (field) or sm³/sm³ (SI) — separator GOR
    P_sep:        float           # psia (field) or bara (SI)
    T_sep:        float           # °F (field) or °C (SI)
    Z_sep:        float           # Z-factor at separator conditions
    Bo_sep:       float = 1.0     # oil FVF at separator conditions
    oil_fraction: float = 0.70    # fraction of cell volume to fill with separator oil
    units:        Units = "field"


@dataclass
class RecombinationResults:
    """All outputs from a single-stage separator recombination."""
    V_oil_sep:       float   # cc — separator oil to charge
    V_oil_STO:       float   # cc — equivalent stock-tank oil volume
    V_gas_std_cc:    float   # cc  @ standard conditions
    V_gas_std_unit:  float   # scf (field) or sm³ (SI) @ standard conditions
    V_gas_sep:       float   # cc  @ separator conditions
    GOR_check:       float   # back-calculated GOR (input units)
    GOR_input:       float   # original input GOR (for comparison)
    R_cc:            float   # cc/cc — GOR in volumetric-ratio form
    P_sep_psia:      float   # separator pressure in psia (internal)
    T_sep_R:         float   # separator temperature in Rankine (internal)
    T_sep_F:         float   # separator temperature in °F (display)
    units:           Units
