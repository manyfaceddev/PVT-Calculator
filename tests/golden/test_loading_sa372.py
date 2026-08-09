import pytest
from pvt.experiments.recombination.loading import LoadingInputs, plan_loading, verify_actual_gor
from pvt.qc.engine import Severity
from tests.golden.test_molar_recombination_sa372 import _split

INPUTS = LoadingInputs(cylinder_volume_cc=1000.0, target_oil_cc=150.0,
                       oil_load_p_psig=2000.0, oil_load_t_f=75.0,
                       gas_load_p_psig=5000.0, gas_load_t_f=75.0, z_gas_load=0.85,
                       sto_density_at_load_g_cc=0.885)

# GOLDEN: ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx, Loading_Volumes sheet
def test_golden_loading_plan():
    p = plan_loading(INPUTS, _split(), sto_density_60f=0.8196, sto_mw=187.05, z_std=0.99)
    assert p.v_oil_charge_cc == 150.0                                   # B22
    assert p.v_sto_equivalent_cc == pytest.approx(161.97, abs=0.01)     # B23
    assert p.n_oil_mol == pytest.approx(0.709687, rel=1e-4)             # B25
    assert p.n_gas_mol == pytest.approx(0.417938, rel=1e-4)             # B29
    assert p.v_gas_std_cc == pytest.approx(9779.46, abs=0.5)            # B30
    assert p.std_cc_per_cc_at_load == pytest.approx(385.39, abs=0.05)   # B31
    assert p.v_gas_charge_cc == pytest.approx(25.38, abs=0.01)          # B32
    assert p.fits is True and p.utilization_pct == pytest.approx(17.5, abs=0.1)

def test_golden_actual_gor_fails_gate():
    gor, dev, qc = verify_actual_gor(108.96, 27.47, INPUTS, 0.8196,
                                     target_gor_scf_stb=339.0, z_std=0.99)
    assert gor == pytest.approx(505.2, abs=0.5)                         # B47
    assert dev == pytest.approx(49.03, abs=0.1)                         # B49
    assert qc.severity == Severity.FAIL                                 # B50 "FAIL >10%"
