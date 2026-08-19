"""
tests/unit/experiments/test_cce_calc.py — CCE calculation engine unit tests.

Small hand-built stage tables (not the fixture workbook -- that's the
golden test, tests/golden/test_cce_workbook.py) exercising every branch
of pvt/experiments/cce/calc.py: the above/at/below-Psat gating for
density, instantaneous compressibility, and Y-function, plus the
res_to_psat edge case when the bubble row is the first stage.

All expected values below are hand-derived directly from the brief's
formulas (see calc.py module docstring) -- shown inline as fractions
reduced to decimals so the arithmetic is checkable by inspection.
"""

import dataclasses

import pytest

from pvt.core.exceptions import InputValidationError
from pvt.experiments.cce.calc import calculate, mean_compressibility_1e6_per_psi
from pvt.experiments.cce.models import CceInputs, CceStage

# Six-stage synthetic table, bubble at step 4 (idx 3, 0-based):
#   step   P      V
#     1   1000   100   <- idx0 (first stage)
#     2    900   104   <- idx1
#     3    800   109   <- idx2
#     4    700   116   <- idx3 (bubble; v_sat)
#     5    600   140   <- idx4
#     6    500   170   <- idx5
STAGES = (
    CceStage(step=1, p=1000.0, v_cell_cc=100.0),
    CceStage(step=2, p=900.0, v_cell_cc=104.0),
    CceStage(step=3, p=800.0, v_cell_cc=109.0),
    CceStage(step=4, p=700.0, v_cell_cc=116.0),
    CceStage(step=5, p=600.0, v_cell_cc=140.0),
    CceStage(step=6, p=500.0, v_cell_cc=170.0),
)

BASE = CceInputs(
    t_res_f=200.0,
    psat_visual=700.0,
    bubble_point_step=4,
    stages=STAGES,
    rho_at_psat_g_cc=0.8,
)


def test_rejects_invalid_inputs_by_default():
    bad = dataclasses.replace(BASE, bubble_point_step=99)
    with pytest.raises(InputValidationError):
        calculate(bad)


def test_validate_inputs_false_skips_validation():
    bad = dataclasses.replace(BASE, bubble_point_step=99)
    with pytest.raises(IndexError):
        # bypasses validate(); bubble_point_step=99 then indexes past the
        # 6-stage tuple, proving validation was genuinely skipped (not
        # just silently tolerated).
        calculate(bad, validate_inputs=False)


def test_psat_from_data_and_v_sat():
    r = calculate(BASE)
    assert r.psat_from_data == 700.0
    assert r.v_sat_cc == 116.0
    assert r.psat_consistency_ok is True


def test_psat_consistency_flagged_false_but_still_calculates():
    close = dataclasses.replace(BASE, psat_visual=705.0)  # 5 psi off, within tolerance
    r = calculate(close)
    assert r.psat_consistency_ok is True
    far = dataclasses.replace(BASE, psat_visual=600.0)  # 100 psi off, advisory-only
    r2 = calculate(far)  # must not raise: consistency is advisory, not blocking
    assert r2.psat_consistency_ok is False


def test_relative_volume_every_stage():
    r = calculate(BASE)
    expected = [100 / 116, 104 / 116, 109 / 116, 116 / 116, 140 / 116, 170 / 116]
    for stage_result, exp in zip(r.stages, expected):
        assert stage_result.rel_vol == pytest.approx(exp, rel=1e-12)


def test_density_defined_at_and_above_psat_only():
    r = calculate(BASE)
    # idx0..3 (steps 1-4, at/above Psat): rho_i = rho_at_psat * v_sat / v_i
    expected_above = [92.8 / 100, 92.8 / 104, 92.8 / 109, 92.8 / 116]
    for stage_result, exp in zip(r.stages[:4], expected_above):
        assert stage_result.density_g_cc == pytest.approx(exp, rel=1e-12)
    # idx3 (bubble row itself) is single-phase -> defined, and equals rho_at_psat
    assert r.stages[3].density_g_cc == pytest.approx(0.8, rel=1e-12)
    # idx4, idx5 (below Psat): density is None
    assert r.stages[4].density_g_cc is None
    assert r.stages[5].density_g_cc is None


def test_density_none_when_rho_at_psat_not_measured():
    bad = dataclasses.replace(BASE, rho_at_psat_g_cc=None)
    r = calculate(bad)
    assert all(s.density_g_cc is None for s in r.stages)


def test_instantaneous_compressibility_interior_only():
    r = calculate(BASE)
    # idx0 (first stage, no i-1 neighbour): None
    assert r.stages[0].inst_compressibility_1e6_per_psi is None
    # idx1: central diff over idx0, idx2 -- both above Psat
    c1 = (109 - 100) / 104 / (1000 - 800) * 1_000_000
    assert r.stages[1].inst_compressibility_1e6_per_psi == pytest.approx(c1, rel=1e-9)
    # idx2: central diff over idx1, idx3 -- idx3 is the bubble row (still
    # single-phase boundary), stencil stays entirely above/at Psat
    c2 = (116 - 104) / 109 / (900 - 700) * 1_000_000
    assert r.stages[2].inst_compressibility_1e6_per_psi == pytest.approx(c2, rel=1e-9)
    # idx3 (bubble row): stencil would need idx4, which is two-phase -> None
    # (ledger D-019; sheet's F35-equivalent contamination, excluded here)
    assert r.stages[3].inst_compressibility_1e6_per_psi is None
    # idx4, idx5: below Psat entirely -> None
    assert r.stages[4].inst_compressibility_1e6_per_psi is None
    assert r.stages[5].inst_compressibility_1e6_per_psi is None


def test_y_function_below_psat_only():
    r = calculate(BASE)
    assert r.stages[0].y_function is None
    assert r.stages[1].y_function is None
    assert r.stages[2].y_function is None
    assert r.stages[3].y_function is None  # bubble row itself: still single-phase
    rv4 = 140 / 116
    y4 = (700 - 600) / (600 * (rv4 - 1))
    assert r.stages[4].y_function == pytest.approx(y4, rel=1e-9)
    rv5 = 170 / 116
    y5 = (700 - 500) / (500 * (rv5 - 1))
    assert r.stages[5].y_function == pytest.approx(y5, rel=1e-9)


def test_res_to_psat_first_stage_to_bubble_row():
    r = calculate(BASE)
    expected = ((116 - 100) / ((100 + 116) / 2)) / (1000 - 700) * 1_000_000
    assert r.mean_compressibility_1_psi["res_to_psat"] == pytest.approx(expected, rel=1e-9)


def test_res_to_psat_omitted_when_bubble_row_is_first_stage():
    # bubble_point_step=1 -> first stage IS the bubble row; a first-stage
    # to bubble-row mean compressibility is undefined (zero-width P range,
    # would divide by zero) so the key is simply absent.
    bad = dataclasses.replace(BASE, bubble_point_step=1, psat_visual=1000.0)
    r = calculate(bad)
    assert "res_to_psat" not in r.mean_compressibility_1_psi
    # and the instantaneous-compressibility interior range is empty too
    assert all(s.inst_compressibility_1e6_per_psi is None for s in r.stages)
    # density is defined only for idx0 (the sole at/above-Psat row)
    assert r.stages[0].density_g_cc == pytest.approx(0.8, rel=1e-12)
    assert all(s.density_g_cc is None for s in r.stages[1:])
    # everything past the bubble row is below Psat
    assert all(s.y_function is not None for s in r.stages[1:])


def test_bubble_row_is_last_stage_no_below_psat_rows():
    bad = dataclasses.replace(BASE, bubble_point_step=6, psat_visual=500.0)
    r = calculate(bad)
    assert all(s.y_function is None for s in r.stages)
    assert r.stages[-1].density_g_cc == pytest.approx(0.8, rel=1e-12)
    # interior inst-compressibility still computable for idx1..idx4
    assert r.stages[0].inst_compressibility_1e6_per_psi is None  # boundary
    assert r.stages[-1].inst_compressibility_1e6_per_psi is None  # bubble row itself
    for idx in (1, 2, 3, 4):
        assert r.stages[idx].inst_compressibility_1e6_per_psi is not None


def test_mean_compressibility_helper_matches_two_point_form():
    # Direct unit check of the shared helper against a hand-computed value;
    # the golden test cross-checks this same helper against workbook cells.
    result = mean_compressibility_1e6_per_psi(
        v_i=100.0, p_i=1000.0, v_f=116.0, p_f=700.0
    )
    expected = ((116.0 - 100.0) / ((100.0 + 116.0) / 2)) / (1000.0 - 700.0) * 1_000_000
    assert result == pytest.approx(expected, rel=1e-12)
