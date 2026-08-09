import pytest

from pvt.core.exceptions import InputValidationError
from pvt.correlations.viscosity.lee_gonzalez_eakin import gas_density_g_cc, gas_viscosity_cp


def test_golden_viscosity_workbook_point():
    # GOLDEN: 5_Viscosity_HPHT_Calc_v2.xlsx @965 psia, Z=0.945, M=19.5, T=256F:
    # sheet rho=0.04155 (coef 0.0014935), mu_g=0.015395 cP. Engine coef is the exact
    # 0.016018463/10.7316 (D-010) -> ~0.06% lower rho; assert at matching tolerance.
    rho = gas_density_g_cc(965.0, 19.5, 0.945, 256.0)
    assert rho == pytest.approx(0.04155, rel=2e-3)
    assert gas_viscosity_cp(256.0, 19.5, rho) == pytest.approx(0.015395, rel=5e-3)


def test_viscosity_increases_with_density():
    lo = gas_viscosity_cp(256.0, 19.5, 0.02)
    hi = gas_viscosity_cp(256.0, 19.5, 0.20)
    assert hi > lo


def test_dilute_limit_positive():
    assert gas_viscosity_cp(100.0, 16.0, 1e-9) > 0.0


# --- Input validation guards -------------------------------------------------

@pytest.mark.parametrize("p_psia, mw, z, t_f", [
    (-1.0, 19.5, 0.945, 256.0),   # p_psia < 0
    (965.0, 0.0, 0.945, 256.0),   # mw <= 0
    (965.0, 19.5, 0.0, 256.0),    # z <= 0
])
def test_gas_density_rejects_bad_inputs(p_psia, mw, z, t_f):
    with pytest.raises(InputValidationError):
        gas_density_g_cc(p_psia, mw, z, t_f)


def test_gas_density_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        gas_density_g_cc(-1.0, 0.0, 0.0, 256.0)
    assert len(exc_info.value.errors) == 3


@pytest.mark.parametrize("t_f, mw, rho_g_cc", [
    (256.0, 0.0, 0.02),    # mw <= 0
    (256.0, 19.5, -0.01),  # rho_g_cc < 0
])
def test_gas_viscosity_rejects_bad_inputs(t_f, mw, rho_g_cc):
    with pytest.raises(InputValidationError):
        gas_viscosity_cp(t_f, mw, rho_g_cc)
