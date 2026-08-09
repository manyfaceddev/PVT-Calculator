"""
pvt/qc/checks/mw_consistency.py — QC check: molecular weight consistency
between the mol- and wt-derived stream MW.

A composition stream carrying both a mol% and a wt% basis implies two
independent routes to the mixture molecular weight (`mw_from_mol()` and
`mw_from_wt()`); they should agree closely when the two bases were derived
consistently. This check grades `CompositionStream.mw_consistency_pct()`
against the "mw_consistency_pct" threshold band.
"""

from __future__ import annotations

from pvt.core.composition import CompositionStream
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID = "mw_consistency_pct"


def check(stream: CompositionStream, registry: ThresholdRegistry | None = None) -> QCResult:
    """Grade a composition stream's mol-vs-wt MW consistency.

    Args:
        stream: Composition stream carrying both a mol% and a wt% basis.
        registry: ThresholdRegistry supplying the "mw_consistency_pct"
            (review%, fail%) band; defaults to house thresholds (5.0/10.0).

    Returns:
        QCResult graded on `stream.mw_consistency_pct()`
        (`(mw_from_mol - mw_from_wt) / mw_from_wt * 100`).
    """
    registry = registry or ThresholdRegistry()

    pct = stream.mw_consistency_pct()

    review_at, fail_at = registry.get(_CHECK_ID)
    severity = grade(pct, review_at, fail_at)
    return QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=pct,
        threshold=f"review >{review_at}% / fail >{fail_at}%",
        message=(
            f"MW consistency (mol vs wt) deviates {pct:+.4f}% ({severity.value})"
        ),
    )
