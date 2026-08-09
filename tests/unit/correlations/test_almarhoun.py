import pytest
from pvt.core.exceptions import InputValidationError
from pvt.correlations.bubble_point.almarhoun import bubble_point


def test_full_precision_value():
    pb = bubble_point(1000.0, 0.65, 0.85, 200.0)
    expected = 5.38088e-3 * 1000.0**0.715082 * 0.65**-1.87784 * 0.85**3.1437 * 659.67**1.32657
    assert pb == pytest.approx(expected, rel=1e-12)


def test_close_to_sheet_rounded_form():
    # GOLDEN(loose): the reference sheet's rounded coefficients give 5585.232 with T+460;
    # full-precision published form lands within 0.6% of it.
    assert bubble_point(1000.0, 0.65, 0.85, 200.0) == pytest.approx(5585.23, rel=0.006)


def test_trends():
    assert bubble_point(1200, 0.65, 0.85, 200) > bubble_point(800, 0.65, 0.85, 200)


# --- Input validation guards -------------------------------------------------

@pytest.mark.parametrize("rs, gas_gravity, oil_sg, t_f", [
    (0.0, 0.65, 0.85, 200.0),      # rs_scf_stb <= 0
    (1000.0, 0.0, 0.85, 200.0),    # gas_gravity <= 0
    (1000.0, 0.65, 0.0, 200.0),    # oil_sg <= 0
    (1000.0, 0.65, 2.0, 200.0),    # oil_sg >= 2
    (1000.0, 0.65, 0.85, -459.67), # t_f <= -459.67 (absolute zero)
])
def test_rejects_bad_inputs(rs, gas_gravity, oil_sg, t_f):
    with pytest.raises(InputValidationError):
        bubble_point(rs, gas_gravity, oil_sg, t_f)


def test_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        bubble_point(0.0, 0.0, 0.0, -500.0)
    assert len(exc_info.value.errors) == 4
