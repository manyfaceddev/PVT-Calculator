"""
pvt/experiments/cce/calc.py — Constant Composition Expansion (CCE)
calculation engine.

Formulas (dissected from the fixture workbook `tests/fixtures/workbooks/
2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`, sheet "CCE Calculation",
engine-correct forms; see tests/golden/test_cce_workbook.py for the full
cell-map writeup and cross-checks against the sheet's own cached cells):

- `psat_from_data` = pressure of the user-picked bubble-point row (sheet
  `J9 =INDEX(B16:B55,$D$10)`).
- `v_sat` = cell volume of the bubble-point row (sheet `J8`); relative
  volume `rv_i = v_i / v_sat` for every stage (sheet col D).
- Density, at/above Psat only (single phase; mass conservation):
  `rho_i = rho_at_psat * v_sat / v_i`. Algebraically identical to the
  sheet's `E_i = J7/C_i` once `rho_at_psat := J7/J8` (sheet's `J10`,
  "Density at Psat") -- NOT `D8` ("Measured HPHT Density"), which is
  measured at the first stage's ("Working Pressure") condition, a
  different pressure than Psat in general. `CceInputs.rho_at_psat_g_cc`
  corresponds to the sheet's J10, not D8; see the golden test module
  docstring for the full derivation.
- Instantaneous compressibility, at/above Psat only, central difference:
  `c_i = -(1/v_i) * (v_{i-1} - v_{i+1}) / (p_{i-1} - p_{i+1})` (reported
  x1e6, 1/psi x1e-6 units, matching the sheet's F-column scaling).
  Requires BOTH neighbours i-1 and i+1 to exist and sit at/above Psat:
    * the first stage (i=0) has no i-1 -- the sheet special-cases it
      with a one-sided forward difference; the engine implements only
      the central-difference method (per the Task 2 brief) and returns
      None there instead.
    * the bubble row itself (i=bubble_idx) needs i+1, which is already
      two-phase -- the sheet's own stencil straddles into two-phase
      volume growth there (ledger D-019, docs/excel-deviations.md:
      sheet `F35` cached 85.17, contaminated); the engine returns None.
  So only strictly interior at/above-Psat stages (1 <= i <= bubble_idx-1)
  get a value.
- Mean compressibility, two-point form (sheet `Mean Compressibility!D4`'s
  correct variant): `c_mean = ((v_f-v_i)/((v_i+v_f)/2)) / (p_i-p_f)`,
  reported x1e6, where (v_i, p_i) is the earlier (higher-pressure) state
  and (v_f, p_f) the later (lower-pressure, more expanded) state.
  `res_to_psat` applies this from the FIRST stage to the bubble row,
  with the CORRECT operand order (ledger D-020, docs/excel-deviations.md:
  sheet `Mean Compressibility!H8` flips the numerator operands for its
  "Reservoir Pressure -> Psat" range and returns the negated value,
  cached -12.365...; `D9` on the same sheet duplicates the identical row
  range with the correct order, cached +12.365433539344826). NOTE: the
  sheet's H8/D9 anchor to a separately-tracked "Reservoir Pressure" lab
  input (`CCE Calculation!D5`), which is NOT the first stage's pressure
  ("Working Pressure", `D7`) in the fixture workbook (3938.73 vs
  7014.73 psig -- two different, independently-entered lab
  measurements). `CceInputs` (Task 1, locked) carries no separate
  reservoir-pressure field, only the stage table, so `res_to_psat` is
  necessarily anchored to `stages[0]` here; for the fixture this is a
  genuinely different number from `abs(H8 cached)` (row16->bubble vs
  row23->bubble) even though both use the identical, correct-physics
  two-point formula. See the golden test module docstring for the full
  writeup of this finding; it is a plan/model scope gap, not a workbook
  defect, so it is not logged to docs/workbook-defect-review.md.
  If the bubble row IS the first stage (bubble_point_step == 1) there is
  no reservoir-to-Psat range to report; the "res_to_psat" key is simply
  omitted rather than dividing by a zero-width pressure range.
- Y-function, below Psat only: `y_i = (psat_from_data - p_i) / (p_i *
  (v_i/v_sat - 1))` (sheet col G).
"""

from pvt.core.exceptions import InputValidationError
from pvt.experiments.cce.models import CceInputs, CceResults, CceStageResult
from pvt.experiments.cce.validate import validate

_REPORTING_SCALE = 1_000_000.0  # x1e6, 1/psi -> 1e-6/psi reporting (sheet F/Mean Comp cols)


def mean_compressibility_1e6_per_psi(
    *, v_i: float, p_i: float, v_f: float, p_f: float
) -> float:
    """Two-point mean compressibility between an earlier (higher-P) state
    (v_i, p_i) and a later, more-expanded (lower-P) state (v_f, p_f), in
    1e-6/psi. Correct-physics operand order (sheet `Mean Compressibility!
    D4`/`D9` form; ledger D-020 -- `H8` flips the numerator operands and
    returns the negated value for the same range)."""
    return ((v_f - v_i) / ((v_i + v_f) / 2)) / (p_i - p_f) * _REPORTING_SCALE


def calculate(inputs: CceInputs, *, validate_inputs: bool = True) -> CceResults:
    """Run the CCE calculation. Raises InputValidationError (with the
    full message list) if validate_inputs is True and inputs fail a
    blocking validation rule. The psat-consistency rule is advisory only
    (messages prefixed "consistency:", validate.py docstring / plan
    Task 1 spec) -- it does not block calculation by itself; the result
    still surfaces it via `psat_consistency_ok`."""
    if validate_inputs and (errors := validate(inputs)):
        blocking = [e for e in errors if not e.startswith("consistency:")]
        if blocking:
            raise InputValidationError(blocking)

    stages = inputs.stages
    bubble_idx = inputs.bubble_point_step - 1  # 0-based index of the bubble-point row
    bubble = stages[bubble_idx]
    v_sat = bubble.v_cell_cc
    psat_from_data = bubble.p
    psat_consistency_ok = abs(inputs.psat_visual - psat_from_data) <= 10.0

    stage_results = []
    for idx, stage in enumerate(stages):
        rel_vol = stage.v_cell_cc / v_sat

        density = None
        if idx <= bubble_idx and inputs.rho_at_psat_g_cc is not None:
            density = inputs.rho_at_psat_g_cc * v_sat / stage.v_cell_cc

        inst_c = None
        if 1 <= idx <= bubble_idx - 1:
            prev_stage = stages[idx - 1]
            next_stage = stages[idx + 1]
            inst_c = (
                -(1.0 / stage.v_cell_cc)
                * (prev_stage.v_cell_cc - next_stage.v_cell_cc)
                / (prev_stage.p - next_stage.p)
                * _REPORTING_SCALE
            )

        y_function = None
        if idx > bubble_idx:
            y_function = (psat_from_data - stage.p) / (stage.p * (rel_vol - 1))

        stage_results.append(
            CceStageResult(
                step=stage.step,
                p=stage.p,
                rel_vol=rel_vol,
                density_g_cc=density,
                inst_compressibility_1e6_per_psi=inst_c,
                y_function=y_function,
            )
        )

    mean_compressibility: dict[str, float] = {}
    if bubble_idx > 0:
        first = stages[0]
        mean_compressibility["res_to_psat"] = mean_compressibility_1e6_per_psi(
            v_i=first.v_cell_cc, p_i=first.p, v_f=v_sat, p_f=psat_from_data
        )

    return CceResults(
        psat_from_data=psat_from_data,
        psat_consistency_ok=psat_consistency_ok,
        v_sat_cc=v_sat,
        stages=tuple(stage_results),
        mean_compressibility_1_psi=mean_compressibility,
    )
