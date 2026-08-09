"""
ui/pages/recombination_page_logic.py — Pure (no `streamlit` widget calls)
helper logic for `ui/pages/recombination_page.py` (Task 12), split out on
purpose so it is plain-`import`-safe.

Why the split: exactly the reason documented in `ui/pages/flash_page_logic.
py` (Task 11) -- `recombination_page.py` is a Streamlit *script* that runs
`st.tabs`/`st.form`/... at module top level (so `AppTest`/`st.Page` can exec
it directly). A plain `from ui.pages import recombination_page` outside a
`ScriptRunContext` runs that top-level widget code once in "bare mode" and,
empirically (see Task 11's report), corrupts Streamlit's form-nesting
tracker for the *next* real `AppTest` run in the same pytest session --
cross-contaminating unrelated test files. Keeping the composition/upload/
report-table plumbing here, with no top-level `streamlit` calls, means
`tests/ui/test_recombination_page.py` can import and test these functions
directly without ever triggering that bare-mode execution. `ui/pages/
recombination_page.py` itself must only ever be reached via
`AppTest.from_file(...)` in tests.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pvt.core.sample import Sample
from pvt.experiments.recombination.models import MultiStageResults
from pvt.io.excel_import import liveoil_v41
from pvt.reporting.tables import ReportRow, ReportTable

MANUAL_SAMPLE = Sample(
    sample_id="Manual Entry", well="", field_name="", reservoir="",
    depth_ft_md=None, fluid_type="", cylinder="",
)


def read_uploaded_liveoil_bytes(data: bytes) -> liveoil_v41.LiveOilImport:
    """Parse a filled ADRIC LiveOil v4.1 workbook from raw bytes.

    `st.file_uploader` yields an `UploadedFile` (a BytesIO-like); `liveoil_
    v41.read` takes `str | Path` because it hands the path straight to
    `openpyxl.load_workbook`. Spools the upload to a `NamedTemporaryFile` and
    reads from its path -- the same pattern `flash_page_logic.
    read_uploaded_bytes` (Task 11) uses for the Flash v6.1 importer, kept
    here so this importer's file-shaped boundary stays intact for its other
    (path-based, golden-tested) callers.
    """
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return liveoil_v41.read(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def volumetric_report_tables(res: MultiStageResults) -> list[ReportTable]:
    """Build report tables for a `calculate_multistage` result (Volumetric
    SF/FF flow, Case 1/Case 2).

    `pvt.reporting.tables.recombination_tables` is shaped for the molar-
    split/loading-plan flow (Tasks 4/5's `MolarSplit`/`LoadingPlan`) -- this
    flow produces neither, so build the report directly from
    `MultiStageResults`' own fields instead, per the Task 12 brief ("build a
    ReportTable list inline from MultiStageResults fields, keep it simple").
    """
    gor_unit = "scf/STB" if res.units == "field" else "sm3/sm3"
    pres_unit = "psia" if res.units == "field" else "bara"
    temp_unit = "F" if res.units == "field" else "C"

    setup_rows = [
        ReportRow("Live Fluid Volume", f"{res.V_live:.2f}", "cc"),
        ReportRow("Oil Source", "Case 1 - Separator Oil" if res.oil_source == "separator"
                  else "Case 2 - Stock Tank Oil", ""),
        ReportRow("Shrinkage Factor (SF)", f"{res.SF:.4f}", ""),
        ReportRow("Flash Factor (FF)", f"{res.FF_input:.4f}", gor_unit),
    ]
    recomb_rows = [
        ReportRow("Recombination Pressure", f"{res.P_recomb_psia:.2f}", pres_unit),
        ReportRow("Recombination Temperature", f"{res.T_recomb_F:.1f}", temp_unit),
        ReportRow("Recombination Z-factor", f"{res.Z_recomb:.4f}", ""),
        ReportRow("Recombination Factor", f"{res.factor_recomb:.6f}", ""),
    ]
    charge_rows = [
        ReportRow("Separator Oil Volume", f"{res.V_oil_sep:.2f}", "cc"),
        ReportRow("Oil Volume at Charging Pressure", f"{res.V_oil_charge:.2f}", "cc"),
        ReportRow("STO-Equivalent Oil Volume", f"{res.V_oil_STO:.2f}", "cc"),
        ReportRow("Total Gas @ Standard", f"{res.total_V_gas_std_cc:.2f}", "cc"),
        ReportRow("Total Gas @ Recombination", f"{res.total_V_gas_recomb_cc:.2f}", "cc"),
        ReportRow("Cylinder Mix Ratio", f"{res.cylinder_mix_ratio:.4f}", ""),
    ]
    gor_rows = [
        ReportRow("Total GOR (input)", f"{res.R_total_input:.4f}", gor_unit),
        ReportRow("GOR (back-calculated)", f"{res.GOR_check:.4f}", gor_unit),
    ]
    stage_rows = [
        ReportRow(f"Stage {sr.stage_num} ({sr.label}) GOR", f"{sr.R_input:.2f}", gor_unit)
        for sr in res.stage_results
    ]
    return [
        ReportTable("Setup", setup_rows),
        ReportTable("Recombination Conditions", recomb_rows),
        ReportTable("Charge Volumes", charge_rows),
        ReportTable("GOR Verification", gor_rows),
        ReportTable("Stage GORs", stage_rows),
    ]
