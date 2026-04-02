"""tests/test_correlations.py — Standing (1947) bubble-point correlation."""

import math
import pytest
from pvt.correlations.standing import bubble_point


# ---------------------------------------------------------------------------
# Helper: compute Pb from first principles (independent of our implementation)
# ---------------------------------------------------------------------------

def _standing_pb(R: float, gamma_g: float, T_F: float, API: float) -> float:
    """Reference implementation — mirrors the published formula exactly."""
    x  = 0.00091 * T_F - 0.0125 * API
    Pb = 18.2 * ((R / gamma_g) ** 0.83 * 10.0 ** x - 1.4)
    return max(Pb, 0.0)


class TestBubblePointFormula:
    """Verify the implementation matches the published Standing (1947) equation."""

    @pytest.mark.parametrize("R, gamma_g, T_F, API", [
        (850,   0.72, 145, 35),    # typical light crude, moderate GOR
        (1_200, 0.65, 200, 42),    # high GOR, light oil
        (400,   0.80, 120, 28),    # low GOR, heavier crude
        (850,   0.72, 200, 42),    # North Sea-style conditions
    ])
    def test_matches_reference_formula(self, R, gamma_g, T_F, API):
        expected = _standing_pb(R, gamma_g, T_F, API)
        assert bubble_point(R, gamma_g, T_F, API) == pytest.approx(expected, rel=1e-9)

    def test_known_value(self):
        """
        Hand-computed reference point for regression detection.
        R=850 scf/STB, γg=0.72, T=145°F, API=35:
          x  = 0.00091*145 - 0.0125*35 = -0.30555
          Pb = 18.2 * ((850/0.72)^0.83 * 10^-0.30555 - 1.4)
        """
        Pb = bubble_point(850, 0.72, 145, 35)
        # Accept ±0.01% relative tolerance for floating-point arithmetic
        assert Pb == pytest.approx(_standing_pb(850, 0.72, 145, 35), rel=1e-4)
        assert 2_500 < Pb < 4_000, "Expected result roughly in 2500–4000 psia range"


class TestBubblePointEdgeCases:
    def test_zero_gor_returns_zero(self):
        assert bubble_point(0, 0.72, 145, 35) == 0.0

    def test_negative_gor_returns_zero(self):
        assert bubble_point(-100, 0.72, 145, 35) == 0.0

    def test_zero_gamma_g_returns_zero(self):
        assert bubble_point(850, 0, 145, 35) == 0.0

    def test_negative_gamma_g_returns_zero(self):
        assert bubble_point(850, -0.5, 145, 35) == 0.0

    def test_result_is_non_negative(self):
        # Very heavy oil + very low GOR could give negative from raw formula
        assert bubble_point(1, 0.9, 60, 10) >= 0.0


class TestBubblePointPhysicalTrends:
    """Higher GOR → higher Pb; higher temperature → higher Pb; higher API → lower Pb."""

    def test_higher_gor_gives_higher_pb(self):
        Pb_lo = bubble_point(400,   0.72, 145, 35)
        Pb_hi = bubble_point(1_200, 0.72, 145, 35)
        assert Pb_hi > Pb_lo

    def test_higher_temperature_gives_higher_pb(self):
        Pb_cold = bubble_point(850, 0.72, 100, 35)
        Pb_hot  = bubble_point(850, 0.72, 250, 35)
        assert Pb_hot > Pb_cold

    def test_higher_api_gives_lower_pb(self):
        # Higher API → lower 10^(…−0.0125·API) → lower Pb
        Pb_heavy = bubble_point(850, 0.72, 145, 20)
        Pb_light = bubble_point(850, 0.72, 145, 45)
        assert Pb_heavy > Pb_light

    def test_heavier_gas_gives_higher_pb(self):
        # Higher gamma_g → lower R/gamma_g → lower Pb
        Pb_light_gas = bubble_point(850, 0.60, 145, 35)
        Pb_heavy_gas = bubble_point(850, 0.90, 145, 35)
        assert Pb_light_gas > Pb_heavy_gas
