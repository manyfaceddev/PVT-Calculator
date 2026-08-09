import warnings

import pytest

from pvt.correlations.pseudocritical.erbar import c7_plus_criticals


def test_typical_c7plus_is_physical():
    tc, pc, vc = c7_plus_criticals(mw=217.0, sg=0.845)
    assert 1100.0 < tc < 1700.0      # R, between C11 and C36+ library values
    assert 100.0 < pc < 400.0        # psia
    assert vc == pytest.approx(0.025 * (217.0 / 0.845**0.69) ** 1.15, rel=1e-12)


def test_monotone_in_mw():
    tc1, pc1, _ = c7_plus_criticals(150.0, 0.80)
    tc2, pc2, _ = c7_plus_criticals(300.0, 0.88)
    assert tc2 > tc1 and pc2 < pc1


def test_clamps_warn():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        c7_plus_criticals(mw=90.0, sg=0.65)
    assert any("clamped" in str(w.message) for w in caught)


# --- Coverage-completion tests -------------------------------------------
# The 100% branch-coverage gate requires both arms of every `If` transcribed
# from EstimatePseudoCriticals to execute somewhere in the suite. The three
# tests above (from the task brief, verbatim) already exercise:
#   - mw < 99 clamp: True (test_clamps_warn) / False (the others)
#   - sg < 0.7 clamp: True (test_clamps_warn) / False (the others)
#   - sg > 0.86 exponential term: True (mw=300/sg=0.88) / False (sg=0.845, sg=0.80)
#   - PNA split (ssg <= sgrb): True (mw=150/sg=0.80, mw=217/sg=0.845)
#                               / False (mw=300/sg=0.88)
# The two defensive floors (`If PseudoTC < 0 Then PseudoTC = 0` and the Pc
# equivalent) are never hit by physically-reasonable C7+ inputs, so a
# dedicated extreme-input case is added below to reach their True arms.


def test_extreme_inputs_floor_tc_and_pc_at_zero():
    """mw=1000/sg=0.72 drives both the Tc and Pc cubics negative in the VBA;
    EstimatePseudoCriticals floors both at 0 (lines ...PseudoTC < 0... /
    ...PseudoPC < 0...). Confirmed via independent hand-trace of the VBA
    (not a physically meaningful C7+ pseudo-component -- this input exists
    only to exercise the defensive floor branches)."""
    tc, pc, vc = c7_plus_criticals(mw=1000.0, sg=0.72)
    assert tc == 0.0
    assert pc == 0.0
    assert vc == pytest.approx(0.025 * (1000.0 / 0.72**0.69) ** 1.15, rel=1e-12)


# --- Step 5: VBA-trace fixture (transcription self-consistency) ----------
# Hand-traced EstimatePseudoCriticals(PseudoMolWt=217.0, PseudoDensGmCC=0.845)
# line-by-line from docs/reference/gasprop_functions.bas independently of
# erbar.py, then confirmed the Python transcription reproduces the trace
# exactly. These are NOT external published goldens -- the correlation is
# proprietary Amoco/Chao-Seader lineage with no public worked example -- they
# pin transcription self-consistency (i.e. "the Python matches the VBA it was
# copied from, to the last bit") rather than correctness against an outside
# reference.
def test_vba_trace_mw217_sg0845():
    # VBA-trace fixture (transcription self-consistency)
    # bp = 560.6575339349728 (deg F, boiling point per the Erbar quartics)
    # sgrp=0.7805270473601936 sgrb=0.8586327919042741 sgrn=1.024472269520219
    #   -> ssg (0.845) <= sgrb -> paraffin/naphthene branch (vfn = 0)
    tc, pc, vc = c7_plus_criticals(mw=217.0, sg=0.845)
    assert tc == pytest.approx(1340.2602949758316, rel=1e-12)
    assert pc == pytest.approx(244.54023185923086, rel=1e-12)
    assert vc == pytest.approx(13.896579108178768, rel=1e-12)
