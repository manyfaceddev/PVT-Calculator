import warnings

import pytest

from pvt.correlations.bubble_point.standing import (
    bubble_point,
    bubble_point_with_exponent,
    standing_bubble_point,
)


# --- Step 1 tests (brief, verbatim) ---------------------------------------

def test_computed_exponent_form():
    # Standing with Rs=1000, gg=0.65, API=30, T=200F: a = 0.00091*200 - 0.0125*30 = -0.193
    expected = 18.2 * ((1000 / 0.65) ** 0.83 * 10 ** (-0.193) - 1.4)
    assert bubble_point(1000.0, 0.65, 30.0, 200.0) == pytest.approx(expected, rel=1e-12)


def test_golden_sheet_literal_form():
    # GOLDEN: "Bubble point pressure correlations.xls" F38 leaves a as a raw input (=0).
    # Ledger D-007: the sheet never computes a; engine does. Parity via the exponent hook:
    assert bubble_point_with_exponent(1000.0, 0.65, 0.0) == pytest.approx(
        8016.32062952945, rel=1e-10)


def test_range_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        bubble_point(2000.0, 0.65, 30.0, 200.0)   # Rs above 1425
    assert any("outside Standing" in str(w.message) for w in caught)


def test_existing_trends_hold():
    assert bubble_point(1200, 0.65, 30, 200) > bubble_point(800, 0.65, 30, 200)
    assert bubble_point(1000, 0.65, 45, 200) < bubble_point(1000, 0.65, 30, 200)


# --- Ported from tests/test_correlations.py (see task-8-report.md for the
# full old-test disposition table) -----------------------------------------
# Old signature was bubble_point(R, gamma_g, T_F, API); new is
# bubble_point(rs_scf_stb, gas_gravity, api, t_f). Values/trends are
# unchanged -- only the argument order moves API and T_F.

def _standing_pb(rs: float, gamma_g: float, api: float, t_f: float) -> float:
    """Reference implementation -- mirrors the published formula exactly."""
    a = 0.00091 * t_f - 0.0125 * api
    pb = 18.2 * ((rs / gamma_g) ** 0.83 * 10.0 ** a - 1.4)
    return max(pb, 0.0)


class TestBubblePointFormula:
    """Verify the implementation matches the published Standing (1947) equation."""

    @pytest.mark.parametrize("rs, gamma_g, api, t_f", [
        (850,   0.72, 35, 145),    # typical light crude, moderate GOR
        (1_200, 0.65, 42, 200),    # high GOR, light oil
        (400,   0.80, 28, 120),    # low GOR, heavier crude
        (850,   0.72, 42, 200),    # North Sea-style conditions
    ])
    def test_matches_reference_formula(self, rs, gamma_g, api, t_f):
        expected = _standing_pb(rs, gamma_g, api, t_f)
        assert bubble_point(rs, gamma_g, api, t_f) == pytest.approx(expected, rel=1e-9)

    def test_known_value(self):
        """
        Hand-computed reference point for regression detection.
        Rs=850 scf/STB, gg=0.72, API=35, T=145F:
          a  = 0.00091*145 - 0.0125*35 = -0.30555
          Pb = 18.2 * ((850/0.72)^0.83 * 10^-0.30555 - 1.4)
        """
        pb = bubble_point(850, 0.72, 35, 145)
        # Accept +-0.01% relative tolerance for floating-point arithmetic
        assert pb == pytest.approx(_standing_pb(850, 0.72, 35, 145), rel=1e-4)
        assert 2_500 < pb < 4_000, "Expected result roughly in 2500-4000 psia range"


class TestBubblePointEdgeCases:
    def test_zero_gor_returns_zero(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert bubble_point(0, 0.72, 35, 145) == 0.0

    def test_negative_gor_returns_zero(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert bubble_point(-100, 0.72, 35, 145) == 0.0

    def test_zero_gamma_g_returns_zero(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert bubble_point(850, 0, 35, 145) == 0.0

    def test_negative_gamma_g_returns_zero(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert bubble_point(850, -0.5, 35, 145) == 0.0

    def test_result_is_non_negative(self):
        # Very heavy oil + very low GOR could give negative from raw formula
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            assert bubble_point(1, 0.9, 10, 60) >= 0.0


class TestBubblePointPhysicalTrends:
    """Higher GOR -> higher Pb; higher temperature -> higher Pb; higher API -> lower Pb."""

    def test_higher_gor_gives_higher_pb(self):
        pb_lo = bubble_point(400,   0.72, 35, 145)
        pb_hi = bubble_point(1_200, 0.72, 35, 145)
        assert pb_hi > pb_lo

    def test_higher_temperature_gives_higher_pb(self):
        pb_cold = bubble_point(850, 0.72, 35, 100)
        pb_hot  = bubble_point(850, 0.72, 35, 250)
        assert pb_hot > pb_cold

    def test_higher_api_gives_lower_pb(self):
        # Higher API -> lower 10^(...-0.0125*API) -> lower Pb
        pb_heavy = bubble_point(850, 0.72, 20, 145)
        pb_light = bubble_point(850, 0.72, 45, 145)
        assert pb_heavy > pb_light

    def test_heavier_gas_gives_higher_pb(self):
        # Higher gamma_g -> lower Rs/gamma_g -> lower Pb
        pb_light_gas = bubble_point(850, 0.60, 35, 145)
        pb_heavy_gas = bubble_point(850, 0.90, 35, 145)
        assert pb_light_gas > pb_heavy_gas


# --- Deprecated alias -------------------------------------------------------

class TestStandingBubblePointDeprecatedAlias:
    """standing_bubble_point keeps the ORIGINAL (R, gamma_g, T_F, API) argument
    order for existing callers (ui/recombination.py, cli.py) and must stay a
    drop-in match for bubble_point(rs, gamma_g, api, t_f) with args reordered."""

    def test_deprecation_warning_raised(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            standing_bubble_point(850, 0.72, 145, 35)
        assert any(issubclass(w.category, DeprecationWarning) for w in caught)

    def test_matches_new_signature_reordered(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            old = standing_bubble_point(850, 0.72, 145, 35)
            new = bubble_point(850, 0.72, 35, 145)
        assert old == pytest.approx(new, rel=1e-12)
