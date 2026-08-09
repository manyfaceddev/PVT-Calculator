"""Wichert-Aziz sour-gas correction for pseudo-critical properties.

Corrects Tpc and Ppc for the presence of CO2 and H2S in natural gas.

Source: Wichert, G. C., and Aziz, K. (1972). "Calculate Z's for Sour Gases."
Hydrocarbon Processing, 51(5), 119-122. As implemented in the Amoco GasProp VBA
(CalculateCriticals).
"""

from pvt.core.exceptions import InputValidationError


def correct(tpc_r: float, ppc_psia: float, y_co2: float, y_h2s: float) -> tuple[float, float]:
    """Return corrected pseudo-critical properties accounting for sour gas components.

    Args:
        tpc_r: Uncorrected pseudo-critical temperature in Rankine.
        ppc_psia: Uncorrected pseudo-critical pressure in psia.
        y_co2: Mole fraction of CO2 (0.0 to 1.0).
        y_h2s: Mole fraction of H2S (0.0 to 1.0).

    Returns:
        Tuple of (corrected_tpc, corrected_ppc).

    Formulas:
        A = y_co2 + y_h2s
        B = y_h2s
        e = 120(A^0.9 − A^1.6) + 15(B^0.5 − B^4)  [°R]
        Tpc' = Tpc − e
        Ppc' = Ppc·Tpc'/(Tpc + B(1−B)e)

    Raises:
        InputValidationError: if y_co2 or y_h2s is outside [0, 1], or their
            sum exceeds 1 -- these are MOLE FRACTIONS (0-1), not mole
            percent; passing e.g. y_co2=20 (meaning 20%) is a common caller
            error this guard is designed to catch.
    """
    errors = []
    if not (0 <= y_co2 <= 1):
        errors.append(f"y_co2 {y_co2} must be a mole FRACTION in [0, 1] (not percent)")
    if not (0 <= y_h2s <= 1):
        errors.append(f"y_h2s {y_h2s} must be a mole FRACTION in [0, 1] (not percent)")
    if y_co2 + y_h2s > 1:
        errors.append(f"y_co2 + y_h2s = {y_co2 + y_h2s} must be <= 1")
    if errors:
        raise InputValidationError(errors)

    A = y_co2 + y_h2s
    B = y_h2s

    e = 120 * (A**0.9 - A**1.6) + 15 * (B**0.5 - B**4)

    tpc_corrected = tpc_r - e
    ppc_corrected = ppc_psia * tpc_corrected / (tpc_r + B * (1 - B) * e)

    return tpc_corrected, ppc_corrected
