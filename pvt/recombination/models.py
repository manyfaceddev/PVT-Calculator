"""
pvt/recombination/models.py — Input / output data models for separator
recombination calculations.  Pure dataclasses; no calculation logic.
"""

from dataclasses import dataclass
from pvt.constants import Units


# ===========================================================================
# Multi-stage models  (primary API)
# ===========================================================================

@dataclass
class SeparatorStage:
    """Conditions and GOR for one separator stage."""
    R:     float        # scf/STB (field) or sm³/sm³ (SI)
    P:     float        # psia (field) or bara (SI)
    T:     float        # °F (field) or °C (SI)
    Z:     float        # gas compressibility factor (dimensionless)
    label: str = ""     # display label, e.g. "HP Separator"


@dataclass
class StageResult:
    """Per-stage output from a recombination calculation."""
    stage_num:          int
    label:              str
    R_input:            float   # GOR in input units
    R_cc:               float   # GOR in cc/cc
    V_gas_std_cc:       float   # cc @ standard conditions
    V_gas_std_unit:     float   # scf (field) or sm³ (SI) @ standard conditions
    V_gas_sep:          float   # cc @ separator P and T
    V_gas_recomb_cc:    float   # cc @ recombination P and T
    P_psia:             float   # separator pressure in psia (internal)
    T_R:                float   # separator temperature in Rankine (internal)
    T_F:                float   # separator temperature in °F (display)
    Z:                  float
    pct_of_total:       float   # % of total solution GOR (including STO) from this stage


@dataclass
class MultiStageResults:
    """Full output from a multi-stage separator recombination calculation."""
    # ── Inputs echoed back ───────────────────────────────────────────────────
    V_live:                float   # cc — target live fluid volume
    # ── Oil volumes ──────────────────────────────────────────────────────────
    V_oil_sep:             float   # cc — oil to charge at recomb P (sep oil for Case 1, STO for Case 2)
    V_oil_STO:             float   # cc — stock-tank oil equivalent
    # ── Gas volumes (separator stages) ───────────────────────────────────────
    stage_results:         list    # list[StageResult]
    total_V_gas_std_cc:    float   # cc @ std — all gas (sep stages + STO flash)
    total_V_gas_std_unit:  float   # scf or sm³ — all gas
    total_V_gas_recomb_cc: float   # cc @ recombination P & T — all gas
    # ── GOR summary ──────────────────────────────────────────────────────────
    R_total_input:         float   # total separator-stage GOR in input units
    R_total_cc:            float   # total separator-stage GOR in cc/cc
    GOR_check:             float   # back-calculated GOR (input units) — for verification
    # ── Cylinder mix ratio ───────────────────────────────────────────────────
    cylinder_mix_ratio:    float   # cc gas @ recomb P&T per cc oil
    # ── Recombination conditions ─────────────────────────────────────────────
    P_recomb_psia:         float
    T_recomb_F:            float
    T_recomb_R:            float
    Z_recomb:              float
    # ── Oil source & charging conditions ─────────────────────────────────────
    oil_source:            str     # "separator" | "stock_tank"
    P_charge_oil_psia:     float   # oil charging pressure (psia)
    V_oil_charge:          float   # oil volume at charging conditions (cc) — what the tech measures
    c_o:                   float   # oil compressibility used (psi^-1)
    # ── Stock tank flash (Case 2 only; 0.0 for Case 1) ───────────────────────
    R_STO_input:           float   # stock tank GOR in input units
    R_STO_cc:              float   # stock tank GOR in cc/cc
    shrinkage_factor:      float   # R_STO_cc / R_sep_total_cc (per user convention: R_sep × SF = R_STO)
    V_STO_gas_std_cc:      float   # STO flash gas @ std conditions (cc)
    V_STO_gas_std_unit:    float   # STO flash gas @ std (scf or sm³)
    V_STO_gas_recomb_cc:   float   # STO flash gas @ recomb P&T (cc)
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
