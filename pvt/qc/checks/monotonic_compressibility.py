"""
pvt/qc/checks/monotonic_compressibility.py -- QC check: CCE instantaneous
compressibility monotonicity above Psat.

Resurrected from CCE v1/v2's QC Protocol (dropped in v5's layout
compaction -- `docs/workbook-defect-review.md` row C5: "Compressibility-
monotonicity and rho*V-constancy checks existed in v1/v2, dropped in v5's
layout compaction. QC Protocol rows 42-87 in v2."). Physically, as
pressure falls toward the bubble point in a single-phase liquid, the
instantaneous isothermal compressibility of the fluid should not DECREASE
-- gas coming out of solution as P approaches Psat makes the fluid
progressively more compressible. A decrease flags either a bad data point
or a fluid/lab issue worth a second look.

Threshold: `"cce_monotonic_violations" = (0.0, 1.0)`, graded on the COUNT
of violating consecutive pairs (not a percent deviation) -- 0 violations
PASS, exactly 1 REVIEW, 2 or more FAIL. This is an engineering-judgment
proposal (like `rho_v_constancy`'s threshold), pending Swej calibration:
the resurrected v1/v2 sheet flagged violations visually, with no numeric
count-based gate of its own.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID = "cce_monotonic_violations"


@dataclass(frozen=True)
class MonotonicViolation:
    """One consecutive pair of (P, instantaneous compressibility) points
    where compressibility decreased as pressure fell."""

    p_prev: float
    c_prev: float
    p_next: float
    c_next: float


@dataclass(frozen=True)
class MonotonicResult:
    """Monotonicity scan over a CCE stage table's above-Psat entries."""

    violations: list[MonotonicViolation]
    """Every consecutive (surviving) pair where compressibility fell,
    in the order encountered."""

    qc: QCResult
    """Graded result (`value` = violation count)."""


def check(
    stages: Sequence[tuple[float, float | None]],
    registry: ThresholdRegistry | None = None,
) -> MonotonicResult:
    """Check that instantaneous compressibility is non-decreasing as
    pressure falls, over a CCE stage table's above-Psat entries.

    Args:
        stages: (P, instantaneous compressibility) pairs, IN THE SAME
            ORDER as the source stage table (i.e. descending P, matching
            `pvt.experiments.cce.calc.calculate`'s stage order). A `None`
            compressibility (below Psat, the bubble row, or the first
            stage -- see `pvt.experiments.cce.calc`'s module docstring)
            is skipped; monotonicity is checked only between consecutive
            SURVIVING (non-`None`) entries, in the order given -- callers
            do not need to pre-filter or pre-sort, and may pass the full
            stage table as-is.
        registry: supplies "cce_monotonic_violations" (review count, fail
            count); defaults to (0.0, 1.0) -- 0 violations PASS, 1
            REVIEW, >1 FAIL.

    Returns:
        MonotonicResult listing every violating consecutive pair and the
        graded QCResult.
    """
    registry = registry or ThresholdRegistry()

    valid = [(p, c) for p, c in stages if c is not None]

    violations: list[MonotonicViolation] = []
    for (p_prev, c_prev), (p_next, c_next) in zip(valid, valid[1:]):
        if c_next < c_prev:
            violations.append(
                MonotonicViolation(p_prev=p_prev, c_prev=c_prev, p_next=p_next, c_next=c_next)
            )

    count = len(violations)
    review_at, fail_at = registry.get(_CHECK_ID)
    severity = grade(float(count), review_at, fail_at)
    qc = QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=float(count),
        threshold=f"review >{review_at} violation(s) / fail >{fail_at} violation(s)",
        message=(
            f"instantaneous compressibility monotonicity: {count} "
            f"violation(s) over {len(valid)} above-Psat points ({severity.value})"
        ),
    )
    return MonotonicResult(violations=violations, qc=qc)
