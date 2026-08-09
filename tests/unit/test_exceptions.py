from pvt.core.exceptions import ConvergenceError, InputValidationError, PvtError

def test_input_validation_error_carries_messages():
    err = InputValidationError(["GOR must be positive", "Z out of range"])
    assert err.errors == ["GOR must be positive", "Z out of range"]
    assert "GOR must be positive; Z out of range" in str(err)
    assert isinstance(err, PvtError)

def test_convergence_error_carries_diagnostics():
    err = ConvergenceError("DAK failed", iterations=100, residual=0.5)
    assert err.iterations == 100
    assert err.residual == 0.5
    assert isinstance(err, PvtError)
