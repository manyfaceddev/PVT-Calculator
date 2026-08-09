"""
Deprecated location — import from pvt.core.constants. Removed after Phase 2.

This module re-exports canonical constants from pvt.core.constants for
backward compatibility. New code should import from pvt.core.constants.
"""

from pvt.core.constants import *  # noqa: F401,F403

# Provide legacy aliases for old names → new canonical names
# (for gradual migration)
SCF_TO_CC = __import__("pvt.core.constants", fromlist=["CC_PER_SCF"]).CC_PER_SCF  # noqa: F405
STB_TO_CC = __import__("pvt.core.constants", fromlist=["CC_PER_STB"]).CC_PER_STB  # noqa: F405
BARA_TO_PSIA = __import__("pvt.core.constants", fromlist=["PSIA_PER_BARA"]).PSIA_PER_BARA  # noqa: F405
CC_TO_SM3 = 1e-6  # 1 sm³ = 1,000,000 cc (derived, not in canonical set)
