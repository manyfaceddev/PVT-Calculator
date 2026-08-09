import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.plus_fractions import plus_fraction
from pvt.experiments.flash.recombine import recombine_mass
from tests.fixtures import sa372_flash as fx


def _streams():
    oil = CompositionStream(library=KF, mol_pct=fx.OIL_MOL_PCT, wt_pct=fx.OIL_WT_PCT)
    gas = CompositionStream(library=KF, mol_pct=fx.GAS_MOL_PCT, wt_pct=fx.GAS_WT_PCT)
    return oil, gas


def test_golden_wf_and_mw():
    oil, gas = _streams()
    r = recombine_mass(13.71, 1.32095, oil, gas)
    assert r.wf_gas == pytest.approx(0.0878821, rel=1e-5)        # Recombination!B18
    assert r.mw_whole_sample == pytest.approx(135.0426, rel=1e-4)  # B21 (Convention A)


def test_golden_c7_plus_of_recombined():
    oil, gas = _streams()
    ws = recombine_mass(13.71, 1.32095, oil, gas).wellstream
    pf = plus_fraction(ws, "C7+")
    # GOLDEN: Plus_Properties_Report, Recombined column
    assert pf.mol_pct == pytest.approx(51.119, abs=0.05)
    assert pf.wt_pct == pytest.approx(84.236, abs=0.05)
    assert pf.mw == pytest.approx(222.53, abs=0.3)
    assert pf.density_g_cc == pytest.approx(0.84661, abs=5e-4)


def test_mol_and_wt_mw_routes_agree():
    oil, gas = _streams()
    ws = recombine_mass(13.71, 1.32095, oil, gas).wellstream
    assert ws.mw_from_mol() == pytest.approx(ws.mw_from_wt(), rel=1e-9)


def test_cut_boundaries():
    oil, _ = _streams()
    c7 = plus_fraction(oil, "C7+")
    # MCP/Benzene/CycloC6 are NOT in C7+ (positional convention, flash workbook rows 57+)
    assert c7.mol_pct == pytest.approx(79.873, abs=0.05)  # GOLDEN: flashed-liquid C7+
