"""tests/test_constants.py — Verify physical constants and unit conversions."""

import pytest
from pvt.constants import (
    P_STD_PSIA,
    T_STD_F,
    T_STD_R,
    SCF_TO_CC,
    STB_TO_CC,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
    CC_TO_SM3,
)


class TestStandardConditions:
    def test_p_std_psia(self):
        assert P_STD_PSIA == pytest.approx(14.696)

    def test_t_std_f(self):
        assert T_STD_F == pytest.approx(60.0)

    def test_t_std_r_is_t_std_f_plus_offset(self):
        assert T_STD_R == pytest.approx(T_STD_F + 459.67)

    def test_t_std_r_value(self):
        assert T_STD_R == pytest.approx(519.67)


class TestVolumeConversions:
    def test_scf_to_cc(self):
        # 1 scf = 28 316.85 cc  (28.31685 L — standard cubic foot)
        assert SCF_TO_CC == pytest.approx(28_316.85, rel=1e-4)

    def test_stb_to_cc(self):
        # 1 STB = 42 US gallons; 1 gal = 3785.41 cc → 42 * 3785.41 = 158 987.2 cc
        assert STB_TO_CC == pytest.approx(42 * 3785.412, rel=1e-3)

    def test_scf_stb_to_cc_cc_is_ratio(self):
        """SCF_STB_TO_CC_CC must equal SCF_TO_CC / STB_TO_CC exactly."""
        assert SCF_STB_TO_CC_CC == pytest.approx(SCF_TO_CC / STB_TO_CC, rel=1e-12)

    def test_scf_stb_to_cc_cc_approx_value(self):
        # ~0.1781 is well-known in petroleum engineering
        assert SCF_STB_TO_CC_CC == pytest.approx(0.17811, rel=1e-3)

    def test_cc_to_sm3(self):
        # 1 sm³ = 1 000 000 cc
        assert CC_TO_SM3 == pytest.approx(1e-6)


class TestPressureConversions:
    def test_bara_to_psia(self):
        # 1 bara = 14.5038 psia
        assert BARA_TO_PSIA == pytest.approx(14.5038, rel=1e-4)

    def test_1_atm_approximately(self):
        # 1 atm ≈ 14.696 psia ≈ 1.01325 bara → ratio ≈ 14.504
        assert BARA_TO_PSIA == pytest.approx(14.504, rel=1e-3)
