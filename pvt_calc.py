"""
pvt_calc.py — DEPRECATED backward-compatibility shim.

All symbols are now in the `pvt` package.  Import from there instead:

    from pvt import SeparatorStage, calculate_multistage, ...

This file is kept only so any external scripts that still reference
`pvt_calc` do not immediately break.  It will be removed in a future
release.
"""

import warnings

warnings.warn(
    "pvt_calc is deprecated. Import from the 'pvt' package instead.",
    DeprecationWarning,
    stacklevel=2,
)

from pvt import (           # noqa: F401, E402
    P_STD_PSIA,
    T_STD_F,
    T_STD_R,
    SCF_TO_CC,
    STB_TO_CC,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
    CC_TO_SM3,
    Units,
    standing_bubble_point,
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
