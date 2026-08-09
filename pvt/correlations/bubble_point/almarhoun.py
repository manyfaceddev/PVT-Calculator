"""
pvt/correlations/bubble_point/almarhoun.py — Al-Marhoun (1988) bubble-point
pressure correlation.

Reference: Al-Marhoun, M. A. (1988). PVT Correlations for Middle East Crude
Oils. Journal of Petroleum Technology, 40(5), 650-666.

    Pb = 5.38088e-3 · Rs^0.715082 · γg^−1.87784 · γo^3.1437 · T_R^1.32657

    where T_R = t_f + 459.67 (absolute temperature in Rankine)
"""


def bubble_point(
    rs_scf_stb: float,
    gas_gravity: float,
    oil_sg: float,
    t_f: float,
) -> float:
    """
    Estimate bubble-point pressure using Al-Marhoun (1988):

        Pb = 5.38088e-3 · Rs^0.715082 · γg^−1.87784 · γo^3.1437 · T_R^1.32657

        where T_R = t_f + 459.67

    Parameters
    ----------
    rs_scf_stb : solution GOR at bubble point, scf/STB
    gas_gravity : gas specific gravity (air = 1.0)
    oil_sg : stock-tank oil specific gravity
    t_f : reservoir temperature, deg F

    Returns
    -------
    Pb in psia
    """
    t_r = t_f + 459.67
    pb = (
        5.38088e-3
        * rs_scf_stb**0.715082
        * gas_gravity**-1.87784
        * oil_sg**3.1437
        * t_r**1.32657
    )
    return pb
