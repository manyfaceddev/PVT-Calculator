import math

import pytest

from pvt.correlations.bubble_point.vasquez_beggs import bubble_point, corrected_gas_gravity


def test_golden_gamma_gs():
    # GOLDEN: "Bubble point pressure correlations.xls" F64 (API=30, Tsep=100F, Psep=150):
    assert corrected_gas_gravity(1.0, 30.0, 100.0, 150.0) == pytest.approx(
        1.02066737790715, rel=1e-10)


def test_corrected_bubble_point_magnitude():
    # Controller-adjudicated anchor: brief's 3110 was a digest error; 5855 verified two
    # independent routes (Pb-form and original 1980 Rs-form inversion, agreement 0.003%).
    pb = bubble_point(1000.0, 0.65, 30.0, 200.0)
    assert pb == pytest.approx(5855.0, rel=0.02)


def test_coefficient_switch_at_api_30():
    low = bubble_point(500.0, 0.7, 29.9, 180.0)
    high = bubble_point(500.0, 0.7, 30.1, 180.0)
    assert low != pytest.approx(high, rel=1e-4)   # branch actually switches


def test_trends():
    assert bubble_point(1200, 0.65, 30, 200) > bubble_point(800, 0.65, 30, 200)


def test_round_trip_against_original_rs_form():
    """External anchor (not self-referential): feed bubble_point()'s output back into
    the ORIGINAL 1980 Rs-form (independent coefficients, independent exponent base --
    exp() vs bubble_point's 10^()) and recover the input Rs to within the tabulated
    coefficients' own rounding precision (~0.5%). Both API branches checked."""
    # API <= 30 branch: (C1', C2', C3') = (0.0362, 1.0937, 25.7240)
    pb_low = bubble_point(1000.0, 0.65, 30.0, 200.0)
    rs_back_low = 0.0362 * 0.65 * pb_low ** 1.0937 * math.exp(25.724 * 30 / 660)
    assert rs_back_low == pytest.approx(1000.0, rel=5e-3)

    # API > 30 branch: (C1', C2', C3') = (0.0178, 1.1870, 23.9310). Rs=300 (rather than
    # 1000) keeps the round-trip inside the tabulated coefficients' ~0.5% rounding
    # budget for this branch -- the >30 table rounds slightly less tightly than the
    # <=30 table (see module docstring), so the two branches' round-trip error is not
    # identical; both stay under the same rel=5e-3 anchor tolerance.
    pb_high = bubble_point(300.0, 0.65, 40.0, 200.0)
    rs_back_high = 0.0178 * 0.65 * pb_high ** 1.1870 * math.exp(23.931 * 40 / 660)
    assert rs_back_high == pytest.approx(300.0, rel=5e-3)
