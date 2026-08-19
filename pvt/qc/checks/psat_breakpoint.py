"""
pvt/qc/checks/psat_breakpoint.py -- QC check: Psat (bubble/dew point)
breakpoint estimate by two-segment trend intersection.

NEW capability, dissected in-task from the fixture workbook `tests/fixtures/
workbooks/Bubble_Dew_Point_QC_Tool_Final.xlsx` (single sheet
"BP_DP_QC_Final", confirmed by loading with openpyxl in both
`data_only=False` and `data_only=True` modes).

Method: a P-vs-QC-value series (QC value can be Relative Volume for black/
volatile oil, or Liquid Dropout / an optical QC signal for condensate --
sheet cell E13 "QC Value (Y)", generic on purpose) is split into an
ABOVE-Psat segment and a BELOW-Psat segment; each segment is fit
independently by ordinary least squares (a straight line, not a
polynomial); the two fitted lines' intersection is the breakpoint pressure
estimate.

Complete cell map (rows 4-10 = setup/results, rows 13-25 = data entry,
columns O/P = the actual least-squares/intersection formulas; all formulas
read with `data_only=False`, cached values with `data_only=True`):

    D5/D6/D7   = Client / Well-Reservoir / Sample ID (metadata, unused here)
    D8/D9      = Fluid Type / Test Type (metadata, unused here)
    D10        = Reservoir Temp (F) (metadata, unused here; column D of the
                 data table is `=$D$10` for every row -- not consumed by
                 the fit)
    K5         = Mode ("Bubble Point" / "Dew Point", metadata)
    K6         = "Above points used" -- COUNT of rows (by row-index order,
                 NOT a pressure threshold) assigned to the above-Psat
                 segment; e.g. K6=6 means data-table rows 1-6 (A14:A19)
    K7         = "Below points used" -- COUNT of rows assigned to the
                 below-Psat segment, immediately following the above block
                 (rows K6+1 .. K6+K7)
    K8         = `=P8` (display alias for the breakpoint pressure)
    K9         = `=P9` (display alias for the QC value at the breakpoint)
    K10        = QC Verdict:
                 `=IF(OR(COUNT(C14:C25)<4,COUNT(E14:E25)<4),"Need data",
                    IF(ABS(P4-P6)<0.000001,"Review slopes","OK"))`
    P4         = Above slope m1, via SUMPRODUCT least squares (see below)
    P5         = Above intercept b1
    P6         = Below slope m2
    P7         = Below intercept b2
    P8         = Estimated breakpoint pressure:
                 `=IFERROR((P7-P5)/(P4-P6),"")`
    P9         = QC value at the breakpoint: `=IFERROR(P4*P8+P5,"")`
    P10        = QC note:
                 `=IF(OR($K$6<2,$K$7<2),"Need >=2 points in each region",
                    IF(ABS(P4-P6)<0.000000001,"Parallel trends - review
                    points","Intersection calculated"))`
    Data table (rows 14-25, one row per candidate point, up to 12 rows):
        A = # (1-based row index within the table)
        B = Use (1/0 -- 0 excludes the row from every fit/region formula)
        C = Pressure (psig)
        D = Temperature (F) (`=$D$10`, unused by the fit)
        E = QC Value (Y)
        F = Region label: `=IF(A<=$K$6,"Above Point",
            IF(A<=$K$6+$K$7,"Below Point",""))` -- NOTE this label uses
            the raw row index A, NOT the `B` Use flag, so a row can be
            LABELED "Above Point" while excluded from the actual fit (Use=0)
        G = X*Y helper column: `=IF(B=1,C*E,"")`
        H = X^2 helper column: `=IF(B=1,C^2,"")`
        I/J = Above-Fit / Below-Fit fitted-Y columns (chart helpers, not
            consumed by P4:P9)
        K/L = "BP X"/"BP Y" -- P8/P9 repeated only on row 14, `NA()`
            elsewhere (chart marker helpers)

    The above/below slope-intercept formulas (P4:P7) are SUMPRODUCT-based
    ordinary least squares over the masked region, e.g. P4 (above slope):

        m1 = (SUM(mask*X*Y) - SUM(mask*X)*SUM(mask*Y)/n) /
             (SUM(mask*X^2) - SUM(mask*X)^2/n)

    where `mask = (B=1)*(A<=K6)`. This is algebraically IDENTICAL to the
    standard mean-centered form used below: with `x_bar = SUM(mask*X)/n`,
    `SUM(mask*X*Y) - SUM(mask*X)*SUM(mask*Y)/n == SUM(mask*(X-x_bar)*
    (Y-y_bar))` (`Sxy`) and `SUM(mask*X^2) - SUM(mask*X)^2/n ==
    SUM(mask*(X-x_bar)^2)` (`Sxx`), so `m1 = Sxy/Sxx` -- the textbook OLS
    slope. `P5` (`=(SUM(mask*Y) - m1*SUM(mask*X))/n`) is likewise
    `y_bar - m1*x_bar`, the textbook OLS intercept. `_fit_line` below
    implements the `Sxy/Sxx` form directly (mirrors `hoffman_crump.
    _fit_least_squares`'s pattern) rather than importing `polynomial_fit`'s
    degree-N Gaussian-elimination machinery -- a straight line needs no
    matrix solve, and the task brief calls for "simple linear regression
    here, no polynomial."

    `P8 = (P7-P5)/(P4-P6)` (`IFERROR(...,"")`-wrapped) is the two-line
    intersection formula `p* = (b_below - b_above)/(m_above - m_below)`
    this module's `psat_estimate` reproduces (golden-verified against the
    fixture's own cached P4:P8 in `tests/golden/test_psat_breakpoint.py`,
    rel=1e-9).

Split semantics (confirmed by dissection, see the module docstring's cell
map above): the sheet does NOT compare a row's own pressure against a
split-pressure cell -- there is no such cell. It counts the first `K6` rows
(by table row order) as "above" and the next `K7` rows as "below" (`F`
column's `A<=$K$6` test). This module's public contract is a genuine
pressure-THRESHOLD split (`p >= split_at` above, `p < split_at` below, per
the task brief) -- order-independent and robust regardless of how the
caller assembled `points`. Given the fixture's own data IS entered in
strict descending-pressure order (matching its "Enter N points above and N
points below the expected breakpoint" instructions, cell L28), a
pressure-threshold split placed between the fixture's last above-row and
first below-row reproduces the EXACT SAME partition the sheet's row-count
split produces -- verified in the golden test, which derives `split_at`
generically from the sheet's own `K6` rather than hand-typing a pressure.
See `docs/excel-deviations.md` D-022 and `docs/workbook-defect-review.md`
row BD1 for the sheet's row-order convention and why this module
deliberately does NOT copy it (no validation exists in the sheet that the
"above" block's pressures actually exceed the "below" block's -- a
data-entry ordering mistake would silently corrupt the fit there with no
error surfaced; a threshold split cannot suffer that failure mode).

Parallel-trend guard: the sheet computes TWO different, mutually
inconsistent absolute thresholds for "are the two trends too parallel to
trust the intersection" -- `P10`'s note uses `ABS(P4-P6)<0.000000001`
(1e-9) while `K10`'s verdict uses `ABS(P4-P6)<0.000001` (1e-6), three
orders of magnitude apart (`docs/workbook-defect-review.md` row BD3). For
a slope difference landing between those two values (very plausible --
this fixture's own slopes are ~1e-5), the sheet would show `K10`="OK" and
`P10`="Parallel trends - review points" side by side, a contradictory
verdict/note pair. Neither threshold is scale-invariant (an absolute slope
tolerance means something different for a Y-axis in relative-volume units
around 1.0 versus, say, liquid-dropout percent around 50), so this module
uses the RELATIVE criterion specified by the task brief instead of
resurrecting either sheet constant: `parallel_warning` is True when
`|m_above - m_below| < 1e-3 * max(|m_above|, |m_below|)` (or when both
slopes are exactly zero, a degenerate case the relative form can't express
since its own scale is zero) -- see `docs/excel-deviations.md` D-023. When
`parallel_warning` is True, `qc.severity` is forced to REVIEW with an
ill-conditioned message REGARDLESS of `visual_psat` distance (per the task
brief) -- including the exactly-parallel edge case, where the intersection
formula's denominator is exactly zero and `psat_estimate` is `math.nan`
(the sheet's own `IFERROR(...,"")` blanks the cell to an empty string in
this case; this module uses a numeric `nan` sentinel instead so downstream
numeric code never needs to special-case a blank/string value).

Registry: `"psat_breakpoint_vs_visual_psi" = (10.0, 25.0)` -- PROPOSAL
status, flagged pending Swej calibration. The review-band edge (10.0 psi)
is not arbitrary: it matches the house 10-psi Psat-consistency convention
already hard-coded in `pvt.experiments.cce.calc.calculate`
(`psat_consistency_ok = abs(inputs.psat_visual - psat_from_data) <= 10.0`)
-- this key EXTENDS that existing pass/fail gate into a three-band
PASS/REVIEW/FAIL grade by adding a 25-psi fail edge, which has no existing
house precedent and is this module's own engineering-judgment proposal.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from pvt.core.exceptions import InputValidationError
from pvt.qc.engine import QCResult, Severity, ThresholdRegistry, grade

_CHECK_ID = "psat_breakpoint_vs_visual_psi"

_PARALLEL_REL_TOL = 1e-3
"""Relative parallel-trend guard: `parallel_warning` fires when
`|m_above - m_below| < _PARALLEL_REL_TOL * max(|m_above|, |m_below|)`. Per
the task brief; see the module docstring for why this replaces the sheet's
own two mutually-inconsistent absolute thresholds."""


@dataclass(frozen=True)
class BreakpointResult:
    """Two-segment trend-intersection Psat/Pdew breakpoint estimate, plus
    its graded QCResult."""

    psat_estimate: float
    """Intersection pressure of the above/below fitted lines,
    `(intercept_below - intercept_above) / (slope_above - slope_below)`.
    `math.nan` when the two segments are exactly parallel (slopes
    identical -- the intersection is undefined; `parallel_warning` is
    always True in that case, see the module docstring)."""

    slope_above: float
    """Above-split (`p >= split_at`) least-squares fit slope."""

    slope_below: float
    """Below-split (`p < split_at`) least-squares fit slope."""

    intercept_above: float
    """Above-split least-squares fit intercept."""

    intercept_below: float
    """Below-split least-squares fit intercept."""

    parallel_warning: bool
    """True when the two segments' slopes are near-parallel (or exactly
    parallel), per `_PARALLEL_REL_TOL` -- the breakpoint is ill-
    conditioned and `qc.severity` is forced to REVIEW regardless of
    `visual_psat` distance."""

    qc: QCResult
    """Graded result, `check_id="psat_breakpoint_vs_visual_psi"`."""


def check(
    points: Sequence[tuple[float, float]],
    split_at: float,
    visual_psat: float | None = None,
    registry: ThresholdRegistry | None = None,
) -> BreakpointResult:
    """Fit above/below trend lines and estimate the Psat/Pdew breakpoint
    by their intersection.

    Args:
        points: (pressure, QC value) pairs spanning both sides of the
            breakpoint -- QC value can be relative volume, liquid
            dropout%, or any other QC signal that trends linearly on each
            side of the breakpoint (sheet column E, "QC Value (Y)").
        split_at: Pressure threshold splitting `points` into the above
            segment (`p >= split_at`) and below segment (`p < split_at`)
            -- see the module docstring's "Split semantics" note for how
            this differs from (and is more robust than) the dissected
            sheet's own row-order split.
        visual_psat: Independently observed (visual) Psat/Pdew, if
            available. When given (and the segments are not near-
            parallel), `qc.severity` grades `|psat_estimate - visual_psat|`
            against the "psat_breakpoint_vs_visual_psi" registry band.
            When `None`, `qc.severity` is trivially PASS
            ("no visual Psat provided; estimate only").
        registry: supplies "psat_breakpoint_vs_visual_psi" (review psi,
            fail psi); defaults to (10.0, 25.0) -- see the module
            docstring for its house-convention lineage.

    Returns:
        BreakpointResult; see its field docstrings and the module
        docstring for the parallel-trend guard's REVIEW override.

    Raises:
        InputValidationError: fewer than 2 points in either the above or
            below segment, or a segment's points all share the same
            pressure (degenerate fit, slope undefined).
    """
    registry = registry or ThresholdRegistry()

    above = [(p, y) for p, y in points if p >= split_at]
    below = [(p, y) for p, y in points if p < split_at]

    slope_above, intercept_above = _fit_line(above, "above-split (p >= split_at) segment")
    slope_below, intercept_below = _fit_line(below, "below-split (p < split_at) segment")

    scale = max(abs(slope_above), abs(slope_below))
    slope_diff = abs(slope_above - slope_below)
    parallel_warning = scale == 0.0 or slope_diff < _PARALLEL_REL_TOL * scale

    denom = slope_above - slope_below

    if parallel_warning:
        psat_estimate = (intercept_below - intercept_above) / denom if denom != 0.0 else math.nan
        severity = Severity.REVIEW
        value = slope_diff
        threshold = (
            f"review: |slope_above - slope_below| < {_PARALLEL_REL_TOL}*"
            "max(|slope_above|,|slope_below|) (parallel-trend guard)"
        )
        message = (
            f"above/below trends are near-parallel or parallel "
            f"(|slope diff|={slope_diff:.6g}, guard tolerance="
            f"{_PARALLEL_REL_TOL * scale:.6g}); breakpoint is ill-conditioned "
            f"(REVIEW), regardless of visual-Psat distance"
        )
    else:
        psat_estimate = (intercept_below - intercept_above) / denom
        if visual_psat is None:
            severity = Severity.PASS
            value = None
            threshold = "n/a (no visual Psat supplied)"
            message = "no visual Psat provided; estimate only"
        else:
            value = abs(psat_estimate - visual_psat)
            review_at, fail_at = registry.get(_CHECK_ID)
            severity = grade(value, review_at, fail_at)
            threshold = f"review >{review_at} psi / fail >{fail_at} psi"
            message = (
                f"breakpoint estimate {psat_estimate:.4f} psi vs visual Psat "
                f"{visual_psat:.4f} psi: |delta|={value:.4f} psi ({severity.value})"
            )

    qc = QCResult(
        check_id=_CHECK_ID,
        severity=severity,
        value=value,
        threshold=threshold,
        message=message,
    )
    return BreakpointResult(
        psat_estimate=psat_estimate,
        slope_above=slope_above,
        slope_below=slope_below,
        intercept_above=intercept_above,
        intercept_below=intercept_below,
        parallel_warning=parallel_warning,
        qc=qc,
    )


def _fit_line(points: Sequence[tuple[float, float]], label: str) -> tuple[float, float]:
    """Ordinary least-squares fit of a straight line (y vs x) through
    `points`. Mirrors `hoffman_crump._fit_least_squares`'s pattern
    (mean-centered `Sxy/Sxx` form -- see the module docstring for its
    algebraic equivalence to the dissected sheet's SUMPRODUCT formulas).

    Returns:
        (slope, intercept).

    Raises:
        InputValidationError: fewer than 2 points, or all points share the
            same x (pressure) -- `Sxx` would be zero, the slope's
            denominator.
    """
    n = len(points)
    if n < 2:
        raise InputValidationError([f"psat breakpoint: {label} needs at least 2 points (found {n})"])

    xs = [p for p, _ in points]
    ys = [v for _, v in points]
    x_bar = sum(xs) / n
    y_bar = sum(ys) / n

    ss_xy = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    ss_xx = sum((x - x_bar) ** 2 for x in xs)
    if ss_xx == 0:
        raise InputValidationError(
            [f"psat breakpoint: {label} -- all pressures are identical ({xs[0]}), cannot compute a slope"]
        )

    slope = ss_xy / ss_xx
    intercept = y_bar - slope * x_bar
    return slope, intercept
