import pytest

from pvt.core.exceptions import InputValidationError
from pvt.correlations.viscosity.jossi_stiel_thodos import gas_viscosity_cp, reduced_density


def test_zero_density_recovers_dilute_term():
    mu0 = gas_viscosity_cp(t_r=600.0, mw=20.0, tpc_r=370.0, ppc_psia=670.0, rho_r=0.0)
    # at rho_r=0 the bracket is 0.1023^4 - 1e-4 ~= 9.5e-6, tiny vs mu*
    chi = (370.0 / 1.8) ** (1 / 6) / (20.0**0.5 * (670.0 / 14.696) ** (2 / 3))
    tr = 600.0 / 370.0
    mu_star = 0.001668 * (0.1338 * tr - 0.0932) ** (5 / 9) / chi   # tr > 1.5 branch
    assert mu0 == pytest.approx(mu_star + (0.1023**4 - 1e-4) / chi, rel=1e-9)


def test_monotone_in_reduced_density():
    args = dict(t_r=600.0, mw=20.0, tpc_r=370.0, ppc_psia=670.0)
    assert gas_viscosity_cp(rho_r=1.0, **args) > gas_viscosity_cp(rho_r=0.3, **args)


def test_branch_boundary_continuity_documented():
    # The two dilute-term branches do NOT meet exactly at Tr=1.5 (VBA-faithful behavior);
    # assert both compute and differ by <5% so the discontinuity is bounded and visible.
    below = gas_viscosity_cp(t_r=1.4999 * 370.0, mw=20.0, tpc_r=370.0, ppc_psia=670.0, rho_r=0.1)
    above = gas_viscosity_cp(t_r=1.5001 * 370.0, mw=20.0, tpc_r=370.0, ppc_psia=670.0, rho_r=0.1)
    assert below == pytest.approx(above, rel=0.05)


def test_reduced_density_formula():
    assert reduced_density(3000.0, 0.9, 700.0, 3.2) == pytest.approx(
        3.2 * 3000.0 / (0.9 * 10.7316 * 700.0), rel=1e-12)


# --- Input validation guards -------------------------------------------------

@pytest.mark.parametrize("p_psia, z, t_r, vc_mix", [
    (3000.0, 0.0, 700.0, 3.2),    # z <= 0
    (3000.0, 0.9, 700.0, 0.0),    # vc_mix <= 0
])
def test_reduced_density_rejects_bad_inputs(p_psia, z, t_r, vc_mix):
    with pytest.raises(InputValidationError):
        reduced_density(p_psia, z, t_r, vc_mix)


def test_reduced_density_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        reduced_density(3000.0, -1.0, 700.0, -1.0)
    assert len(exc_info.value.errors) == 2


@pytest.mark.parametrize("t_r, mw, tpc_r, ppc_psia, rho_r", [
    (600.0, 0.0, 370.0, 670.0, 0.5),    # mw <= 0
    (600.0, 20.0, 0.0, 670.0, 0.5),     # tpc_r <= 0
    (600.0, 20.0, 370.0, 0.0, 0.5),     # ppc_psia <= 0
    (600.0, 20.0, 370.0, 670.0, -0.1),  # rho_r < 0
])
def test_gas_viscosity_rejects_bad_inputs(t_r, mw, tpc_r, ppc_psia, rho_r):
    with pytest.raises(InputValidationError):
        gas_viscosity_cp(t_r, mw, tpc_r, ppc_psia, rho_r)


def test_gas_viscosity_collects_all_violations():
    with pytest.raises(InputValidationError) as exc_info:
        gas_viscosity_cp(600.0, 0.0, 0.0, 0.0, -1.0)
    assert len(exc_info.value.errors) == 4
