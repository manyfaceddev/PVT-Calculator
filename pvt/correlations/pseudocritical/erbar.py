"""Erbar (Chao-Seader program) C7+ pseudo-criticals; source: Amoco GasProp VBA
(docs/reference/gasprop_functions.bas), transcribed verbatim.

`c7_plus_criticals` is a line-for-line transcription of the private VBA
subroutine `EstimatePseudoCriticals` (module `GasProp Functions`): a
boiling-point estimate from a quartic-in-MW plus an SG-slope quartic (with
an added exponential term above SG 0.86), followed by a paraffin/
naphthene/aromatic (PNA) split whose per-family Tc/Pc are cubics in that
boiling point. Critical volume is Hall's (1971) correlation, not Erbar's.
All numeric coefficients are copied verbatim from the .bas file -- none are
rounded or "cleaned up".

Deviation from the .bas file, documented here for transparency: VBA line
497 converts its `PseudoDensGmCC` (C7+ density, g/cc) argument to a
water-relative specific gravity via `ssg = PseudoDensGmCC / 0.999015`
before using it anywhere downstream (SG-slope term, the SG>0.86 branch, the
PNA split, and Hall's Vc). This module's public signature instead takes
`sg` (specific gravity) directly per this task's interface contract, and
that `sg` is used everywhere the VBA uses `ssg` -- i.e. the /0.999015
conversion is not applied a second time. This is forced by the task's own
pinned characterization test (`vc == pytest.approx(0.025 * (mw /
sg**0.69) ** 1.15, rel=1e-12)` for mw=217/sg=0.845 in
tests/unit/correlations/test_erbar.py): applying the extra /0.999015
division would shift Vc by ~0.07%, far outside that tolerance. Since
0.999015 (water density at the .bas file's reference conditions) never
appears anywhere else in this task's brief or interface, `sg` is treated as
already being what the VBA calls `ssg`.
"""

import math
import warnings

_MW_FLOOR = 99.0
_MW_FLOOR_REPLACEMENT = 110.0
_SG_FLOOR = 0.7
_SG_FLOOR_REPLACEMENT = 0.74
_SG_HIGH_BREAK = 0.86


def _clamp_inputs(mw: float, sg: float) -> tuple[float, float]:
    """Apply the source's input floors, warning (message contains "clamped")
    whenever a floor is hit. Mirrors gasprop_functions.bas lines 494 and 496.
    """
    if mw < _MW_FLOOR:
        warnings.warn(
            f"c7_plus_criticals: mw={mw} < {_MW_FLOOR} clamped to {_MW_FLOOR_REPLACEMENT}",
            stacklevel=3,
        )
        mw = _MW_FLOOR_REPLACEMENT
    if sg < _SG_FLOOR:
        warnings.warn(
            f"c7_plus_criticals: sg={sg} < {_SG_FLOOR} clamped to {_SG_FLOOR_REPLACEMENT}",
            stacklevel=3,
        )
        sg = _SG_FLOOR_REPLACEMENT
    return mw, sg


def _boiling_point_f(mw: float, sg: float) -> float:
    """Estimated normal boiling point (deg F) of the C7+ pseudo-component.

    Transcribes gasprop_functions.bas lines 500-510 (the `bp` variable)
    exactly: a quartic in `mw`, plus an SG-slope quartic in `mw` applied as
    `sx * (sg - 0.6)`, plus (for sg > 0.86) an added exponential correction.
    Callers must pre-clamp mw/sg (via `_clamp_inputs`) -- this helper does
    not clamp.
    """
    bp = (
        -264.65726
        + (
            6.2374923
            + (-0.021451518 + (4.3992405e-5 - 3.43845e-8 * mw) * mw) * mw
        )
        * mw
    )
    sx = (
        364.9632
        + (
            -4.759161
            + (0.04974927 + (-1.5157213e-4 + 1.431011e-7 * mw) * mw) * mw
        )
        * mw
    )
    bp = bp + sx * (sg - 0.6)

    if sg > _SG_HIGH_BREAK:
        c1 = sg - _SG_HIGH_BREAK
        sz = (
            (16.823557 + (-0.071486 + 0.000998994 * mw) * mw)
            + (65.42352 + (0.9092107 - 0.00801609 * mw) * mw) * c1
        ) * c1
        bp = bp + math.exp(sz)

    return bp


def c7_plus_criticals(mw: float, sg: float) -> tuple[float, float, float]:
    """Return (tc_r, pc_psia, vc) pseudo-critical properties for a C7+
    pseudo-component, via Erbar's (Chao-Seader program) Tc/Pc correlation
    and Hall's (1971) Vc correlation.

    Args:
        mw: C7+ molecular weight (lb/lbmol). Clamped to 110.0 if < 99.0
            (source input floor -- emits a `UserWarning` containing
            "clamped" when triggered).
        sg: C7+ specific gravity, relative to water. Clamped to 0.74 if
            < 0.7 (source input floor -- emits a `UserWarning` containing
            "clamped" when triggered).

    Returns:
        tc_r: Pseudo-critical temperature, deg Rankine. Floored at 0.0
            (source defensive clamp; only reachable for non-physical
            mw/sg combinations far outside the correlation's intended
            range).
        pc_psia: Pseudo-critical pressure, psia. Floored at 0.0 (same
            defensive clamp as tc_r).
        vc: Pseudo-critical volume, in the same units (ft3/lbmol) as
            `pvt.correlations.viscosity.critical_volumes.VC_TABLE` (Hall
            1971: vc = 0.025 * (mw / sg**0.69) ** 1.15). Pass this value as
            `critical_volumes.vc_mix`'s `c7_plus_vc` argument to combine it
            with the other 11 components' tabulated Vc values.
    """
    mw, sg = _clamp_inputs(mw, sg)

    bp = _boiling_point_f(mw, sg)
    b2 = bp * bp
    b3 = b2 * bp

    sgrp = 0.57248636 + 0.0006948103 * bp - 0.00000075728178 * b2 + 3.207736e-10 * b3
    sgrb = 0.91610329 - 0.00025041792 * bp + 0.00000035706705 * b2 - 1.663182e-10 * b3
    sgrn = 1.9082378 - 0.0034097612 * bp + 0.0000043083811 * b2 - 0.00000000185173 * b3

    xmp = 45.19165 + 0.26993166 * bp - 0.00008805269 * b2 + 0.000000358456 * b3
    xmb = 14.93085 + 0.407469 * bp - 0.0004228928 * b2 + 0.000000585848 * b3
    xmn = 4.825517 + 0.13158172 * bp + 0.00042669638 * b2 - 0.000000149796 * b3

    if sg <= sgrb:
        vfp = (sg - sgrb) / (sgrp - sgrb)
        vfb = 1.0 - vfp
        vfn = 0.0
    else:
        vfb = (sg - sgrn) / (sgrb - sgrn)
        vfn = 1.0 - vfb
        vfp = 0.0

    qq = vfp * sgrp + vfb * sgrb + vfn * sgrn
    wfp = vfp * sgrp / qq
    wfb = vfb * sgrb / qq
    wfn = vfn * sgrn / qq
    qq = wfp / xmp + wfb / xmb + wfn / xmn
    xfp = wfp / (xmp * qq)
    xfb = wfb / (xmb * qq)
    xfn = wfn / (xmn * qq)

    xzu = 727.47745 + 1.2626579 * bp - 0.00045330572 * b2 + 0.000000123217 * b3
    xzi = 839.54553 + 1.0776683 * bp - 0.00047253008 * b2 + 0.00000028135443 * b3
    xzo = 1521.9287 - 1.5416102 * bp + 0.0033237804 * b2 - 0.00000165984 * b3
    tc_r = xfp * xzu + xfb * xzi + xfn * xzo
    if tc_r < 0:
        tc_r = 0.0

    xzu = 593.11935 - 1.1655109 * bp + 0.001210827 * b2 - 0.000000692878 * b3
    xzi = 1128.158 - 2.8264468 * bp + 0.0028014571 * b2 - 0.000000972225 * b3
    xzo = 2748.4398 - 9.519013 * bp + 0.012696074 * b2 - 0.00000597439 * b3
    pc_psia = xfp * xzu + xfb * xzi + xfn * xzo
    if pc_psia < 0:
        pc_psia = 0.0

    # Hall (1971) Vc -- note use of specific gravity, not density.
    vc = 0.025 * (mw / (sg**0.69)) ** 1.15

    return tc_r, pc_psia, vc
