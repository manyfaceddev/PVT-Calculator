"""
pvt/experiments/cce/models.py — Input / output data models for Constant
Composition Expansion (CCE) calculations.

Pure dataclasses; no calculation logic (see calc.py, Task 2).

Source workbook cell map (`tests/fixtures/workbooks/
2_CCE_Calculation_Sheet_v5_OpenSafe_A4.xlsx`, sheet "CCE Calculation"),
confirmed by loading the fixture with openpyxl in both `data_only=True`
and `data_only=False` modes (see also
`tests/unit/experiments/test_cce_validate.py`):

    D5  = Reservoir Pressure (psig)                -> CceInputs.reservoir_p_psia
    D6  = Temperature (deg F)                      -> CceInputs.t_res_f
    D9  = Visual Bubble Point (psig)                -> CceInputs.psat_visual
    D10 = Bubble Point Step # (1-based row index)   -> CceInputs.bubble_point_step
    Stage table, rows 16-55 (40 stages):
        A = Step (1..40)                                    -> CceStage.step
        B = Pressure (psig, as-entered; D3 policy)          -> CceStage.p
        C = Volume (cc) -- ENTERED value                    -> CceStage.v_cell_cc
        D = Relative Volume  (formula `=C{row}/$J$8`)       -- DERIVED, not imported
        E = Density (g/cm3)  (formula `=IF(...,$J$7/C{row},"")`) -- DERIVED, not imported

    Column determination: loading the workbook with `data_only=False`
    shows C16 holds a raw float (94.08822903) with no formula, while D16
    and E16 hold formula strings that reference C16. C is therefore the
    entered cell volume; D and E are workbook-computed and are NOT
    imported as inputs anywhere (the engine recomputes them in calc.py,
    Task 2).

    NOTE on a brief/plan documentation offset: the task-1 brief and the
    Phase 3a plan's Task 1/Task 5 cell maps describe the visual Psat as
    cell D8. The fixture workbook actually has D8 = "Measured HPHT
    Density (g/cm3)" = 0.72868 and D9 = "Visual Bubble Point (psig)" =
    1155.73 (rows 6-10 run Temperature, Working Pressure, Density,
    Visual Psat, Bubble Step, in that order). The *values* the brief
    quotes (visual Psat ~1155.73, bubble step 20) match D9/D10 exactly
    and unambiguously identify the correct cells, so this module (and
    its tests) use D9 for psat_visual. Flagged here for the Task 5
    importer author to use the corrected address. This is a
    plan-documentation offset, not a workbook defect, so it is not
    logged to docs/workbook-defect-review.md.

    ROUND-2 NOTE (Task 2 controller adjudication, docs/excel-deviations.md
    D-020): the plan's Task 5 cell map also lists D7 as the reservoir
    pressure. The fixture has D7 = "Working Pressure (psig)" = 7014.73
    (the first stage's pressure, row 16) -- a DIFFERENT, independently
    entered lab input from D5 = "Reservoir Pressure (psig)" = 3938.73,
    which is what `Mean Compressibility!H8` actually anchors its
    "Reservoir Pressure -> Psat" range to (via `MATCH` on the stage
    table, landing on row 23, not row 16). CceInputs.reservoir_p_psia
    below corresponds to D5, not D7. Flagged here for the Task 5
    importer author: it must read BOTH D5 (reservoir_p_psia) and D9
    (psat_visual) -- the plan's D7/D8 cell list is wrong on both.

Pressure policy (defect D3, see plan Global Constraints): CceStage.p is
carried as-entered from the workbook (labelled "psig" on the sheet); the
engine's absolute-psia policy and the "as entered" import note are an
importer (Task 5) concern. This module performs no unit conversion.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CceStage:
    """One CCE expansion stage: step index, cell pressure, and total cell
    volume (entered, sheet column C)."""

    step: int
    p: float  # pressure, as-entered (psia policy pending D3 ruling; see module docstring)
    v_cell_cc: float  # total cell volume at p (cc)


@dataclass(frozen=True)
class CceInputs:
    """Inputs for a Constant Composition Expansion test.

    `reservoir_p_psia` (sheet `CCE Calculation!D5`, "Reservoir Pressure")
    anchors the reservoir->Psat mean compressibility, per `Mean
    Compressibility!H8`'s MATCH on the stage table (see calc.py, Task 2
    round 2). Optional -- defaults to None, in which case calc.py's
    `mean_compressibility_1_psi` carries no "res_to_psat" key, only the
    always-available "first_stage_to_psat" pairing.
    """

    t_res_f: float
    psat_visual: float  # visually observed Psat (sheet D9)
    bubble_point_step: int  # user-picked step, 1-based (sheet D10)
    stages: tuple[CceStage, ...]  # descending P, 2..40 stages
    rho_at_psat_g_cc: float | None = None  # density at Psat, if measured
    reservoir_p_psia: float | None = None  # reservoir pressure, if tracked separately (sheet D5)


@dataclass(frozen=True)
class CceStageResult:
    """Per-stage CCE calculation output (calc.py, Task 2, populates these).

    `rel_vol` is defined for every stage (V_i / V_sat). `density_g_cc`
    and `inst_compressibility_1e6_per_psi` are single-phase-only (at/above
    Psat) and None below Psat; `inst_compressibility_1e6_per_psi` is
    additionally None at the bubble-point row itself, which the sheet's
    central-difference formula straddles into two-phase volume growth
    (ledger row D-019 -- Task 2 concern, this dataclass only declares the
    shape). `y_function` is two-phase-only (below Psat) and None at/above
    Psat.
    """

    step: int
    p: float
    rel_vol: float
    density_g_cc: float | None = None
    inst_compressibility_1e6_per_psi: float | None = None
    y_function: float | None = None


@dataclass(frozen=True)
class CceResults:
    """Full output of a CCE calculation (see calc.py, Task 2)."""

    psat_from_data: float
    psat_consistency_ok: bool  # |psat_visual - picked-row P| <= 10 psi
    v_sat_cc: float
    stages: tuple[CceStageResult, ...]
    mean_compressibility_1_psi: dict[str, float]
    """Keys: "first_stage_to_psat" (always present once >=2 stages sit at
    or above Psat) and "res_to_psat" (present only when
    CceInputs.reservoir_p_psia is set; see calc.py, Task 2 round 2)."""
