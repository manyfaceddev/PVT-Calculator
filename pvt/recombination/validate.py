"""
pvt/recombination/validate.py — Input validation for recombination calculations.
Returns lists of human-readable error strings; empty list means inputs are valid.
"""

from pvt.recombination.models import RecombinationInputs, SeparatorStage
from pvt.constants import Units


def validate(inp: RecombinationInputs) -> list[str]:
    """Validate single-stage recombination inputs."""
    errors: list[str] = []
    if inp.V_cell <= 0:
        errors.append("Cell volume must be > 0 cc.")
    if inp.R_sep <= 0:
        errors.append("GOR must be > 0.")
    if inp.P_sep <= 0:
        errors.append("Separator pressure must be > 0.")
    if inp.Z_sep <= 0 or inp.Z_sep > 2.0:
        errors.append("Z-factor must be in range (0, 2.0].")
    if inp.Bo_sep <= 0 or inp.Bo_sep > 5.0:
        errors.append("Bo_sep must be in range (0, 5.0].")
    if not (0.0 < inp.oil_fraction < 1.0):
        errors.append("Oil fraction must be between 0 and 1 (exclusive).")
    if inp.units == "field" and inp.T_sep < -100:
        errors.append("Separator temperature (°F) looks unrealistically low.")
    if inp.units == "si" and inp.T_sep < -73:
        errors.append("Separator temperature (°C) looks unrealistically low.")
    return errors


def validate_multistage(
    stages:       list[SeparatorStage],
    V_live:       float,
    Bo_sep:       float,
    P_recomb:     float,
    T_recomb:     float,
    Z_recomb:     float,
    units:        Units,
    oil_source:   str   = "separator",
    R_STO:        float = 0.0,
    P_charge_oil: float = 2014.7,
    c_o:          float = 10.0e-6,
) -> list[str]:
    """Validate multi-stage recombination inputs."""
    errors: list[str] = []

    if not stages:
        errors.append("At least one separator stage is required.")

    for i, s in enumerate(stages, 1):
        if s.R <= 0:
            errors.append(f"Stage {i} GOR must be > 0.")
        if s.P <= 0:
            errors.append(f"Stage {i} pressure must be > 0.")
        if s.Z <= 0 or s.Z > 2.0:
            errors.append(f"Stage {i} Z-factor must be in (0, 2.0].")
        if units == "field" and s.T < -100:
            errors.append(f"Stage {i} temperature (°F) looks unrealistically low.")
        if units == "si" and s.T < -73:
            errors.append(f"Stage {i} temperature (°C) looks unrealistically low.")

    if V_live <= 0:
        errors.append("Live fluid volume must be > 0 cc.")

    # Bo_sep only meaningful for Case 1 (separator oil)
    if oil_source == "separator":
        if Bo_sep <= 0 or Bo_sep > 5.0:
            errors.append("Bo_sep must be in range (0, 5.0].")

    if P_recomb <= 0:
        errors.append("Recombination pressure must be > 0.")
    if Z_recomb <= 0 or Z_recomb > 2.0:
        errors.append("Recombination Z-factor must be in (0, 2.0].")
    if units == "field" and T_recomb < -100:
        errors.append("Recombination temperature (°F) looks unrealistically low.")
    if units == "si" and T_recomb < -73:
        errors.append("Recombination temperature (°C) looks unrealistically low.")

    # Oil charging pressure
    if P_charge_oil <= 0:
        errors.append("Oil charging pressure must be > 0.")
    if P_charge_oil >= P_recomb:
        errors.append(
            "Oil charging pressure must be less than recombination pressure "
            "(oil is loaded at a lower pressure; gas brings it up to P_recomb)."
        )

    # Oil compressibility
    if c_o < 0:
        errors.append("Oil compressibility (c_o) must be ≥ 0.")
    if c_o > 1.0e-3:
        errors.append("Oil compressibility (c_o) seems unrealistically high (> 1000 × 10⁻⁶ psi⁻¹).")

    # Case 2 — stock tank GOR
    if oil_source == "stock_tank":
        if R_STO < 0:
            errors.append("Stock tank GOR must be ≥ 0.")

    return errors
