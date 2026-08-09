"""
pvt/reporting/tables.py — Build ReportTable structures from the typed result
dataclasses produced by pvt.experiments (Tasks 2-6), for consumption by
pvt.reporting.excel_export.

`flash_tables` and `recombination_tables` each enumerate every field of
their input dataclasses as a formatted `ReportRow`, plus a "QC Summary"
section holding one row per `QCResult` passed in (check_id / severity /
message) -- every QCResult a caller passes in is guaranteed to appear.
"""

from dataclasses import dataclass

from pvt.experiments.flash.models import FlashResults
from pvt.experiments.flash.recombine import MassRecombination
from pvt.experiments.recombination.loading import LoadingPlan
from pvt.experiments.recombination.molar import MolarSplit
from pvt.qc.engine import QCResult


@dataclass(frozen=True)
class ReportRow:
    """A single labelled value in a report table (label, value, unit)."""

    label: str
    value: str
    unit: str = ""


@dataclass(frozen=True)
class ReportTable:
    """A titled block of report rows -- one report section."""

    title: str
    rows: list[ReportRow]


def _qc_rows(qc: list[QCResult]) -> list[ReportRow]:
    """One row per QCResult: label=check_id, value=severity, unit=message."""
    return [ReportRow(result.check_id, result.severity.value, result.message) for result in qc]


def flash_tables(
    results: FlashResults, recomb: MassRecombination, qc: list[QCResult]
) -> list[ReportTable]:
    """Build the Flash Results / Whole Sample / QC Summary report tables.

    Args:
        results: Flash-separation results (Task 2's `calculate`).
        recomb: Mass-basis flash-gas + flash-oil recombination (Task 3's
            `recombine_mass`).
        qc: QC results to list in the QC Summary section -- every entry
            appears as its own row.
    """
    flash_rows = [
        ReportRow("Charge Pressure Volume", f"{results.v_press_cc:.4f}", "cc"),
        ReportRow("Flashed Oil Mass", f"{results.m_oil_g:.2f}", "g"),
        ReportRow("Gas Volume (Measured)", f"{results.v_gas_meas_cc:.2f}", "cc"),
        ReportRow("Gas Volume (Standard)", f"{results.v_gas_std_cc:.2f}", "cc"),
        ReportRow("Gas Density (Standard)", f"{results.gas_density_std_g_cc:.6f}", "g/cc"),
        ReportRow("Flashed Gas Mass", f"{results.m_gas_g:.5f}", "g"),
        ReportRow("GOR", f"{results.gor_cc_cc:.4f}", "cc/cc"),
        ReportRow("GOR", f"{results.gor_scf_bbl:.2f}", "scf/bbl"),
        ReportRow("Bo", f"{results.bo_flash:.4f}", "vol/vol"),
        ReportRow("Shrinkage", f"{results.shrinkage:.4f}", ""),
        ReportRow("Oil Density (60F)", f"{results.oil_density_60f_g_cc:.4f}", "g/cc"),
        ReportRow("API Gravity", f"{results.api:.1f}", "API"),
    ]
    whole_sample_rows = [
        ReportRow("Gas Mass Fraction", f"{recomb.wf_gas * 100.0:.2f}", "wt%"),
        ReportRow("Oil Mass Fraction", f"{recomb.wf_oil * 100.0:.2f}", "wt%"),
        ReportRow("Whole Sample MW", f"{recomb.mw_whole_sample:.2f}", "g/mol"),
    ]
    return [
        ReportTable("Flash Results", flash_rows),
        ReportTable("Whole Sample", whole_sample_rows),
        ReportTable("QC Summary", _qc_rows(qc)),
    ]


def recombination_tables(
    split: MolarSplit, plan: LoadingPlan, qc: list[QCResult]
) -> list[ReportTable]:
    """Build the Molar Split / Loading Plan / QC Summary report tables.

    Args:
        split: Molar gas/oil split (Task 4's `molar_split`).
        plan: Cylinder loading plan (Task 5's `plan_loading`).
        qc: QC results to list in the QC Summary section -- every entry
            appears as its own row.
    """
    split_rows = [
        ReportRow("GOR (Effective)", f"{split.gor_scf_stb_effective:.2f}", "scf/STB"),
        ReportRow("GOR", f"{split.gor_cc_cc:.4f}", "cc/cc"),
        ReportRow("Gas Moles per cc STO", f"{split.n_gas_per_cc_sto:.6f}", "mol/cc"),
        ReportRow("Oil Moles per cc STO", f"{split.n_oil_per_cc_sto:.6f}", "mol/cc"),
        ReportRow("Gas Mole Fraction", f"{split.f_gas * 100.0:.2f}", "mol%"),
        ReportRow("Oil Mole Fraction", f"{split.f_oil * 100.0:.2f}", "mol%"),
        ReportRow("Gas Mass Fraction", f"{split.w_gas * 100.0:.2f}", "wt%"),
        ReportRow("Oil Mass Fraction", f"{split.w_oil * 100.0:.2f}", "wt%"),
        ReportRow("Wellstream MW", f"{split.mw_wellstream:.2f}", "g/mol"),
    ]
    plan_rows = [
        ReportRow("Oil Charge Volume", f"{plan.v_oil_charge_cc:.2f}", "cc"),
        ReportRow("STO Equivalent Volume", f"{plan.v_sto_equivalent_cc:.2f}", "cc"),
        ReportRow("Oil Moles Charged", f"{plan.n_oil_mol:.6f}", "mol"),
        ReportRow("Gas Moles Required", f"{plan.n_gas_mol:.6f}", "mol"),
        ReportRow("Gas Volume (Standard)", f"{plan.v_gas_std_cc:.2f}", "cc"),
        ReportRow("Std cc per cc (Load)", f"{plan.std_cc_per_cc_at_load:.4f}", ""),
        ReportRow("Gas Charge Volume", f"{plan.v_gas_charge_cc:.2f}", "cc"),
        ReportRow("Total Charge Volume", f"{plan.total_charge_cc:.2f}", "cc"),
        ReportRow("Fits Cylinder", "Yes" if plan.fits else "No", ""),
        ReportRow("Cylinder Utilization", f"{plan.utilization_pct:.2f}", "%"),
    ]
    return [
        ReportTable("Molar Split", split_rows),
        ReportTable("Loading Plan", plan_rows),
        ReportTable("QC Summary", _qc_rows(qc)),
    ]
