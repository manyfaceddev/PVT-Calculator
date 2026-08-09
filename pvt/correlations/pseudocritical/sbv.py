"""Stewart-Burkhardt-Voo (1959) pseudo-critical mixing rules from composition.

This is a sweet-gas correlation (no H2S/CO2 term); apply
``wichert_aziz.correct`` to its (Tpc, Ppc) output for sour gas.
"""
import math

from pvt.core.composition import CompositionStream


def pseudo_criticals(stream: CompositionStream) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia]) from mole composition via SBV J/K."""
    z = {k: v / 100.0 for k, v in stream.normalized_mol().items()}
    lib = stream.library
    j = sum(y * lib.get(c).tc_r / lib.get(c).pc_psia for c, y in z.items()) / 3.0
    j += (2.0 / 3.0) * sum(y * math.sqrt(lib.get(c).tc_r / lib.get(c).pc_psia)
                           for c, y in z.items()) ** 2
    k = sum(y * lib.get(c).tc_r / math.sqrt(lib.get(c).pc_psia) for c, y in z.items())
    tpc = k * k / j
    return tpc, tpc / j
