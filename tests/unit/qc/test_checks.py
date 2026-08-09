import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.qc.checks import composition_normalization, hoffman_crump, mw_consistency
from pvt.qc.engine import Severity
from tests.fixtures import sa372


def test_normalization_review_band():
    sto = CompositionStream(library=KF.with_c36_mw(635.0), mol_pct=sa372.STO_MOL_PCT)
    qc = composition_normalization.check(sto, "mol")
    assert qc.severity == Severity.REVIEW        # GOLDEN: raw sum 99.31 -> "REVIEW" (I67)


def test_normalization_wt_basis_pass():
    # Not part of the brief's golden set: exercises the wt-basis branch of
    # composition_normalization.check (the brief's golden only covers "mol").
    stream = CompositionStream(library=KF, wt_pct={"C1": 40.0, "C2": 60.0})
    qc = composition_normalization.check(stream, "wt")
    assert qc.severity == Severity.PASS
    assert qc.value == pytest.approx(0.0)


def test_hoffman_b_factor_matches_reference():
    # GOLDEN(loose): PVT-check Hoffman sheet, C1 at Tsep=55.4F: b=805.4586 with ITS table;
    # KF library Tb/Pc/Tc differ in the 3rd digit -> 1% tolerance.
    res = hoffman_crump.check(
        CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0}),
        CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0}),
        p_psia=355.0, t_f=55.4)
    c1 = next(p for p in res.points if p.code == "C1")
    b_c1 = c1.f_factor / (1 / KF.get("C1").tb_r - 1 / (55.4 + 459.67))
    assert b_c1 == pytest.approx(805.4586, rel=0.01)


def test_hoffman_r2_perfect_for_two_points():
    res = hoffman_crump.check(
        CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0}),
        CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0}),
        p_psia=355.0, t_f=55.4)
    assert res.r_squared == pytest.approx(1.0, abs=1e-12)   # 2 points define the line
    assert res.qc.severity == Severity.PASS


def test_hoffman_crump_excludes_missing_and_nonpositive_components():
    # Not part of the brief's golden set: the brief's interface requires
    # "per component present in both streams with x>0 and y>0" -- the two
    # golden tests above never exercise the exclusion paths (every component
    # in their gas/liquid pair is present in both, with positive values).
    # N2 is gas-only (absent from liquid); CO2 is present in both but zero
    # in the gas stream -- covering both the "missing from other stream" and
    # "non-positive fraction" exclusion branches with real fixture-shaped data.
    gas = CompositionStream(library=KF, mol_pct={"C1": 89.0, "C3": 10.0, "N2": 1.0, "CO2": 0.0})
    liquid = CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 79.0, "CO2": 1.0})
    res = hoffman_crump.check(gas, liquid, p_psia=355.0, t_f=55.4)
    codes = {p.code for p in res.points}
    assert codes == {"C1", "C3"}
    assert res.qc.check_id == "hoffman_r2"


def test_mw_consistency_grades():
    sto = CompositionStream(library=KF.with_c36_mw(635.0), mol_pct=sa372.STO_MOL_PCT)
    derived = CompositionStream(library=sto.library, mol_pct=sa372.STO_MOL_PCT,
                                wt_pct=sto.wt_from_mol())
    assert mw_consistency.check(derived).severity == Severity.PASS
