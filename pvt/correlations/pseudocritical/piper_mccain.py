"""Piper, McCain & Corredor (1993) pseudo-critical properties (SPE 26668).

Two forms, both solving the same J/K shape as SBV (``Tpc = K**2 / J``,
``Ppc = Tpc / J``):

- ``from_gravity``: gas gravity + sour-gas mole fractions only (no library).
- ``from_composition``: full mole composition off a ``CompositionStream``.

Coefficients below are the *published* SPE 26668 values. See
``docs/excel-deviations.md`` D-003: the reference workbook
(``Z factor calculation.xls``, ``Properties!J4``) holds alpha2 = -0.09034,
a digit transposition of the published -0.90348. The transposed value makes
the CO2 term ~10x weaker than intended; this engine uses the published
value, so results diverge from the workbook whenever CO2 is present (see
``test_deviation_d003_co2_coefficient``).

See also D-004: the workbook's C7+ molecular weight is an unweighted
average across the C7+ species; this engine mole-fraction-weights it
(``Sigma(y_i * MW_i) / Sigma(y_i)``), which is the physically correct
mixing rule and the one SPE 26668 itself specifies.
"""
from collections.abc import Callable

from pvt.core.components import KATZ_FIROOZABADI
from pvt.core.composition import CompositionStream

# Gravity form (SPE 26668) takes no library, so the three sour species'
# Tc/Pc are pinned to the canonical KF library rows rather than a second,
# separately-sourced table copied from the paper. This keeps from_gravity
# and from_composition numerically consistent when the latter is fed a
# KF-library stream (the only library this codebase has).
_H2S = KATZ_FIROOZABADI.get("H2S")
_CO2 = KATZ_FIROOZABADI.get("CO2")
_N2 = KATZ_FIROOZABADI.get("N2")

# Gravity form: J/K coefficients (alpha0..alpha5 / beta0..beta5).
_GRAV_ALPHA = (0.11582, -0.4582, -0.90348, -0.66026, 0.70729, -0.099397)
_GRAV_BETA = (3.8216, -0.06534, -0.42113, -0.91249, 17.438, -3.2191)

# Compositional form: J/K coefficients (alpha0..alpha7 / beta0..beta7).
# Index 4/5 weight the C1-C6 hydrocarbon sum (linear/squared); index 6/7
# weight the C7+ y*MW term (linear/squared). Index 5 is published as 0.0
# (no squared-HC-sum term in this form) -- kept for positional alignment
# with the gravity form's alpha4/alpha5 (gamma, gamma**2) slots.
_COMP_ALPHA = (0.052073, 1.0160, 0.86961, 0.72646, 0.85101, 0.0, 0.020818, -0.0001506)
_COMP_BETA = (-0.39741, 1.0503, 0.96592, 0.78569, 0.98211, 0.0, 0.45536, -0.0037684)

# Compositional form bucketing. C1-C6 hydrocarbons get their own weighted
# sum; H2S/CO2/N2 are the "sour" species with dedicated coefficients; every
# other component (C7, C8, ..., C36+, and -- deliberately -- the
# naphthenes/aromatics MCP, Benzene, CycloC6, MCH, Toluene, EBenzene,
# MP-Xylene, O-Xylene, TMB124, ...) falls into the C7+ bucket. SPE 26668
# defines the C7+ term via mole fraction and MW alone, with no allowance
# for ring/aromatic structure, so anything that isn't light HC or sour is
# treated as "heptanes-plus-like" for this correlation's J/K purposes.
_HC_C1_C6 = frozenset({"C1", "C2", "C3", "iC4", "nC4", "NeoC5", "iC5", "nC5", "C6"})
_SOUR = frozenset({"H2S", "CO2", "N2"})


def from_gravity(
    gas_gravity: float, y_h2s: float = 0.0, y_co2: float = 0.0, y_n2: float = 0.0
) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia]) from gas gravity and sour-gas mole fractions.

    Args:
        gas_gravity: Gas specific gravity relative to air.
        y_h2s: H2S mole FRACTION (0-1).
        y_co2: CO2 mole FRACTION (0-1).
        y_n2: N2 mole FRACTION (0-1).
    """
    a0, a1, a2, a3, a4, a5 = _GRAV_ALPHA
    b0, b1, b2, b3, b4, b5 = _GRAV_BETA

    j = (
        a0
        + a1 * y_h2s * (_H2S.tc_r / _H2S.pc_psia)
        + a2 * y_co2 * (_CO2.tc_r / _CO2.pc_psia)
        + a3 * y_n2 * (_N2.tc_r / _N2.pc_psia)
        + a4 * gas_gravity
        + a5 * gas_gravity**2
    )
    k = (
        b0
        + b1 * y_h2s * (_H2S.tc_r / _H2S.pc_psia**0.5)
        + b2 * y_co2 * (_CO2.tc_r / _CO2.pc_psia**0.5)
        + b3 * y_n2 * (_N2.tc_r / _N2.pc_psia**0.5)
        + b4 * gas_gravity
        + b5 * gas_gravity**2
    )
    tpc = k * k / j
    return tpc, tpc / j


def from_composition(stream: CompositionStream, c7p_mw: float | None = None) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia]) from a full mole composition.

    The C7+ bucket is every component that is neither a sour species
    (H2S/CO2/N2) nor in the C1-C6 hydrocarbon list -- see module docstring
    for why naphthenes/aromatics land here by design. Its molecular weight
    is mole-fraction-weighted (``Sigma(y_i*MW_i) / Sigma(y_i)``) unless
    `c7p_mw` is supplied, which overrides the computed value outright.

    Args:
        stream: Composition on a mol% basis (any library).
        c7p_mw: Optional override for the C7+ bucket's molecular weight.
    """
    lib = stream.library
    y = {code: v / 100.0 for code, v in stream.normalized_mol().items()}

    def tc_over_pc(code: str) -> float:
        c = lib.get(code)
        return c.tc_r / c.pc_psia

    def tc_over_sqrt_pc(code: str) -> float:
        c = lib.get(code)
        return c.tc_r / c.pc_psia**0.5

    def sour_term(code: str, denom_fn: Callable[[str], float]) -> float:
        """`y[code] * denom_fn(code)`, or 0.0 if `code` isn't in the composition.

        Guards the `lib.get(code)` inside `denom_fn` too: a library need not
        define H2S/CO2/N2 rows if the stream never uses them.
        """
        return y[code] * denom_fn(code) if code in y else 0.0

    h2s_j = sour_term("H2S", tc_over_pc)
    co2_j = sour_term("CO2", tc_over_pc)
    n2_j = sour_term("N2", tc_over_pc)
    h2s_k = sour_term("H2S", tc_over_sqrt_pc)
    co2_k = sour_term("CO2", tc_over_sqrt_pc)
    n2_k = sour_term("N2", tc_over_sqrt_pc)

    s_j = sum(yi * tc_over_pc(c) for c, yi in y.items() if c in _HC_C1_C6)
    s_k = sum(yi * tc_over_sqrt_pc(c) for c, yi in y.items() if c in _HC_C1_C6)

    c7p_codes = [c for c in y if c not in _SOUR and c not in _HC_C1_C6]
    y_c7p = sum(y[c] for c in c7p_codes)
    if c7p_mw is not None:
        mw_c7p = c7p_mw
    elif y_c7p > 0:
        mw_c7p = sum(y[c] * lib.get(c).mw for c in c7p_codes) / y_c7p
    else:
        mw_c7p = 0.0
    c7p_term = y_c7p * mw_c7p

    a0, a1, a2, a3, a4, a5, a6, a7 = _COMP_ALPHA
    b0, b1, b2, b3, b4, b5, b6, b7 = _COMP_BETA

    j = (
        a0
        + a1 * h2s_j
        + a2 * co2_j
        + a3 * n2_j
        + a4 * s_j
        + a5 * s_j**2
        + a6 * c7p_term
        + a7 * c7p_term**2
    )
    k = (
        b0
        + b1 * h2s_k
        + b2 * co2_k
        + b3 * n2_k
        + b4 * s_k
        + b5 * s_k**2
        + b6 * c7p_term
        + b7 * c7p_term**2
    )
    tpc = k * k / j
    return tpc, tpc / j
