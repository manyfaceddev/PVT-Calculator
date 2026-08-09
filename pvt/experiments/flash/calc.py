"""Atmospheric flash separation, water-pump method (ADRIC Flash v6.1 methodology)."""
from pvt.core import constants as c
from pvt.core import units as u
from pvt.core.exceptions import InputValidationError
from pvt.experiments.flash.models import FlashResults, FlashVolumetrics
from pvt.experiments.flash.validate import validate


def calculate(inputs: FlashVolumetrics, *, validate_inputs: bool = True) -> FlashResults:
    if validate_inputs and (errors := validate(inputs)):
        raise InputValidationError(errors)
    i = inputs
    v_press = (i.pump_final_cc - i.pump_initial_cc) * i.pump_constant * i.vcf
    m_oil = i.oil_gross_g - i.oil_tare_g
    v_gas_meas = (i.gasometer_final_cc - i.gasometer_initial_cc) * i.gasometer_factor
    # Ideal-gas (Z=1) correction to lab standard conditions; measured absolute pressure
    # is the input (workbook's unused B25 composite: ledger D-017).
    v_gas_std = v_gas_meas * (i.gas_abs_pressure_mbar / c.P_STD_MBAR) * (
        c.T_STD_K / (i.gas_temp_c + 273.15))
    gas_density = i.gas_gravity * c.AIR_DENSITY_STD_G_CC
    gor_cc = v_gas_std / i.v_sto_cc
    rho_sto = m_oil / i.v_sto_cc
    return FlashResults(
        v_press_cc=v_press, m_oil_g=m_oil, v_gas_meas_cc=v_gas_meas,
        v_gas_std_cc=v_gas_std, gas_density_std_g_cc=gas_density,
        m_gas_g=v_gas_std * gas_density, gor_cc_cc=gor_cc,
        gor_scf_bbl=gor_cc * c.FT3_PER_BBL, bo_flash=v_press / i.v_sto_cc,
        shrinkage=i.v_sto_cc / v_press, oil_density_60f_g_cc=rho_sto,
        api=u.api_from_density_g_cc(rho_sto),
    )
