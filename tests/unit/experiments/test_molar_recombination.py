import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.experiments.recombination.molar import k_values


def test_k_values_basic_and_zero_x_excluded():
    gas = CompositionStream(library=KF, mol_pct={"C1": 80.0, "C2": 20.0})
    liquid = CompositionStream(library=KF, mol_pct={"C2": 50.0, "C7": 50.0})
    k = k_values(gas, liquid)
    # C1 has x=0 in the liquid (absent) -> excluded, per "x>0 only".
    assert "C1" not in k
    # C2 present in both, already-normalized (sums to 100 each): K = y/x.
    assert k["C2"] == pytest.approx(20.0 / 50.0)
    # C7 present in liquid only -> y=0 (absent from gas) -> K=0.0, but x>0 so included.
    assert k["C7"] == pytest.approx(0.0)
