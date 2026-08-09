import pytest
from pvt.core.exceptions import ConvergenceError, InputValidationError
from pvt.correlations.zfactor.dak import z_factor

# GOLDEN: "Z factor calculation.xls" (verified reproducible to <=1e-6 during the digest).
# Fixture 1 pseudo-criticals (SBV on the workbook's own table): Tpc=527.028947342463 R,
# Ppc=676.464314208584 psia; T=243.8 F = 703.47 R.
TPC1, PPC1, T1 = 527.028947342463, 676.464314208584, 703.47

@pytest.mark.parametrize("p,expected", [
    (3758.6, 0.780550600353551),
    (100.0, 0.978736951911),
    (2100.0, 0.655284016707),
    (5850.0, 1.033339359558),
])
def test_golden_fixture1(p, expected):
    assert z_factor(p, T1, TPC1, PPC1) == pytest.approx(expected, abs=2e-6)

def test_golden_fixture3_gravity_based():
    # GOLDEN: gravity form gamma=0.737 -> Tpc=382.01179500604, Ppc=655.135642524563; T=243.8F
    assert z_factor(3758.6, 703.47, 382.01179500604, 655.135642524563) == pytest.approx(
        0.945786085258, abs=2e-6)

def test_low_pressure_limit():
    assert z_factor(0.001, 703.47, TPC1, PPC1) == pytest.approx(1.0, abs=1e-4)

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

def test_high_pressure_validity_enforced():
    with pytest.raises(InputValidationError):
        z_factor(21000.0, T1, TPC1, PPC1)   # Ppr >= 30

def test_convergence_error_path():
    with pytest.raises(ConvergenceError):
        z_factor(3000.0, T1, TPC1, PPC1, max_iter=1, tol=1e-15)

def test_z_positive_safety_valve():
    # Test that if z goes negative, it's reset to 1e-3 and iteration continues
    # Using an extreme starting point to trigger the safety valve
    result = z_factor(5850.0, T1, TPC1, PPC1, z0=1e-6, max_iter=100, tol=1e-10)
    assert result > 0
    assert result == pytest.approx(1.033339359558, abs=2e-6)
