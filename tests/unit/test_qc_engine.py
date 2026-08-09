import pytest
from pvt.qc.engine import QCResult, Severity, ThresholdRegistry, grade, worst

@pytest.mark.parametrize("value,expected", [
    (0.4, Severity.PASS), (-0.4, Severity.PASS),
    (1.0, Severity.REVIEW), (2.0, Severity.REVIEW), (2.1, Severity.FAIL),
])
def test_grade_bands(value, expected):
    assert grade(value, review_at=0.5, fail_at=2.0) == expected

def test_registry_defaults_and_override():
    reg = ThresholdRegistry()
    assert len(ThresholdRegistry.DEFAULTS) == 10
    assert reg.get("mass_balance_pct") == (2.0, 3.0)
    reg.override("mass_balance_pct", 1.0, 2.0, note="tight client spec")
    assert reg.get("mass_balance_pct") == (1.0, 2.0)
    assert "tight client spec" in reg.audit[0]

def test_worst_orders_severities():
    mk = lambda s: QCResult("x", s, None, "", "")
    assert worst([mk(Severity.PASS), mk(Severity.REVIEW)]) == Severity.REVIEW
    assert worst([mk(Severity.FAIL), mk(Severity.PASS)]) == Severity.FAIL
    assert worst([]) == Severity.PASS
