"""Mass-basis recombination of flash gas + flash oil streams into a wellstream.

Live-fluid technique: wf_gas = m_gas / (m_gas + m_oil). Wellstream wt% is a
mass-fraction-weighted blend of each stream's own normalized (sum-to-100)
wt% basis; wellstream mol% is back-calculated from wt%/MW and renormalized
to sum to 100, so mw_from_mol() and mw_from_wt() on the wellstream agree by
construction (both routes to the same recombined mass).
"""

from dataclasses import dataclass

from pvt.core.composition import CompositionStream


@dataclass(frozen=True)
class MassRecombination:
    """Result of a mass-basis flash-gas + flash-oil recombination."""

    wf_gas: float
    wf_oil: float
    wellstream: CompositionStream
    mw_whole_sample: float


def recombine_mass(
    m_oil_g: float,
    m_gas_g: float,
    oil_stream: CompositionStream,
    gas_stream: CompositionStream,
) -> MassRecombination:
    """Recombine flash oil + flash gas into a wellstream on a mass basis.

    Args:
        m_oil_g: Mass of flashed oil (g).
        m_gas_g: Mass of flashed gas (g).
        oil_stream: Flashed-oil composition (mol% and wt% bases).
        gas_stream: Flashed-gas composition (mol% and wt% bases).

    Returns:
        MassRecombination with the gas/oil mass fractions, the recombined
        wellstream composition, and the whole-sample MW (100/Sum(wt_i/MW_i)).
    """
    wf_gas = m_gas_g / (m_oil_g + m_gas_g)
    wf_oil = m_oil_g / (m_oil_g + m_gas_g)

    oil_wt = oil_stream.normalized_wt()
    gas_wt = gas_stream.normalized_wt()
    library = oil_stream.library

    codes = set(oil_wt) | set(gas_wt)
    wellstream_wt = {
        code: wf_gas * gas_wt.get(code, 0.0) + wf_oil * oil_wt.get(code, 0.0) for code in codes
    }

    mol_raw = {code: w / library.get(code).mw for code, w in wellstream_wt.items()}
    total_mol_raw = sum(mol_raw.values())
    wellstream_mol = {code: m * 100.0 / total_mol_raw for code, m in mol_raw.items()}

    wellstream = CompositionStream(library=library, mol_pct=wellstream_mol, wt_pct=wellstream_wt)

    return MassRecombination(
        wf_gas=wf_gas,
        wf_oil=wf_oil,
        wellstream=wellstream,
        mw_whole_sample=wellstream.mw_from_wt(),
    )
