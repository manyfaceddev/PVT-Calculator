"""
tests/test_recombination_calc.py — Core calculation tests for separator recombination.

Key invariants tested
---------------------
1. Mass balance      — V_oil_sep + total_V_gas_recomb_cc == V_live (exact)
2. GOR round-trip    — GOR_check == R_total_input (within floating-point noise)
3. Bo_sep identity   — V_oil_STO == V_oil_sep / Bo_sep
4. Mix-ratio formula — cylinder_mix_ratio drives the oil/gas split correctly
5. pct_of_total      — sums to 100 % across all stages
6. Unit-system parity — field and SI routes produce consistent results
7. Physical trends   — higher P_recomb → smaller gas volume at recomb
"""

import pytest
from pvt.recombination.models import SeparatorStage
from pvt.recombination.calc import calculate_multistage
from pvt.constants import SCF_STB_TO_CC_CC, BARA_TO_PSIA, P_STD_PSIA, T_STD_R


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def single_stage_field():
    """Typical North-Sea-style single stage in field units."""
    stage = SeparatorStage(R=850, P=815, T=145, Z=0.855, label="Separator")
    return dict(
        stages=[stage],
        V_live=300.0,
        Bo_sep=1.0,
        P_recomb=5014.7,   # psia  (≈ 5000 psig)
        T_recomb=200.0,    # °F
        Z_recomb=0.82,
        units="field",
    )


@pytest.fixture
def two_stage_field():
    """Two-stage separator in field units."""
    stages = [
        SeparatorStage(R=800, P=800, T=140, Z=0.865, label="HP Sep"),
        SeparatorStage(R=50,  P=65,  T=100, Z=0.977, label="LP Sep"),
    ]
    return dict(
        stages=stages,
        V_live=500.0,
        Bo_sep=1.05,
        P_recomb=5014.7,
        T_recomb=200.0,
        Z_recomb=0.82,
        units="field",
    )


# ---------------------------------------------------------------------------
# 1. Mass balance  (critical invariant)
# ---------------------------------------------------------------------------

class TestMassBalance:
    def test_single_stage_oil_plus_gas_equals_v_live(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.V_oil_sep + res.total_V_gas_recomb_cc == pytest.approx(
            single_stage_field["V_live"], rel=1e-12
        )

    def test_two_stage_oil_plus_gas_equals_v_live(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        assert res.V_oil_sep + res.total_V_gas_recomb_cc == pytest.approx(
            two_stage_field["V_live"], rel=1e-12
        )

    @pytest.mark.parametrize("v_live", [50.0, 150.0, 300.0, 1000.0])
    def test_mass_balance_at_various_live_volumes(self, v_live):
        stage = SeparatorStage(R=850, P=815, T=145, Z=0.855)
        res   = calculate_multistage(
            [stage], V_live=v_live, Bo_sep=1.0,
            P_recomb=5014.7, T_recomb=200.0, Z_recomb=0.82, units="field",
        )
        assert res.V_oil_sep + res.total_V_gas_recomb_cc == pytest.approx(v_live, rel=1e-12)

    def test_mass_balance_multi_stage_gas_sum_correct(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        stage_gas_sum = sum(sr.V_gas_recomb_cc for sr in res.stage_results)
        assert stage_gas_sum == pytest.approx(res.total_V_gas_recomb_cc, rel=1e-12)


# ---------------------------------------------------------------------------
# 2. GOR round-trip
# ---------------------------------------------------------------------------

class TestGORRoundTrip:
    def test_single_stage_gor_check_matches_input(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.GOR_check == pytest.approx(res.R_total_input, rel=1e-10)

    def test_two_stage_gor_check_matches_input(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        assert res.GOR_check == pytest.approx(res.R_total_input, rel=1e-10)

    def test_r_total_input_is_sum_of_stage_gors_field(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        # In field units: R_total = sum of individual stage GORs
        assert res.R_total_input == pytest.approx(
            sum(s.R for s in two_stage_field["stages"]), rel=1e-10
        )


# ---------------------------------------------------------------------------
# 3. Bo_sep identity
# ---------------------------------------------------------------------------

class TestBoSep:
    def test_v_oil_sto_equals_v_oil_sep_over_bo(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.V_oil_STO == pytest.approx(res.V_oil_sep / single_stage_field["Bo_sep"],
                                               rel=1e-12)

    @pytest.mark.parametrize("bo", [0.95, 1.00, 1.10, 1.25, 1.50])
    def test_v_oil_sto_scales_with_bo(self, bo):
        stage = SeparatorStage(R=850, P=815, T=145, Z=0.855)
        res   = calculate_multistage(
            [stage], V_live=300.0, Bo_sep=bo,
            P_recomb=5014.7, T_recomb=200.0, Z_recomb=0.82, units="field",
        )
        assert res.V_oil_STO == pytest.approx(res.V_oil_sep / bo, rel=1e-12)

    def test_higher_bo_gives_more_oil_to_charge(self):
        """
        cylinder_mix_ratio = R_cc × factor_recomb / Bo_sep

        Higher Bo_sep divides the mix ratio → lower CMR → more separator oil
        needed per cc of live fluid (V_oil_sep = V_live / (1 + CMR) goes up).
        """
        stage = SeparatorStage(R=850, P=815, T=145, Z=0.855)
        kwargs = dict(V_live=300.0, P_recomb=5014.7, T_recomb=200.0,
                      Z_recomb=0.82, units="field", stages=[stage])
        res_lo_bo = calculate_multistage(**kwargs, Bo_sep=1.0)
        res_hi_bo = calculate_multistage(**kwargs, Bo_sep=1.2)
        # Higher Bo → lower cylinder_mix_ratio → more separator oil to charge
        assert res_hi_bo.cylinder_mix_ratio < res_lo_bo.cylinder_mix_ratio
        assert res_hi_bo.V_oil_sep > res_lo_bo.V_oil_sep


# ---------------------------------------------------------------------------
# 4. Cylinder mix ratio formula
# ---------------------------------------------------------------------------

class TestCylinderMixRatio:
    def test_mix_ratio_drives_volume_split(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        # V_gas_recomb / V_oil_sep == cylinder_mix_ratio (by construction)
        assert res.total_V_gas_recomb_cc / res.V_oil_sep == pytest.approx(
            res.cylinder_mix_ratio, rel=1e-10
        )

    def test_mix_ratio_formula_manual(self, single_stage_field):
        """Verify cylinder_mix_ratio against manual computation."""
        kw = single_stage_field
        P_recomb_psia = kw["P_recomb"]
        T_recomb_R    = kw["T_recomb"] + 459.67
        factor_recomb = (P_STD_PSIA / P_recomb_psia) * (T_recomb_R / T_STD_R) * kw["Z_recomb"]
        R_cc          = kw["stages"][0].R * SCF_STB_TO_CC_CC
        expected_cmr  = R_cc * factor_recomb / kw["Bo_sep"]

        res = calculate_multistage(**kw)
        assert res.cylinder_mix_ratio == pytest.approx(expected_cmr, rel=1e-10)

    def test_mix_ratio_is_positive(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.cylinder_mix_ratio > 0


# ---------------------------------------------------------------------------
# 5. Per-stage percentages
# ---------------------------------------------------------------------------

class TestStagePercentages:
    def test_single_stage_pct_is_100(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.stage_results[0].pct_of_total == pytest.approx(100.0, rel=1e-10)

    def test_two_stage_pcts_sum_to_100(self, two_stage_field):
        res  = calculate_multistage(**two_stage_field)
        total = sum(sr.pct_of_total for sr in res.stage_results)
        assert total == pytest.approx(100.0, rel=1e-10)

    def test_pcts_proportional_to_gor_contribution(self, two_stage_field):
        res  = calculate_multistage(**two_stage_field)
        stages = two_stage_field["stages"]
        total_gor = sum(s.R for s in stages)
        for sr, stage in zip(res.stage_results, stages):
            expected_pct = stage.R / total_gor * 100.0
            assert sr.pct_of_total == pytest.approx(expected_pct, rel=1e-10)


# ---------------------------------------------------------------------------
# 6. Unit-system parity
# ---------------------------------------------------------------------------

class TestUnitParity:
    def test_si_and_field_give_same_v_oil_sep(self):
        """
        Identical physical conditions expressed in both unit systems should
        yield the same separator oil volume (cc is cc regardless of units).
        """
        # Field: P=815 psia, T=145°F, R=850 scf/STB
        # SI equivalents
        P_bara   = 815 / BARA_TO_PSIA
        T_C      = (145 - 32) * 5 / 9
        R_sm3    = 850 * SCF_STB_TO_CC_CC   # sm³/sm³ == cc/cc  → same numeric value
        P_r_bara = 5014.7 / BARA_TO_PSIA
        T_r_C    = (200 - 32) * 5 / 9

        stage_f  = SeparatorStage(R=850,   P=815,    T=145,  Z=0.855)
        stage_si = SeparatorStage(R=R_sm3, P=P_bara, T=T_C,  Z=0.855)

        res_f  = calculate_multistage(
            [stage_f],  V_live=300.0, Bo_sep=1.0,
            P_recomb=5014.7,   T_recomb=200.0, Z_recomb=0.82, units="field",
        )
        res_si = calculate_multistage(
            [stage_si], V_live=300.0, Bo_sep=1.0,
            P_recomb=P_r_bara, T_recomb=T_r_C,  Z_recomb=0.82, units="si",
        )

        assert res_f.V_oil_sep           == pytest.approx(res_si.V_oil_sep,           rel=1e-6)
        assert res_f.total_V_gas_recomb_cc == pytest.approx(res_si.total_V_gas_recomb_cc, rel=1e-6)
        assert res_f.cylinder_mix_ratio  == pytest.approx(res_si.cylinder_mix_ratio,  rel=1e-6)

    def test_si_units_reported_in_correct_unit_attribute(self):
        stage = SeparatorStage(R=151.4, P=55.8, T=62.8, Z=0.865)
        res   = calculate_multistage(
            [stage], V_live=300.0, Bo_sep=1.0,
            P_recomb=346.7, T_recomb=93.3, Z_recomb=0.82, units="si",
        )
        assert res.units == "si"

    def test_field_units_reported_correctly(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.units == "field"


# ---------------------------------------------------------------------------
# 7. Physical trends
# ---------------------------------------------------------------------------

class TestPhysicalTrends:
    def test_higher_recomb_pressure_gives_smaller_gas_volume(self):
        """Gas is more compressed at higher P → less cc of gas to charge."""
        stage  = SeparatorStage(R=850, P=815, T=145, Z=0.855)
        common = dict(stages=[stage], V_live=300.0, Bo_sep=1.0,
                      T_recomb=200.0, Z_recomb=0.82, units="field")
        res_lo = calculate_multistage(**common, P_recomb=2_000.0)
        res_hi = calculate_multistage(**common, P_recomb=8_000.0)
        assert res_hi.total_V_gas_recomb_cc < res_lo.total_V_gas_recomb_cc

    def test_higher_recomb_pressure_leaves_more_oil(self):
        stage  = SeparatorStage(R=850, P=815, T=145, Z=0.855)
        common = dict(stages=[stage], V_live=300.0, Bo_sep=1.0,
                      T_recomb=200.0, Z_recomb=0.82, units="field")
        res_lo = calculate_multistage(**common, P_recomb=2_000.0)
        res_hi = calculate_multistage(**common, P_recomb=8_000.0)
        assert res_hi.V_oil_sep > res_lo.V_oil_sep

    def test_higher_gor_gives_more_gas_and_less_oil(self):
        common = dict(V_live=300.0, Bo_sep=1.0,
                      P_recomb=5014.7, T_recomb=200.0, Z_recomb=0.82, units="field")
        stage_lo = SeparatorStage(R=400,   P=815, T=145, Z=0.855)
        stage_hi = SeparatorStage(R=1_200, P=815, T=145, Z=0.855)
        res_lo   = calculate_multistage(stages=[stage_lo], **common)
        res_hi   = calculate_multistage(stages=[stage_hi], **common)
        assert res_hi.total_V_gas_recomb_cc > res_lo.total_V_gas_recomb_cc
        assert res_hi.V_oil_sep < res_lo.V_oil_sep

    def test_recomb_conditions_stored_on_result(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.P_recomb_psia == pytest.approx(single_stage_field["P_recomb"])
        assert res.T_recomb_F    == pytest.approx(single_stage_field["T_recomb"])
        assert res.Z_recomb      == pytest.approx(single_stage_field["Z_recomb"])

    def test_v_live_echoed_on_result(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        assert res.V_live == pytest.approx(single_stage_field["V_live"])


# ---------------------------------------------------------------------------
# 8. Stage-level outputs
# ---------------------------------------------------------------------------

class TestStageOutputs:
    def test_stage_num_assigned_correctly(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        assert [sr.stage_num for sr in res.stage_results] == [1, 2]

    def test_stage_label_propagated(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        assert res.stage_results[0].label == "HP Sep"
        assert res.stage_results[1].label == "LP Sep"

    def test_stage_r_input_matches_input_gor(self, two_stage_field):
        res    = calculate_multistage(**two_stage_field)
        stages = two_stage_field["stages"]
        for sr, stage in zip(res.stage_results, stages):
            assert sr.R_input == pytest.approx(stage.R, rel=1e-12)

    def test_stage_gas_std_cc_sums_to_total(self, two_stage_field):
        res = calculate_multistage(**two_stage_field)
        assert sum(sr.V_gas_std_cc for sr in res.stage_results) == pytest.approx(
            res.total_V_gas_std_cc, rel=1e-12
        )

    def test_v_gas_sep_positive_for_valid_inputs(self, single_stage_field):
        res = calculate_multistage(**single_stage_field)
        for sr in res.stage_results:
            assert sr.V_gas_sep > 0

    def test_v_gas_recomb_less_than_v_gas_sep_at_high_recomb_pressure(self):
        """At high recombination pressure, gas is more compressed than at sep pressure."""
        stage = SeparatorStage(R=850, P=65, T=100, Z=0.977)  # low-P separator
        res   = calculate_multistage(
            [stage], V_live=300.0, Bo_sep=1.0,
            P_recomb=5014.7, T_recomb=200.0, Z_recomb=0.82, units="field",
        )
        sr = res.stage_results[0]
        # Recomb P (5014 psia) >> sep P (65 psia) → gas more compressed at recomb
        assert sr.V_gas_recomb_cc < sr.V_gas_sep
