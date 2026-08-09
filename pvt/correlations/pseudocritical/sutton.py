"""Sutton (1985) pseudo-critical properties from gas gravity.

Source: Sutton, R.P., SPE 14265; coefficients as used in the ADRIC CVD workbook
(Additional_QC!E9/F9) and DV v5 Additional_QC.
"""
from pvt.core.exceptions import InputValidationError


def pseudo_criticals(gas_gravity: float) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia]) for a sweet natural gas of given gravity (air=1)."""
    if not 0.55 <= gas_gravity <= 2.0:
        raise InputValidationError([f"gas_gravity {gas_gravity} outside Sutton range 0.55-2.0"])
    ppc = 756.8 - 131.0 * gas_gravity - 3.6 * gas_gravity**2
    tpc = 169.2 + 349.5 * gas_gravity - 74.0 * gas_gravity**2
    return tpc, ppc
