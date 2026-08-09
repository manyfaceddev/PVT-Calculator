"""
tests/ui/test_flash_page.py — Tests for `ui/pages/flash_page.py` (Task 11).

`ui/` sits outside the `pvt` coverage gate; these tests prove the page boots,
that the manual-entry flow reproduces the SA-372 golden GOR through the real
engine chain (`FlashVolumetrics` -> `calculate` -> metric card), and that the
two AppTest-unscriptable widgets (`st.file_uploader`, `st.data_editor` — the
installed Streamlit version's `AppTest` exposes neither, confirmed empirically:
`streamlit.testing.v1.element_tree` has no file-uploader node type and
`AppTest` has no `.data_editor` accessor) have their underlying logic covered
directly as plain functions instead, from `ui.pages.flash_page_logic`:

- The upload path spools `UploadedFile.getvalue()` bytes to a tempfile before
  handing them to `flash_v61.read` (which takes `str | Path`, not a
  BytesIO-like) via `read_uploaded_bytes`; that helper is tested directly
  against the real fixture workbook's bytes.
- The manual composition editor's DataFrame -> CompositionStream assembly is
  `streams_from_composition_df`; tested directly against the golden SA-372
  composition fixture, cross-checked against
  `tests/golden/test_flash_recombination_sa372.py`'s wf_gas figure.

IMPORTANT: `ui.pages.flash_page` itself is a Streamlit *script* -- it runs
`st.tabs`/`st.form`/... at module top level by design, so `AppTest` can exec
it directly. It must NOT be reached via a plain `import`/`from ... import`
anywhere in this file (even just to read a constant): a bare import executes
that top-level widget code once outside any `ScriptRunContext` ("missing
ScriptRunContext" bare mode) and, empirically, leaves Streamlit's form-
nesting tracker believing a form is still open -- which then breaks the
*next* real `AppTest` run in the same pytest session with "Forms cannot be
nested in other forms", including in unrelated test files sharing the
session (confirmed against `tests/ui/test_shell.py`). Only ever reach
`flash_page.py` through `AppTest.from_file(...)` here; the plain-function
helpers it uses live in `flash_page_logic`, which has no top-level
`streamlit` calls and is plain-import-safe.
"""

from __future__ import annotations

import math
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import Workbook
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
from streamlit.testing.v1 import AppTest

from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from pvt.experiments.flash.recombine import recombine_mass
from tests.fixtures import sa372_flash as fx
from tests.unit.experiments.test_flash_validate import SA372
from ui.pages import flash_page_logic

WB = Path("tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx")

# SA-372 manual-entry numbers (== tests/unit/experiments/test_flash_validate.SA372).
SA372_MANUAL_INPUTS = {
    "flash.pump_initial_cc": 50.0, "flash.pump_final_cc": 70.8945,
    "flash.v_sto_cc": 15.7576, "flash.oil_tare_g": 100.0,
    "flash.oil_gross_g": 113.71, "flash.gasometer_initial_cc": 500.0,
    "flash.gasometer_final_cc": 1458.2037, "flash.gas_temp_c": 20.0,
    "flash.gas_abs_pressure_mbar": 1012.25, "flash.gas_gravity": 1.146,
}


def test_flash_page_manual_flow() -> None:
    """Brief's Step-1 test, verbatim: fill the manual form with SA-372
    numbers, submit, and confirm the GOR metric card renders "335.1"
    (r.gor_scf_bbl == 335.13, golden per tests/golden/test_flash_sa372.py)."""
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    assert not at.exception
    for key, val in SA372_MANUAL_INPUTS.items():
        at.number_input(key=key).set_value(val)
    at.button[0].click()
    at.run()
    assert not at.exception
    assert any("335.1" in str(m.value) for m in at.markdown)  # GOR card rendered


def test_flash_page_boots_without_exception() -> None:
    """Standalone boot: both tabs' widgets (upload + manual form) instantiate
    without raising, before any user interaction."""
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Flash Separation" in rendered
    # Manual-form widgets exist on first boot (st.tabs runs both bodies every
    # script pass; AppTest can locate them without switching tabs).
    assert at.number_input(key="flash.gas_gravity") is not None


def test_flash_page_manual_flow_invalid_inputs_shows_error() -> None:
    """An invalid manual entry (pump_final <= pump_initial) surfaces
    validate.py's error via st.error rather than raising/crashing the page."""
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    at.number_input(key="flash.pump_initial_cc").set_value(80.0)
    at.number_input(key="flash.pump_final_cc").set_value(70.0)
    at.button[0].click()
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    assert any("pump" in str(e.value).lower() for e in at.error)


def test_read_uploaded_bytes_reproduces_workbook_golden() -> None:
    """`flash_page_logic.read_uploaded_bytes` is the plain-function
    extraction of the upload-handling logic (spool `UploadedFile.getvalue()`
    bytes to a tempfile, then call `flash_v61.read`, since that importer
    takes `str | Path` and `st.file_uploader` yields a BytesIO-like, not a
    path). Exercised directly against the real fixture workbook's raw bytes
    — the same shape `uploaded.getvalue()` would hand the page."""
    data = WB.read_bytes()
    imp = flash_page_logic.read_uploaded_bytes(data)
    assert imp.sample.sample_id == "SA-372"
    from pvt.experiments.flash.calc import calculate
    r = calculate(imp.volumetrics)
    assert r.gor_scf_bbl == pytest.approx(335.13, abs=0.01)


def test_streams_from_composition_df_empty_returns_none() -> None:
    """The seeded (all-zero) composition editor DataFrame yields (None,
    None) -- "composition not entered", distinct from "entered, all zero"."""
    df = flash_page_logic.seed_composition_df()
    oil_stream, gas_stream = flash_page_logic.streams_from_composition_df(df)
    assert oil_stream is None
    assert gas_stream is None


def test_seed_composition_df_has_all_52_kf_codes() -> None:
    df = flash_page_logic.seed_composition_df()
    assert list(df["Code"]) == list(KF.codes)
    assert (df["Gas Mol%"] == 0.0).all()
    assert (df["Oil Wt%"] == 0.0).all()


def test_streams_from_composition_df_round_trips_recombination_golden() -> None:
    """Fill the composition editor's DataFrame with the golden SA-372 GC
    fixture and confirm `streams_from_composition_df` produces
    CompositionStreams that reproduce the golden recombination wf_gas from
    tests/golden/test_flash_recombination_sa372.py."""
    codes = list(KF.codes)
    df = pd.DataFrame({
        "Code": codes,
        "Gas Mol%": [fx.GAS_MOL_PCT.get(c, 0.0) for c in codes],
        "Gas Wt%": [fx.GAS_WT_PCT.get(c, 0.0) for c in codes],
        "Oil Mol%": [fx.OIL_MOL_PCT.get(c, 0.0) for c in codes],
        "Oil Wt%": [fx.OIL_WT_PCT.get(c, 0.0) for c in codes],
    })
    oil_stream, gas_stream = flash_page_logic.streams_from_composition_df(df)
    assert oil_stream is not None
    assert gas_stream is not None
    recomb = recombine_mass(13.71, 1.32095, oil_stream, gas_stream)
    assert recomb.wf_gas == pytest.approx(0.0878821, rel=1e-5)


def _run_with_active_streams(
    oil_stream: CompositionStream, gas_stream: CompositionStream
) -> AppTest:
    """Drive the page's shared-results section directly by pre-seeding
    `st.session_state["flash.active"]` before `.run()` (AppTest supports
    this), bypassing the manual form/composition editor entirely. Needed
    here because `st.data_editor` isn't AppTest-scriptable (see module
    docstring) -- this is the only way to reach the composition-QC/Hoffmann
    branch with an arbitrary, precisely-controlled composition."""
    at = AppTest.from_file("ui/pages/flash_page.py")
    at.session_state["flash.active"] = {
        "volumetrics": SA372,
        "oil_stream": oil_stream,
        "gas_stream": gas_stream,
        "sample": flash_page_logic.MANUAL_SAMPLE,
    }
    at.run()
    return at


def test_hoffman_overlap_codes_below_threshold_cases() -> None:
    """Logic-level check of `hoffman_overlap_codes` itself, isolating the
    counting logic from the page: zero overlap (disjoint streams) and
    single overlap (one shared, positive-mole-fraction code) both return
    fewer than the 2 points `hoffman_crump.check`'s least-squares fit needs
    to avoid a ZeroDivisionError."""
    gas_disjoint = CompositionStream(library=KF, mol_pct={"C1": 100.0}, wt_pct={"C1": 100.0})
    oil_disjoint = CompositionStream(library=KF, mol_pct={"C10": 100.0}, wt_pct={"C10": 100.0})
    assert flash_page_logic.hoffman_overlap_codes(gas_disjoint, oil_disjoint) == set()

    gas_one = CompositionStream(
        library=KF, mol_pct={"C1": 50.0, "C2": 50.0}, wt_pct={"C1": 50.0, "C2": 50.0}
    )
    oil_one = CompositionStream(
        library=KF, mol_pct={"C1": 50.0, "C10": 50.0}, wt_pct={"C1": 50.0, "C10": 50.0}
    )
    assert flash_page_logic.hoffman_overlap_codes(gas_one, oil_one) == {"C1"}


def test_flash_page_hoffman_skipped_for_zero_overlap_composition() -> None:
    """Gas all-C1 / oil all-C10: zero components with a positive mole
    fraction in both streams. Before the fix, this reached
    `hoffman_crump.check` unguarded and crashed the page with
    `ZeroDivisionError` (its least-squares fit divides by `n`, here 0
    points). The page's overlap precheck must catch this and degrade to a
    warning instead."""
    gas_stream = CompositionStream(library=KF, mol_pct={"C1": 100.0}, wt_pct={"C1": 100.0})
    oil_stream = CompositionStream(library=KF, mol_pct={"C10": 100.0}, wt_pct={"C10": 100.0})
    at = _run_with_active_streams(oil_stream, gas_stream)
    assert not at.exception
    assert any("fewer than 2" in str(w.value).lower() for w in at.warning)


def _seeded_df_with(overrides: dict[tuple[str, str], object]) -> pd.DataFrame:
    """seed_composition_df() with a handful of (code, column) cells
    overridden -- helper for the negative/NaN composition-editor tests
    below."""
    df = flash_page_logic.seed_composition_df()
    for (code, column), value in overrides.items():
        df.loc[df["Code"] == code, column] = value
    return df


def test_streams_from_composition_df_drops_nan_cells() -> None:
    """`st.data_editor` hands back float('nan') for a cell the user
    cleared; NaN is truthy in Python, so a naive `if value:` guard would
    silently write it into the composition dict. Must be dropped -- the
    component ends up absent, same as a genuinely blank/zero cell."""
    df = _seeded_df_with({("C1", "Gas Mol%"): math.nan, ("C1", "Gas Wt%"): 50.0})
    oil_stream, gas_stream = flash_page_logic.streams_from_composition_df(df)
    assert gas_stream is not None
    assert "C1" not in gas_stream.mol_pct
    assert gas_stream.wt_pct is not None
    assert gas_stream.wt_pct["C1"] == pytest.approx(50.0)


def test_streams_from_composition_df_rejects_negative_values() -> None:
    """A negative composition-editor cell must raise InputValidationError
    naming the offending component/column, mirroring the Excel importers'
    import-boundary guard, rather than silently being accepted."""
    df = _seeded_df_with({("C1", "Oil Mol%"): -5.0})
    with pytest.raises(InputValidationError) as exc_info:
        flash_page_logic.streams_from_composition_df(df)
    message = str(exc_info.value)
    assert "C1" in message
    assert "Oil Mol%" in message


def test_upload_identity_prefers_file_id() -> None:
    rec = UploadedFileRec(file_id="abc", name="x.xlsx", type="application/xlsx", data=b"hello")
    uploaded = UploadedFile(rec, None)
    assert flash_page_logic.upload_identity(uploaded) == "abc"


def test_upload_identity_falls_back_to_content_hash_without_file_id() -> None:
    class _FakeUpload:
        def getvalue(self) -> bytes:
            return b"same bytes"

    identity_a = flash_page_logic.upload_identity(_FakeUpload())
    identity_b = flash_page_logic.upload_identity(_FakeUpload())
    assert identity_a == identity_b  # same bytes -> same fallback hash
    assert len(identity_a) == 64  # sha256 hex digest


def _fake_uploaded_flash_workbook(file_id: str) -> UploadedFile:
    data = WB.read_bytes()
    rec = UploadedFileRec(file_id=file_id, name="flash.xlsx", type="application/xlsx", data=data)
    return UploadedFile(rec, None)


def _fake_uploaded_bad_workbook(file_id: str) -> UploadedFile:
    """A structurally-invalid workbook (no Volumetrics_Master sheet at
    all) -- `read_uploaded_bytes` raises InputValidationError on it."""
    buffer = BytesIO()
    Workbook().save(buffer)
    rec = UploadedFileRec(
        file_id=file_id, name="bad.xlsx", type="application/xlsx", data=buffer.getvalue()
    )
    return UploadedFile(rec, None)


def test_flash_upload_reparse_gated_by_file_identity() -> None:
    """Review-round finding: the upload branch used to re-parse the
    workbook (and re-write `flash.active`/render `st.success`) on EVERY
    script rerun while a file sat in the uploader, not just the run it was
    newly attached on. `st.file_uploader` isn't AppTest-scriptable, but
    pre-seeding `session_state[widget_key]` with an UploadedFile works the
    same way `.set_value()` does for other widgets -- the same file stays
    "attached" across `.run()` calls exactly like a real unrelated rerun."""
    at = AppTest.from_file("ui/pages/flash_page.py")
    at.session_state["flash.uploaded_file"] = _fake_uploaded_flash_workbook("wb-1")
    at.run()
    assert not at.exception
    assert len(at.success) == 1  # first attach -> parsed once

    # Unrelated rerun, same file still attached -> must NOT re-parse.
    at.run()
    assert not at.exception
    assert len(at.success) == 0

    # A different file_id -> re-triggers the import.
    at.session_state["flash.uploaded_file"] = _fake_uploaded_flash_workbook("wb-2")
    at.run()
    assert not at.exception
    assert len(at.success) == 1


def test_flash_upload_error_persists_across_unrelated_rerun() -> None:
    """Re-review regression: the file-identity gate (above) only ran the
    try/except -- and thus only called st.error -- on the run file_id
    actually changed. An unrelated rerun with the SAME bad file still
    attached rendered nothing at all, indistinguishable from no upload.
    The error must now be cached and re-rendered on every run while the
    identity is unchanged, and cleared once a good file replaces it."""
    at = AppTest.from_file("ui/pages/flash_page.py")
    at.session_state["flash.uploaded_file"] = _fake_uploaded_bad_workbook("bad-1")
    at.run()
    assert not at.exception
    assert len(at.error) == 1

    # Unrelated rerun, same bad file still attached -> error must STILL render.
    at.run()
    assert not at.exception
    assert len(at.error) == 1

    # Attach a good workbook (new identity) -> error gone, results render.
    at.session_state["flash.uploaded_file"] = _fake_uploaded_flash_workbook("good-1")
    at.run()
    assert not at.exception
    assert len(at.error) == 0
    assert len(at.success) == 1
    assert "flash.active" in at.session_state


def test_flash_manual_invalid_resubmit_clears_stale_results() -> None:
    """Review-round finding: an invalid resubmit must clear the previously
    rendered (valid) result rather than leaving it on screen underneath the
    new errors."""
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    for key, val in SA372_MANUAL_INPUTS.items():
        at.number_input(key=key).set_value(val)
    at.button[0].click()
    at.run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "335.1" in rendered  # valid submit -> GOR card rendered

    at.number_input(key="flash.pump_initial_cc").set_value(80.0)
    at.number_input(key="flash.pump_final_cc").set_value(70.0)
    at.button[0].click()
    at.run()
    assert not at.exception
    assert len(at.error) >= 1
    rendered_after = "\n".join(m.value for m in at.markdown)
    assert "335.1" not in rendered_after  # stale GOR card must be gone


def test_flash_page_hoffman_skipped_for_single_overlap_composition() -> None:
    """Exactly one component (C1) overlaps between the two streams -- still
    below the 2-point minimum for `hoffman_crump.check`'s least-squares fit
    (n=1 divides by zero computing x_bar/y_bar). Must degrade to a warning,
    not raise."""
    gas_stream = CompositionStream(
        library=KF, mol_pct={"C1": 50.0, "C2": 50.0}, wt_pct={"C1": 50.0, "C2": 50.0}
    )
    oil_stream = CompositionStream(
        library=KF, mol_pct={"C1": 50.0, "C10": 50.0}, wt_pct={"C1": 50.0, "C10": 50.0}
    )
    at = _run_with_active_streams(oil_stream, gas_stream)
    assert not at.exception
    assert any("fewer than 2" in str(w.value).lower() for w in at.warning)


def test_mol_only_composition_still_renders_normalization_and_hoffmann() -> None:
    """Review-round finding: a mol%-only manual composition (no wt% basis
    at all) used to lose ALL composition QC -- mw_consistency.check raised
    InputValidationError (it needs both bases) from inside a single `[...]`
    list literal, discarding every other check's already-computed result,
    including Hoffmann-Crump (which only needs mol%). Each check must now
    run independently: the mol%-only composition still renders its
    normalization pills and the Hoffmann section, with a caption explaining
    why MW consistency was skipped, and no crash."""
    gas_stream = CompositionStream(library=KF, mol_pct={"C1": 90.0, "C3": 10.0})
    oil_stream = CompositionStream(library=KF, mol_pct={"C1": 20.0, "C3": 80.0})
    at = _run_with_active_streams(oil_stream, gas_stream)
    assert not at.exception
    assert any("mw consistency" in str(cap.value).lower() for cap in at.caption)
    assert any("skipped" in str(cap.value).lower() for cap in at.caption)
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Composition QC" in rendered
    assert "Hoffmann-Crump" in rendered
    # Normalization pills (mol% is present) must still have rendered.
    assert any("composition_sum" in str(m.value) for m in at.markdown)
