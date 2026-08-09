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

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
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
