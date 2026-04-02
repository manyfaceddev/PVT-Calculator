"""
pvt — PVT Calculator core library.

A pure-Python library for reservoir fluid property calculations.
No UI dependencies; safe to import in scripts, tests, and CLIs.

Modules
-------
pvt.constants           Physical constants and unit-conversion factors
pvt.correlations        Empirical PVT correlations (Standing, etc.)
pvt.recombination       Separator recombination calculations

Planned modules
---------------
pvt.pvt_cell            CCE, CVD, DL — PVT cell experiment calculations
pvt.phase_envelope      Psat / Tsat / phase boundary calculations
pvt.fluid_properties    Bo, GOR, Rs, Bg, viscosity correlations
"""

# Flat re-exports so existing code can do `from pvt import ...`
from pvt.constants import (
    P_STD_PSIA,
    T_STD_F,
    T_STD_R,
    SCF_TO_CC,
    STB_TO_CC,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
    CC_TO_SM3,
    Units,
)
from pvt.correlations.standing import bubble_point as standing_bubble_point
from pvt.recombination import (
    SeparatorStage,
    StageResult,
    MultiStageResults,
    RecombinationInputs,
    RecombinationResults,
    calculate,
    calculate_multistage,
    validate,
    validate_multistage,
)

__all__ = [
    # Constants
    "P_STD_PSIA", "T_STD_F", "T_STD_R",
    "SCF_TO_CC", "STB_TO_CC", "SCF_STB_TO_CC_CC",
    "BARA_TO_PSIA", "CC_TO_SM3", "Units",
    # Correlations
    "standing_bubble_point",
    # Recombination
    "SeparatorStage", "StageResult", "MultiStageResults",
    "RecombinationInputs", "RecombinationResults",
    "calculate", "calculate_multistage",
    "validate", "validate_multistage",
]
