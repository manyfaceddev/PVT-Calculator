import pytest
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
