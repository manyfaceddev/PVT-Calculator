"""
pvt/experiments/recombination/validate.py — Input validation for recombination calculations.
Returns lists of human-readable error strings; empty list means inputs are valid.
"""

from pvt.experiments.recombination.models import SeparatorStage
from pvt.core.constants import Units


def validate_multistage(
    stages:     list[SeparatorStage],
    V_live:     float,
    SF:         float,          # Separator-Oil Shrinkage Factor (0 < SF ≤ 1)
    P_recomb:   float,
    T_recomb:   float,
    Z_recomb:   float,
    units:      Units,
    oil_source: str   = "separator",
    FF:         float = 0.0,    # Flash Factor (scf/STB STO or sm³/sm³); Case 2 only
) -> list[str]:
    """Validate multi-stage recombination inputs (Carlsen & Whitson framework)."""
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

    # SF only meaningful for Case 1 (separator oil); Case 2 charges STO directly.
    if oil_source == "separator":
        if SF <= 0 or SF > 1.0:
            errors.append("Shrinkage Factor (SF) must be in range (0, 1.0]. "
                          "Typical values: 0.65–0.99.")

    if P_recomb <= 0:
        errors.append("Recombination pressure must be > 0.")
    if Z_recomb <= 0 or Z_recomb > 2.0:
        errors.append("Recombination Z-factor must be in (0, 2.0].")
    if units == "field" and T_recomb < -100:
        errors.append("Recombination temperature (°F) looks unrealistically low.")
    if units == "si" and T_recomb < -73:
        errors.append("Recombination temperature (°C) looks unrealistically low.")

    # Case 2 — Flash Factor
    if oil_source == "stock_tank":
        if FF < 0:
            errors.append("Flash Factor (FF) must be ≥ 0.")

    return errors
