"""
pvt/correlations/viscosity/jossi_stiel_thodos.py — Jossi, Stiel & Thodos (1962)
dense-gas viscosity correlation.

Reference: Jossi, J.A., Stiel, L.I., and Thodos, G. (1962). The Viscosity of
Pure Substances in the Dense Gaseous and Liquid Phases. AIChE Journal, 8(1),
59-63. Transcribed from the preserved VBA `ThodosGasVisc`
(docs/reference/gasprop_functions.bas):

    chi = (Tpc/1.8)^(1/6) / (sqrt(MW) * (Ppc/14.696)^(2/3))     (Tpc in deg R,
                                                                  Ppc in psia)
    Tr <= 1.5:  mu* = 0.00034 * Tr^0.888 / chi
    Tr >  1.5:  mu* = 0.001668 * (0.1338*Tr - 0.0932)^(5/9) / chi

    mu = [ (0.1023 + 0.023364*rho_r + 0.058533*rho_r^2
            - 0.040758*rho_r^3 + 0.0093324*rho_r^4)^4 - 1e-4 ] / chi + mu*

mu* is the dilute-gas (zero-density) viscosity term; the two branches do not
meet exactly at Tr=1.5 -- this is faithful to the VBA source, not a
transcription error (see `test_branch_boundary_continuity_documented`).

D-011 (docs/excel-deviations.md): the VBA source hardcodes the gas constant
in `reduced_density` as the rounded literal 10.73. This module uses the
canonical `R_PSIA_FT3_LBMOL_R` (10.7316) instead, per the task brief; the two
agree to ~0.015%, immaterial at the analytic tolerances this module's tests
use.

Note on the dilute-term branches: the Tr<=1.5 / Tr>1.5 split and its
0.00034/0.888 and 0.001668/0.1338/0.0932/(5/9) coefficients are the Amoco
GasProp VBA's variant of the Stiel-Thodos (1961) dilute-gas viscosity
correlation, not a transcription of the originally-published Stiel-Thodos
coefficients. This VBA variant deviates from published Stiel-Thodos forms
by roughly -2% to +3% depending on Tr, with the ~1% jump right at Tr=1.5
(see the branch-boundary note above) being a symptom of that same VBA-vs-
published divergence. This module is deliberately VBA-faithful, not
published-Stiel-Thodos-faithful -- see D-011 and the module-level goal of
transcribing `docs/reference/gasprop_functions.bas` exactly.
"""

from pvt.core import constants
from pvt.core.exceptions import InputValidationError


def reduced_density(p_psia: float, z: float, t_r: float, vc_mix: float) -> float:
    """
    Compute reduced density per the Jossi-Stiel-Thodos VBA form:

        rho_r = vc_mix * P / (Z * R * T)

    Parameters
    ----------
    p_psia : pressure, psia
    z : gas compressibility factor (dimensionless)
    t_r : temperature, deg R
    vc_mix : mixture pseudo-critical volume, ft3/lbmol

    Returns
    -------
    rho_r, reduced density (dimensionless)

    Raises
    ------
    InputValidationError
        If z <= 0 or vc_mix <= 0.
    """
    errors = []
    if z <= 0:
        errors.append(f"z {z} must be > 0")
    if vc_mix <= 0:
        errors.append(f"vc_mix {vc_mix} must be > 0")
    if errors:
        raise InputValidationError(errors)
    return vc_mix * p_psia / (z * constants.R_PSIA_FT3_LBMOL_R * t_r)


def gas_viscosity_cp(t_r: float, mw: float, tpc_r: float, ppc_psia: float, rho_r: float) -> float:
    """
    Estimate dense-gas viscosity using Jossi, Stiel & Thodos (1962), per the
    Gas_Gradient VBA `ThodosGasVisc`:

        chi = (Tpc/1.8)^(1/6) / (sqrt(MW) * (Ppc/14.696)^(2/3))
        Tr <= 1.5:  mu* = 0.00034 * Tr^0.888 / chi
        Tr >  1.5:  mu* = 0.001668 * (0.1338*Tr - 0.0932)^(5/9) / chi
        mu = [ (0.1023 + 0.023364*rho_r + 0.058533*rho_r^2
                - 0.040758*rho_r^3 + 0.0093324*rho_r^4)^4 - 1e-4 ] / chi + mu*

    Parameters
    ----------
    t_r : temperature, deg R
    mw : gas apparent molecular weight, g/mol (lbm/lbmol)
    tpc_r : mixture pseudo-critical temperature, deg R
    ppc_psia : mixture pseudo-critical pressure, psia
    rho_r : reduced density (see `reduced_density`)

    Returns
    -------
    mu, gas viscosity in cP

    Raises
    ------
    InputValidationError
        If mw <= 0, tpc_r <= 0, ppc_psia <= 0, or rho_r < 0.
    """
    errors = []
    if mw <= 0:
        errors.append(f"mw {mw} must be > 0")
    if tpc_r <= 0:
        errors.append(f"tpc_r {tpc_r} must be > 0")
    if ppc_psia <= 0:
        errors.append(f"ppc_psia {ppc_psia} must be > 0")
    if rho_r < 0:
        errors.append(f"rho_r {rho_r} must be >= 0")
    if errors:
        raise InputValidationError(errors)

    chi = (tpc_r / 1.8) ** (1 / 6) / (mw**0.5 * (ppc_psia / constants.P_ATM_PSIA) ** (2 / 3))

    t_r_reduced = t_r / tpc_r
    if t_r_reduced <= 1.5:
        mu_star = 0.00034 * t_r_reduced**0.888 / chi
    else:
        mu_star = 0.001668 * (0.1338 * t_r_reduced - 0.0932) ** (5 / 9) / chi

    poly = (
        0.1023
        + 0.023364 * rho_r
        + 0.058533 * rho_r**2
        - 0.040758 * rho_r**3
        + 0.0093324 * rho_r**4
    )
    return (poly**4 - 1e-4) / chi + mu_star
