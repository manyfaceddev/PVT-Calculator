"""
pvt/correlations/viscosity/critical_volumes.py — Critical volume (Vc) table
for the Gas_Gradient VBA's 12-component gas mixture, ported verbatim from
`CalculateCriticals` (docs/reference/gasprop_functions.bas, lines ~437-444):

    crit_vc = Array(1.44, 1.59, 1.51, 2.37, 1.565, 3.21, _
                    4.21, 4.08, 4.9, 4.87, 5.93, C7plusVC)

with components in the VBA's fixed positional order (confirmed against the
parallel `mol_wt` array at the same lines):

    N2, C1, CO2, C2, H2S, C3, iC4, nC4, iC5, nC5, C6, C7+

`C7plusVC` is not a fixed table entry -- the VBA computes it per-call from
`EstimatePseudoCriticals` (Hall's (1971) Vc correlation), transcribed in
this codebase as `erbar.c7_plus_criticals`'s third return value. `vc_mix`
below takes that value as an explicit argument (`c7_plus_vc`) rather than
baking in a constant.

Units: whatever units the VBA's crit_vc table carries downstream into
`ThodosGasVisc`'s reduced-density calculation
(`rhorv = vcmv * PresPsia / (GasZ * 10.73 * TdegR)`) -- i.e. ft3/lbmol,
consistent with `pvt.correlations.viscosity.jossi_stiel_thodos.reduced_density`'s
`vc_mix` parameter (same name, same units, this module is its natural
composition-weighted source).
"""

from pvt.core.exceptions import InputValidationError

VC_TABLE: dict[str, float] = {
    "N2": 1.44,
    "C1": 1.59,
    "CO2": 1.51,
    "C2": 2.37,
    "H2S": 1.565,
    "C3": 3.21,
    "iC4": 4.21,
    "nC4": 4.08,
    "iC5": 4.9,
    "nC5": 4.87,
    "C6": 5.93,
}
"""Critical volume (ft3/lbmol) by component code, verbatim from the
Gas_Gradient VBA `crit_vc` array (see module docstring). Deliberately does
NOT include a "C7+" entry -- the VBA computes that pseudo-component's Vc
per-call (via Erbar/Hall), so callers supply it to `vc_mix` as `c7_plus_vc`
instead of looking it up here."""

_C7_PLUS_KEYS = frozenset({"C7+"})
"""Recognized key(s) for the C7+ pseudo-component bucket in `vc_mix`'s
`mol_fractions` argument -- routed to the `c7_plus_vc` parameter rather than
`VC_TABLE`."""


def vc_mix(mol_fractions: dict[str, float], c7_plus_vc: float = 0.0) -> float:
    """Mole-fraction-weighted mixture critical volume, per the VBA
    `CalculateCriticals` accumulation `vcm = vcm + mol_frac(n) * crit_vc(n)`.

    Args:
        mol_fractions: Mole fraction (0-1) by component code. Keys must
            either be present in `VC_TABLE`, or be `"C7+"` (routed to
            `c7_plus_vc`).
        c7_plus_vc: C7+ pseudo-component critical volume, ft3/lbmol --
            typically `erbar.c7_plus_criticals(mw, sg)[2]` (Hall's (1971)
            Vc). Only used if `mol_fractions` has a `"C7+"` key; ignored
            otherwise.

    Returns:
        Mixture critical volume, ft3/lbmol.

    Raises:
        InputValidationError: if any key in `mol_fractions` is not a
            recognized component code (i.e. not in `VC_TABLE` and not
            `"C7+"`).
    """
    unknown = sorted(
        code for code in mol_fractions if code not in VC_TABLE and code not in _C7_PLUS_KEYS
    )
    if unknown:
        raise InputValidationError([f"unknown component code(s) in mol_fractions: {unknown}"])

    total = 0.0
    for code, y in mol_fractions.items():
        vc = c7_plus_vc if code in _C7_PLUS_KEYS else VC_TABLE[code]
        total += y * vc
    return total
