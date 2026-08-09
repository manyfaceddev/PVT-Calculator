"""
tests/unit/test_ui_components.py — Tests for `ui/common/components.py`'s
pure title/filename derivation helpers (demo-minor review fix).

`ui/` sits outside the `pvt` coverage gate; these tests cover
`_derive_title`/`_prefixed_filename` directly (plain functions, no
`streamlit` widget calls) and confirm `report_download` itself still runs
without raising when called outside a Streamlit `ScriptRunContext` (the
same "bare mode" every other plain-function test in `tests/ui/` relies on
implicitly via `AppTest` -- here exercised directly since `report_download`
has no `st.tabs`/`st.form` top-level-script requirement).
"""

from __future__ import annotations

from pvt.core.sample import Sample
from pvt.reporting.tables import ReportRow, ReportTable
from ui.common.components import _derive_title, _prefixed_filename, report_download

SAMPLE = Sample(
    sample_id="SA-372", well="WELL-X", field_name="Upper Zakum", reservoir="Kharaib-2",
    depth_ft_md=9105.0, fluid_type="Black Oil", cylinder="RF1168636",
)


def test_derive_title_strips_extension_and_title_cases():
    assert _derive_title("flash_separation_report.xlsx") == "Flash Separation Report"
    assert _derive_title("recombination_volumetric_report.xlsx") == "Recombination Volumetric Report"


def test_derive_title_falls_back_to_filename_when_stem_is_empty():
    assert _derive_title(".xlsx") == ".xlsx"


def test_prefixed_filename_embeds_sample_id():
    assert _prefixed_filename("flash_separation_report.xlsx", "SA-372") == (
        "SA-372_flash_separation_report.xlsx"
    )


def test_prefixed_filename_collapses_whitespace_in_sample_id():
    # MANUAL_SAMPLE's sample_id is "Manual Entry" -- must not produce a
    # filename with a literal space in it.
    assert _prefixed_filename("flash_separation_report.xlsx", "Manual Entry") == (
        "Manual_Entry_flash_separation_report.xlsx"
    )


def test_prefixed_filename_falls_back_when_sample_id_is_blank():
    assert _prefixed_filename("report.xlsx", "") == "sample_report.xlsx"


def test_report_download_runs_without_raising_with_default_title():
    tables = [ReportTable("QC Summary", [ReportRow("composition_sum", "PASS", "msg")])]
    report_download(tables, SAMPLE, "flash_separation_report.xlsx")


def test_report_download_runs_without_raising_with_explicit_title():
    tables = [ReportTable("QC Summary", [ReportRow("composition_sum", "PASS", "msg")])]
    report_download(tables, SAMPLE, "flash_separation_report.xlsx", title="Custom Title")
