import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF, Component, ComponentLibrary
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from tests.fixtures import sa372

def _sto():
    return CompositionStream(library=KF.with_c36_mw(sa372.STO_C36_MW), mol_pct=sa372.STO_MOL_PCT)

# Tiny two-component library with power-of-two MW/density so that
# deliberately canceling mol%/wt% values sum to *exactly* zero in floating
# point (no rounding noise) — used to exercise the defensive zero-denominator
# guards below.
_CANCEL_LIB = ComponentLibrary({
    "A": Component(code="A", name="A", mw=2.0, liquid_density_g_cc=2.0,
                    tb_r=1.0, pc_psia=1.0, tc_r=1.0),
    "B": Component(code="B", name="B", mw=4.0, liquid_density_g_cc=4.0,
                    tb_r=1.0, pc_psia=1.0, tc_r=1.0),
})

def test_normalized_mol_sums_to_100():
    assert sum(_sto().normalized_mol().values()) == pytest.approx(100.0, abs=1e-9)

def test_raw_sum_preserved():
    assert _sto().raw_mol_sum() == pytest.approx(99.31, abs=0.01)   # workbook I66 → "REVIEW"

def test_mw_from_mol_matches_workbook():
    assert _sto().mw_from_mol() == pytest.approx(sa372.STO_MW_FROM_MOL, rel=2e-4)

def test_gas_stream_mw_and_gravity():
    gas = CompositionStream(library=KF, mol_pct=sa372.GAS_MOL_PCT)
    assert gas.mw_from_mol() == pytest.approx(sa372.GAS_MW_FROM_MOL, rel=2e-3)
    assert gas.gas_gravity() == pytest.approx(sa372.GAS_MW_FROM_MOL / 28.964, rel=2e-3)

def test_wt_from_mol_round_trips_mw():
    sto = _sto()
    derived = CompositionStream(library=sto.library, wt_pct=sto.wt_from_mol())
    assert derived.mw_from_wt() == pytest.approx(sto.mw_from_mol(), rel=1e-9)

def test_unknown_component_rejected():
    with pytest.raises(InputValidationError):
        CompositionStream(library=KF, mol_pct={"C99": 100.0})

def test_needs_at_least_one_basis():
    with pytest.raises(InputValidationError):
        CompositionStream(library=KF)


# ---------------------------------------------------------------------------
# Zero-sum guards — one all-zero-value composition per raw-sum check
# ---------------------------------------------------------------------------

def test_normalized_mol_zero_sum_raises():
    cs = CompositionStream(library=KF, mol_pct={"C1": 0.0})
    with pytest.raises(InputValidationError):
        cs.normalized_mol()

def test_normalized_wt_zero_sum_raises():
    cs = CompositionStream(library=KF, wt_pct={"C1": 0.0})
    with pytest.raises(InputValidationError):
        cs.normalized_wt()

def test_mw_from_mol_zero_sum_raises():
    cs = CompositionStream(library=KF, mol_pct={"C1": 0.0})
    with pytest.raises(InputValidationError):
        cs.mw_from_mol()


# ---------------------------------------------------------------------------
# mw_consistency_pct / liquid_density_ideal_g_cc — normal path
# ---------------------------------------------------------------------------

def test_mw_consistency_pct_near_zero_for_self_derived_wt():
    """mol → wt_from_mol() → wt basis should round-trip mw to ~0% error."""
    sto = _sto()
    both = CompositionStream(library=sto.library, mol_pct=sto.mol_pct, wt_pct=sto.wt_from_mol())
    assert both.mw_consistency_pct() == pytest.approx(0.0, abs=1e-9)

def test_liquid_density_ideal_matches_workbook():
    sto = _sto()
    both = CompositionStream(library=sto.library, mol_pct=sto.mol_pct, wt_pct=sto.wt_from_mol())
    assert both.liquid_density_ideal_g_cc() == pytest.approx(sa372.STO_DENSITY_60F, rel=0.02)


# ---------------------------------------------------------------------------
# Zero-denominator guards reachable only once a basis is already normalized
# (mw_from_wt, wt_from_mol, liquid_density_ideal_g_cc) — need deliberately
# canceling +/- values, since a real (non-negative) composition can never
# hit these once its raw sum is non-zero.
# ---------------------------------------------------------------------------

def test_mw_from_wt_zero_denominator_raises():
    cs = CompositionStream(library=_CANCEL_LIB, wt_pct={"A": 4.0, "B": -8.0})
    with pytest.raises(InputValidationError):
        cs.mw_from_wt()

def test_wt_from_mol_zero_denominator_raises():
    cs = CompositionStream(library=_CANCEL_LIB, mol_pct={"A": 4.0, "B": -2.0})
    with pytest.raises(InputValidationError):
        cs.wt_from_mol()

def test_liquid_density_ideal_zero_denominator_raises():
    cs = CompositionStream(library=_CANCEL_LIB, wt_pct={"A": 4.0, "B": -8.0})
    with pytest.raises(InputValidationError):
        cs.liquid_density_ideal_g_cc()
