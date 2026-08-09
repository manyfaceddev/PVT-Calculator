import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from pvt.qc.checks import composition_normalization, hoffman_crump, mw_consistency
from pvt.qc.checks.hoffman_crump import HoffmanPoint
from pvt.qc.engine import Severity, ThresholdRegistry
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


def test_hoffman_r2_review_band_three_component_fit():
    # Not part of the brief's golden set: review-round-1 finding -- the
    # hoffman_r2 R^2-floor -> grade() conversion was only ever exercised at
    # r_squared=1.0 (both golden tests), where a regressed/flipped
    # conversion would also pass. This test lands the fit at a KNOWN
    # imperfect R^2, with margin from both band edges, so the conversion's
    # arithmetic (not just its "perfect fit -> PASS" happy path) is checked.
    #
    # OFFLINE derivation (see task-6-report.md "Fix: hoffman_r2 band
    # coverage" for the full search): start from the two-point golden's
    # exact-fit line (C1 y=90/x=20, C3 y=10/x=80 -> K=4.5/0.125, which sit
    # exactly on a line by construction, same as test_hoffman_r2_perfect_
    # for_two_points). Add a third component, nC5, deliberately off that
    # line -- nC5 is heavy (low volatility), so a K far below what the C1/C3
    # line predicts at nC5's F-factor pulls the least-squares R^2 down from
    # 1.0. mol_pct={"C1": 90.0, "C3": 10.0, "nC5": 0.2} (gas) /
    # {"C1": 20.0, "C3": 80.0, "nC5": 5.6} (liquid) at p=355 psia, t=55.4F
    # was found by a small grid/line search (varying only the nC5 liquid
    # fraction) to give r_squared = 0.9656953264177762 -- independently
    # confirmed by calling this module directly during the search, not just
    # derived by hand. That value sits inside [0.95, 0.98) with margin from
    # both edges (~0.016 above the 0.95 floor, ~0.014 below the 0.98 floor),
    # i.e. deviation = 1 - r_squared = 0.03430 sits strictly between the
    # default band's review_at=1-0.98=0.02 and fail_at=1-0.95=0.05 ->
    # REVIEW.
    gas = CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0, "nC5": 0.2})
    liquid = CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0, "nC5": 5.6})
    res = hoffman_crump.check(gas, liquid, p_psia=355.0, t_f=55.4)
    assert res.r_squared == pytest.approx(0.9656953264177762, abs=1e-9)
    assert res.qc.severity == Severity.REVIEW

    # Same imperfect fit, but with hoffman_r2 overridden to a much tighter
    # R^2-floor pair (0.999, 0.998) -> review_at=1-0.999=0.001,
    # fail_at=1-0.998=0.002, both far below the fit's actual deviation
    # (0.0343) -> FAIL. This exercises override-driven severity (not just
    # the house-default band) with the same r_squared as above.
    tight_registry = ThresholdRegistry()
    tight_registry.override("hoffman_r2", 0.999, 0.998, note="test: force FAIL on an imperfect fit")
    res_tight = hoffman_crump.check(gas, liquid, p_psia=355.0, t_f=55.4, registry=tight_registry)
    assert res_tight.r_squared == pytest.approx(res.r_squared)
    assert res_tight.qc.severity == Severity.FAIL


def test_hoffman_crump_zero_qualifying_components_raises_typed_error():
    # Review-round-2 finding: before the fix, fewer than 2 qualifying
    # components (present, positive-mole-fraction, in BOTH streams) reached
    # the least-squares fit's `x_bar = sum(xs) / n` with n=0, raising a raw
    # ZeroDivisionError instead of a typed, actionable error.
    gas = CompositionStream(library=KF, mol_pct={"C1": 100.0})
    liquid = CompositionStream(library=KF, mol_pct={"C10": 100.0})
    with pytest.raises(InputValidationError) as exc_info:
        hoffman_crump.check(gas, liquid, p_psia=355.0, t_f=55.4)
    message = str(exc_info.value).lower()
    assert "at least 2" in message
    assert "found 0" in message


def test_hoffman_crump_one_qualifying_component_raises_typed_error():
    # Same guard, n=1: the fit is still undetermined (a single point can't
    # define a slope) -- also raised a raw ZeroDivisionError before the fix
    # (n=1 makes ss_xx=0 downstream, dividing the slope by zero).
    gas = CompositionStream(library=KF, mol_pct={"C1": 50.0, "C2": 50.0})
    liquid = CompositionStream(library=KF, mol_pct={"C1": 50.0, "C10": 50.0})
    with pytest.raises(InputValidationError) as exc_info:
        hoffman_crump.check(gas, liquid, p_psia=355.0, t_f=55.4)
    assert "found 1" in str(exc_info.value)


def test_fit_least_squares_zero_ss_xx_raises_distinct_typed_error():
    # n=2 (passes the < 2 guard) but both points share the same F-factor --
    # ss_xx (the slope's denominator) is degenerate zero. Constructed
    # directly against HoffmanPoint/_fit_least_squares since coaxing two
    # different real KF components to share an F-factor exactly would
    # require an contrived temperature search; this isolates the
    # least-squares arithmetic itself.
    points = [
        HoffmanPoint(code="A", k=1.0, f_factor=1.0, log10_kp=1.0),
        HoffmanPoint(code="B", k=1.0, f_factor=1.0, log10_kp=2.0),
    ]
    with pytest.raises(InputValidationError) as exc_info:
        hoffman_crump._fit_least_squares(points)
    assert "F-factor" in str(exc_info.value)


def test_fit_least_squares_zero_ss_tot_raises_distinct_typed_error():
    # n=2, distinct F-factors (ss_xx != 0, passes that guard), but both
    # points share the same log10(K*P) -- ss_tot (R²'s denominator) is
    # degenerate zero. A message distinct from the ss_xx case, per the
    # brief.
    points = [
        HoffmanPoint(code="A", k=1.0, f_factor=1.0, log10_kp=5.0),
        HoffmanPoint(code="B", k=1.0, f_factor=2.0, log10_kp=5.0),
    ]
    with pytest.raises(InputValidationError) as exc_info:
        hoffman_crump._fit_least_squares(points)
    assert "log10(K*P)" in str(exc_info.value)


def test_mw_consistency_grades():
    sto = CompositionStream(library=KF.with_c36_mw(635.0), mol_pct=sa372.STO_MOL_PCT)
    derived = CompositionStream(library=sto.library, mol_pct=sa372.STO_MOL_PCT,
                                wt_pct=sto.wt_from_mol())
    assert mw_consistency.check(derived).severity == Severity.PASS
