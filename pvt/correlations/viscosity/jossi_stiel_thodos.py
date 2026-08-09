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
"""

from pvt.core.constants import R_PSIA_FT3_LBMOL_R


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
    """
    return vc_mix * p_psia / (z * R_PSIA_FT3_LBMOL_R * t_r)


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
    """
    chi = (tpc_r / 1.8) ** (1 / 6) / (mw**0.5 * (ppc_psia / 14.696) ** (2 / 3))

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
