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

`reservoir_p` (Task 2 round 2, sheet `D5`; as-entered pressure units,
D3 policy) is optional -- rules below only run when it's provided. A
non-positive value is a genuine input error (blocking, mirrors the
volume/temperature "must be" messages). Two advisory bands (prefixed
`ADVISORY_PREFIX`, same non-blocking mechanism as the psat-consistency
rule): a value outside the plausible range relative to the stage table
-- below the last (lowest-pressure) stage's P, or above RESERVOIR_P_MAX
-- and a value at/below the picked bubble-row pressure. In both cases
calc.py's `res_to_psat` MATCH(-1)-style anchor search lands at/below the
bubble row and the "res_to_psat" key is omitted rather than computed
from a two-phase anchor (ledger D-024, docs/excel-deviations.md).

`rho_at_psat_g_cc`, if provided, must be > 0 (blocking): calc.py
multiplies it straight through into every at/above-Psat stage density.
"""

from pvt.experiments.cce.models import CceInputs

ADVISORY_PREFIX = "consistency:"
PSAT_CONSISTENCY_TOL_PSI = 10.0
T_RES_F_MIN = -60.0
T_RES_F_MAX = 500.0
RESERVOIR_P_MAX = 25_000.0


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
    picked_p = inputs.stages[inputs.bubble_point_step - 1].p if bubble_in_range else None
    if picked_p is not None and abs(inputs.psat_visual - picked_p) > PSAT_CONSISTENCY_TOL_PSI:
        messages.append(
            f"{ADVISORY_PREFIX} visual Psat ({inputs.psat_visual:g}) differs from the "
            f"picked-row pressure ({picked_p:g}) by more than "
            f"{PSAT_CONSISTENCY_TOL_PSI:g} psi"
        )

    # Rule 6: reservoir temperature must be physically plausible
    if not (T_RES_F_MIN <= inputs.t_res_f <= T_RES_F_MAX):
        messages.append(
            f"t_res_f ({inputs.t_res_f:g}) is outside the physical range "
            f"{T_RES_F_MIN:g}..{T_RES_F_MAX:g} F"
        )

    # Rule 7: reservoir_p, if tracked, must be physically sane; the
    # plausibility band against the stage table and the at/below-Psat
    # band (res_to_psat omitted, ledger D-024) are advisory only.
    if inputs.reservoir_p is not None:
        if inputs.reservoir_p <= 0:
            messages.append(
                f"reservoir_p ({inputs.reservoir_p:g}) must be > 0"
            )
        elif inputs.stages:
            last_stage_p = inputs.stages[-1].p
            if (
                inputs.reservoir_p < last_stage_p
                or inputs.reservoir_p > RESERVOIR_P_MAX
            ):
                messages.append(
                    f"{ADVISORY_PREFIX} reservoir_p ({inputs.reservoir_p:g}) is "
                    f"outside the plausible range ({last_stage_p:g}.."
                    f"{RESERVOIR_P_MAX:g}, as-entered pressure units) for this "
                    f"stage table"
                )
            elif picked_p is not None and inputs.reservoir_p <= picked_p:
                messages.append(
                    f"{ADVISORY_PREFIX} reservoir_p ({inputs.reservoir_p:g}) is at or "
                    f"below the picked bubble-row pressure ({picked_p:g}); the "
                    f"reservoir-to-Psat mean compressibility is a single-phase "
                    f"quantity and will be omitted"
                )

    # Rule 8: density at Psat, if provided, must be positive -- calc.py
    # multiplies it straight through into every at/above-Psat density.
    if inputs.rho_at_psat_g_cc is not None and inputs.rho_at_psat_g_cc <= 0:
        messages.append(
            f"rho_at_psat_g_cc ({inputs.rho_at_psat_g_cc:g}) must be > 0"
        )

    return messages
