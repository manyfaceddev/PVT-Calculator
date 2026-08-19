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

    "hoffman_r2" is one exception: its (0.98, 0.95) pair is an R²-floor
    threshold (see `pvt.qc.checks.hoffman_crump`'s module docstring for the
    review/fail semantics and the deviation conversion its check performs).
    Unlike the other entries, it is not transcribed from an ADRIC house
    convention -- the source PVT-check sheets show the Hoffman-Crump
    crossplot visually, with no numeric R² gate of their own -- so this
    default is proposed by engineering judgment, configurable via
    `override`, pending Swej calibration.

    "cce_sp_fit_dev_pct" (0.05, 0.10) and "cce_tp_fit_dev_pct" (1.0, 2.0)
    ARE ported verbatim from a real house convention: the CCE v5 fixture's
    own `QC Protocol!C26:C29` cells (see
    `pvt.qc.checks.polynomial_fit`'s module docstring), not a proposal.

    "cce_monotonic_violations" (0.0, 1.0 -- a violation COUNT, not a
    percent) and "cce_rho_v_spread_pct" (0.5, 1.0) grade checks
    RESURRECTED from CCE v1/v2 (dropped in v5's layout compaction, see
    `docs/workbook-defect-review.md` row C5). Neither had a numeric gate
    even when present in v1/v2 -- these bands are engineering-judgment
    proposals, configurable via `override`, pending Swej calibration (see
    `pvt.qc.checks.monotonic_compressibility` / `rho_v_constancy` module
    docstrings).

    "psat_breakpoint_vs_visual_psi" (10.0, 25.0) grades a NEW check (Phase
    3a Task 4, dissected from `Bubble_Dew_Point_QC_Tool_Final.xlsx`, see
    `pvt.qc.checks.psat_breakpoint`'s module docstring): its review edge
    (10.0 psi) matches the existing house Psat-consistency convention
    already hard-coded in `pvt.experiments.cce.calc.calculate`
    (`psat_consistency_ok`'s <=10 psi gate); the 25.0 psi fail edge has no
    existing house precedent and is this key's own engineering-judgment
    proposal, pending Swej calibration.
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
        "hoffman_r2": (0.98, 0.95),
        "cce_sp_fit_dev_pct": (0.05, 0.10),
        "cce_tp_fit_dev_pct": (1.0, 2.0),
        "cce_monotonic_violations": (0.0, 1.0),
        "cce_rho_v_spread_pct": (0.5, 1.0),
        "psat_breakpoint_vs_visual_psi": (10.0, 25.0),
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
