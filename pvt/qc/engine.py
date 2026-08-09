"""
pvt/qc/engine.py — QC severity engine.

Shared vocabulary for every check module under pvt.qc.checks (Phase 2):
grade a numeric deviation against a two-band threshold (review / fail),
carry the result in a typed QCResult, and roll many results up to the
worst severity for a study-level verdict.
"""

from __future__ import annotations

import enum
from collections.abc import Iterable
from dataclasses import dataclass


class Severity(enum.StrEnum):
    """QC verdict for a single check, ordered best to worst: PASS < REVIEW < FAIL."""

    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"


_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.PASS: 0,
    Severity.REVIEW: 1,
    Severity.FAIL: 2,
}


@dataclass(frozen=True)
class QCResult:
    """Outcome of a single QC check."""

    check_id: str
    severity: Severity
    value: float | None
    threshold: str
    message: str


def grade(value: float, review_at: float, fail_at: float, *, absolute: bool = True) -> Severity:
    """
    Grade a value against a two-band threshold.

    |value| (or value itself when absolute=False) <= review_at -> PASS;
    <= fail_at -> REVIEW; otherwise -> FAIL. Band edges are inclusive downward,
    so a value exactly at fail_at grades REVIEW, not FAIL.
    """
    graded = abs(value) if absolute else value
    if graded <= review_at:
        return Severity.PASS
    if graded <= fail_at:
        return Severity.REVIEW
    return Severity.FAIL


def worst(results: Iterable[QCResult]) -> Severity:
    """Return the worst (highest-severity) result, or PASS if results is empty."""
    worst_severity = Severity.PASS
    for result in results:
        if _SEVERITY_ORDER[result.severity] > _SEVERITY_ORDER[worst_severity]:
            worst_severity = result.severity
    return worst_severity


class ThresholdRegistry:
    """
    Per-check (review_at, fail_at) threshold pairs.

    Defaults come from the ADRIC house conventions; any threshold may be
    overridden per study, and every override is recorded in `.audit` with
    the caller-supplied note so the QC report can explain why a study's
    bands differ from house defaults.
    """

    DEFAULTS: dict[str, tuple[float, float]] = {
        "composition_sum": (0.5, 2.0),
        "mass_balance_pct": (2.0, 3.0),
        "molar_balance_pct": (2.0, 3.0),
        "z_deviation_pct": (2.0, 5.0),
        "density_rsd_pct": (0.5, 1.0),
        "viscosity_vs_sim_pct": (2.0, 5.0),
        "mmp_mass_balance_pct": (5.0, 5.0),
        "gor_actual_vs_target_pct": (5.0, 10.0),
        "mw_consistency_pct": (5.0, 10.0),
    }

    def __init__(self) -> None:
        self._thresholds: dict[str, tuple[float, float]] = dict(self.DEFAULTS)
        self.audit: list[str] = []

    def get(self, check_id: str) -> tuple[float, float]:
        """Return the (review_at, fail_at) threshold pair for check_id."""
        return self._thresholds[check_id]

    def override(self, check_id: str, review_at: float, fail_at: float, note: str) -> None:
        """Replace a check's threshold pair and record the change with its note."""
        self._thresholds[check_id] = (review_at, fail_at)
        self.audit.append(
            f"{check_id}: threshold overridden to ({review_at}, {fail_at}) — {note}"
        )
