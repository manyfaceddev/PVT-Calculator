"""
pvt/core/constants.py — Canonical physical constants and unit-conversion factors.

Single source of truth for all PVT calculations. Import from here.
All values are Final (immutable) and documented with source citations.

Nomenclature:
  - Field units: psia, °F, scf, STB (stock tank barrel)
  - SI units: Pa, K, sm³ (standard cubic meters)
  - Derived: ratio conversions (e.g., CC_PER_SCF: cc per scf at std conditions)
"""

from typing import Final, Literal

# ===========================================================================
# Lab Standard Conditions (ADRIC sheets)
# ===========================================================================

P_STD_PSIA: Final[float] = 14.73
"""Lab standard pressure: 14.73 psia (ADRIC sheets; 1015.5981 mbar equivalent)."""

P_STD_MBAR: Final[float] = 1015.5981
"""Lab standard pressure: 1015.5981 mbar (14.73 psia equivalent)."""

T_STD_F: Final[float] = 60.0
"""Lab standard temperature: 60°F."""

T_STD_R: Final[float] = 519.67
"""Lab standard temperature: 519.67 °R (T_STD_F + 459.67)."""

T_STD_K: Final[float] = 288.7056
"""Lab standard temperature: 288.7056 K (60°F in Kelvin)."""

RANKINE_OFFSET: Final[float] = 459.67
"""Conversion offset from Fahrenheit to Rankine (°F + 459.67 = °R)."""

# ===========================================================================
# Volume Conversions (at standard conditions)
# ===========================================================================

CC_PER_SCF: Final[float] = 28316.85
"""1 scf = 28,316.85 cc (standard cubic foot to cubic centimeter)."""

CC_PER_STB: Final[float] = 158987.29
"""1 STB = 158,987.29 cc (NIST: 158987.294928 cc; lab sheets canonize to 158987.29)."""

SCF_PER_LBMOL: Final[float] = 379.482
"""1 lbmol ideal gas @ STP ≈ 379.482 scf (standard cubic feet per pound-mole)."""

FT3_PER_BBL: Final[float] = 5.61458
"""1 bbl = 5.61458 ft³ (barrel to cubic feet)."""

CC_TO_SM3: Final[float] = 1e-6
"""Volume conversion: 1 sm³ = 1,000,000 cc (standard cubic meters to cubic centimeters)."""

SCF_STB_TO_CC_CC: Final[float] = CC_PER_SCF / CC_PER_STB
"""Ratio: scf per STB → cc per cc at standard conditions (≈ 0.178108)."""

# ===========================================================================
# Gas and Fluid Properties
# ===========================================================================

AIR_MW: Final[float] = 28.964
"""Molecular weight of air (g/mol)."""

AIR_DENSITY_STD_G_CC: Final[float] = 0.0012255
"""Air density at lab standard conditions: 14.73 psia, 60°F ≈ 0.0012255 g/cc."""

R_PSIA_FT3_LBMOL_R: Final[float] = 10.7316
"""Universal gas constant: 10.7316 psia·ft³/(lbmol·°R)."""

R_PSIA_CC_MOL_K: Final[float] = 1205.91
"""Universal gas constant: 1205.91 psia·cc/(mol·K) [≈ 82.057 × 14.696]."""

WATER_DENSITY_60F_G_CC: Final[float] = 0.9991
"""Water density at 60°F: 0.9991 g/cc."""

# ===========================================================================
# Pressure and Unit Conversions
# ===========================================================================

G_PER_LB: Final[float] = 453.59237
"""Grams per pound (mass conversion)."""

PSIA_PER_BARA: Final[float] = 14.5038
"""1 bara = 14.5038 psia (absolute pressure conversion)."""

P_ATM_PSIA: Final[float] = 14.696
"""Standard atmospheric pressure: 14.696 psia (1 atm)."""

# ===========================================================================
# Type Alias
# ===========================================================================

Units = Literal["field", "si"]
"""Unit system type: 'field' (psia, °F, scf, STB) or 'si' (Pa, K, sm³)."""
