import pytest
from pvt.core.exceptions import InputValidationError
from pvt.correlations.pseudocritical.sutton import pseudo_criticals

def test_known_value_gamma_07():
    tpc, ppc = pseudo_criticals(0.7)
    # Sutton (1985): Ppc = 756.8 - 131*g - 3.6*g^2 ; Tpc = 169.2 + 349.5*g - 74*g^2
    assert ppc == pytest.approx(756.8 - 131 * 0.7 - 3.6 * 0.49, rel=1e-12)
    assert tpc == pytest.approx(169.2 + 349.5 * 0.7 - 74 * 0.49, rel=1e-12)

def test_physical_trend():
    assert pseudo_criticals(0.9)[0] > pseudo_criticals(0.6)[0]   # heavier gas -> higher Tpc
    assert pseudo_criticals(0.9)[1] < pseudo_criticals(0.6)[1]   # ... lower Ppc

@pytest.mark.parametrize("bad", [0.0, 0.4, 2.5, -1.0])
def test_out_of_range_rejected(bad):
    with pytest.raises(InputValidationError):
        pseudo_criticals(bad)
