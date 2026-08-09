import pytest
from pvt.core.exceptions import ConvergenceError, InputValidationError
from pvt.correlations.zfactor.dak import z_factor

# GOLDEN: "Z factor calculation.xls" (verified reproducible to <=1e-6 during the digest).
# Fixture 1 pseudo-criticals (SBV on the workbook's own table): Tpc=527.028947342463 R,
# Ppc=676.464314208584 psia; T=243.8 F + 460 (workbook convention) = 703.8 R.
# 243.8 F + 460: the source workbook's Rankine offset convention (matches its Tc(F)+460 component table).
# Engine code elsewhere uses the exact 459.67; parity with workbook-cached Z values requires the workbook's basis.
# Controller-verified: goldens reproduce to <=8.2e-7 at 703.8 vs up to 5.4e-4 at 703.47.
TPC1, PPC1, T1 = 527.028947342463, 676.464314208584, 703.8

@pytest.mark.parametrize("p,expected", [
    (3758.6, 0.780734027334595),
    (100.0, 0.978768959845925),
    (2100.0, 0.655819147786408),
    (5850.0, 1.03330449490003),
])
def test_golden_fixture1(p, expected):
    assert z_factor(p, T1, TPC1, PPC1) == pytest.approx(expected, abs=2e-6)

def test_golden_fixture3_gravity_based():
    # GOLDEN: gravity form gamma=0.737 -> Tpc=382.01179500604, Ppc=655.135642524563; T=243.8F
    assert z_factor(3758.6, 703.8, 382.01179500604, 655.135642524563) == pytest.approx(
        0.945986816664325, abs=2e-6)

def test_low_pressure_limit():
    assert z_factor(0.001, T1, TPC1, PPC1) == pytest.approx(1.0, abs=1e-4)

def test_warm_start_agrees_with_cold():
    cold = z_factor(3600.0, T1, TPC1, PPC1)
    warm = z_factor(3600.0, T1, TPC1, PPC1, z0=z_factor(3350.0, T1, TPC1, PPC1))
    assert warm == pytest.approx(cold, abs=1e-12)

def test_validity_range_enforced():
    with pytest.raises(InputValidationError):
        z_factor(3000.0, 400.0, TPC1, PPC1)   # Tpr < 1.0

def test_negative_pressure_error():
    with pytest.raises(InputValidationError):
        z_factor(-1.0, T1, TPC1, PPC1)

def test_nonpositive_temperature_error():
    with pytest.raises(InputValidationError):
        z_factor(1000.0, 0.0, TPC1, PPC1)

def test_nonpositive_tpc_error():
    with pytest.raises(InputValidationError):
        z_factor(1000.0, T1, 0.0, PPC1)

def test_nonpositive_ppc_error():
    with pytest.raises(InputValidationError):
        z_factor(1000.0, T1, TPC1, 0.0)

def test_nonpositive_z0_error():
    with pytest.raises(InputValidationError):
        z_factor(1000.0, T1, TPC1, PPC1, z0=0.0)

def test_negative_z0_error():
    with pytest.raises(InputValidationError):
        z_factor(1000.0, T1, TPC1, PPC1, z0=-0.5)

def test_high_pressure_validity_enforced():
    with pytest.raises(InputValidationError):
        z_factor(21000.0, T1, TPC1, PPC1)   # Ppr >= 30

def test_convergence_error_path():
    with pytest.raises(ConvergenceError):
        z_factor(3000.0, T1, TPC1, PPC1, max_iter=1, tol=1e-15)

def test_z_positive_safety_valve():
    # Test that if Newton step produces z <= 0, it's reset to 1e-3.
    # z0=0.1 at p=100 triggers the clamp in first iteration (z would go to -1.44, reset to 1e-3).
    # The extreme starting point causes divergence, but we verify the clamp is executed via coverage.
    with pytest.raises(ConvergenceError):
        z_factor(100.0, T1, TPC1, PPC1, z0=0.1, max_iter=100, tol=1e-10)
