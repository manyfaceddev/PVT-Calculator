"""
pvt/correlations/viscosity/lee_gonzalez_eakin.py — Lee, Gonzalez & Eakin (1966)
gas viscosity correlation.

Reference: Lee, A.L., Gonzalez, M.H., and Eakin, B.E. (1966). The Viscosity of
Natural Gases. JPT, August 1966, pp. 997-1000 (SPE 1340).

    K = (9.4 + 0.02*M) * T^1.5 / (209 + 19*M + T)      (T in deg R)
    X = 3.5 + 986/T + 0.01*M
    Y = 2.4 - 0.2*X
    mu_g = 1e-4 * K * exp(X * rho_g^Y)                  (rho_g in g/cc, mu_g in cP)

`gas_density_g_cc()` computes the gas density input to the above via the
real-gas law:

    rho_g = P*M / (Z*R*T) [lbm/ft3] * (lbm/ft3 -> g/cc)

D-010 (docs/excel-deviations.md): the source workbook
(5_Viscosity_HPHT_Calc_v2.xlsx) hardcodes the lbm/ft3 -> g/cc conversion as
the rounded 0.0014935. This module derives `DENSITY_COEF` exactly from
canonical constants instead (see below) -- the two agree to ~0.06%, well
within the golden test's tolerance.
"""

import math
from typing import Final

from pvt.core import constants
from pvt.core.exceptions import InputValidationError

_LBM_FT3_TO_G_CC: Final[float] = constants.G_PER_LB / 30.48**3
"""Exact lbm/ft3 -> g/cc conversion: G_PER_LB / (30.48^3 cc per ft3)
= 453.59237 / 28316.846592 = 0.01601846337... (30.48 cm/ft is the formula-
grade, exact-by-definition inch/foot conversion, so this is derived rather
than hardcoded as the rounded 0.016018463 literal)."""

DENSITY_COEF: Final[float] = _LBM_FT3_TO_G_CC / constants.R_PSIA_FT3_LBMOL_R
"""P*M/(Z*T) [psia*g/mol / R] -> rho_g [g/cc] conversion factor.

= _LBM_FT3_TO_G_CC / R_PSIA_FT3_LBMOL_R ~= 0.01601846337 / 10.7316 ~= 0.0014926
(D-010: the source workbook hardcodes the rounded 0.0014935 instead)."""


def gas_density_g_cc(p_psia: float, mw: float, z: float, t_f: float) -> float:
    """
    Compute gas density from the real-gas law, per Lee-Gonzalez-Eakin (1966):

        rho_g = P*M / (Z*(T_F + 459.67)) * DENSITY_COEF

    Parameters
    ----------
    p_psia : pressure, psia
    mw : gas apparent molecular weight, g/mol (lbm/lbmol)
    z : gas compressibility factor (dimensionless)
    t_f : temperature, deg F

    Returns
    -------
    rho_g, gas density in g/cc

    Raises
    ------
    InputValidationError
        If p_psia < 0, mw <= 0, or z <= 0.
    """
    errors = []
    if p_psia < 0:
        errors.append(f"p_psia {p_psia} must be >= 0")
    if mw <= 0:
        errors.append(f"mw {mw} must be > 0")
    if z <= 0:
        errors.append(f"z {z} must be > 0")
    if errors:
        raise InputValidationError(errors)
    t_r = t_f + 459.67
    return p_psia * mw / (z * t_r) * DENSITY_COEF


def gas_viscosity_cp(t_f: float, mw: float, rho_g_cc: float) -> float:
    """
    Estimate gas viscosity using Lee, Gonzalez & Eakin (1966):

        K = (9.4 + 0.02*M) * T^1.5 / (209 + 19*M + T)      (T in deg R)
        X = 3.5 + 986/T + 0.01*M
        Y = 2.4 - 0.2*X
        mu_g = 1e-4 * K * exp(X * rho_g^Y)

    Parameters
    ----------
    t_f : temperature, deg F
    mw : gas apparent molecular weight, g/mol (lbm/lbmol)
    rho_g_cc : gas density, g/cc (see `gas_density_g_cc`)

    Returns
    -------
    mu_g, gas viscosity in cP

    Raises
    ------
    InputValidationError
        If mw <= 0 or rho_g_cc < 0.
    """
    errors = []
    if mw <= 0:
        errors.append(f"mw {mw} must be > 0")
    if rho_g_cc < 0:
        errors.append(f"rho_g_cc {rho_g_cc} must be >= 0")
    if errors:
        raise InputValidationError(errors)
    t_r = t_f + 459.67
    k = (9.4 + 0.02 * mw) * t_r**1.5 / (209 + 19 * mw + t_r)
    x = 3.5 + 986 / t_r + 0.01 * mw
    y = 2.4 - 0.2 * x
    return 1e-4 * k * math.exp(x * rho_g_cc**y)
