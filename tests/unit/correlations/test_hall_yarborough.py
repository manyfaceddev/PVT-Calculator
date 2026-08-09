import pytest
from pvt.core.exceptions import ConvergenceError, InputValidationError
from pvt.correlations.zfactor.dak import z_factor as dak_z
from pvt.correlations.zfactor.hall_yarborough import z_factor as hy_z

TPC, PPC, T = 382.01179500604, 655.135642524563, 703.47  # sweet 0.737-gravity gas


@pytest.mark.parametrize("p", [200.0, 800.0, 1600.0, 2400.0, 3200.0, 4000.0])
def test_agrees_with_dak_within_2pct(p):
    assert hy_z(p, T, TPC, PPC) == pytest.approx(dak_z(p, T, TPC, PPC), rel=0.02)


def test_low_pressure_limit():
    assert hy_z(0.01, T, TPC, PPC) == pytest.approx(1.0, abs=1e-4)


def test_z_is_a_over_y_not_y():
    # D-006 guard: at high pressure Z > 0.9 while reduced density y is small (~0.1);
    # returning y instead of A/y (the CVD workbook bug) would fail this bound.
    assert hy_z(4000.0, T, TPC, PPC) > 0.7


# --- Additional coverage: input validation, convergence failure, and the
# defensive y-domain clamps (same contract shape as dak.z_factor). ---

def test_negative_pressure_error():
    with pytest.raises(InputValidationError):
        hy_z(-1.0, T, TPC, PPC)


def test_nonpositive_temperature_error():
    with pytest.raises(InputValidationError):
        hy_z(1000.0, 0.0, TPC, PPC)


def test_nonpositive_tpc_error():
    with pytest.raises(InputValidationError):
        hy_z(1000.0, T, 0.0, PPC)


def test_nonpositive_ppc_error():
    with pytest.raises(InputValidationError):
        hy_z(1000.0, T, TPC, 0.0)


def test_convergence_error_path():
    with pytest.raises(ConvergenceError):
        hy_z(3000.0, T, TPC, PPC, max_iter=1, tol=1e-15)


def test_upper_clamp_safety_valve():
    # Extreme, non-physical Ppr (~150) drives the first Newton step past y=1;
    # verifies the y>=1 -> 0.999 reset (D-006-adjacent defensive clamp) is
    # exercised and iteration still converges rather than raising a math error.
    z = hy_z(100000.0, T, TPC, PPC)
    assert z > 1.0
