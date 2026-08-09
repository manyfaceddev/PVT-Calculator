"""Plus-fraction properties (C7+, C11+, C20+, C36+) from a composition stream.

Boundaries are positional on the component library's fixed slot order (the
52-row Katz-Firoozabadi table), not name-pattern matching: a cut is every
component at or after its start code. This is what makes "C7+" exclude the
cyclics that sort before C7 (MCP, Benzene, CycloC6) while including the
cyclics that sort after it (MCH, Toluene) — matching the flash workbook's
Plus_Properties_Report convention.
"""

from dataclasses import dataclass

from pvt.core.composition import CompositionStream

# Cut name -> the library code where the cut starts (inclusive). Everything
# from this code's position to the end of the library's code order is in
# the cut. "C36+" is the library's last slot, so its "cut" is itself alone.
_CUT_START_CODE: dict[str, str] = {
    "C7+": "C7",
    "C11+": "C11",
    "C20+": "C20",
    "C36+": "C36+",
}


@dataclass(frozen=True)
class PlusFraction:
    """Aggregate properties of a plus-fraction cut of a composition stream."""

    mol_pct: float
    wt_pct: float
    mw: float
    density_g_cc: float


def plus_fraction(stream: CompositionStream, cut: str) -> PlusFraction:
    """Compute plus-fraction properties for `cut` on `stream`'s composition.

    Args:
        stream: Composition stream with both mol% and wt% bases present.
        cut: One of "C7+", "C11+", "C20+", "C36+".

    Returns:
        PlusFraction with mol%/wt% of the whole sample represented by the
        cut, its mole-weighted MW, and its ideal-mixing density.
    """
    library = stream.library
    start_idx = library.codes.index(_CUT_START_CODE[cut])
    cut_codes = set(library.codes[start_idx:])

    mol_cut = {code: z for code, z in stream.normalized_mol().items() if code in cut_codes}
    wt_cut = {code: w for code, w in stream.normalized_wt().items() if code in cut_codes}

    mol_pct = sum(mol_cut.values())
    wt_pct = sum(wt_cut.values())

    mw = sum(z * library.get(code).mw for code, z in mol_cut.items()) / mol_pct
    density_denom = sum(w / library.get(code).liquid_density_g_cc for code, w in wt_cut.items())
    density = wt_pct / density_denom

    return PlusFraction(mol_pct=mol_pct, wt_pct=wt_pct, mw=mw, density_g_cc=density)
