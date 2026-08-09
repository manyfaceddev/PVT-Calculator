from dataclasses import dataclass


@dataclass(frozen=True)
class FlashVolumetrics:
    pump_initial_cc: float
    pump_final_cc: float
    v_sto_cc: float
    oil_tare_g: float
    oil_gross_g: float
    gasometer_initial_cc: float
    gasometer_final_cc: float
    gas_temp_c: float
    gas_abs_pressure_mbar: float
    gas_gravity: float
    pump_constant: float = 1.0
    vcf: float = 1.0
    gasometer_factor: float = 1.0


@dataclass(frozen=True)
class FlashResults:
    v_press_cc: float
    m_oil_g: float
    v_gas_meas_cc: float
    v_gas_std_cc: float
    gas_density_std_g_cc: float
    m_gas_g: float
    gor_cc_cc: float
    gor_scf_bbl: float
    bo_flash: float
    shrinkage: float
    oil_density_60f_g_cc: float
    api: float
