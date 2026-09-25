"""
tests/unit/experiments/test_cce_validate.py — CCE validation rule tests.

The happy-path fixture is built by reading the committed workbook
`tests/fixtures/workbooks/2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`
(sheet "CCE Calculation") directly with openpyxl -- there is no importer
yet (that is Task 5); this module's `_load_cce_happy_path` helper is a
test-only reader, not production code.

Cell-map notes (confirmed by loading the fixture with both
`data_only=True` and `data_only=False`):

- Stage table: rows 16-55 (40 stages). Columns:
    A = step (1..40)
    B = pressure, psig-as-entered (D3 pressure policy; see plan Global
        Constraints -- the engine treats this as absolute psia pass-through)
    C = ENTERED cell volume (cc)
    D = Relative Volume  (formula `=C{row}/$J$8`)      -- DERIVED
    E = Density (g/cm3)  (formula `=IF(...,$J$7/C{row},"")`) -- DERIVED
  Column determination: with `data_only=False`, C16 holds the raw float
  94.08822903 (no formula), while D16 and E16 hold formula strings that
  reference C16. So C is the entered volume; D/E are workbook-computed
  and are intentionally NOT read here (calc.py, Task 2, recomputes them).

- D5 = "Reservoir Pressure (psig)" = 3938.73    -> CceInputs.reservoir_p
  D9 = "Visual Bubble Point (psig)" = 1155.73  -> CceInputs.psat_visual
  D10 = "Bubble Point Step #:" = 20             -> CceInputs.bubble_point_step

  D5 is a separate, independently-entered lab input from D7 "Working
  Pressure (psig)" = 7014.73 (row 16's pressure, the first stage) --
  added in Task 2 round 2 (controller adjudication, see
  pvt/experiments/cce/calc.py and docs/excel-deviations.md D-020) so
  that calc.py can anchor the reservoir->Psat mean compressibility the
  same way Mean Compressibility!H8 does.

  NOTE -- brief/plan discrepancy: the task-1 brief and the Phase 3a plan's
  Task 1/Task 5 cell maps both describe the visual Psat as cell **D8**.
  The fixture actually has D8 = "Measured HPHT Density (g/cm3)" = 0.72868
  and D9 = "Visual Bubble Point (psig)" = 1155.73 (rows 6-10 run
  Temperature, Working Pressure, Density, Visual Psat, Bubble Step). The
  *values* the brief quotes (visual Psat ~1155.73, bubble step 20) match
  D9/D10 exactly and unambiguously identify the correct cells, so this
  test (and pvt/experiments/cce/models.py's docstring) use D9. Flagged
  for the Task 5 importer author to use the corrected address. This is a
  plan-documentation offset, not a workbook defect, so it is not logged
  to docs/workbook-defect-review.md.

- Using the full 40-row table (not just rows 16-25) is required for the
  happy path to be self-consistent: D10 (bubble_point_step) = 20 must be
  a valid 1-based index into the stage table for the "bubble_point_step
  within stage range" rule to pass, which needs >= 20 stages present.
"""

import dataclasses
from pathlib import Path

import openpyxl

from pvt.experiments.cce.models import CceInputs, CceStage
from pvt.experiments.cce.validate import validate

WB = Path("tests/fixtures/workbooks/2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx")


def _load_cce_happy_path() -> CceInputs:
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

    return CceInputs(
        t_res_f=float(ws["D6"].value),
        psat_visual=float(ws["D9"].value),
        bubble_point_step=int(ws["D10"].value),
        stages=tuple(stages),
        reservoir_p=float(ws["D5"].value),
    )


HAPPY = _load_cce_happy_path()


def test_happy_path_from_fixture():
    assert validate(HAPPY) == []


def test_fixture_shape_sanity():
    # Sanity-checks on the fixture read itself, independent of validate().
    assert len(HAPPY.stages) == 40
    assert HAPPY.bubble_point_step == 20
    assert HAPPY.psat_visual == 1155.73
    assert HAPPY.stages[19].step == 20
    assert HAPPY.stages[19].p == 1155.73
    assert HAPPY.reservoir_p == 3938.73


def test_too_few_stages_flagged():
    # Every other rule is neutralized (bubble step indexes the one
    # remaining stage, visual Psat matches it, reservoir_p untracked) so
    # Rule 1's exact message is the ONLY thing that can satisfy this test
    # -- a reworded or deleted rule fails here, not just in the
    # count-based test_errors_accumulate.
    bad = dataclasses.replace(
        HAPPY,
        stages=HAPPY.stages[:1],
        bubble_point_step=1,
        psat_visual=HAPPY.stages[0].p,
        reservoir_p=None,
    )
    assert validate(bad) == ["at least 2 stages are required"]


def test_pressure_not_descending_flagged():
    stages = list(HAPPY.stages)
    stages[5], stages[6] = stages[6], stages[5]  # break strict descent
    bad = dataclasses.replace(HAPPY, stages=tuple(stages))
    errors = validate(bad)
    assert any("descend" in e.lower() for e in errors)


def test_equal_adjacent_pressures_flagged():
    # The rule is STRICTLY descending (`prev.p <= nxt.p` fires): a
    # duplicate adjacent pressure is its own boundary, and load-bearing --
    # it is the only guard between calc.py's central-difference
    # denominator (p_{i-1} - p_{i+1}) and a ZeroDivisionError.
    stages = list(HAPPY.stages)
    stages[6] = dataclasses.replace(stages[6], p=stages[5].p)  # equal, not ascending
    bad = dataclasses.replace(HAPPY, stages=tuple(stages))
    errors = validate(bad)
    assert "stage pressures must be strictly descending" in errors


def test_nonpositive_volume_flagged():
    stages = list(HAPPY.stages)
    stages[0] = dataclasses.replace(stages[0], v_cell_cc=0.0)
    bad = dataclasses.replace(HAPPY, stages=tuple(stages))
    errors = validate(bad)
    assert any("volume" in e.lower() for e in errors)

    # Negative volume trips the same rule (the guard is <= 0, not == 0).
    stages[0] = dataclasses.replace(HAPPY.stages[0], v_cell_cc=-5.0)
    neg = dataclasses.replace(HAPPY, stages=tuple(stages))
    errors_neg = validate(neg)
    assert any("volume" in e.lower() for e in errors_neg)


def test_bubble_point_step_out_of_range_flagged():
    bad = dataclasses.replace(HAPPY, bubble_point_step=41)
    errors = validate(bad)
    assert any("bubble_point_step" in e.lower() for e in errors)


def test_bubble_point_step_zero_flagged():
    bad = dataclasses.replace(HAPPY, bubble_point_step=0)
    errors = validate(bad)
    assert any("bubble_point_step" in e.lower() for e in errors)


def test_psat_consistency_advisory_flagged_but_nonblocking():
    bad = dataclasses.replace(HAPPY, psat_visual=HAPPY.psat_visual + 50.0)
    errors = validate(bad)
    assert any(e.startswith("consistency:") for e in errors)
    assert len(errors) == 1  # advisory only -- nothing else is broken


def test_psat_consistency_within_tolerance_not_flagged():
    bad = dataclasses.replace(HAPPY, psat_visual=HAPPY.psat_visual + 5.0)
    errors = validate(bad)
    assert not any(e.startswith("consistency:") for e in errors)


def test_psat_consistency_skipped_when_bubble_step_out_of_range():
    # Guard: must not raise (or double-report) when the picked row can't
    # be indexed at all.
    bad = dataclasses.replace(HAPPY, bubble_point_step=0, psat_visual=1.0)
    errors = validate(bad)
    assert not any(e.startswith("consistency:") for e in errors)


def test_t_res_f_too_low_flagged():
    bad = dataclasses.replace(HAPPY, t_res_f=-100.0)
    errors = validate(bad)
    assert any("t_res_f" in e.lower() for e in errors)


def test_t_res_f_too_high_flagged():
    bad = dataclasses.replace(HAPPY, t_res_f=600.0)
    errors = validate(bad)
    assert any("t_res_f" in e.lower() for e in errors)


def test_t_res_f_range_edges_are_inclusive():
    # Exactly AT the band edges must validate clean (T_RES_F_MIN/MAX are
    # inclusive); a strict comparison slipping in would fail here.
    for edge in (-60.0, 500.0):
        ok = dataclasses.replace(HAPPY, t_res_f=edge)
        errors = validate(ok)
        assert not any("t_res_f" in e.lower() for e in errors)


def test_errors_accumulate():
    bad = dataclasses.replace(
        HAPPY,
        stages=HAPPY.stages[:1],  # too few stages
        t_res_f=1000.0,  # out of physical range
        bubble_point_step=99,  # out of range (also suppresses the consistency check)
        # neutralized: HAPPY.reservoir_p (3938.73) would fall below
        # the single remaining stage's P (7014.73) once stages is
        # truncated above, tripping the new reservoir_p advisory
        # rule as an unrelated 4th message -- keep this test's "3
        # independent violations" intent unambiguous.
        reservoir_p=None,
    )
    errors = validate(bad)
    assert len(errors) == 3


def test_reservoir_p_none_skips_rule():
    bad = dataclasses.replace(HAPPY, reservoir_p=None)
    assert validate(bad) == []


def test_reservoir_p_valid_not_flagged():
    # HAPPY.reservoir_p = 3938.73, well within (last stage's P ..
    # RESERVOIR_P_MAX) -- already implied by test_happy_path_from_fixture,
    # asserted explicitly here per the round-2 coverage requirement.
    errors = validate(HAPPY)
    assert not any("reservoir_p" in e.lower() for e in errors)


def test_reservoir_p_nonpositive_flagged_blocking():
    bad = dataclasses.replace(HAPPY, reservoir_p=0.0)
    errors = validate(bad)
    reservoir_errors = [e for e in errors if "reservoir_p" in e.lower()]
    assert len(reservoir_errors) == 1
    assert "must be > 0" in reservoir_errors[0]
    assert not reservoir_errors[0].startswith("consistency:")  # blocking, not advisory

    neg = dataclasses.replace(HAPPY, reservoir_p=-500.0)
    errors_neg = validate(neg)
    assert any("reservoir_p" in e.lower() for e in errors_neg)


def test_reservoir_p_below_last_stage_flagged_advisory():
    # HAPPY's last stage (step 40) has P=218.0346 -- below that is
    # implausible (the reservoir pressure should be at or above every
    # pressure the expansion ever reaches).
    bad = dataclasses.replace(HAPPY, reservoir_p=100.0)
    errors = validate(bad)
    assert any(
        e.startswith("consistency:") and "reservoir_p" in e for e in errors
    )


def test_reservoir_p_above_max_flagged_advisory():
    bad = dataclasses.replace(HAPPY, reservoir_p=30_000.0)
    errors = validate(bad)
    assert any(
        e.startswith("consistency:") and "reservoir_p" in e for e in errors
    )


def test_reservoir_p_plausibility_band_edges_not_flagged():
    # Exactly AT the plausibility band edges (last stage's P and
    # RESERVOIR_P_MAX) the band itself must stay silent (strict < / >).
    # At the LOWER edge (218.0346, far below the picked bubble-row
    # pressure 1155.73) the separate at/below-Psat advisory fires instead;
    # at the UPPER edge (25000) nothing fires at all.
    lower = dataclasses.replace(HAPPY, reservoir_p=HAPPY.stages[-1].p)
    errors_lower = validate(lower)
    assert not any("plausible range" in e for e in errors_lower)
    assert any("at or below the picked bubble-row pressure" in e for e in errors_lower)

    upper = dataclasses.replace(HAPPY, reservoir_p=25_000.0)
    assert validate(upper) == []


def test_reservoir_p_at_or_below_bubble_row_flagged_advisory():
    # reservoir_p inside the plausible band but at/below the picked
    # bubble-row pressure (1155.73): res_to_psat would need a two-phase
    # anchor, so calc.py omits it (ledger D-024) and validate() says so
    # with a non-blocking advisory. Exactly AT the bubble-row pressure is
    # inside this band (<=).
    for value in (500.0, HAPPY.stages[HAPPY.bubble_point_step - 1].p):
        bad = dataclasses.replace(HAPPY, reservoir_p=value)
        errors = validate(bad)
        assert any(
            e.startswith("consistency:")
            and "at or below the picked bubble-row pressure" in e
            for e in errors
        )

    # Just above the bubble-row pressure: no advisory.
    ok = dataclasses.replace(HAPPY, reservoir_p=1200.0)
    assert validate(ok) == []


def test_reservoir_p_below_bubble_advisory_skipped_when_bubble_step_invalid():
    # With bubble_point_step out of range there is no picked row to
    # compare against -- the at/below-bubble advisory must not fire (or
    # crash); only the bubble_point_step error itself is reported for
    # this reservoir_p.
    bad = dataclasses.replace(HAPPY, bubble_point_step=0, reservoir_p=500.0)
    errors = validate(bad)
    assert not any("at or below the picked bubble-row pressure" in e for e in errors)
    assert any("bubble_point_step" in e for e in errors)


def test_reservoir_p_plausibility_check_skipped_when_no_stages():
    # Guard: a positive reservoir_p with an empty stage table must
    # not crash trying to index stages[-1] -- the plausibility-band check
    # is simply skipped (the "too few stages" rule already flags the
    # empty table separately).
    bad = dataclasses.replace(HAPPY, stages=(), reservoir_p=1000.0)
    errors = validate(bad)
    assert not any("reservoir_p" in e.lower() for e in errors)


def test_rho_at_psat_nonpositive_flagged_blocking():
    # rho_at_psat_g_cc multiplies straight through into every
    # at/above-Psat density (calc.py), so a non-positive value is a
    # blocking input error, mirroring the reservoir_p > 0 rule.
    for value in (0.0, -0.8):
        bad = dataclasses.replace(HAPPY, rho_at_psat_g_cc=value)
        errors = validate(bad)
        rho_errors = [e for e in errors if "rho_at_psat_g_cc" in e]
        assert len(rho_errors) == 1
        assert "must be > 0" in rho_errors[0]
        assert not rho_errors[0].startswith("consistency:")


def test_rho_at_psat_positive_not_flagged():
    ok = dataclasses.replace(HAPPY, rho_at_psat_g_cc=0.72868)
    assert validate(ok) == []
