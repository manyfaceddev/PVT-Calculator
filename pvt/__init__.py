"""
pvt — PVT Calculator core library.

A pure-Python library for reservoir fluid property calculations.
No UI dependencies; safe to import in scripts, tests, and CLIs.

Modules
-------
pvt.core                 Canonical constants, units, components, composition, exceptions
pvt.correlations         Empirical PVT correlations (Standing bubble point, etc.)
pvt.qc                   QC engine (severity grading, threshold registry)
pvt.experiments          Laboratory experiment modules (recombination, ...)

Planned modules
---------------
pvt.experiments.cce      Constant Composition Expansion
pvt.experiments.cvd      Constant Volume Depletion
pvt.io                   Excel / report ingestion
pvt.reporting            Report generation
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
from pvt.correlations.bubble_point import standing_bubble_point
from pvt.experiments.recombination import (
    SeparatorStage,
    StageResult,
    MultiStageResults,
    calculate_multistage,
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
    "calculate_multistage", "validate_multistage",
]
