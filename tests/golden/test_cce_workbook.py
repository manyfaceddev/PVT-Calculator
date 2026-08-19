"""
tests/golden/test_cce_workbook.py — CCE engine vs the dissected workbook's
cached cells (GOLDEN-INTEGRITY: expected values are read live from the
fixture with openpyxl, never hand-typed from a digest).

Fixture: tests/fixtures/workbooks/2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx
Sheets used: "CCE Calculation" (stage table + auto-calculated params J6:J11)
and "Mean Compressibility" (D4, H7/H8, D9).

Cell map (confirmed by loading the fixture with both data_only=True and
data_only=False -- see also pvt/experiments/cce/models.py and
tests/unit/experiments/test_cce_validate.py):
    D6 = Temperature (F); D9 = Visual Bubble Point (psig); D10 = Bubble
    Point Step # (1-based). Stage table rows 16-55: A=step, B=P
    (psig-as-entered), C=entered cell volume (cc). D/E/F/G (Relative
    Volume / Density / Inst. Compressibility / Y-Function) are all
    DERIVED (formula cells) -- this test recomputes them with the engine
    and compares against the sheet's own cached results, it never reads
    D/E/F/G as engine input.

J-column auto-calculated parameters (rows 6-11):
    J6 = C16 (volume at the first/"Working Pressure" stage)
    J7 = D8*J6 = "Sample Mass (g)" -- D8 ("Measured HPHT Density") times
         the volume at the first stage; mass held constant while
         single-phase (mass conservation).
    J8 = V_sat (INDEX into C at the bubble row)
    J9 = Psat from Data (INDEX into B at the bubble row)
    J10 = J7/J8 = "Density at Psat" (g/cm3) -- this is the quantity that
          corresponds to CceInputs.rho_at_psat_g_cc (NOT D8, which is
          measured at the first-stage/"Working Pressure" condition, a
          different, generally-higher pressure than Psat). Column E's
          formula IF(A<=D10, J7/C, "") is algebraically identical to
          rho_at_psat * v_sat / v_i once rho_at_psat := J10 = J7/J8
          (J7/C_i = (J7/J8)*J8/C_i = rho_at_psat*v_sat/v_i), so wiring
          CceInputs.rho_at_psat_g_cc = J10's cached value reproduces
          column E exactly -- verified below at rel=1e-9.
    J11/K11 = |D9-J9| consistency gate (psat_consistency_ok).

F-column (instantaneous compressibility) stencil, read with
data_only=False: general rows (17-54) use a genuine central difference,
F_i = (C_{i+1}-C_{i-1})/C_i/(B_{i-1}-B_{i+1})*1e6, gated on A_i<=D10 (at
or above Psat). This central form needs both neighbours, so it cannot
apply to the very first stage (row 16: no row 15 to reference) -- the
sheet instead special-cases row 16 with a one-sided forward-difference
formula, (C17-C16)/C16/(B16-B17)*1e6. The engine implements ONLY the
central-difference method (per the Task 2 brief); row 16 is therefore
structurally a boundary the engine cannot evaluate (no i-1) and returns
None there, diverging from the sheet's one-sided F16 -- this is not
compared. At the OTHER end of the at/above-Psat gate, row 35 (the bubble
row, A35=20=D10) is where the sheet's central-difference stencil reaches
into row 36 (two-phase, A36=21>D10): F35 is contaminated (cached 85.17;
ledger D-019, docs/excel-deviations.md). The engine excludes both the
bubble row and this boundary row structurally (central diff needs
i-1>=0 and i+1 at/above Psat), so only rows 17-34 (interior, steps 2-19)
are compared against the sheet 1:1.

Mean Compressibility sheet:
    D4 = Range 1 (row16 -> row19), correct two-point form -- direct,
         uncontested golden check of the engine's two-point helper.
    H7 = 'CCE Calculation'!D5 ("Reservoir Pressure", a SEPARATE lab input
         from D7 "Working Pressure" = row16's pressure). H8 = "Mean Comp
         from Reservoir Pressure to Psat", INDEX/MATCHing H7 to the CCE
         table (which lands on row 23, NOT row 16 -- D5=3938.73 equals
         B23, not B16=D7=7014.73) then applying the two-point form with
         the numerator operands FLIPPED (ledger D-020): cached -12.365
         (negative). D9 duplicates the identical row23->row35 range with
         the CORRECT operand order and is the positive, correct-physics
         counterpart: cached +12.365433539344826 = abs(H8 cached),
         verified below.

FINDING (documented in calc.py's module docstring and the Task 2
report, not a workbook defect -- a plan/model scope gap): CceInputs
(Task 1, locked) carries no field for the sheet's separate "Reservoir
Pressure" (D5) lab input; it only has the stage table, whose first entry
is "Working Pressure" (D7, row16). The Task 2 brief's res_to_psat formula
is anchored to the first STAGE (row16), not to D5's reservoir pressure --
for this fixture those are two different pressures (7014.73 vs
3938.73), landing on different rows (16 vs 23), so
CceResults.mean_compressibility_1_psi["res_to_psat"] (row16->row35,
verified below against an independently-computed value) is NOT expected
to equal abs(H8 cached) (row23->row35). Both row pairs are exercised
through the same shared helper so the *formula* is validated against
H8/D9 exactly; only the *anchor row* for res_to_psat differs from the
sheet's H8, by construction of the Task 1 model.
"""

from pathlib import Path

import openpyxl
import pytest

from pvt.experiments.cce.calc import calculate, mean_compressibility_1e6_per_psi
from pvt.experiments.cce.models import CceInputs, CceStage

WB = Path("tests/fixtures/workbooks/2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx")


def _load() -> tuple[CceInputs, dict]:
    wb = openpyxl.load_workbook(WB, data_only=True)
    ws = wb["CCE Calculation"]

    stages = []
    row = 16
    while ws[f"A{row}"].value is not None:
        stages.append(
            CceStage(
                step=int(ws[f"A{row}"].value),
                p=float(ws[f"B{row}"].value),
                v_cell_cc=float(ws[f"C{row}"].value),
            )
        )
        row += 1

    rho_at_psat = float(ws["J10"].value)  # "Density at Psat" -- see module docstring
    inputs = CceInputs(
        t_res_f=float(ws["D6"].value),
        psat_visual=float(ws["D9"].value),
        bubble_point_step=int(ws["D10"].value),
        stages=tuple(stages),
        rho_at_psat_g_cc=rho_at_psat,
    )

    cached = {
        "D": [ws[f"D{r}"].value for r in range(16, 56)],
        "E": [ws[f"E{r}"].value for r in range(16, 56)],
        "F": [ws[f"F{r}"].value for r in range(16, 56)],
        "G": [ws[f"G{r}"].value for r in range(16, 56)],
        "J8": float(ws["J8"].value),
        "J9": float(ws["J9"].value),
        "J11": float(ws["J11"].value),
    }
    return inputs, cached


INPUTS, CACHED = _load()
RESULTS = calculate(INPUTS)
BUBBLE_IDX = INPUTS.bubble_point_step - 1  # 0-based; 19 for this fixture


def test_fixture_shape_sanity():
    assert len(INPUTS.stages) == 40
    assert INPUTS.bubble_point_step == 20
    assert INPUTS.psat_visual == pytest.approx(1155.73)


def test_v_sat_and_psat_from_data_match_j8_j9():
    assert RESULTS.v_sat_cc == pytest.approx(CACHED["J8"], rel=1e-9)
    assert RESULTS.psat_from_data == pytest.approx(CACHED["J9"], rel=1e-9)
    assert RESULTS.psat_from_data == INPUTS.stages[BUBBLE_IDX].p


def test_psat_consistency_matches_j11_k11_gate():
    # J11 = |D9-J9| = 0 < 10 -> K11 = "OK"
    assert CACHED["J11"] == pytest.approx(0.0, abs=1e-9)
    assert RESULTS.psat_consistency_ok is True


def test_relative_volume_all_40_rows():
    for idx, stage_result in enumerate(RESULTS.stages):
        assert stage_result.rel_vol == pytest.approx(CACHED["D"][idx], rel=1e-9)


def test_density_above_and_at_psat_matches_column_e():
    for idx in range(0, BUBBLE_IDX + 1):
        assert RESULTS.stages[idx].density_g_cc == pytest.approx(
            CACHED["E"][idx], rel=1e-6
        )


def test_density_none_below_psat():
    for idx in range(BUBBLE_IDX + 1, len(RESULTS.stages)):
        assert RESULTS.stages[idx].density_g_cc is None


def test_instantaneous_compressibility_interior_rows_match_column_f():
    # Interior rows only: idx 1..(BUBBLE_IDX-1) i.e. steps 2-19 (rows 17-34).
    # idx0 (row16, boundary, no i-1) and idx==BUBBLE_IDX (row35, bubble,
    # straddles into two-phase) are excluded -- see module docstring.
    for idx in range(1, BUBBLE_IDX):
        assert RESULTS.stages[idx].inst_compressibility_1e6_per_psi == pytest.approx(
            CACHED["F"][idx], rel=1e-6
        )


def test_instantaneous_compressibility_boundary_and_bubble_row_are_none():
    assert RESULTS.stages[0].inst_compressibility_1e6_per_psi is None
    assert RESULTS.stages[BUBBLE_IDX].inst_compressibility_1e6_per_psi is None
    # ledger D-019: the sheet's own F35 is contaminated by the two-phase
    # neighbour, cached ~85.17 -- confirms *why* it must be excluded, not
    # just *that* it differs.
    assert CACHED["F"][BUBBLE_IDX] == pytest.approx(85.16667974300425, rel=1e-6)


def test_instantaneous_compressibility_none_below_psat():
    for idx in range(BUBBLE_IDX + 1, len(RESULTS.stages)):
        assert RESULTS.stages[idx].inst_compressibility_1e6_per_psi is None


def test_y_function_below_psat_matches_column_g():
    for idx in range(BUBBLE_IDX + 1, len(RESULTS.stages)):
        assert RESULTS.stages[idx].y_function == pytest.approx(
            CACHED["G"][idx], rel=1e-6
        )


def test_y_function_none_at_and_above_psat():
    for idx in range(0, BUBBLE_IDX + 1):
        assert RESULTS.stages[idx].y_function is None


def test_mean_compressibility_range1_matches_sheet_d4():
    # Mean Compressibility!D4 = Range 1: row16 (step1) -> row19 (step4).
    row16, row19 = INPUTS.stages[0], INPUTS.stages[3]
    c = mean_compressibility_1e6_per_psi(
        v_i=row16.v_cell_cc, p_i=row16.p, v_f=row19.v_cell_cc, p_f=row19.p
    )
    assert c == pytest.approx(7.988732593178792, rel=1e-6)  # Mean Compressibility!D4


def test_mean_compressibility_reservoir_to_psat_matches_abs_h8_and_d9():
    # ledger D-020: Mean Compressibility!H8 flips the numerator operands
    # for the "Reservoir Pressure -> Psat" range and returns -12.365...;
    # D9 duplicates the identical row23->row35 range with the correct
    # operand order and cached +12.365433539344826 = abs(H8 cached).
    # Row 23 is located generically: it's the stage whose pressure
    # matches D5 ("Reservoir Pressure"), read directly here (NOT via
    # CceInputs, which has no such field -- see module docstring finding).
    wb = openpyxl.load_workbook(WB, data_only=True)
    ws = wb["CCE Calculation"]
    reservoir_p = float(ws["D5"].value)  # 3938.73
    reservoir_stage = next(s for s in INPUTS.stages if s.p == reservoir_p)
    bubble_stage = INPUTS.stages[BUBBLE_IDX]

    c = mean_compressibility_1e6_per_psi(
        v_i=reservoir_stage.v_cell_cc,
        p_i=reservoir_stage.p,
        v_f=bubble_stage.v_cell_cc,
        p_f=bubble_stage.p,
    )
    h8_cached = -12.365433539344826
    d9_cached = 12.365433539344826
    assert c == pytest.approx(d9_cached, rel=1e-6)
    assert c == pytest.approx(abs(h8_cached), rel=1e-6)


def test_res_to_psat_is_first_stage_to_bubble_row_not_reservoir_row():
    # See module docstring FINDING: CceInputs has no distinct "Reservoir
    # Pressure" field, so res_to_psat is anchored to the first STAGE
    # (row16/"Working Pressure", 7014.73), not D5's "Reservoir Pressure"
    # (3938.73, row23) that Mean Compressibility!H8/D9 use. The two
    # anchors land on different rows in this fixture, so the numeric
    # values are legitimately different; this test cross-checks the
    # engine's own row16->row35 result against an independent computation
    # of that SAME row pair, not against H8/D9.
    row16, bubble = INPUTS.stages[0], INPUTS.stages[BUBBLE_IDX]
    expected = mean_compressibility_1e6_per_psi(
        v_i=row16.v_cell_cc, p_i=row16.p, v_f=bubble.v_cell_cc, p_f=bubble.p
    )
    assert RESULTS.mean_compressibility_1_psi["res_to_psat"] == pytest.approx(
        expected, rel=1e-9
    )
    # Sanity: distinct from the reservoir-row-anchored D9/H8 value --
    # documents the finding numerically rather than just asserting it away.
    assert RESULTS.mean_compressibility_1_psi["res_to_psat"] != pytest.approx(
        12.365433539344826, rel=1e-3
    )
