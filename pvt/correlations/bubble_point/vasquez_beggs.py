"""
pvt/correlations/bubble_point/vasquez_beggs.py — Vasquez & Beggs (1980)
bubble-point pressure correlation.

Reference: Vasquez, M. and Beggs, H.D. (1980). Correlations for Fluid
Physical Property Prediction. JPT, June 1980. Tabulated coefficients per
Ahmed, T., Reservoir Engineering Handbook.

Two equivalent presentations of the same correlation exist in the
literature, and this module implements the second one directly:

1. Original Rs-form (1980 paper), Pb solved for by inversion:

       Rs = C1' x gamma_g x Pb^C2' x exp(C3' x API / (T + 460))

   with (C1', C2', C3') = (0.0362, 1.0937, 25.7240) for API <= 30, and
   (0.0178, 1.1870, 23.9310) for API > 30 (T in deg F).

2. Ahmed's tabulated Pb-form (algebraically identical, base-10, solved
   for Pb directly -- this is what `bubble_point()` below implements):

       Pb = [C1 x (Rs / gamma_g) x 10^(-C3 x API / (T + 460))]^C2

   with (C1, C2, C3) = (27.62, 0.914, 11.172) for API <= 30, and
   (56.18, 0.842, 10.393) for API > 30.

Coefficient identity (why both forms agree): C2 = 1/C2', C3 = C3' x C2 x
log10(e), and C1 = [(1/C1')^(1/C2')]^C2' ... equivalently C1^C2 =
(1/C1')^(1/C2'). Concretely, for API <= 30: 1/1.0937 = 0.914328 (rounds
to the tabulated C2 = 0.914); 25.7240/1.0937 x log10(e) = 10.2147, and
10.2147 x 0.914328 = 11.1718 (rounds to the tabulated C3 = 11.172); and
(1/0.0362)^0.914328 = 27.6243 (rounds to the tabulated C1 = 27.62). The
API > 30 branch matches the same way: 1/1.1870 = 0.842, 23.9310 x 0.842
x log10(e) = 10.393 rounds to 10.393, and (1/0.0178)^0.842 rounds to
56.18. Because the two published tables are independently rounded to 3-4
significant figures, the two forms agree to within ~0.5% rather than
being bit-identical -- see `test_round_trip_against_original_rs_form` in
tests/unit/correlations/test_vasquez_beggs.py, which cross-checks
`bubble_point()` (form 2) against form 1 directly (not against itself).

D-008 (docs/excel-deviations.md): the source workbook computes the
exponent term as a = -C3 x API x (T + 460) -- multiplying by (T + 460)
instead of dividing -- which overflows to #NUM!. This module divides by
(T + 460), per both published forms above.
"""

import math

# Ahmed's tabulated Pb-form coefficients (C1, C2, C3), selected by
# stock-tank oil API gravity. API <= 30 uses one triplet; API > 30
# switches to the other.
_COEFFS_API_LE_30 = (27.62, 0.914, 11.172)
_COEFFS_API_GT_30 = (56.18, 0.842, 10.393)


def corrected_gas_gravity(
    gas_gravity: float,
    api: float,
    t_sep_f: float,
    p_sep_psia: float,
) -> float:
    """
    Correct separator gas gravity to an equivalent gravity at a 100 psia
    reference separator pressure (gamma_gs), per Vasquez & Beggs (1980):

        gamma_gs = gamma_g x [1 + 5.912e-5 x API x Tsep x log10(Psep / 114.7)]

    Parameters
    ----------
    gas_gravity : separator gas specific gravity (air = 1.0)
    api : stock-tank oil API gravity
    t_sep_f : separator temperature, deg F
    p_sep_psia : separator pressure, psia

    Returns
    -------
    gamma_gs, the corrected gas gravity (air = 1.0)
    """
    return gas_gravity * (
        1.0 + 5.912e-5 * api * t_sep_f * math.log10(p_sep_psia / 114.7)
    )


def bubble_point(
    rs_scf_stb: float,
    gas_gravity: float,
    api: float,
    t_f: float,
) -> float:
    """
    Estimate bubble-point pressure using Vasquez & Beggs (1980), Ahmed's
    tabulated Pb-form:

        Pb = [C1 x (Rs / gamma_g) x 10^(-C3 x API / (T + 460))]^C2

    where (C1, C2, C3) = (27.62, 0.914, 11.172) for API <= 30, and
    (56.18, 0.842, 10.393) for API > 30 (T in deg F). This form is the
    published inversion of the original 1980 Rs-form
    (Rs = C1' x gamma_g x Pb^C2' x exp(C3' x API/(T+460))) -- see the
    module docstring for the coefficient identity between the two, and
    docs/excel-deviations.md D-008 for the source workbook's sign/grouping
    error in this exponent term (multiplies by (T+460) instead of
    dividing, overflowing to #NUM!).

    Parameters
    ----------
    rs_scf_stb : solution GOR at bubble point, scf/STB
    gas_gravity : gas specific gravity (air = 1.0)
    api : stock-tank oil API gravity
    t_f : reservoir temperature, deg F

    Returns
    -------
    Pb in psia
    """
    c1, c2, c3 = _COEFFS_API_LE_30 if api <= 30 else _COEFFS_API_GT_30
    exponent_term = 10.0 ** (-c3 * api / (t_f + 460.0))
    return (c1 * (rs_scf_stb / gas_gravity) * exponent_term) ** c2
