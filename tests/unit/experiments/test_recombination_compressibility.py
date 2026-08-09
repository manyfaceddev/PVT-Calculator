"""
tests/unit/experiments/test_recombination_compressibility.py — Unit tests for
`pvt.experiments.recombination.compressibility.effective_c_o`.

`effective_c_o` recovers the pre-Task-10 `ui/recombination.py`'s
`_compute_compressibility` logic as a pure `pvt/` calculation (field units
only, 1/psia basis) -- see the module docstring for the recovery citation.
"""

import pytest

from pvt.core.exceptions import InputValidationError
from pvt.experiments.recombination.compressibility import effective_c_o


def test_constant_model_passes_value_through_unchanged():
    assert effective_c_o("constant", 12.5e-6, p_ref_psia=5000.0) == 12.5e-6


def test_constant_model_ignores_reference_pressure():
    # p_ref_psia has no effect on the "constant" model -- same value at two
    # different reference pressures.
    lo = effective_c_o("constant", 8.0e-6, p_ref_psia=100.0)
    hi = effective_c_o("constant", 8.0e-6, p_ref_psia=9000.0)
    assert lo == hi == 8.0e-6


def test_polynomial_model_evaluates_at_reference_pressure():
    # c_o(P) = a0 + a1*P + a2*P^2, hand-computed at P=1000 psia:
    #   1e-5 + 2e-9*1000 + 3e-13*1000**2 = 1e-5 + 2e-6 + 3e-7 = 1.23e-5
    coeffs = [1e-5, 2e-9, 3e-13]
    assert effective_c_o("polynomial", coeffs, p_ref_psia=1000.0) == pytest.approx(1.23e-5)


def test_polynomial_model_single_coefficient_behaves_like_constant():
    assert effective_c_o("polynomial", [7e-6], p_ref_psia=3000.0) == pytest.approx(7e-6)


def test_polynomial_model_rejects_scalar_input():
    with pytest.raises(InputValidationError):
        effective_c_o("polynomial", 1e-5, p_ref_psia=1000.0)


def test_polynomial_model_rejects_empty_coefficients():
    with pytest.raises(InputValidationError):
        effective_c_o("polynomial", [], p_ref_psia=1000.0)


def test_constant_model_rejects_sequence_input():
    with pytest.raises(InputValidationError):
        effective_c_o("constant", [1e-5, 2e-9], p_ref_psia=1000.0)


def test_unknown_model_raises():
    with pytest.raises(InputValidationError):
        effective_c_o("quadratic", 1e-5, p_ref_psia=1000.0)  # type: ignore[arg-type]
