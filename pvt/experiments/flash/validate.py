from pvt.experiments.flash.models import FlashVolumetrics


def validate(inputs: FlashVolumetrics) -> list[str]:
    """Validate FlashVolumetrics inputs. Returns list of error messages (empty if valid)."""
    errors = []

    # Rule 1: pump_final > pump_initial
    if inputs.pump_final_cc <= inputs.pump_initial_cc:
        errors.append("pump_final_cc must be greater than pump_initial_cc")

    # Rule 2: gasometer_final >= gasometer_initial
    if inputs.gasometer_final_cc < inputs.gasometer_initial_cc:
        errors.append("gasometer_final_cc must be >= gasometer_initial_cc")

    # Rule 3: v_sto_cc > 0
    if inputs.v_sto_cc <= 0:
        errors.append("v_sto_cc must be > 0")

    # Rule 4: oil_gross_g > oil_tare_g
    if inputs.oil_gross_g <= inputs.oil_tare_g:
        errors.append("oil_gross_g must be greater than oil_tare_g")

    # Rule 5: 0.5 < gas_gravity < 3.0
    if not (0.5 < inputs.gas_gravity < 3.0):
        errors.append("gas_gravity must be between 0.5 and 3.0 (exclusive)")

    # Rule 6: 500 < gas_abs_pressure_mbar < 1500
    if not (500 < inputs.gas_abs_pressure_mbar < 1500):
        errors.append("gas_abs_pressure_mbar must be between 500 and 1500 (exclusive)")

    # Rule 7: -10 < gas_temp_c < 60
    if not (-10 < inputs.gas_temp_c < 60):
        errors.append("gas_temp_c must be between -10 and 60 (exclusive)")

    # Rule 8: factors > 0
    if inputs.pump_constant <= 0:
        errors.append("pump_constant must be > 0")
    if inputs.vcf <= 0:
        errors.append("vcf must be > 0")
    if inputs.gasometer_factor <= 0:
        errors.append("gasometer_factor must be > 0")

    return errors
