"""
pvt_calc.py — Core calculation functions for PVT separator recombination.
No UI logic. All inputs/outputs in stated units.
"""

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
P_STD_PSIA = 14.696          # psia
T_STD_F    = 60.0            # °F
T_STD_R    = T_STD_F + 459.67  # Rankine

# Conversion: scf/STB → cc/cc
SCF_TO_CC  = 28_316.85       # 1 scf = 28316.85 cc
STB_TO_CC  = 158_987.1       # 1 STB = 158987.1 cc
SCF_STB_TO_CC_CC = SCF_TO_CC / STB_TO_CC   # ≈ 0.178107

# SI pressure conversions
BARA_TO_PSIA = 14.5038       # 1 bara = 14.5038 psia
CC_TO_SM3 = 1e-6             # 1 sm³ = 1,000,000 cc


Units = Literal["field", "si"]


@dataclass
class RecombinationInputs:
    """All inputs for a separator recombination calculation."""
    V_cell: float          # cc — recombination cell volume
    R_sep: float           # scf/STB (field) or sm³/sm³ (SI) — separator GOR
    P_sep: float           # psia (field) or bara (SI) — separator pressure
    T_sep: float           # °F (field) or °C (SI) — separator temperature
    Z_sep: float           # dimensionless — Z-factor at separator conditions
    Bo_sep: float = 1.0    # dimensionless — oil FVF at separator conditions
    oil_fraction: float = 0.70  # fraction of cell to fill with separator oil
    units: Units = "field"


@dataclass
class RecombinationResults:
    """All outputs from a separator recombination calculation."""
    # --- primary charges ---
    V_oil_sep: float       # cc — separator oil to charge
    V_oil_STO: float       # cc — equivalent stock-tank oil volume
    V_gas_std_cc: float    # cc  @ standard conditions
    V_gas_std_unit: float  # scf (field) or sm³ (SI) @ standard conditions
    V_gas_sep: float       # cc  @ separator conditions

    # --- verification ---
    GOR_check: float       # back-calculated GOR in original input units
    GOR_input: float       # original input GOR for comparison

    # --- intermediate (for step-by-step display) ---
    R_cc: float            # cc/cc — GOR in volumetric-ratio form
    P_sep_psia: float      # separator pressure in psia (internal)
    T_sep_R: float         # separator temperature in Rankine (internal)
    T_sep_F: float         # separator temperature in °F (for display)
    units: Units


def validate(inp: RecombinationInputs) -> list[str]:
    """Return list of error messages; empty list means OK."""
    errors: list[str] = []
    if inp.V_cell <= 0:
        errors.append("Cell volume must be > 0 cc.")
    if inp.R_sep <= 0:
        errors.append("GOR must be > 0.")
    if inp.P_sep <= 0:
        errors.append("Separator pressure must be > 0.")
    if inp.units == "si" and inp.P_sep <= 0:
        errors.append("Separator pressure (bara) must be > 0.")
    if inp.Z_sep <= 0 or inp.Z_sep > 2.0:
        errors.append("Z-factor must be in range (0, 2.0].")
    if inp.Bo_sep <= 0 or inp.Bo_sep > 5.0:
        errors.append("Bo_sep must be in range (0, 5.0].")
    if not (0.0 < inp.oil_fraction < 1.0):
        errors.append("Oil fraction must be between 0 and 1 (exclusive).")
    # Temperature sanity in absolute units
    if inp.units == "field" and inp.T_sep < -100:
        errors.append("Separator temperature (°F) looks unrealistically low.")
    if inp.units == "si" and inp.T_sep < -73:
        errors.append("Separator temperature (°C) looks unrealistically low.")
    return errors


def calculate(inp: RecombinationInputs) -> RecombinationResults:
    """
    Perform separator recombination calculation.

    Steps
    -----
    1. Convert inputs to internal SI-ish units where needed (psia, Rankine, cc).
    2. Compute cell oil & gas volumes.
    3. Convert gas volume to standard conditions, then back to separator conditions.
    4. Back-calculate GOR as a verification check.
    """
    # ------------------------------------------------------------------
    # 1. Unit conversions → internal (psia, Rankine)
    # ------------------------------------------------------------------
    if inp.units == "field":
        P_sep_psia = inp.P_sep
        T_sep_R    = inp.T_sep + 459.67      # °F → Rankine
        T_sep_F    = inp.T_sep
        # GOR: scf/STB → cc/cc
        R_cc = inp.R_sep * SCF_STB_TO_CC_CC
    else:  # SI
        P_sep_psia = inp.P_sep * BARA_TO_PSIA
        T_sep_C    = inp.T_sep
        T_sep_F    = T_sep_C * 9.0 / 5.0 + 32.0
        T_sep_R    = T_sep_F + 459.67
        # GOR: sm³/sm³ — already a volume ratio (cc/cc), same numerically
        R_cc = inp.R_sep

    # ------------------------------------------------------------------
    # 2. Oil volumes
    # ------------------------------------------------------------------
    V_oil_sep = inp.oil_fraction * inp.V_cell          # cc, separator oil
    V_oil_STO = V_oil_sep / inp.Bo_sep                 # cc, stock-tank oil

    # ------------------------------------------------------------------
    # 3. Gas volumes
    # ------------------------------------------------------------------
    # Gas at standard conditions (cc)
    V_gas_std_cc = R_cc * V_oil_STO

    # Gas at standard conditions in reporting units
    if inp.units == "field":
        V_gas_std_unit = V_gas_std_cc / SCF_TO_CC      # → scf
    else:
        V_gas_std_unit = V_gas_std_cc * CC_TO_SM3      # → sm³

    # Gas at separator conditions (real-gas law):
    #   V_gas_sep = V_gas_std × (P_std / P_sep) × (T_sep / T_std) × Z_sep
    V_gas_sep = (
        V_gas_std_cc
        * (P_STD_PSIA / P_sep_psia)
        * (T_sep_R / T_STD_R)
        * inp.Z_sep
    )

    # ------------------------------------------------------------------
    # 4. GOR back-calculation (verification)
    # ------------------------------------------------------------------
    # R_cc_check = V_gas_std_cc / V_oil_STO  (should equal R_cc)
    R_cc_check = V_gas_std_cc / V_oil_STO if V_oil_STO > 0 else 0.0
    if inp.units == "field":
        GOR_check = R_cc_check / SCF_STB_TO_CC_CC
    else:
        GOR_check = R_cc_check   # sm³/sm³ is the same as cc/cc ratio

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
