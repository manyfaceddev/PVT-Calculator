import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.experiments.recombination.molar import GorBasis, molar_split, wellstream
from tests.fixtures import sa372


# GOLDEN: ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx, Recombination sheet
def _split():
    return molar_split(339.0, GorBasis.STOCK_TANK, 1.0,
                       sto_density_g_cc=0.8196, sto_mw=187.05, gas_mw=26.10, z_std=0.99)

def test_golden_molar_split():
    s = _split()
    assert s.gor_cc_cc == pytest.approx(60.378, abs=0.001)            # B25
    assert s.n_gas_per_cc_sto == pytest.approx(0.00258036, rel=1e-4)  # B26
    assert s.n_oil_per_cc_sto == pytest.approx(0.00438162, rel=1e-4)  # B27
    assert s.f_gas == pytest.approx(0.370636, abs=1e-5)               # B29
    assert s.w_gas == pytest.approx(0.075937, abs=1e-5)               # B31
    assert s.mw_wellstream == pytest.approx(127.40, abs=0.01)         # B33

def test_golden_wellstream_composition():
    lib = KF.with_c36_mw(635.0)
    sto = CompositionStream(library=lib, mol_pct=sa372.STO_MOL_PCT)
    gas = CompositionStream(library=lib, mol_pct=sa372.GAS_MOL_PCT)
    ws = wellstream(_split(), sto, gas)
    z = ws.normalized_mol()
    assert z["C1"] == pytest.approx(23.17, abs=0.02)                  # J-col, C1 row
    assert z["C36+"] == pytest.approx(2.97, abs=0.01)
    assert sum(z.values()) == pytest.approx(100.0, abs=1e-9)

def test_separator_basis_direction():
    # D-018: conventional direction — separator GOR (scf/sep-bbl) / shrinkage -> STO basis.
    sep = molar_split(339.0, GorBasis.SEPARATOR, 0.8, 0.8196, 187.05, 26.10)
    st = molar_split(339.0, GorBasis.STOCK_TANK, 0.8, 0.8196, 187.05, 26.10)
    assert sep.gor_scf_stb_effective == pytest.approx(339.0 / 0.8)
    assert st.gor_scf_stb_effective == pytest.approx(339.0)
