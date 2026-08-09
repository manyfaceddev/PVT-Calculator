"""
pvt/correlations/bubble_point/standing.py — Standing (1947) empirical correlations.

Reference: Standing, M.B. (1947). A Pressure-Volume-Temperature Correlation
for Mixtures of California Oils and Gases. Drill. & Prod. Prac., API.
"""

import warnings

# Standing (1947) original California-crude data range. Inputs outside this
# range emit a UserWarning (message contains "outside Standing") -- the
# correlation is a curve fit, not a physical law, and extrapolation accuracy
# degrades outside the range it was regressed on.
_RS_MIN, _RS_MAX = 20.0, 1425.0
_GAS_GRAVITY_MIN, _GAS_GRAVITY_MAX = 0.59, 0.95
_API_MIN, _API_MAX = 16.5, 63.8
_T_F_MIN, _T_F_MAX = 100.0, 258.0


def bubble_point_with_exponent(
    rs_scf_stb: float,
    gas_gravity: float,
    a: float,
) -> float:
    """
    Raw Standing (1947) bubble-point form with the correlation exponent `a`
    supplied directly, rather than computed from temperature and API:

        Pb = 18.2 x [(Rs / gamma_g)^0.83 x 10^a - 1.4]

    where, in the full correlation, `a = 0.00091*T_F - 0.0125*API`.

    This is a parity/testing hook (see docs/excel-deviations.md D-007): the
    source workbook ("Bubble point pressure correlations.xls" F38) leaves
    `a` as a raw user-entered input and never computes it from T/API itself.
    `bubble_point()` is the normal entry point for callers -- it computes
    `a` and range-checks the inputs, then delegates here for the arithmetic.

    Parameters
    ----------
    rs_scf_stb : total solution GOR, scf/STB
    gas_gravity : gas specific gravity (air = 1.0)
    a : correlation exponent (0.00091*T_F - 0.0125*API in the full form)

    Returns
    -------
    Pb in psia (>= 0; returns 0 for non-physical inputs)
    """
    if gas_gravity <= 0 or rs_scf_stb <= 0:
        return 0.0
    pb = 18.2 * ((rs_scf_stb / gas_gravity) ** 0.83 * 10.0 ** a - 1.4)
    return max(pb, 0.0)


def bubble_point(
    rs_scf_stb: float,
    gas_gravity: float,
    api: float,
    t_f: float,
) -> float:
    """
    Estimate bubble-point pressure using Standing (1947), computing the
    correlation exponent from temperature and API gravity:

        a  = 0.00091*T_F - 0.0125*API
        Pb = 18.2 x [(Rs / gamma_g)^0.83 x 10^a - 1.4]

    Emits a `UserWarning` (message contains "outside Standing") for any
    input outside Standing's (1947) original California-crude data range:
    Rs 20-1425 scf/STB, gas_gravity 0.59-0.95, API 16.5-63.8, T 100-258 F.

    Parameters
    ----------
    rs_scf_stb : total solution GOR, scf/STB
    gas_gravity : gas specific gravity (air = 1.0)
    api : stock-tank oil API gravity
    t_f : reservoir temperature, deg F

    Returns
    -------
    Pb in psia (>= 0; returns 0 for non-physical inputs)

    Notes
    -----
    Accuracy +-10-15% for typical crude oils. Originally derived from
    California crude data.
    """
    _warn_if_outside_range(rs_scf_stb, gas_gravity, api, t_f)
    a = 0.00091 * t_f - 0.0125 * api
    return bubble_point_with_exponent(rs_scf_stb, gas_gravity, a)


def _warn_if_outside_range(
    rs_scf_stb: float,
    gas_gravity: float,
    api: float,
    t_f: float,
) -> None:
    """Warn (once per out-of-range input) when a Standing (1947) input falls
    outside the original correlation's California-crude data range."""
    if not (_RS_MIN <= rs_scf_stb <= _RS_MAX):
        warnings.warn(
            f"bubble_point: Rs={rs_scf_stb} scf/STB is outside Standing (1947) "
            f"data range [{_RS_MIN}, {_RS_MAX}]",
            stacklevel=3,
        )
    if not (_GAS_GRAVITY_MIN <= gas_gravity <= _GAS_GRAVITY_MAX):
        warnings.warn(
            f"bubble_point: gas_gravity={gas_gravity} is outside Standing (1947) "
            f"data range [{_GAS_GRAVITY_MIN}, {_GAS_GRAVITY_MAX}]",
            stacklevel=3,
        )
    if not (_API_MIN <= api <= _API_MAX):
        warnings.warn(
            f"bubble_point: API={api} is outside Standing (1947) "
            f"data range [{_API_MIN}, {_API_MAX}]",
            stacklevel=3,
        )
    if not (_T_F_MIN <= t_f <= _T_F_MAX):
        warnings.warn(
            f"bubble_point: T={t_f} F is outside Standing (1947) "
            f"data range [{_T_F_MIN}, {_T_F_MAX}]",
            stacklevel=3,
        )


def standing_bubble_point(
    R_scf_stb: float,
    gamma_g: float,
    T_F: float,
    API: float,
) -> float:
    """
    Deprecated alias for `bubble_point`.

    Preserves the ORIGINAL argument order (R, gamma_g, T_F, API) used by
    existing callers (ui/recombination.py, cli.py) -- this is a wrapper, not
    a plain re-export, because `bubble_point`'s new signature puts `api`
    before `t_f`. Kept for one deprecation phase; new code should call
    `bubble_point(rs_scf_stb, gas_gravity, api, t_f)` directly.
    """
    warnings.warn(
        "standing_bubble_point is deprecated; use "
        "pvt.correlations.bubble_point.standing.bubble_point"
        "(rs_scf_stb, gas_gravity, api, t_f) instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return bubble_point(R_scf_stb, gamma_g, API, T_F)
