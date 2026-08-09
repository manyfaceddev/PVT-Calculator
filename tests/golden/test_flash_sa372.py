import pytest
from pvt.experiments.flash.calc import calculate
from tests.unit.experiments.test_flash_validate import SA372

# GOLDEN: ADRIC_Flash_Separation_Calc_v6.1.xlsx, Volumetrics_Master (cached values)
def test_sa372_flash_chain():
    r = calculate(SA372)
    assert r.v_press_cc == pytest.approx(20.8945, abs=1e-4)          # B13
    assert r.m_oil_g == pytest.approx(13.71, abs=1e-9)               # B16
    assert r.v_gas_meas_cc == pytest.approx(958.2037, abs=1e-4)      # B19
    assert r.v_gas_std_cc == pytest.approx(940.5655, abs=0.001)      # B27
    assert r.gas_density_std_g_cc == pytest.approx(0.001404423, rel=1e-6)  # B28
    assert r.m_gas_g == pytest.approx(1.32095, abs=1e-5)             # B29
    assert r.gor_cc_cc == pytest.approx(59.6896, abs=0.001)          # B31
    assert r.gor_scf_bbl == pytest.approx(335.13, abs=0.01)          # B32
    assert r.bo_flash == pytest.approx(1.32600, abs=1e-5)            # B33
    assert r.shrinkage == pytest.approx(0.754151, abs=1e-6)          # B34
    assert r.oil_density_60f_g_cc == pytest.approx(0.870056, abs=1e-6)  # B36
    assert r.api == pytest.approx(31.133, abs=0.001)                 # B37

def test_invalid_inputs_raise():
    import dataclasses
    from pvt.core.exceptions import InputValidationError
    with pytest.raises(InputValidationError):
        calculate(dataclasses.replace(SA372, v_sto_cc=0.0))
