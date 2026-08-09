"""tests/unit/test_constants.py — Verify canonical physical constants and unit conversions."""

import pytest
from pvt.core import constants as c


class TestLabStandardConditions:
    """Lab standard conditions per ADRIC sheets."""

    def test_p_std_psia(self):
        assert c.P_STD_PSIA == 14.73

    def test_t_std_f(self):
        assert c.T_STD_F == 60.0

    def test_t_std_r(self):
        assert c.T_STD_R == 519.67

    def test_t_std_k(self):
        assert c.T_STD_K == pytest.approx(288.7056)

    def test_p_std_mbar(self):
        assert c.P_STD_MBAR == pytest.approx(1015.5981)

    def test_rankine_offset(self):
        assert c.RANKINE_OFFSET == 459.67

    def test_kelvin_offset(self):
        assert c.KELVIN_OFFSET == 273.15


class TestVolumeConversions:
    """Volume conversion factors."""

    def test_cc_per_scf(self):
        # 1 scf = 28,316.85 cc (standard cubic foot)
        assert c.CC_PER_SCF == 28316.85

    def test_cc_per_stb(self):
        # 1 STB = 42 US gallons; lab sheets use 158987.29 cc (NIST: 158987.294928)
        assert c.CC_PER_STB == 158987.29

    def test_scf_per_lbmol(self):
        # 1 lbmol ideal gas @ STP ≈ 379.482 scf
        assert c.SCF_PER_LBMOL == 379.482

    def test_scf_per_lbmol_matches_atm_basis_molar_volume(self):
        # SCF_PER_LBMOL is the molar volume at the 14.696 psia atmosphere
        # basis (R * T_STD_R / P_ATM_PSIA), NOT the 14.73 psia lab basis
        # (which would give ~378.61 scf/lbmol instead).
        molar_volume_atm_basis = c.R_PSIA_FT3_LBMOL_R * c.T_STD_R / c.P_ATM_PSIA
        assert abs(c.SCF_PER_LBMOL - molar_volume_atm_basis) < 0.01

    def test_ft3_per_bbl(self):
        # 1 bbl = 5.61458 ft³
        assert c.FT3_PER_BBL == 5.61458

    def test_scf_stb_to_cc_cc_ratio(self):
        # Ratio of volumes: scf per STB → cc per cc
        assert c.SCF_STB_TO_CC_CC == pytest.approx(c.CC_PER_SCF / c.CC_PER_STB, rel=1e-12)

    def test_scf_stb_to_cc_cc_approx_value(self):
        # ~0.178108 is well-known in petroleum engineering
        assert c.SCF_STB_TO_CC_CC == pytest.approx(0.178108, rel=1e-5)


class TestGasConstants:
    """Physical constants for gas calculations."""

    def test_air_mw(self):
        # Molecular weight of air
        assert c.AIR_MW == 28.964

    def test_air_density_std(self):
        # Air density at lab standard conditions (14.73 psia, 60°F)
        assert c.AIR_DENSITY_STD_G_CC == 0.0012255

    def test_r_psia_ft3_lbmol_r(self):
        # Universal gas constant in US field units
        assert c.R_PSIA_FT3_LBMOL_R == 10.7316

    def test_r_psia_cc_mol_k(self):
        # Universal gas constant in mixed units (psia·cc/mol·K)
        # R[atm·cc/mol/K] = 82.057, 1 atm = 14.696 psia
        assert c.R_PSIA_CC_MOL_K == pytest.approx(82.057 * 14.696, rel=1e-4)

    def test_gas_constants_consistency(self):
        # Both R constants should be consistent
        assert c.R_PSIA_FT3_LBMOL_R == 10.7316
        assert c.R_PSIA_CC_MOL_K == pytest.approx(1205.91)


class TestConversionFactors:
    """Unit conversion factors."""

    def test_g_per_lb(self):
        # Grams per pound
        assert c.G_PER_LB == 453.59237

    def test_psia_per_bara(self):
        # 1 bara = 14.5038 psia
        assert c.PSIA_PER_BARA == 14.5038

    def test_water_density_60f(self):
        # Water density at 60°F (standard lab temperature)
        assert c.WATER_DENSITY_60F_G_CC == 0.9991

    def test_p_atm_psia(self):
        # Standard atmospheric pressure
        assert c.P_ATM_PSIA == 14.696


class TestTypeAlias:
    """Type alias for unit systems."""

    def test_units_type_exists(self):
        # Verify Units type alias is available
        from typing import get_args
        assert get_args(c.Units) == ("field", "si")


class TestLabConditionsConsistency:
    """Lab standard conditions consistency checks."""

    def test_lab_standard_conditions(self):
        assert c.P_STD_PSIA == 14.73
        assert c.T_STD_R == 519.67
        assert c.T_STD_K == pytest.approx(288.7056)
        assert c.P_STD_MBAR == pytest.approx(1015.5981)


class TestGasConstantsConsistent:
    """Verify gas constant values are internally consistent."""

    def test_gas_constants_consistent(self):
        # R in psia·cc/(mol·K) derived from R[atm·cc/mol/K]=82.057
        # Conversion: 82.057 * 14.696 psia/atm ≈ 1205.91
        assert c.R_PSIA_CC_MOL_K == pytest.approx(82.057 * 14.696, rel=1e-4)
        assert c.R_PSIA_FT3_LBMOL_R == 10.7316


class TestDerivedRatio:
    """Test derived constants."""

    def test_derived_ratio(self):
        assert c.SCF_STB_TO_CC_CC == pytest.approx(0.178108, rel=1e-5)


class TestAirDensityAtLabStandard:
    """Verify air density matches ideal gas law at lab standard conditions."""

    def test_air_density_matches_ideal_gas_at_lab_std(self):
        # rho = MW·P/(R·T) at 14.73 psia / 288.7056 K, in g/cc
        rho = c.AIR_MW * c.P_STD_PSIA / (c.R_PSIA_CC_MOL_K * c.T_STD_K)
        assert rho == pytest.approx(c.AIR_DENSITY_STD_G_CC, rel=2e-3)


# ============================================================================
# Old test assertions (from tests/test_constants.py) migrated & updated
# ============================================================================

class TestLegacyStandardConditions:
    """Legacy assertions from old test suite (updated to new names)."""

    def test_p_std_psia_legacy(self):
        # Old test used 14.696; new canonical is 14.73
        assert c.P_STD_PSIA == pytest.approx(14.73)

    def test_t_std_f_legacy(self):
        assert c.T_STD_F == pytest.approx(60.0)

    def test_t_std_r_is_t_std_f_plus_offset(self):
        assert c.T_STD_R == pytest.approx(c.T_STD_F + 459.67)

    def test_t_std_r_value_legacy(self):
        assert c.T_STD_R == pytest.approx(519.67)


class TestLegacyVolumeConversions:
    """Legacy volume conversion tests (updated to new constant names)."""

    def test_cc_per_scf_legacy(self):
        # 1 scf = 28,316.85 cc (28.31685 L — standard cubic foot)
        assert c.CC_PER_SCF == pytest.approx(28_316.85, rel=1e-4)

    def test_cc_per_stb_legacy(self):
        # 1 STB = 42 US gallons; canonical uses 158987.29 cc
        # Old value was 158987.1; new value is more precise
        assert c.CC_PER_STB == pytest.approx(158987.29, rel=1e-4)

    def test_scf_stb_to_cc_cc_is_ratio_legacy(self):
        """SCF_STB_TO_CC_CC must equal CC_PER_SCF / CC_PER_STB exactly."""
        assert c.SCF_STB_TO_CC_CC == pytest.approx(c.CC_PER_SCF / c.CC_PER_STB, rel=1e-12)

    def test_scf_stb_to_cc_cc_approx_value_legacy(self):
        # ~0.1781 is well-known in petroleum engineering
        assert c.SCF_STB_TO_CC_CC == pytest.approx(0.17811, rel=1e-3)


class TestLegacyPressureConversions:
    """Legacy pressure conversion tests (updated to new constant names)."""

    def test_psia_per_bara_legacy(self):
        # 1 bara = 14.5038 psia
        assert c.PSIA_PER_BARA == pytest.approx(14.5038, rel=1e-4)

    def test_1_atm_approximately(self):
        # 1 atm ≈ 14.696 psia ≈ 1.01325 bara → ratio ≈ 14.504
        assert c.PSIA_PER_BARA == pytest.approx(14.504, rel=1e-3)


class TestLegacyVolumeConversionsCC_TO_SM3:
    """Legacy: CC_TO_SM3 conversion (now in canonical constants)."""

    def test_cc_to_sm3(self):
        # 1 sm³ = 1,000,000 cc (canonical constant)
        assert c.CC_TO_SM3 == pytest.approx(1e-6)
