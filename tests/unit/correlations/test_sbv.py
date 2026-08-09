import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.correlations.pseudocritical.sbv import pseudo_criticals

def test_golden_equimolar_c1c2c3():
    # GOLDEN: "Z factor calculation.xls" I5/I6 (SBV, sweet). The workbook's own Tc/Pc table
    # differs slightly from the KF library (D-001 canonization); measured deltas vs workbook:
    # Tpc 7.5e-4, Ppc 1.36e-3 relative — tolerance 2e-3 absorbs the table difference while
    # still failing on real formula regressions (the 1e-12 single-component identity test
    # pins the algebra exactly).
    stream = CompositionStream(library=KF, mol_pct={"C1": 100/3, "C2": 100/3, "C3": 100/3})
    tpc, ppc = pseudo_criticals(stream)
    assert tpc == pytest.approx(527.028947342463, rel=2e-3)
    assert ppc == pytest.approx(676.464314208584, rel=2e-3)

def test_single_component_recovers_own_criticals():
    stream = CompositionStream(library=KF, mol_pct={"C1": 100.0})
    tpc, ppc = pseudo_criticals(stream)
    c1 = KF.get("C1")
    assert tpc == pytest.approx(c1.tc_r, rel=1e-12)
    assert ppc == pytest.approx(c1.pc_psia, rel=1e-12)
