"""
pvt/qc/checks/hoffman_crump.py — QC check: Hoffman-Crump K-value consistency
crossplot for a flash gas/liquid pair.

For every component present, with a positive mole fraction, in BOTH the gas
and liquid streams of a flash, the classic Hoffman (1953) / Crump K-value
consistency plot forms one point:

    K = y / x                                    (vapor-liquid K-value)
    b = log10(Pc / 14.7) / (1/Tb - 1/Tc)          (component b-factor)
    F = b * (1/Tb - 1/T_R)                        (x-axis)
    log10(K * P) = ...                            (y-axis)

where Tb, Pc, Tc are the component's boiling point, critical pressure and
critical temperature, and T_R is the flash temperature in Rankine. A
thermodynamically consistent K-value set falls on (nearly) a single straight
line across all components; this check fits that line by ordinary least
squares and grades its R².

Threshold convention: `ThresholdRegistry.get("hoffman_r2")` returns an
**R-squared floor** pair `(review_r2, fail_r2)` -- e.g. the default
`(0.98, 0.95)` reads "R² >= 0.98 is PASS, R² >= 0.95 is REVIEW, below that is
FAIL" -- because that is how an engineer specifies acceptance on this plot.
`grade()` itself only understands "smaller deviation is better" bands, so
`check()` converts: it grades `1 - r_squared` against
`(1 - review_r2, 1 - fail_r2)`.

The default thresholds (0.98, 0.95) are proposed by engineering judgment --
the source PVT-check sheets show this crossplot visually, with no numeric R²
gate of their own -- and are configurable via `registry.override`, pending
Swej calibration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pvt.core import units as u
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID = "hoffman_r2"

_HOFFMAN_P_ATM = 14.7
"""Hoffman-Crump convention constant: 14.7 psia, the reference pressure
baked into the classic b-factor correlation (b = log10(Pc/14.7)/(1/Tb -
1/Tc)). This is deliberately NOT `pvt.core.constants.P_STD_PSIA` (14.73, the
ADRIC lab volumetric standard) nor `P_ATM_PSIA` (14.696, the gas-constant /
psig->psia basis) -- it is the older, rounder reference pressure the
original correlation was published with, and using either engine constant in
its place would shift every b-factor by a fraction of a percent. Kept
module-local (not added to `pvt.core.constants`) because it belongs to this
one correlation, not to the engine's general unit system."""


@dataclass(frozen=True)
class HoffmanPoint:
    """One component's Hoffman-Crump crossplot point."""

    code: str
    """Component code."""

    k: float
    """Vapor-liquid K-value (y/x, mole-fraction basis)."""

    f_factor: float
    """Crossplot x-axis value: b * (1/Tb - 1/T_R)."""

    log10_kp: float
    """Crossplot y-axis value: log10(K * P)."""


@dataclass(frozen=True)
class HoffmanResult:
    """Hoffman-Crump crossplot fit over all qualifying components."""

    points: list[HoffmanPoint]
    """One point per component present, with a positive mole fraction, in
    both the gas and liquid streams."""

    slope: float
    """Least-squares fit slope (log10_kp vs f_factor)."""

    intercept: float
    """Least-squares fit intercept."""

    r_squared: float
    """Least-squares fit coefficient of determination."""

    qc: QCResult
    """Graded R² result (check_id "hoffman_r2")."""


def check(
    gas: CompositionStream,
    liquid: CompositionStream,
    p_psia: float,
    t_f: float,
    registry: ThresholdRegistry | None = None,
) -> HoffmanResult:
    """Build and grade a Hoffman-Crump K-value consistency crossplot.

    Args:
        gas: Equilibrium gas (vapor) composition stream; supplies `y`.
        liquid: Equilibrium liquid composition stream; supplies `x`.
        p_psia: Flash (separator) pressure (psia).
        t_f: Flash (separator) temperature (°F).
        registry: ThresholdRegistry supplying the "hoffman_r2" R²-floor pair
            (review, fail); defaults to house thresholds (0.98, 0.95). See
            the module docstring for the R²-floor -> `grade()` conversion.

    Returns:
        HoffmanResult with one point per qualifying component, the
        least-squares fit, and the graded R² QCResult.

    Raises:
        InputValidationError: fewer than 2 qualifying components (present,
            with a positive mole fraction, in both streams), or a
            degenerate fit (every qualifying component shares the same
            F-factor or the same log10(K*P), zeroing the least-squares
            fit's ss_xx/ss_tot denominator).
    """
    registry = registry or ThresholdRegistry()

    y_mol = gas.normalized_mol()
    x_mol = liquid.normalized_mol()
    t_r = u.f_to_r(t_f)

    points: list[HoffmanPoint] = []
    for code, y in y_mol.items():
        if code not in x_mol:
            continue
        x = x_mol[code]
        if not (x > 0 and y > 0):
            continue

        component = gas.library.get(code)
        k = y / x
        b = math.log10(component.pc_psia / _HOFFMAN_P_ATM) / (
            1.0 / component.tb_r - 1.0 / component.tc_r
        )
        f_factor = b * (1.0 / component.tb_r - 1.0 / t_r)
        log10_kp = math.log10(k * p_psia)
        points.append(HoffmanPoint(code=code, k=k, f_factor=f_factor, log10_kp=log10_kp))

    slope, intercept, r_squared = _fit_least_squares(points)

    review_r2, fail_r2 = registry.get(_CHECK_ID)
    deviation = 1.0 - r_squared
    severity = grade(deviation, review_at=1.0 - review_r2, fail_at=1.0 - fail_r2)
    qc = QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=r_squared,
        threshold=f"review R²>={review_r2} / fail R²>={fail_r2}",
        message=(
            f"Hoffman-Crump crossplot R²={r_squared:.4f} over {len(points)} "
            f"points ({severity.value})"
        ),
    )
    return HoffmanResult(
        points=points, slope=slope, intercept=intercept, r_squared=r_squared, qc=qc
    )


def _fit_least_squares(points: list[HoffmanPoint]) -> tuple[float, float, float]:
    """Ordinary least-squares fit of log10_kp (y) against f_factor (x).

    Returns:
        (slope, intercept, r_squared).

    Raises:
        InputValidationError: fewer than 2 points (x_bar/y_bar would divide
            by n=0, or the fit is undetermined with n=1), or a degenerate
            fit -- every point sharing the same F-factor (ss_xx=0, the
            slope's denominator) or the same log10(K*P) (ss_tot=0, the R²
            denominator).
    """
    n = len(points)
    if n < 2:
        raise InputValidationError(
            [
                "Hoffmann-Crump QC needs at least 2 components present in "
                f"both streams (found {n})"
            ]
        )
    xs = [p.f_factor for p in points]
    ys = [p.log10_kp for p in points]
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n

    ss_xy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    ss_xx = sum((x - x_bar) ** 2 for x in xs)
    if ss_xx == 0:
        raise InputValidationError(
            [
                "Hoffmann-Crump QC: all qualifying components share the same "
                "F-factor (degenerate fit, cannot compute a slope)"
            ]
        )
    slope = ss_xy / ss_xx
    intercept = y_bar - slope * x_bar

    ss_tot = sum((y - y_bar) ** 2 for y in ys)
    if ss_tot == 0:
        raise InputValidationError(
            [
                "Hoffmann-Crump QC: all qualifying components share the same "
                "log10(K*P) (degenerate fit, cannot compute R²)"
            ]
        )
    ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    r_squared = 1.0 - ss_res / ss_tot

    return slope, intercept, r_squared
