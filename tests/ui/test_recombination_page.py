"""
tests/ui/test_recombination_page.py — Tests for `ui/pages/recombination_page.py`
(Task 12).

`ui/` sits outside the `pvt` coverage gate; these tests prove both tabs boot
without exception, that the Volumetric (SF/FF) manual flow reproduces a
known `calculate_multistage` figure, that the Molar manual flow reproduces
the golden `f_gas ≈ 0.370636` figure (the brief's Step-1 contract) through
the real engine chain, and that the two AppTest-unscriptable widgets
(`st.file_uploader` in the Molar upload sub-tab) has its underlying logic
covered directly via `ui.pages.recombination_page_logic`.

IMPORTANT: `ui.pages.recombination_page` itself is a Streamlit *script* -- it
runs `st.tabs`/`st.form`/... at module top level by design, so `AppTest` can
exec it directly. It must NOT be reached via a plain `import`/`from ...
import` anywhere in this file: see `ui/pages/recombination_page_logic.py`'s
module docstring (and Task 11's report) for the Streamlit form-tracker
corruption a bare import causes. Only ever reach `recombination_page.py`
through `AppTest.from_file(...)` here; the plain-function helpers it uses
live in `recombination_page_logic`, which has no top-level `streamlit` calls
and is plain-import-safe.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
from streamlit.testing.v1 import AppTest

from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.experiments.recombination.molar import GorBasis, molar_split
from ui.pages import recombination_page_logic

WB = Path("tests/fixtures/workbooks/ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx")

PAGE = "ui/pages/recombination_page.py"


def test_recombination_page_boots_without_exception() -> None:
    """Standalone boot: both tabs' widgets (volumetric form, molar
    upload/manual) instantiate without raising, before any user interaction."""
    at = AppTest.from_file(PAGE).run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Recombination" in rendered
    # Widgets from both tabs exist on first boot (st.tabs runs both bodies
    # every script pass; AppTest can locate them without switching tabs).
    assert at.number_input(key="recomb.vol_v_live") is not None
    assert at.number_input(key="recomb.molar_gor") is not None


def test_volumetric_manual_flow_reproduces_known_result() -> None:
    """Case 1 (separator oil), single stage, SF=1.0, no charging-pressure
    compressibility effect (c_o=0) -- matches
    tests/test_recombination_calc.py's `single_stage_field` fixture, whose
    V_oil_sep + total_V_gas_recomb_cc == V_live == 300.0 and whose
    cylinder_mix_ratio is independently re-derived there. Confirms the
    Oil Charge Volume metric card renders the expected figure."""
    at = AppTest.from_file(PAGE).run()
    at.radio(key="recomb.vol_oil_source").set_value("separator")
    at.number_input(key="recomb.vol_v_live").set_value(300.0)
    at.number_input(key="recomb.vol_sf").set_value(1.0)
    at.number_input(key="recomb.vol_p_recomb").set_value(5014.7)
    at.number_input(key="recomb.vol_t_recomb").set_value(200.0)
    at.number_input(key="recomb.vol_z_recomb").set_value(0.82)
    at.number_input(key="recomb.vol_r_sep").set_value(850.0)
    at.number_input(key="recomb.vol_p_sep").set_value(815.0)
    at.number_input(key="recomb.vol_t_sep").set_value(145.0)
    at.number_input(key="recomb.vol_z_sep").set_value(0.855)
    at.number_input(key="recomb.vol_p_charge").set_value(5014.7)  # == p_recomb -> c_o has no effect
    at.button(key="recomb.vol_submit").click()
    at.run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    # With p_charge == p_recomb, V_oil_charge == V_oil_sep exactly (see
    # TestOilCompressibility.test_charging_pressure_affects_charging_volume);
    # V_oil_charge == 205.074... (independently computed via
    # calculate_multistage with these exact inputs) -> "205.07" on the
    # Oil Charge Volume metric card's :.2f formatting.
    assert "205.07" in rendered


def test_volumetric_manual_flow_invalid_inputs_shows_error() -> None:
    """An invalid manual entry (separator temperature unrealistically low --
    the one field with no widget min_value clamp, since real lab
    temperatures can be negative) surfaces validate.py's error via st.error
    rather than raising/crashing the page."""
    at = AppTest.from_file(PAGE).run()
    at.number_input(key="recomb.vol_t_sep").set_value(-150.0)
    at.button(key="recomb.vol_submit").click()
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    assert any("temperature" in str(e.value).lower() for e in at.error)


def test_molar_manual_flow_reproduces_golden_f_gas() -> None:
    """Brief's Step-1 test: fill the Molar manual-entry form with the SA-372
    golden inputs (tests/golden/test_molar_recombination_sa372.py's `_split`)
    and confirm the Gas Mole Fraction metric card renders "0.3706"
    (f_gas == 0.370636, golden)."""
    at = AppTest.from_file(PAGE).run()
    at.number_input(key="recomb.molar_gor").set_value(339.0)
    at.radio(key="recomb.molar_basis").set_value("stock_tank")
    at.number_input(key="recomb.molar_shrinkage").set_value(1.0)
    at.number_input(key="recomb.molar_sto_density").set_value(0.8196)
    at.number_input(key="recomb.molar_sto_mw").set_value(187.05)
    at.number_input(key="recomb.molar_gas_mw").set_value(26.10)
    at.number_input(key="recomb.molar_z_std").set_value(0.99)
    at.button(key="recomb.molar_submit").click()
    at.run()
    assert not at.exception
    assert any("0.3706" in str(m.value) for m in at.markdown)  # Gas Mole Fraction card


def test_molar_manual_flow_then_verify_actual_gor() -> None:
    """After a molar manual submission, the Actual-GOR Verification form
    becomes available; submitting it with the golden loading defaults and
    tests/golden/test_loading_sa372.py's actual charge volumes reproduces
    that test's FAIL-severity QC pill."""
    at = AppTest.from_file(PAGE).run()
    at.number_input(key="recomb.molar_gor").set_value(339.0)
    at.radio(key="recomb.molar_basis").set_value("stock_tank")
    at.number_input(key="recomb.molar_shrinkage").set_value(1.0)
    at.number_input(key="recomb.molar_sto_density").set_value(0.8196)
    at.number_input(key="recomb.molar_sto_mw").set_value(187.05)
    at.number_input(key="recomb.molar_gas_mw").set_value(26.10)
    at.number_input(key="recomb.molar_cyl_vol").set_value(1000.0)
    at.number_input(key="recomb.molar_target_oil").set_value(150.0)
    at.number_input(key="recomb.molar_oil_load_p").set_value(2000.0)
    at.number_input(key="recomb.molar_oil_load_t").set_value(75.0)
    at.number_input(key="recomb.molar_gas_load_p").set_value(5000.0)
    at.number_input(key="recomb.molar_gas_load_t").set_value(75.0)
    at.number_input(key="recomb.molar_z_gas_load").set_value(0.85)
    at.number_input(key="recomb.molar_sto_density_load").set_value(0.885)
    at.button(key="recomb.molar_submit").click()
    at.run()
    assert not at.exception

    at.number_input(key="recomb.verify_oil_cc").set_value(108.96)
    at.number_input(key="recomb.verify_gas_cc").set_value(27.47)
    at.button(key="recomb.verify_submit").click()
    at.run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "FAIL" in rendered  # tests/golden/test_loading_sa372.py: dev ~49% -> FAIL


def test_molar_verify_result_invalidated_on_resubmit_with_new_split() -> None:
    """Review-round-1 fix: a stale Actual-GOR QC pill (graded against an OLD
    split's target GOR) must not survive a NEW molar split. Submit GOR=339,
    verify (FAIL pill, message cites "target 339.0"), then resubmit the form
    with GOR=500 WITHOUT re-verifying -> the old pill's text must be gone
    from the rendered output (and, by the same session_state.pop, excluded
    from qc_results/report_download) until the user re-verifies against the
    new split."""
    at = AppTest.from_file(PAGE).run()
    at.number_input(key="recomb.molar_gor").set_value(339.0)
    at.radio(key="recomb.molar_basis").set_value("stock_tank")
    at.number_input(key="recomb.molar_shrinkage").set_value(1.0)
    at.number_input(key="recomb.molar_sto_density").set_value(0.8196)
    at.number_input(key="recomb.molar_sto_mw").set_value(187.05)
    at.number_input(key="recomb.molar_gas_mw").set_value(26.10)
    at.number_input(key="recomb.molar_cyl_vol").set_value(1000.0)
    at.number_input(key="recomb.molar_target_oil").set_value(150.0)
    at.number_input(key="recomb.molar_oil_load_p").set_value(2000.0)
    at.number_input(key="recomb.molar_oil_load_t").set_value(75.0)
    at.number_input(key="recomb.molar_gas_load_p").set_value(5000.0)
    at.number_input(key="recomb.molar_gas_load_t").set_value(75.0)
    at.number_input(key="recomb.molar_z_gas_load").set_value(0.85)
    at.number_input(key="recomb.molar_sto_density_load").set_value(0.885)
    at.button(key="recomb.molar_submit").click()
    at.run()
    assert not at.exception

    at.number_input(key="recomb.verify_oil_cc").set_value(108.96)
    at.number_input(key="recomb.verify_gas_cc").set_value(27.47)
    at.button(key="recomb.verify_submit").click()
    at.run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "target 339.0" in rendered  # sanity check: old pill present pre-resubmit
    assert "deviates" in rendered

    # Resubmit the molar form with a different GOR, WITHOUT re-verifying.
    at.number_input(key="recomb.molar_gor").set_value(500.0)
    at.button(key="recomb.molar_submit").click()
    at.run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "target 339.0" not in rendered
    assert "deviates" not in rendered


def _run_with_molar_active(active: dict) -> AppTest:
    """Drive the shared molar-results section directly by pre-seeding
    `st.session_state["recomb.molar_active"]` before `.run()`, bypassing
    `st.file_uploader` entirely (not AppTest-scriptable -- same pattern as
    `tests/ui/test_flash_page.py`'s `_run_with_active_streams`)."""
    at = AppTest.from_file(PAGE)
    at.session_state["recomb.molar_active"] = active
    at.run()
    return at


def test_molar_upload_path_renders_wellstream_table_and_report() -> None:
    """Pre-seed `recomb.molar_active` with a real LiveOil import (composition
    streams present) and confirm the wellstream table / composition QC /
    loading plan / report download all render without exception."""
    imp = recombination_page_logic.read_uploaded_liveoil_bytes(WB.read_bytes())
    sto_mw = imp.sto_stream.mw_from_mol()
    gas_mw = imp.gas_stream.mw_from_mol()
    split = molar_split(
        imp.gor, imp.gor_basis, imp.shrinkage, imp.sto_density_60f, sto_mw, gas_mw,
        z_std=imp.z_std,
    )
    active = {
        "split": split, "sto_stream": imp.sto_stream, "gas_stream": imp.gas_stream,
        "sto_density_60f": imp.sto_density_60f, "sto_mw": sto_mw, "z_std": imp.z_std,
        "loading": imp.loading, "sample": imp.sample,
    }
    at = _run_with_molar_active(active)
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "0.3706" in rendered  # same golden f_gas, via the upload/composition path
    assert len(at.dataframe) >= 1  # wellstream composition table
    # `report_download` (st.download_button) ran to completion with no
    # exception above -- AppTest has no dedicated `.download_button`
    # accessor (confirmed: not in streamlit.testing.v1.AppTest's public
    # attributes), so a clean `not at.exception` is the available proof.


def test_read_uploaded_liveoil_bytes_reproduces_workbook_golden() -> None:
    """`recombination_page_logic.read_uploaded_liveoil_bytes` is the
    plain-function extraction of the upload-handling logic. Exercised
    directly against the real fixture workbook's raw bytes -- the same shape
    `uploaded.getvalue()` would hand the page."""
    imp = recombination_page_logic.read_uploaded_liveoil_bytes(WB.read_bytes())
    assert imp.sample.sample_id == "SA-372"
    split = molar_split(
        imp.gor, imp.gor_basis, imp.shrinkage, imp.sto_density_60f,
        imp.sto_stream.mw_from_mol(), imp.gas_stream.mw_from_mol(), z_std=imp.z_std,
    )
    assert split.f_gas == pytest.approx(0.370636, abs=1e-4)


def test_molar_split_zero_shrinkage_raises_zero_division_error() -> None:
    """Documents the failure mode the Molar upload tab's `ZeroDivisionError`
    guard exists for: `GorBasis.SEPARATOR` divides by `shrinkage`, so a
    malformed-but-structurally-valid LiveOil workbook with shrinkage=0.0 in
    `Recombination!B7` would otherwise crash the page with a raw
    `ZeroDivisionError` rather than a graceful `st.error`. (The page's own
    file-uploader branch that catches this isn't AppTest-scriptable -- see
    module docstring -- so this proves the failure mode is real rather than
    exercising the page's except-branch directly.)"""
    with pytest.raises(ZeroDivisionError):
        molar_split(339.0, GorBasis.SEPARATOR, 0.0, 0.8196, 187.05, 26.10)


def test_volumetric_report_tables_builds_expected_sections() -> None:
    """Logic-level test of the pure `volumetric_report_tables` builder
    against a real `calculate_multistage` result (single_stage_field
    equivalent from tests/test_recombination_calc.py)."""
    from pvt.experiments.recombination.calc import calculate_multistage
    from pvt.experiments.recombination.models import SeparatorStage

    stage = SeparatorStage(R=850, P=815, T=145, Z=0.855, label="Separator")
    res = calculate_multistage(
        [stage], V_live=300.0, SF=1.0, P_recomb=5014.7, T_recomb=200.0, Z_recomb=0.82,
        units="field",
    )
    tables = recombination_page_logic.volumetric_report_tables(res)
    titles = [t.title for t in tables]
    assert titles == [
        "Setup", "Recombination Conditions", "Charge Volumes", "GOR Verification",
        "Stage GORs",
    ]
    stage_table = tables[-1]
    assert len(stage_table.rows) == 1
    assert stage_table.rows[0].label == "Stage 1 (Separator) GOR"


def test_wellstream_table_orders_by_kf_slot_not_alphabetically() -> None:
    """Review-round finding: the wellstream table used to sort rows
    alphabetically by Code, scattering "C10" between "C1" and "C2" and
    putting "Benzene" ahead of every numbered light end. Must instead match
    `KATZ_FIROOZABADI.codes`' slot order (the lab GC report's own layout)."""
    ws_mol = {"C10": 5.0, "C1": 50.0, "Benzene": 2.0, "C2": 43.0}
    df = recombination_page_logic.wellstream_table(ws_mol)
    codes = list(df["Code"])
    assert codes.index("C1") < codes.index("C10")
    assert codes.index("C1") < codes.index("Benzene")
    assert codes.index("C2") < codes.index("C10")
    assert codes == [code for code in KF.codes if code in ws_mol]


def test_upload_identity_prefers_file_id() -> None:
    rec = UploadedFileRec(file_id="xyz", name="x.xlsx", type="application/xlsx", data=b"hello")
    uploaded = UploadedFile(rec, None)
    assert recombination_page_logic.upload_identity(uploaded) == "xyz"


def _fake_uploaded_liveoil_workbook(file_id: str) -> UploadedFile:
    data = WB.read_bytes()
    rec = UploadedFileRec(file_id=file_id, name="liveoil.xlsx", type="application/xlsx", data=data)
    return UploadedFile(rec, None)


def test_molar_upload_reparse_gated_by_file_identity() -> None:
    """Review-round finding, same as flash_page's upload branch: the molar
    upload branch used to re-parse the workbook (and re-write
    "recomb.molar_active", and re-pop "recomb.verify_result") on EVERY
    script rerun while a file sat in the uploader, not just the run it was
    newly attached on. Pre-seeding `session_state[widget_key]` with an
    UploadedFile keeps the file "attached" across `.run()` calls exactly
    like a real unrelated rerun (`st.file_uploader` itself isn't
    AppTest-scriptable -- see module docstring)."""
    at = AppTest.from_file(PAGE)
    at.session_state["recomb.molar_uploaded_file"] = _fake_uploaded_liveoil_workbook("wb-1")
    at.run()
    assert not at.exception
    assert len(at.success) == 1  # first attach -> parsed once

    # Unrelated rerun, same file still attached -> must NOT re-parse.
    at.run()
    assert not at.exception
    assert len(at.success) == 0

    # A different file_id -> re-triggers the import.
    at.session_state["recomb.molar_uploaded_file"] = _fake_uploaded_liveoil_workbook("wb-2")
    at.run()
    assert not at.exception
    assert len(at.success) == 1


def test_molar_upload_verify_pill_survives_unrelated_rerun_with_file_still_attached() -> None:
    """The concrete symptom the file-identity gate fixes: without it, the
    upload branch's `st.session_state.pop("recomb.verify_result", None)` ran
    on every rerun the file remained attached -- including the very next,
    completely unrelated one -- wiping the Actual-GOR QC pill moments after
    the Verify form set it."""
    at = AppTest.from_file(PAGE)
    at.session_state["recomb.molar_uploaded_file"] = _fake_uploaded_liveoil_workbook("wb-1")
    at.run()
    assert not at.exception

    at.number_input(key="recomb.verify_oil_cc").set_value(108.96)
    at.number_input(key="recomb.verify_gas_cc").set_value(27.47)
    at.button(key="recomb.verify_submit").click()
    at.run()
    assert not at.exception
    assert "recomb.verify_result" in at.session_state
    rendered = "\n".join(m.value for m in at.markdown)
    assert "target 339.0" in rendered  # pill present, sanity check

    # Unrelated rerun -- file remains attached, no new upload/verify action.
    at.run()
    assert not at.exception
    assert "recomb.verify_result" in at.session_state  # pill must SURVIVE
    rendered_after = "\n".join(m.value for m in at.markdown)
    assert "target 339.0" in rendered_after


def test_molar_upload_invalid_resubmit_clears_stale_active_and_verify_result() -> None:
    """A new (different file_id) upload that fails validation must clear
    both "recomb.molar_active" and "recomb.verify_result" rather than
    leaving the previous, now-stale, results/pill rendered underneath the
    new error."""
    at = AppTest.from_file(PAGE)
    at.session_state["recomb.molar_uploaded_file"] = _fake_uploaded_liveoil_workbook("wb-1")
    at.run()
    at.number_input(key="recomb.verify_oil_cc").set_value(108.96)
    at.number_input(key="recomb.verify_gas_cc").set_value(27.47)
    at.button(key="recomb.verify_submit").click()
    at.run()
    assert "recomb.molar_active" in at.session_state
    assert "recomb.verify_result" in at.session_state

    # A different (invalid -- wrong-template) file_id must clear both.
    flash_wb = Path("tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx")
    rec = UploadedFileRec(
        file_id="wb-bad", name="wrong.xlsx", type="application/xlsx", data=flash_wb.read_bytes()
    )
    at.session_state["recomb.molar_uploaded_file"] = UploadedFile(rec, None)
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    assert "recomb.molar_active" not in at.session_state
    assert "recomb.verify_result" not in at.session_state
