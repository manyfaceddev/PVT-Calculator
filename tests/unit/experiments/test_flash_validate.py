import dataclasses
from pvt.experiments.flash.models import FlashVolumetrics
from pvt.experiments.flash.validate import validate

SA372 = FlashVolumetrics(
    pump_initial_cc=50.0, pump_final_cc=70.8945, v_sto_cc=15.7576,
    oil_tare_g=100.0, oil_gross_g=113.71,
    gasometer_initial_cc=500.0, gasometer_final_cc=1458.2037,
    gas_temp_c=20.0, gas_abs_pressure_mbar=1012.25, gas_gravity=1.146,
)

def test_happy_path():
    assert validate(SA372) == []

def test_reversed_pump_flagged():
    bad = dataclasses.replace(SA372, pump_final_cc=40.0)
    assert any("pump" in e.lower() for e in validate(bad))

def test_errors_accumulate():
    bad = dataclasses.replace(SA372, pump_final_cc=40.0, gas_gravity=5.0, v_sto_cc=0.0)
    assert len(validate(bad)) == 3

def test_gasometer_final_less_than_initial():
    bad = dataclasses.replace(SA372, gasometer_final_cc=400.0)
    errors = validate(bad)
    assert any("gasometer" in e.lower() for e in errors)

def test_v_sto_cc_zero():
    bad = dataclasses.replace(SA372, v_sto_cc=0.0)
    errors = validate(bad)
    assert any("v_sto" in e.lower() or "storage" in e.lower() for e in errors)

def test_oil_gross_less_than_tare():
    bad = dataclasses.replace(SA372, oil_gross_g=90.0)
    errors = validate(bad)
    assert any("oil" in e.lower() and "gross" in e.lower() for e in errors)

def test_gas_gravity_too_low():
    bad = dataclasses.replace(SA372, gas_gravity=0.3)
    errors = validate(bad)
    assert any("gravity" in e.lower() for e in errors)

def test_gas_gravity_too_high():
    bad = dataclasses.replace(SA372, gas_gravity=3.5)
    errors = validate(bad)
    assert any("gravity" in e.lower() for e in errors)

def test_pressure_too_low():
    bad = dataclasses.replace(SA372, gas_abs_pressure_mbar=400.0)
    errors = validate(bad)
    assert any("pressure" in e.lower() for e in errors)

def test_pressure_too_high():
    bad = dataclasses.replace(SA372, gas_abs_pressure_mbar=1600.0)
    errors = validate(bad)
    assert any("pressure" in e.lower() for e in errors)

def test_temperature_too_low():
    bad = dataclasses.replace(SA372, gas_temp_c=-15.0)
    errors = validate(bad)
    assert any("temp" in e.lower() for e in errors)

def test_temperature_too_high():
    bad = dataclasses.replace(SA372, gas_temp_c=70.0)
    errors = validate(bad)
    assert any("temp" in e.lower() for e in errors)

def test_pump_constant_zero():
    bad = dataclasses.replace(SA372, pump_constant=0.0)
    errors = validate(bad)
    assert any("pump_constant" in e.lower() or "factor" in e.lower() for e in errors)

def test_vcf_zero():
    bad = dataclasses.replace(SA372, vcf=0.0)
    errors = validate(bad)
    assert any("vcf" in e.lower() or "factor" in e.lower() for e in errors)

def test_gasometer_factor_zero():
    bad = dataclasses.replace(SA372, gasometer_factor=0.0)
    errors = validate(bad)
    assert any("gasometer_factor" in e.lower() or "factor" in e.lower() for e in errors)
