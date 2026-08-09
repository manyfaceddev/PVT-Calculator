"""
pvt/correlations/bubble_point/glaso.py — Glaso (1980) bubble-point pressure
correlation.

Reference: Glaso, O. (1980). Generalized Pressure-Volume-Temperature
Correlations. JPT, May 1980, pp. 785-795 (SPE 8016).

    Pb* = (Rs / gamma_g)^0.816 x T^0.172 / API^0.989          (T in deg F)
    log10(Pb) = 1.7669 + 1.7447 x log10(Pb*) - 0.30218 x (log10(Pb*))^2
    Pb = 10^log10(Pb)

D-009 (docs/excel-deviations.md): the source workbook multiplies Pb* by a
stray factor of 14.5 and never applies the final 10^log10(Pb) step (i.e. it
returns log10(Pb) itself, mislabeled as Pb). This module applies neither
deviation -- `pb_star()` computes Pb* exactly per the published form above
(no stray factor), and `bubble_point()` exponentiates the quadratic back out
of log space to return Pb, not log10(Pb). The workbook also carries the
correlation constants rounded to 1.767/1.745; this module uses the
published 4-5 significant-figure constants 1.7669/1.7447 (the third
constant, -0.30218, is unchanged either way).

`pb_star()` is exposed as a public function (not just an internal step of
`bubble_point()`) because it is independently anchored against the source
workbook: cell F81 caches 497.662528246482, which is Pb* x 14.5 (the sheet's
stray factor) for these same inputs -- dividing out the bug reproduces
`pb_star()`'s output to 1e-6 relative precision. See
`test_pb_star_matches_workbook_cell` in
tests/unit/correlations/test_glaso.py.
"""

import math


def pb_star(
    rs_scf_stb: float,
    gas_gravity: float,
    api: float,
    t_f: float,
) -> float:
    """
    Compute the Glaso (1980) correlating number Pb*:

        Pb* = (Rs / gamma_g)^0.816 x T^0.172 / API^0.989

    Parameters
    ----------
    rs_scf_stb : solution GOR at bubble point, scf/STB
    gas_gravity : gas specific gravity (air = 1.0)
    api : stock-tank oil API gravity
    t_f : reservoir temperature, deg F

    Returns
    -------
    Pb*, the dimensionless Glaso correlating number
    """
    return (rs_scf_stb / gas_gravity) ** 0.816 * t_f**0.172 / api**0.989


def bubble_point(
    rs_scf_stb: float,
    gas_gravity: float,
    api: float,
    t_f: float,
) -> float:
    """
    Estimate bubble-point pressure using Glaso (1980):

        Pb* = (Rs / gamma_g)^0.816 x T^0.172 / API^0.989
        log10(Pb) = 1.7669 + 1.7447 x log10(Pb*) - 0.30218 x (log10(Pb*))^2
        Pb = 10^log10(Pb)

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
    log10_pb_star = math.log10(pb_star(rs_scf_stb, gas_gravity, api, t_f))
    log10_pb = 1.7669 + 1.7447 * log10_pb_star - 0.30218 * log10_pb_star**2
    return 10.0**log10_pb
