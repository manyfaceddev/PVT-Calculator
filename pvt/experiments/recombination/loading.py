"""Cylinder loading-volume planning + actual-GOR verification, per the LiveOil
v4.1 Loading_Volumes sheet.

`plan_loading` takes a target stock-tank-oil (STO) charge volume and the
molar gas/oil split from `molar.molar_split`, and works out how much
recombination gas (by volume, at gas-cylinder load conditions) must be
charged alongside it to hit the split's GOR, plus whether the combined oil +
gas charge fits the transfer cylinder. `verify_actual_gor` runs the same
real-gas bookkeeping in reverse: given the oil and gas volumes actually
metered into the cylinder, it recovers the as-loaded GOR and grades its
deviation from the target GOR via the QC engine.

Pressure basis: `P_load_psia = psig + 14.73` (`constants.P_STD_PSIA`), NOT
`psig + 14.696` (`constants.P_ATM_PSIA`). This is deliberate — the
Loading_Volumes sheet's B16/B17 gauge->absolute formulas add the lab
volumetric standard (14.73 psia), not the atmosphere/gas-constant standard
(14.696 psia) used elsewhere for psig->psia conversions. See the dual-basis
note in `pvt.core.constants`.
"""

from dataclasses import dataclass

from pvt.core import constants as c
from pvt.core import units as u
from pvt.experiments.recombination.molar import MolarSplit
from pvt.qc.engine import QCResult, ThresholdRegistry, grade

_FILL_LIMIT_FRACTION = 0.95
"""Cylinder fill-limit gate: total charge must be <= 95% of cylinder volume
(headspace reserve for thermal expansion during recombination)."""


@dataclass(frozen=True)
class LoadingInputs:
    """Cylinder-loading conditions and targets for a recombination charge."""

    cylinder_volume_cc: float
    """Transfer-cylinder internal volume (cc)."""

    target_oil_cc: float
    """Target volume of stock-tank oil to charge, at oil-load conditions (cc)."""

    oil_load_p_psig: float
    """Oil-cylinder gauge pressure at loading (psig). Descriptive/traceability
    field — `sto_density_at_load_g_cc` already reflects this condition, so
    the loading-plan formulas do not re-derive it."""

    oil_load_t_f: float
    """Oil-cylinder temperature at loading (°F). See `oil_load_p_psig`."""

    gas_load_p_psig: float
    """Gas-cylinder gauge pressure at loading (psig) — the charge pressure
    the recombination gas is metered in at."""

    gas_load_t_f: float
    """Gas-cylinder temperature at loading (°F)."""

    z_gas_load: float
    """Gas Z-factor at gas-load conditions (`gas_load_p_psig`, `gas_load_t_f`)."""

    sto_density_at_load_g_cc: float
    """Stock-tank oil density at oil-load conditions (g/cc)."""


@dataclass(frozen=True)
class LoadingPlan:
    """Planned oil + gas cylinder charge to hit a target GOR."""

    v_oil_charge_cc: float
    """Oil volume charged, at oil-load conditions (cc) — equals `target_oil_cc`."""

    v_sto_equivalent_cc: float
    """`v_oil_charge_cc` converted to a stock-tank (60°F) equivalent volume."""

    n_oil_mol: float
    """Moles of stock-tank oil charged (= v_sto_equivalent_cc * rho_60F / MW)."""

    n_gas_mol: float
    """Moles of recombination gas required to hit the split's GOR."""

    v_gas_std_cc: float
    """`n_gas_mol` expressed as a standard-conditions gas volume (cc)."""

    std_cc_per_cc_at_load: float
    """Real-gas conversion factor: standard cc per cc at gas-load conditions."""

    v_gas_charge_cc: float
    """Gas volume to charge, at gas-load conditions (cc)."""

    total_charge_cc: float
    """`v_oil_charge_cc + v_gas_charge_cc` — total cylinder charge volume (cc)."""

    fits: bool
    """Whether `total_charge_cc` fits within the fill-limit gate (95% of cylinder)."""

    utilization_pct: float
    """`total_charge_cc / cylinder_volume_cc * 100` — cylinder fill percentage."""


def plan_loading(
    inputs: LoadingInputs,
    split: MolarSplit,
    sto_density_60f: float,
    sto_mw: float,
    z_std: float = 0.99,
) -> LoadingPlan:
    """Plan the oil + gas cylinder charge needed to hit `split`'s GOR.

    Args:
        inputs: Cylinder and loading-condition inputs (target oil volume,
            cylinder volume, gas-load pressure/temperature/Z).
        split: Molar gas/oil split (moles gas per cc STO) from `molar_split`,
            defining the target GOR to charge toward.
        sto_density_60f: Stock-tank oil density at 60°F standard conditions (g/cc).
        sto_mw: Stock-tank oil molecular weight (g/mol).
        z_std: Gas Z-factor at standard conditions (default 0.99, per the
            LiveOil Loading_Volumes sheet).

    Returns:
        LoadingPlan with the oil/gas charge volumes, intermediate moles and
        standard-volume figures, and the cylinder fill-limit gate result.
    """
    v_oil_charge = inputs.target_oil_cc
    v_sto_equiv = v_oil_charge * inputs.sto_density_at_load_g_cc / sto_density_60f
    n_oil = v_sto_equiv * sto_density_60f / sto_mw
    n_gas = split.n_gas_per_cc_sto * v_sto_equiv

    v_gas_std = n_gas * z_std * c.R_PSIA_CC_MOL_K * c.T_STD_K / c.P_STD_PSIA

    # Gas-load conditions (the cylinder the recombination gas is charged into).
    p_load_psia = u.psig_to_psia(inputs.gas_load_p_psig, p_atm_psia=c.P_STD_PSIA)
    t_load_k = u.f_to_k(inputs.gas_load_t_f)
    z_load = inputs.z_gas_load

    factor = p_load_psia * z_std * c.T_STD_K / (z_load * t_load_k * c.P_STD_PSIA)
    v_gas_charge = v_gas_std / factor

    total_charge = v_oil_charge + v_gas_charge
    fits = total_charge <= _FILL_LIMIT_FRACTION * inputs.cylinder_volume_cc
    utilization_pct = total_charge / inputs.cylinder_volume_cc * 100.0

    return LoadingPlan(
        v_oil_charge_cc=v_oil_charge,
        v_sto_equivalent_cc=v_sto_equiv,
        n_oil_mol=n_oil,
        n_gas_mol=n_gas,
        v_gas_std_cc=v_gas_std,
        std_cc_per_cc_at_load=factor,
        v_gas_charge_cc=v_gas_charge,
        total_charge_cc=total_charge,
        fits=fits,
        utilization_pct=utilization_pct,
    )


def verify_actual_gor(
    actual_oil_cc: float,
    actual_gas_cc: float,
    inputs: LoadingInputs,
    sto_density_60f: float,
    target_gor_scf_stb: float,
    z_std: float = 0.99,
    registry: ThresholdRegistry | None = None,
) -> tuple[float, float, QCResult]:
    """Back-calculate the as-loaded GOR from actual charge volumes and grade it.

    Runs the `plan_loading` real-gas bookkeeping in reverse: converts the
    actual gas volume (metered at gas-load conditions) to standard
    conditions, converts the actual oil volume to a stock-tank equivalent,
    and forms their ratio as a scf/STB GOR.

    Args:
        actual_oil_cc: Oil volume actually charged, at oil-load conditions (cc).
        actual_gas_cc: Gas volume actually charged, at gas-load conditions (cc).
        inputs: Loading-condition inputs (gas-load pressure/temperature/Z,
            oil density at load).
        sto_density_60f: Stock-tank oil density at 60°F standard conditions (g/cc).
        target_gor_scf_stb: Target GOR (scf/STB) to compare the actual GOR against.
        z_std: Gas Z-factor at standard conditions (default 0.99).
        registry: ThresholdRegistry supplying the "gor_actual_vs_target_pct"
            (review%, fail%) band; defaults to house thresholds (5%/10%).

    Returns:
        (actual_gor_scf_stb, deviation_pct, qc) — the as-loaded GOR, its
        signed percent deviation from `target_gor_scf_stb`
        ((actual - target) / target * 100), and the graded QCResult.
    """
    registry = registry or ThresholdRegistry()

    p_load_psia = u.psig_to_psia(inputs.gas_load_p_psig, p_atm_psia=c.P_STD_PSIA)
    t_load_k = u.f_to_k(inputs.gas_load_t_f)
    z_load = inputs.z_gas_load

    n_actual = actual_gas_cc * p_load_psia / (z_load * c.R_PSIA_CC_MOL_K * t_load_k)
    v_std = n_actual * z_std * c.R_PSIA_CC_MOL_K * c.T_STD_K / c.P_STD_PSIA

    sto_actual = actual_oil_cc * inputs.sto_density_at_load_g_cc / sto_density_60f
    gor = (v_std / sto_actual) * c.CC_PER_STB / c.CC_PER_SCF

    dev_pct = (gor - target_gor_scf_stb) / target_gor_scf_stb * 100.0

    check_id = "gor_actual_vs_target_pct"
    review_at, fail_at = registry.get(check_id)
    severity = grade(dev_pct, review_at, fail_at)
    qc = QCResult(
        check_id=check_id,
        severity=severity,
        value=dev_pct,
        threshold=f"review >{review_at}% / fail >{fail_at}%",
        message=(
            f"Actual GOR {gor:.1f} scf/STB deviates {dev_pct:+.2f}% from "
            f"target {target_gor_scf_stb:.1f} scf/STB ({severity.value})"
        ),
    )
    return gor, dev_pct, qc
