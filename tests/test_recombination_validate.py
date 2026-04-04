"""tests/test_recombination_validate.py — Input validation for recombination."""

import pytest
from pvt.recombination.models import SeparatorStage
from pvt.recombination.validate import validate_multistage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_stage():
    return SeparatorStage(R=850, P=815, T=145, Z=0.855, label="Separator")


@pytest.fixture
def valid_kwargs():
    """Keyword args that should produce zero validation errors in field units."""
    return dict(V_live=300.0, SF=1.0, P_recomb=5014.7, T_recomb=200.0,
                Z_recomb=0.82, units="field")


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestValidInput:
    def test_single_stage_field_units_is_valid(self, valid_stage, valid_kwargs):
        errors = validate_multistage([valid_stage], **valid_kwargs)
        assert errors == []

    def test_multistage_field_units_is_valid(self, valid_kwargs):
        stages = [
            SeparatorStage(R=800, P=800, T=140, Z=0.865, label="HP Sep"),
            SeparatorStage(R=50,  P=65,  T=100, Z=0.977, label="LP Sep"),
        ]
        errors = validate_multistage(stages, **valid_kwargs)
        assert errors == []

    def test_si_units_is_valid(self):
        stage  = SeparatorStage(R=151.4, P=55.8, T=62.8, Z=0.865)
        errors = validate_multistage(
            [stage],
            V_live=300.0, SF=1.0, P_recomb=346.7, T_recomb=93.3,
            Z_recomb=0.82, units="si",
        )
        assert errors == []


# ---------------------------------------------------------------------------
# Stage-level errors
# ---------------------------------------------------------------------------

class TestStageErrors:
    def test_empty_stages_list(self, valid_kwargs):
        errors = validate_multistage([], **valid_kwargs)
        assert any("stage" in e.lower() for e in errors)

    def test_negative_gor(self, valid_kwargs):
        stage  = SeparatorStage(R=-1, P=815, T=145, Z=0.855)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("GOR" in e for e in errors)

    def test_zero_gor(self, valid_kwargs):
        stage  = SeparatorStage(R=0, P=815, T=145, Z=0.855)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("GOR" in e for e in errors)

    def test_negative_pressure(self, valid_kwargs):
        stage  = SeparatorStage(R=850, P=-10, T=145, Z=0.855)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("pressure" in e.lower() for e in errors)

    def test_zero_z_factor(self, valid_kwargs):
        stage  = SeparatorStage(R=850, P=815, T=145, Z=0.0)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("Z-factor" in e for e in errors)

    def test_z_factor_above_limit(self, valid_kwargs):
        stage  = SeparatorStage(R=850, P=815, T=145, Z=2.1)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("Z-factor" in e for e in errors)

    def test_temperature_too_low_field(self, valid_kwargs):
        stage  = SeparatorStage(R=850, P=815, T=-200, Z=0.855)
        errors = validate_multistage([stage], **valid_kwargs)
        assert any("temperature" in e.lower() for e in errors)

    def test_temperature_too_low_si(self):
        stage  = SeparatorStage(R=151.4, P=55.8, T=-100, Z=0.865)
        errors = validate_multistage(
            [stage],
            V_live=300.0, SF=1.0, P_recomb=346.7, T_recomb=93.3,
            Z_recomb=0.82, units="si",
        )
        assert any("temperature" in e.lower() for e in errors)


# ---------------------------------------------------------------------------
# Global / recombination-level errors
# ---------------------------------------------------------------------------

class TestGlobalErrors:
    def test_zero_v_live(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "V_live": 0.0}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("live" in e.lower() or "volume" in e.lower() for e in errors)

    def test_negative_v_live(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "V_live": -50.0}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("live" in e.lower() or "volume" in e.lower() for e in errors)

    def test_zero_sf(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "SF": 0.0}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("SF" in e or "Shrinkage" in e for e in errors)

    def test_sf_above_limit(self, valid_stage, valid_kwargs):
        """SF > 1.0 would mean oil expands going to stock tank — physically impossible."""
        kwargs = {**valid_kwargs, "SF": 1.1}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("SF" in e or "Shrinkage" in e for e in errors)

    def test_zero_p_recomb(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "P_recomb": 0.0}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("recomb" in e.lower() and "pressure" in e.lower() for e in errors)

    def test_negative_z_recomb(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "Z_recomb": -0.1}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("Z-factor" in e for e in errors)

    def test_z_recomb_above_limit(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "Z_recomb": 2.5}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("Z-factor" in e for e in errors)

    def test_recomb_temperature_too_low_field(self, valid_stage, valid_kwargs):
        kwargs = {**valid_kwargs, "T_recomb": -200.0}
        errors = validate_multistage([valid_stage], **kwargs)
        assert any("recomb" in e.lower() and "temperature" in e.lower() for e in errors)

    def test_multiple_errors_returned(self, valid_kwargs):
        # Bad GOR and bad Z together → at least two errors
        stage  = SeparatorStage(R=-1, P=815, T=145, Z=5.0)
        errors = validate_multistage([stage], **valid_kwargs)
        assert len(errors) >= 2
