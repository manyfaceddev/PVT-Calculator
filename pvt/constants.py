"""
pvt/constants.py — Physical constants and unit-conversion factors used across
all PVT modules.  Import from here rather than redefining per-module.
"""

from typing import Literal

# ---------------------------------------------------------------------------
# Standard conditions
# ---------------------------------------------------------------------------
P_STD_PSIA: float = 14.696          # psia
T_STD_F:    float = 60.0            # °F
T_STD_R:    float = T_STD_F + 459.67  # Rankine = 519.67 R

# ---------------------------------------------------------------------------
# Volume conversions
# ---------------------------------------------------------------------------
SCF_TO_CC:        float = 28_316.85          # 1 scf  = 28 316.85 cc
STB_TO_CC:        float = 158_987.1          # 1 STB  = 158 987.1  cc
SCF_STB_TO_CC_CC: float = SCF_TO_CC / STB_TO_CC   # ≈ 0.178107  (scf/STB → cc/cc)

# ---------------------------------------------------------------------------
# Pressure / SI conversions
# ---------------------------------------------------------------------------
BARA_TO_PSIA: float = 14.5038       # 1 bara = 14.5038 psia
CC_TO_SM3:    float = 1e-6          # 1 sm³  = 1 000 000 cc

# ---------------------------------------------------------------------------
# Type alias for unit system
# ---------------------------------------------------------------------------
Units = Literal["field", "si"]
