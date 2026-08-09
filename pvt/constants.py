"""
Deprecated location — import from pvt.core.constants. Removed after Phase 2.

This module re-exports canonical constants from pvt.core.constants for
backward compatibility during Phase 1–2. New code should import from pvt.core.constants.
Legacy consumers (pvt/ui, pvt/cli.py) still import these old names.
"""

from pvt.core.constants import *  # noqa: F401,F403
from pvt.core.constants import CC_PER_SCF, CC_PER_STB, PSIA_PER_BARA

# Legacy aliases for backward compatibility (removed after Phase 2)
SCF_TO_CC = CC_PER_SCF
STB_TO_CC = CC_PER_STB
BARA_TO_PSIA = PSIA_PER_BARA
# CC_TO_SM3 is re-exported via `import *` from pvt.core.constants above
