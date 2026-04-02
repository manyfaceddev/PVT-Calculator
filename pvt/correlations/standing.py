"""
pvt/correlations/standing.py — Standing (1947) empirical correlations.

Reference: Standing, M.B. (1947). A Pressure-Volume-Temperature Correlation
for Mixtures of California Oils and Gases. Drill. & Prod. Prac., API.
"""


def bubble_point(
    R_scf_stb: float,
    gamma_g:   float,
    T_F:       float,
    API:       float,
) -> float:
    """
    Estimate bubble-point pressure using Standing (1947).

        Pb = 18.2 × [(R / γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]

    Parameters
    ----------
    R_scf_stb : total solution GOR in scf/STB
    gamma_g   : gas specific gravity (air = 1.0)
    T_F       : reservoir temperature in °F
    API       : stock-tank oil API gravity

    Returns
    -------
    Pb in psia  (≥ 0; returns 0 for non-physical inputs)

    Notes
    -----
    Accuracy ±10–15 % for typical crude oils.
    Originally derived from California crude data.
    """
    if gamma_g <= 0 or R_scf_stb <= 0:
        return 0.0
    x  = 0.00091 * T_F - 0.0125 * API
    Pb = 18.2 * ((R_scf_stb / gamma_g) ** 0.83 * 10.0 ** x - 1.4)
    return max(Pb, 0.0)
