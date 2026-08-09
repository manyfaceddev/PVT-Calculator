import pytest
from pvt.core.exceptions import InputValidationError
from pvt.correlations.pseudocritical.wichert_aziz import correct

def test_no_impurities_is_identity():
    assert correct(370.0, 670.0, 0.0, 0.0) == (370.0, 670.0)

def test_hand_computed_case():
    # A=0.15 (10% CO2, 5% H2S), B=0.05:
    # e = 120*(0.15**0.9 - 0.15**1.6) + 15*(0.05**0.5 - 0.05**4)
    e = 120 * (0.15**0.9 - 0.15**1.6) + 15 * (0.05**0.5 - 0.05**4)
    tpc, ppc = correct(400.0, 700.0, 0.10, 0.05)
    assert tpc == pytest.approx(400.0 - e, rel=1e-12)
    assert ppc == pytest.approx(700.0 * (400.0 - e) / (400.0 + 0.05 * 0.95 * e), rel=1e-12)

def test_correction_lowers_both():
    tpc, ppc = correct(400.0, 700.0, 0.10, 0.05)
    assert tpc < 400.0 and ppc < 700.0


# --- Input validation guards -------------------------------------------------
# Catches the mole-PERCENT trap: e.g. y_co2=20 meaning "20%" instead of 0.20.

@pytest.mark.parametrize("y_co2, y_h2s", [
    (-0.1, 0.05),   # y_co2 < 0
    (20.0, 0.05),   # y_co2 > 1 (mole-percent trap)
    (0.10, -0.05),  # y_h2s < 0
    (0.10, 5.0),    # y_h2s > 1 (mole-percent trap)
    (0.7, 0.4),     # both in [0,1] individually but sum > 1
])
def test_rejects_bad_inputs(y_co2, y_h2s):
    with pytest.raises(InputValidationError):
        correct(400.0, 700.0, y_co2, y_h2s)


def test_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        correct(400.0, 700.0, -1.0, -1.0)
    assert len(exc_info.value.errors) == 2
