"""
pvt/qc/checks/polynomial_fit.py -- QC check: CCE polynomial-fit deviation,
single-phase (relative volume vs pressure) and two-phase (Y-function vs
pressure).

Dissected from the fixture workbook (`tests/fixtures/workbooks/
2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`, sheet "QC Protocol"):

    Section A "SINGLE-PHASE RELATIVE VOLUME FIT" (B4:C13): a 3rd-order
    polynomial `RelVol = a0 + a1*P + a2*P^2 + a3*P^3` fit against
    `CCE Calculation!D16:D35` (relative volume, steps 1-20, at/above
    Psat); max/mean deviation-% (col K) grades each row against
    `QC Protocol!C26/C27`.
    Section B "TWO-PHASE Y-FUNCTION FIT" (B15:C23): a 2nd-order polynomial
    `Y = b0 + b1*P + b2*P^2` fit against `CCE Calculation!G36:G55`
    (Y-function, steps 21-40, below Psat); graded against `C28/C29`.
    Section C "QC THRESHOLDS" (C26:C29): SP PASS/WARN = 0.05% / 0.1%, TP
    PASS/WARN = 1% / 2% -- ported VERBATIM as this module's registry
    defaults ("cce_sp_fit_dev_pct", "cce_tp_fit_dev_pct"); these are an
    actual house convention read off the sheet, not an engineering-
    judgment proposal (contrast `monotonic_compressibility`/
    `rho_v_constancy`'s thresholds).

    Cell `C43` labels the sheet's a0..a3/b0..b2 coefficients "optional
    manual tuning inputs. Normal routine use does not require changing
    them" -- i.e. these are TYPED, STATIC constants shared by every
    sample that ever loads this template, not re-fit per dataset (ledger
    row D-021, `docs/excel-deviations.md`): `check_single_phase`/
    `check_two_phase` below instead compute a fresh ordinary-least-
    squares fit for the exact dataset passed in, on every call. The
    sheet's own K/L-column deviation grades against ITS fixed
    coefficients, so the two are not a like-for-like residual comparison
    -- the engine's own per-dataset fit is, by construction of least
    squares, never worse (and usually meaningfully better) than a fixed
    historical coefficient set re-applied to a new sample.

Numerical care: the design matrix is built from CENTERED/SCALED pressure,
`p' = (p - mean(p)) / std(p)`, before forming the normal equations
`(X^T X) c = X^T y`. Raw psia magnitudes (hundreds to thousands) raised to
the 3rd power in an UN-scaled Vandermonde column span many orders of
magnitude (e.g. 7000 vs 7000**3 = 3.43e11), which conditions the normal-
equations matrix extremely poorly; centering/scaling keeps every column
of comparable magnitude, which is standard least-squares practice and is
what keeps the pure-Python Gaussian-elimination solve below well-behaved
at degree 3 over the fixture's ~1200-7000 psia range (see
`test_check_single_phase_realistic_psia_range_does_not_blow_up` and the
exact-polynomial-reconstruction tests in
`tests/unit/qc/test_cce_checks.py`, which would lose precision well
short of their rel=1e-9 tolerance if conditioning were poor).
`FitResult.coeffs` are therefore in the SCALED basis (evaluate as
`sum(c_k * p'**k for k in range(degree+1))` with `p' = (p - p_mean) /
p_std`); `FitResult.p_mean`/`p_std` carry the scaling parameters, and
`FitResult.fitted` already carries the fitted values back-transformed to
original units so callers never need to redo the scaling themselves.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass

from pvt.core.exceptions import InputValidationError
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_CHECK_ID_SINGLE_PHASE = "cce_sp_fit_dev_pct"
_CHECK_ID_TWO_PHASE = "cce_tp_fit_dev_pct"

_SINGULAR_PIVOT_TOL = 1e-12


@dataclass(frozen=True)
class FitResult:
    """Least-squares polynomial fit of a CCE QC curve (relative volume or
    Y-function) against pressure, plus its graded max-deviation QCResult."""

    coeffs: tuple[float, ...]
    """Fit coefficients c0..c_degree, LOW-to-high degree, in the SCALED
    pressure basis `p' = (p - p_mean) / p_std` -- see the module
    docstring. Evaluate as `sum(c_k * p'**k for k in range(degree+1))`."""

    fitted: tuple[float, ...]
    """Fitted y-values, back-transformed to original units, one per input
    point, in the same order as the input `points`."""

    max_dev_pct: float
    """`max(|fitted_i - actual_i| / |actual_i|) * 100` across all points
    -- the quantity graded against the registry threshold."""

    mean_dev_pct: float
    """`mean(|fitted_i - actual_i| / |actual_i|) * 100` across all
    points."""

    qc: QCResult
    """Graded result (`value` = `max_dev_pct`)."""

    p_mean: float
    """Scaling parameter: mean of the input pressures (see `coeffs`)."""

    p_std: float
    """Scaling parameter: population std-dev of the input pressures (see
    `coeffs`)."""


def check_single_phase(
    points: Sequence[tuple[float, float]],
    degree: int = 3,
    registry: ThresholdRegistry | None = None,
) -> FitResult:
    """Fit + grade the single-phase relative-volume-vs-pressure curve.

    Args:
        points: (P, relative volume) pairs, one per at/above-Psat CCE
            stage (sheet `CCE Calculation!B16:D35`-equivalent).
        degree: Polynomial degree (sheet default: 3rd order).
        registry: supplies "cce_sp_fit_dev_pct" (review%, fail%); defaults
            to the sheet's own `QC Protocol!C26:C27` = (0.05, 0.10).

    Returns:
        FitResult; `qc.severity` graded on `max_dev_pct`.

    Raises:
        InputValidationError: fewer than `degree + 1` points, all
            pressures identical, fewer distinct pressures than
            `degree + 1` (degenerate/singular fit), or an actual value of
            exactly zero (percent deviation undefined).
    """
    return _fit_and_grade(points, degree, _CHECK_ID_SINGLE_PHASE, "single-phase RV", registry)


def check_two_phase(
    points: Sequence[tuple[float, float]],
    degree: int = 2,
    registry: ThresholdRegistry | None = None,
) -> FitResult:
    """Fit + grade the two-phase Y-function-vs-pressure curve.

    Args:
        points: (P, Y-function) pairs, one per below-Psat CCE stage
            (sheet `CCE Calculation!B36:G55`-equivalent).
        degree: Polynomial degree (sheet default: 2nd order).
        registry: supplies "cce_tp_fit_dev_pct" (review%, fail%); defaults
            to the sheet's own `QC Protocol!C28:C29` = (1.0, 2.0).

    Returns:
        FitResult; `qc.severity` graded on `max_dev_pct`.

    Raises:
        InputValidationError: same conditions as `check_single_phase`.
    """
    return _fit_and_grade(points, degree, _CHECK_ID_TWO_PHASE, "two-phase Y-function", registry)


def _fit_and_grade(
    points: Sequence[tuple[float, float]],
    degree: int,
    check_id: str,
    label: str,
    registry: ThresholdRegistry | None,
) -> FitResult:
    registry = registry or ThresholdRegistry()
    n = len(points)
    n_coeffs = degree + 1
    if n < n_coeffs:
        raise InputValidationError(
            [
                f"{label} fit needs at least {n_coeffs} points for a "
                f"degree-{degree} polynomial (found {n})"
            ]
        )

    xs = [p for p, _ in points]
    ys = [v for _, v in points]

    p_mean = statistics.fmean(xs)
    p_std = statistics.pstdev(xs)
    if p_std == 0:
        raise InputValidationError(
            [f"{label} fit: all pressures are identical ({xs[0]}), cannot scale for fitting"]
        )

    xs_scaled = [(x - p_mean) / p_std for x in xs]
    design_rows = [[x**k for k in range(n_coeffs)] for x in xs_scaled]

    # Normal equations: (X^T X) c = X^T y.
    ata = [
        [sum(design_rows[i][r] * design_rows[i][c] for i in range(n)) for c in range(n_coeffs)]
        for r in range(n_coeffs)
    ]
    aty = [sum(design_rows[i][r] * ys[i] for i in range(n)) for r in range(n_coeffs)]

    coeffs = tuple(_solve_linear_system(ata, aty, label))

    fitted = tuple(sum(coeffs[k] * x**k for k in range(n_coeffs)) for x in xs_scaled)

    deviations_pct = []
    for actual, fit in zip(ys, fitted):
        if actual == 0:
            raise InputValidationError(
                [f"{label} fit: an actual value is exactly zero, cannot express deviation as a percent"]
            )
        deviations_pct.append(abs(fit - actual) / abs(actual) * 100.0)

    max_dev_pct = max(deviations_pct)
    mean_dev_pct = statistics.fmean(deviations_pct)

    review_at, fail_at = registry.get(check_id)
    severity = grade(max_dev_pct, review_at, fail_at)
    qc = QCResult(
        check_id=check_id,
        severity=severity,
        value=max_dev_pct,
        threshold=f"review >{review_at}% / fail >{fail_at}%",
        message=(
            f"{label} degree-{degree} fit over {n} points: "
            f"max |dev|={max_dev_pct:.4f}%, mean |dev|={mean_dev_pct:.4f}% "
            f"({severity.value})"
        ),
    )
    return FitResult(
        coeffs=coeffs,
        fitted=fitted,
        max_dev_pct=max_dev_pct,
        mean_dev_pct=mean_dev_pct,
        qc=qc,
        p_mean=p_mean,
        p_std=p_std,
    )


def _solve_linear_system(a: list[list[float]], b: list[float], label: str) -> list[float]:
    """Solve `a @ x = b` via Gaussian elimination with partial pivoting
    (pure Python, no numpy/scipy). `a`/`b` are never mutated -- an
    augmented working copy is built internally.

    Raises:
        InputValidationError: `a` is singular (or numerically so) --
            i.e. fewer distinct x-values than coefficients, which makes
            the normal-equations matrix rank-deficient.
    """
    n = len(b)
    aug = [row[:] + [b[i]] for i, row in enumerate(a)]

    for col in range(n):
        pivot_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot_row][col]) < _SINGULAR_PIVOT_TOL:
            raise InputValidationError(
                [
                    f"{label} fit: degenerate/singular normal-equations system "
                    "(likely fewer distinct pressures than fit coefficients)"
                ]
            )
        aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pivot
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]

    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n] - sum(aug[i][j] * x[j] for j in range(i + 1, n))
        x[i] = s / aug[i][i]
    return x
