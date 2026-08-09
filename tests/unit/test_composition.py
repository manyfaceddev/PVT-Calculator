import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from tests.fixtures import sa372

def _sto():
    return CompositionStream(library=KF.with_c36_mw(sa372.STO_C36_MW), mol_pct=sa372.STO_MOL_PCT)

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
