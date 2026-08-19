"""
pvt/experiments/cce/validate.py — Input validation for CCE calculations.

Returns a list of human-readable messages; an empty list means the
inputs are valid enough to calculate. One message per rule (never one
per stage), mirroring `pvt/experiments/flash/validate.py`.

The psat-consistency rule is advisory only: it mirrors the sheet's ✓/⚠
gate at `CCE Calculation!J11:K11` (`=ABS(D9-J9)` compared against 10) and
is prefixed "consistency:" so callers can tell it apart from a blocking
error -- the calculation still runs when only this rule fires (plan
Task 1 spec).
"""

from pvt.experiments.cce.models import CceInputs

PSAT_CONSISTENCY_TOL_PSI = 10.0
T_RES_F_MIN = -60.0
T_RES_F_MAX = 500.0


def validate(inputs: CceInputs) -> list[str]:
    """Validate CceInputs. Returns a list of messages (empty if valid)."""
    messages: list[str] = []

    # Rule 1: at least 2 stages
    if len(inputs.stages) < 2:
        messages.append("at least 2 stages are required")

    # Rule 2: pressure strictly descending across stages
    for prev, nxt in zip(inputs.stages, inputs.stages[1:]):
        if prev.p <= nxt.p:
            messages.append("stage pressures must be strictly descending")
            break

    # Rule 3: cell volumes must be positive
    for stage in inputs.stages:
        if stage.v_cell_cc <= 0:
            messages.append("all stage volumes (v_cell_cc) must be > 0")
            break

    # Rule 4: bubble_point_step must index a real stage (1-based)
    step_count = len(inputs.stages)
    bubble_in_range = 1 <= inputs.bubble_point_step <= step_count
    if not bubble_in_range:
        messages.append(
            f"bubble_point_step ({inputs.bubble_point_step}) must be within "
            f"1..{step_count} (stage count)"
        )

    # Rule 5: consistency advisory (non-blocking) -- only checkable once
    # bubble_point_step actually indexes a stage.
    if bubble_in_range:
        picked_p = inputs.stages[inputs.bubble_point_step - 1].p
        if abs(inputs.psat_visual - picked_p) > PSAT_CONSISTENCY_TOL_PSI:
            messages.append(
                f"consistency: visual Psat ({inputs.psat_visual:g}) differs from the "
                f"picked-row pressure ({picked_p:g}) by more than "
                f"{PSAT_CONSISTENCY_TOL_PSI:g} psi"
            )

    # Rule 6: reservoir temperature must be physically plausible
    if not (T_RES_F_MIN <= inputs.t_res_f <= T_RES_F_MAX):
        messages.append(
            f"t_res_f ({inputs.t_res_f:g}) is outside the physical range "
            f"{T_RES_F_MIN:g}..{T_RES_F_MAX:g} F"
        )

    return messages
