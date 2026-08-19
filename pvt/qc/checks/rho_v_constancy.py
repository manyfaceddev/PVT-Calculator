"""
pvt/qc/checks/rho_v_constancy.py -- QC check: CCE density*volume (mass)
constancy above Psat.

Resurrected from CCE v1/v2's QC Protocol (dropped in v5's layout
compaction -- `docs/workbook-defect-review.md` row C5, same heritage note
as `monotonic_compressibility`: "...rho*V-constancy checks existed in
v1/v2, dropped in v5's layout compaction. QC Protocol rows 42-87 in
v2."). Above Psat the CCE cell holds a fixed single-phase mass, so
`rho_i * V_i` (density times total cell volume) should be constant across
every at/above-Psat stage -- literally the identity
`pvt.experiments.cce.calc.calculate`'s own density formula is built from
(`rho_i = rho_at_psat * v_sat / v_i` implies `rho_i * v_i = rho_at_psat *
v_sat`, a constant, for every stage i). This check re-derives that
constant independently, from the (density, volume) pairs actually
reported by a run, and grades how far each stage's product spreads from
the mean -- catching a transcription error or a broken import that
quietly violates the mass-conservation identity the engine's own formula
assumes.

Threshold: `"cce_rho_v_spread_pct" = (0.5, 1.0)`, graded on
`spread_pct = max(|rho_i*V_i - mean(rho*V)|) / mean(rho*V) * 100`. An
engineering-judgment proposal (like `monotonic_compressibility`'s
threshold), pending Swej calibration.
"""

from __future__ import annotations

from collections.abc import Sequence

from pvt.core.exceptions import InputValidationError
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID = "cce_rho_v_spread_pct"


def check(
    points: Sequence[tuple[float, float]],
    registry: ThresholdRegistry | None = None,
) -> QCResult:
    """Grade the density*volume (mass) constancy of a set of at/above-
    Psat CCE stages.

    Args:
        points: (density g/cc, cell volume cc) pairs, one per at/above-
            Psat CCE stage.
        registry: supplies "cce_rho_v_spread_pct" (review%, fail%);
            defaults to house thresholds (0.5, 1.0).

    Returns:
        QCResult graded on `spread_pct` (see module docstring); `value`
        is `spread_pct`.

    Raises:
        InputValidationError: fewer than 2 points, or the mean product is
            zero (degenerate -- cannot express spread as a percent).
    """
    registry = registry or ThresholdRegistry()

    n = len(points)
    if n < 2:
        raise InputValidationError([f"rho*V constancy check needs at least 2 points (found {n})"])

    products = [rho * v for rho, v in points]
    mean_product = sum(products) / n
    if mean_product == 0:
        raise InputValidationError(
            ["rho*V constancy check: mean(rho*V) is zero, cannot express spread as a percent"]
        )

    spread_pct = max(abs(p - mean_product) for p in products) / abs(mean_product) * 100.0

    review_at, fail_at = registry.get(_CHECK_ID)
    severity = grade(spread_pct, review_at, fail_at)
    return QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=spread_pct,
        threshold=f"review >{review_at}% / fail >{fail_at}%",
        message=(
            f"rho*V spread {spread_pct:.4f}% over {n} points "
            f"(mean rho*V={mean_product:.6f}) ({severity.value})"
        ),
    )
