import pytest

from pvt.core.exceptions import InputValidationError
from pvt.correlations.bubble_point.glaso import bubble_point, pb_star


def test_pb_star_matches_workbook_cell():
    # GOLDEN: reference sheet F81 (497.662528246482) is Pb* x its stray 14.5 factor
    # (D-009); dividing out the bug yields an exact workbook anchor for the published
    # Pb* form.
    assert pb_star(1000.0, 0.65, 30.0, 200.0) == pytest.approx(
        497.662528246482 / 14.5, rel=1e-6)


def test_corrected_magnitude():
    # Controller-adjudicated: brief's 3299 was a digest evaluation error (Task 9
    # precedent). Hand-derivation: Pb*=34.32, log10(Pb)=3.7336, Pb~=5413. Sibling
    # sanity on identical inputs: Standing 5131 (engine recompute -- see below;
    # was misquoted 5149), Al-Marhoun 5585, V-B 5855.
    #
    # Standing recheck: pvt.correlations.bubble_point.standing.bubble_point(1000.0,
    # 0.65, 30.0, 200.0) == 5130.9995766428665, not the previously-quoted 5149 (no
    # source anchor for 5149 was ever recorded -- this was a stale/incorrect digest
    # figure, corrected here by recomputing with the engine directly).
    assert bubble_point(1000.0, 0.65, 30.0, 200.0) == pytest.approx(5413.4, rel=0.02)


def test_trends():
    assert bubble_point(1200, 0.65, 30, 200) > bubble_point(800, 0.65, 30, 200)
    assert bubble_point(1000, 0.65, 45, 200) < bubble_point(1000, 0.65, 30, 200)


# --- Input validation guards -------------------------------------------------

@pytest.mark.parametrize("rs, gas_gravity, api, t_f", [
    (0.0, 0.65, 30.0, 200.0),     # rs_scf_stb <= 0
    (1000.0, 0.0, 30.0, 200.0),   # gas_gravity <= 0
    (1000.0, 0.65, 0.0, 200.0),   # api <= 0
    (1000.0, 0.65, 30.0, 0.0),    # t_f <= 0
])
def test_pb_star_rejects_bad_inputs(rs, gas_gravity, api, t_f):
    with pytest.raises(InputValidationError):
        pb_star(rs, gas_gravity, api, t_f)


@pytest.mark.parametrize("rs, gas_gravity, api, t_f", [
    (0.0, 0.65, 30.0, 200.0),     # rs_scf_stb <= 0
    (1000.0, 0.0, 30.0, 200.0),   # gas_gravity <= 0
    (1000.0, 0.65, 0.0, 200.0),   # api <= 0
    (1000.0, 0.65, 30.0, 0.0),    # t_f <= 0
])
def test_bubble_point_rejects_bad_inputs(rs, gas_gravity, api, t_f):
    with pytest.raises(InputValidationError):
        bubble_point(rs, gas_gravity, api, t_f)


def test_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        pb_star(0.0, 0.0, 0.0, 0.0)
    assert len(exc_info.value.errors) == 4
    assert bubble_point(1000, 0.85, 30, 200) < bubble_point(1000, 0.65, 30, 200)
