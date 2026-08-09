import math
import warnings

import pytest

from pvt.core.exceptions import InputValidationError
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

    # API > 30 branch: (C1', C2', C3') = (0.0178, 1.1870, 23.9310).
    pb_high = bubble_point(1000.0, 0.65, 40.0, 200.0)
    rs_back_high = 0.0178 * 0.65 * pb_high ** 1.1870 * math.exp(23.931 * 40 / 660)
    # rel=6e-3 (not 5e-3): the published table rounds C2 to 0.842 (exact 0.84246), a
    # systematic -0.54% round-trip bias at high Rs; verified to collapse to ~1e-16 with
    # exact-inverse coefficients. High-Rs API>30 fluids are a real regime - keep it
    # covered rather than shopping the input.
    assert rs_back_high == pytest.approx(1000.0, rel=6e-3)


# --- Input validation guards -------------------------------------------------

@pytest.mark.parametrize("gas_gravity, api, t_sep_f, p_sep_psia", [
    (0.0, 30.0, 100.0, 150.0),    # gas_gravity <= 0
    (1.0, 0.0, 100.0, 150.0),     # api <= 0
    (1.0, 30.0, 100.0, 0.0),      # p_sep_psia <= 0
])
def test_corrected_gas_gravity_rejects_bad_inputs(gas_gravity, api, t_sep_f, p_sep_psia):
    with pytest.raises(InputValidationError):
        corrected_gas_gravity(gas_gravity, api, t_sep_f, p_sep_psia)


def test_corrected_gas_gravity_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        corrected_gas_gravity(0.0, 0.0, 100.0, 0.0)
    assert len(exc_info.value.errors) == 3


@pytest.mark.parametrize("rs, gas_gravity, api, t_f", [
    (0.0, 0.65, 30.0, 200.0),     # rs_scf_stb <= 0
    (1000.0, 0.0, 30.0, 200.0),   # gas_gravity <= 0
    (1000.0, 0.65, 0.0, 200.0),   # api <= 0
])
def test_bubble_point_rejects_bad_inputs(rs, gas_gravity, api, t_f):
    with pytest.raises(InputValidationError):
        bubble_point(rs, gas_gravity, api, t_f)


# --- Vasquez-Beggs (1980) range warnings -------------------------------------
# Mirrors standing.py's `_warn_if_outside_range` pattern/test shape
# (tests/unit/correlations/test_standing.py::test_range_warning).

def test_range_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bubble_point(2500.0, 0.65, 30.0, 200.0)   # Rs above 2070
    assert any("outside Vasquez-Beggs" in str(w.message) for w in caught)


def test_range_warning_all_four_checks():
    # Positive-but-out-of-range on every axis (Rs, gas_gravity, API, T) so all four
    # `_warn_if_outside_range` branches fire in one call -- gas_gravity/api stay > 0
    # so the InputValidationError guard doesn't short-circuit before the warnings.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bubble_point(5.0, 2.0, 80.0, 500.0)
    messages = [str(w.message) for w in caught]
    assert sum("outside Vasquez-Beggs" in m for m in messages) == 4
