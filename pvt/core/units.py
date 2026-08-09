"""
pvt/core/units.py — Unit conversion functions.

All conversions are one-liners built strictly on pvt.core.constants.
No numeric literals except pure math (e.g., 5/9, 32, 141.5/131.5).
"""

from pvt.core import constants


# ===========================================================================
# Temperature Conversions
# ===========================================================================


def f_to_r(temp_f: float) -> float:
    """Fahrenheit to Rankine."""
    return temp_f + constants.RANKINE_OFFSET


def r_to_f(temp_r: float) -> float:
    """Rankine to Fahrenheit."""
    return temp_r - constants.RANKINE_OFFSET


def f_to_c(temp_f: float) -> float:
    """Fahrenheit to Celsius."""
    return (temp_f - 32) * 5 / 9


def c_to_f(temp_c: float) -> float:
    """Celsius to Fahrenheit."""
    return temp_c * 9 / 5 + 32


def c_to_k(temp_c: float) -> float:
    """Celsius to Kelvin."""
    return temp_c + constants.KELVIN_OFFSET


def k_to_c(temp_k: float) -> float:
    """Kelvin to Celsius."""
    return temp_k - constants.KELVIN_OFFSET


def f_to_k(temp_f: float) -> float:
    """Fahrenheit to Kelvin."""
    return (temp_f + constants.RANKINE_OFFSET) * 5 / 9


# ===========================================================================
# Pressure Conversions
# ===========================================================================


def psig_to_psia(p_psig: float, p_atm_psia: float = constants.P_ATM_PSIA) -> float:
    """Gauge pressure (psig) to absolute pressure (psia)."""
    return p_psig + p_atm_psia


def psia_to_psig(p_psia: float, p_atm_psia: float = constants.P_ATM_PSIA) -> float:
    """Absolute pressure (psia) to gauge pressure (psig)."""
    return p_psia - p_atm_psia


def bara_to_psia(p_bara: float) -> float:
    """Absolute pressure (bara) to psia."""
    return p_bara * constants.PSIA_PER_BARA


def psia_to_bara(p_psia: float) -> float:
    """Absolute pressure (psia) to bara."""
    return p_psia / constants.PSIA_PER_BARA


def mbar_to_psia(p_mbar: float) -> float:
    """Pressure (mbar) to psia."""
    return p_mbar * constants.P_STD_PSIA / constants.P_STD_MBAR


# ===========================================================================
# Volume Conversions (at standard conditions)
# ===========================================================================


def scf_stb_to_cc_cc(ratio: float) -> float:
    """Ratio scf/STB to cc/cc at standard conditions."""
    return ratio * constants.SCF_STB_TO_CC_CC


def cc_cc_to_scf_stb(ratio: float) -> float:
    """Ratio cc/cc to scf/STB at standard conditions."""
    return ratio / constants.SCF_STB_TO_CC_CC


def scf_to_cc(volume_scf: float) -> float:
    """Standard cubic feet (scf) to cubic centimeters (cc)."""
    return volume_scf * constants.CC_PER_SCF


def cc_to_scf(volume_cc: float) -> float:
    """Cubic centimeters (cc) to standard cubic feet (scf)."""
    return volume_cc / constants.CC_PER_SCF


def stb_to_cc(volume_stb: float) -> float:
    """Stock tank barrel (STB) to cubic centimeters (cc)."""
    return volume_stb * constants.CC_PER_STB


def cc_to_stb(volume_cc: float) -> float:
    """Cubic centimeters (cc) to stock tank barrel (STB)."""
    return volume_cc / constants.CC_PER_STB


# ===========================================================================
# Density and API Gravity Conversions
# ===========================================================================


def api_from_density_g_cc(rho: float) -> float:
    """
    API gravity from density.

    House convention: treats g/cc at 60 °F as SG 60/60 (all ADRIC sheets do);
    `sg_from_density_g_cc` gives the strict conversion.
    """
    return (141.5 / rho) - 131.5


def density_g_cc_from_api(api: float) -> float:
    """Density (g/cc at 60 °F) from API gravity."""
    return 141.5 / (api + 131.5)


def sg_from_density_g_cc(rho: float) -> float:
    """Specific gravity (60/60 °F) from density in g/cc."""
    return rho / constants.WATER_DENSITY_60F_G_CC
