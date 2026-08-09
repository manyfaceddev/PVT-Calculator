import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.correlations.pseudocritical import piper_mccain as pm


def test_golden_gravity_form_sweet():
    # GOLDEN: "Z factor calculation.xls" unknown-composition sheet F4/F5
    # (gamma=0.737, no impurities -- transposed CO2 coefficient unexercised, fixture valid)
    tpc, ppc = pm.from_gravity(0.737)
    assert tpc == pytest.approx(382.01179500604, rel=1e-9)
    assert ppc == pytest.approx(655.135642524563, rel=1e-9)


def test_golden_compositional_form():
    # GOLDEN: sour known-composition sheet I5/I6; library Tc/Pc differ from the workbook's
    # in the 3rd-4th significant figure -> 2e-3 relative tolerance. All ten components fall
    # in the sour (CO2/N2) or C1-C6 buckets, so the C7+ term is unexercised here.
    mol = {"C1": 93.55, "C2": 3.09, "C3": 1.34, "nC4": 0.18, "iC4": 0.47,
           "nC5": 0.14, "iC5": 0.22, "C6": 0.54, "CO2": 0.37, "N2": 0.10}
    tpc, ppc = pm.from_composition(CompositionStream(library=KF, mol_pct=mol))
    assert tpc == pytest.approx(347.652082782798, rel=2e-3)
    assert ppc == pytest.approx(670.332106175576, rel=2e-3)


def test_deviation_d003_co2_coefficient():
    # D-003: with CO2 present the published coefficient (-0.90348) must bite: it shrinks J
    # roughly 10x more than the transposed -0.09034 would, so Tpc must shift markedly.
    sweet_tpc = pm.from_gravity(0.737)[0]
    sour_tpc = pm.from_gravity(0.737, y_co2=0.20)[0]
    assert abs(sour_tpc - sweet_tpc) / sweet_tpc > 0.02   # >2% shift at 20% CO2


def test_compositional_form_h2s_present():
    # Self-derived (formula-spec, not workbook): exercises the H2S branch, which the golden
    # compositional fixture above never touches. Independently computed from the published
    # J/K formula + KF library Tc/Pc, so a tight tolerance is appropriate.
    mol = {"C1": 90.0, "C2": 5.0, "H2S": 5.0}
    tpc, ppc = pm.from_composition(CompositionStream(library=KF, mol_pct=mol))
    assert tpc == pytest.approx(352.01020902580774, rel=1e-9)
    assert ppc == pytest.approx(696.130410852105, rel=1e-9)


def test_c7_plus_bucket_includes_naphthenes_mole_weighted_mw():
    # D-004: C7+ MW must be mole-fraction-weighted, not a plain average, and the bucket must
    # include non-C1-C6/non-sour species by name -- including naphthenes like MCP (clarification
    # #2), which have no "C7+" label but aren't light HC or sour either.
    mol = {"C1": 97.0, "C7": 2.0, "MCP": 1.0}
    stream = CompositionStream(library=KF, mol_pct=mol)
    tpc, ppc = pm.from_composition(stream)
    assert tpc == pytest.approx(341.9685331365925, rel=1e-9)
    assert ppc == pytest.approx(639.224488627113, rel=1e-9)

    # Passing the mole-weighted MW explicitly via c7p_mw must reproduce the auto-computed
    # result exactly -- proving from_composition's internal weighting matches
    # Sigma(y_i*MW_i)/Sigma(y_i) rather than an unweighted average (D-004's Excel behavior).
    weighted_mw = (2 * KF.get("C7").mw + 1 * KF.get("MCP").mw) / 3
    tpc_override, ppc_override = pm.from_composition(stream, c7p_mw=weighted_mw)
    assert tpc_override == pytest.approx(tpc, rel=1e-12)
    assert ppc_override == pytest.approx(ppc, rel=1e-12)

    # The D-004 workbook bug (unweighted average of C7+ species' MW) gives a materially
    # different C7+ MW and therefore a different, wrong, result.
    unweighted_mw = (KF.get("C7").mw + KF.get("MCP").mw) / 2
    tpc_unweighted, _ = pm.from_composition(stream, c7p_mw=unweighted_mw)
    assert tpc_unweighted != pytest.approx(tpc, rel=1e-9)
