"""
pvt/experiments/recombination/compressibility.py — Oil isothermal
compressibility evaluation for the recombination oil-charging-volume
calculation (`pvt.experiments.recombination.calc.calculate_multistage`'s
`c_o` parameter).

Field units only (1/psia basis). Recovered from the pre-Task-10
`ui/recombination.py`'s `_compute_compressibility` (deleted in Task 10 along
with the rest of that module; see `git show 1a0c863:ui/recombination.py`,
lines ~414-449) and reimplemented here as a pure `pvt/` calculation with no
UI dependency.

That original function additionally converted SI-basis (1/bara, 1/bara²,
...) coefficients to field units before evaluating the polynomial. This
module deliberately does NOT do that conversion: which unit system the
operator typed their numbers in is a UI/CLI-boundary concern, not a property
of the compressibility model itself -- `calculate_multistage`'s own `c_o`
parameter is likewise always consumed as a plain 1/psia (or, historically,
whatever-basis-the-caller-already-converted-to) value with no conversion of
its own (see its `c_o_psia` line). A caller collecting inputs in SI units
must convert `value_or_coeffs` to a 1/psia^n basis (multiply the n-th
coefficient, 0-indexed, by `PSIA_PER_BARA ** (n + 1)`) and `p_ref_psia` to
psia *before* calling `effective_c_o` -- closing the old UI-leak the brief
calls out.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pvt.core.exceptions import InputValidationError


def effective_c_o(
    model: Literal["constant", "polynomial"],
    value_or_coeffs: float | Sequence[float],
    p_ref_psia: float,
) -> float:
    """Evaluate oil isothermal compressibility c_o (1/psia) at a reference pressure.

    Args:
        model: "constant" -- `value_or_coeffs` is a single c_o value (1/psia),
            returned unchanged regardless of `p_ref_psia`.
            "polynomial" -- `value_or_coeffs` is `[a0, a1, a2, ...]`
            (lowest-order coefficient first) for
            `c_o(P) = a0 + a1*P + a2*P**2 + ...` (P in psia), evaluated at
            `p_ref_psia`.
        value_or_coeffs: A single float for "constant"; a non-empty sequence
            of coefficients for "polynomial".
        p_ref_psia: Reference (oil-charging) pressure, in psia. Ignored for
            "constant".

    Returns:
        c_o in 1/psia, ready to pass straight into
        `calculate_multistage`'s `c_o` parameter.

    Raises:
        InputValidationError: `model` is not "constant"/"polynomial", the
            "constant" model is given a non-scalar, or the "polynomial"
            model is given a scalar or an empty coefficient sequence.
    """
    if model == "constant":
        if isinstance(value_or_coeffs, int | float):
            return float(value_or_coeffs)
        raise InputValidationError(
            ["constant compressibility model requires a single numeric value, "
             f"got {value_or_coeffs!r}"]
        )

    if model == "polynomial":
        if isinstance(value_or_coeffs, int | float):
            raise InputValidationError(
                ["polynomial compressibility model requires a sequence of "
                 f"coefficients, got a scalar ({value_or_coeffs!r})"]
            )
        coeffs = list(value_or_coeffs)
        if not coeffs:
            raise InputValidationError(
                ["polynomial compressibility model requires at least one coefficient"]
            )
        return sum(a * p_ref_psia**i for i, a in enumerate(coeffs))

    raise InputValidationError([f"unknown compressibility model: {model!r}"])
