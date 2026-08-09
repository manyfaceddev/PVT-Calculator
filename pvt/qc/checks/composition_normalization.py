"""
pvt/qc/checks/composition_normalization.py — QC check: composition raw-sum
normalization deviation.

Lab compositions (mol% or wt%) are expected to sum to 100 before use; small
deviations come from analytical rounding, larger ones flag a transcription
or unit error. This check grades |raw_sum - 100| against the
"composition_sum" threshold band.
"""

from __future__ import annotations

from typing import Literal

from pvt.core.composition import CompositionStream
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID = "composition_sum"


def check(
    stream: CompositionStream,
    basis: Literal["mol", "wt"],
    registry: ThresholdRegistry | None = None,
) -> QCResult:
    """Grade a composition stream's raw-sum deviation from 100.

    Args:
        stream: The composition to check.
        basis: Which raw basis to sum -- "mol" uses `stream.raw_mol_sum()`,
            "wt" uses `stream.raw_wt_sum()`.
        registry: ThresholdRegistry supplying the "composition_sum"
            (review%, fail%) band; defaults to house thresholds (0.5/2.0).

    Returns:
        QCResult graded on the signed deviation `raw_sum - 100.0` (its
        magnitude is what `grade()` bands against; the sign is preserved in
        `value`/`message` so a report can tell over- from under-normalized).
    """
    registry = registry or ThresholdRegistry()

    raw_sum = stream.raw_mol_sum() if basis == "mol" else stream.raw_wt_sum()
    deviation = raw_sum - 100.0

    review_at, fail_at = registry.get(_CHECK_ID)
    severity = grade(deviation, review_at, fail_at)
    return QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=deviation,
        threshold=f"review >{review_at} / fail >{fail_at}",
        message=(
            f"{basis}% raw sum {raw_sum:.4f} deviates {deviation:+.4f} from "
            f"100 ({severity.value})"
        ),
    )
