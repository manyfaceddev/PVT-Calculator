"""
ui/pages/flash_page_logic.py — Pure (no `streamlit` widget calls) helper
logic for `ui/pages/flash_page.py` (Task 11), split out on purpose so it is
plain-`import`-safe.

Why the split: `flash_page.py` is a Streamlit *script* — like every module
under `ui/pages/`, it runs page-rendering code (`st.tabs`, `st.form`, ...) at
module top level, by design, so `st.Page`/`AppTest` can execute it directly.
That's fine when it's *exec*'d by `AppTest`/the navigation shell (each run
gets a fresh, properly isolated `ScriptRunContext`) but not when it's reached
via a plain `from ui.pages import flash_page` — a normal Python import runs
that same top-level code exactly once, outside any script context ("missing
ScriptRunContext" bare mode), and it is cached in `sys.modules` from then on.
Empirically, that bare-mode execution of `st.form(...)` leaves Streamlit's
form-nesting tracker thinking a form is still open, which then makes the
*next* real `AppTest` run in the same process fail immediately with
"Forms cannot be nested in other forms" — including in unrelated test files
sharing the pytest session (confirmed: importing `ui.pages.flash_page` at
test-module level broke `tests/ui/test_shell.py`'s independent AppTest
cases too). Keeping the composition/upload plumbing here, with no top-level
`streamlit` calls, means `tests/ui/test_flash_page.py` can import and test
these functions directly without ever triggering that bare-mode execution.
"""

from __future__ import annotations

import hashlib
import math
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from pvt.core.components import KATZ_FIROOZABADI as KF
from pvt.core.composition import CompositionStream
from pvt.core.exceptions import InputValidationError
from pvt.core.sample import Sample
from pvt.io.excel_import import flash_v61

# ---------------------------------------------------------------------------
# Manual-form field metadata: (field, label, unit, default).
#
# `pvt.experiments.flash.validate` only carries explicit numeric bands for
# gas_temp_c / gas_abs_pressure_mbar / gas_gravity (Rules 5-7); every other
# field there is a *relational* rule (final > initial, gross > tare, v_sto >
# 0, factor > 0) with no standalone upper bound. `FIELD_RANGES` below uses
# those three explicit bands verbatim and falls back to a physically
# sensible non-negative (or > 0, for the strictly-positive fields) floor
# with no upper bound elsewhere.
# ---------------------------------------------------------------------------
FIELD_META: list[tuple[str, str, str, float]] = [
    ("pump_initial_cc", "Initial pump reading", "cc", 0.0),
    ("pump_final_cc", "Final pump reading", "cc", 0.0),
    ("v_sto_cc", "Stock tank oil volume (V_sto)", "cc", 1.0),
    ("oil_tare_g", "Oil tare weight", "g", 0.0),
    ("oil_gross_g", "Final oil + tare weight", "g", 0.0),
    ("gasometer_initial_cc", "Initial gasometer reading", "cc", 0.0),
    ("gasometer_final_cc", "Final gasometer reading", "cc", 0.0),
    ("gas_temp_c", "Gas temperature", "C", 20.0),
    ("gas_abs_pressure_mbar", "Measured gas abs. pressure", "mbar", 1013.25),
    ("gas_gravity", "Gas gravity (Air=1)", "", 1.0),
    ("pump_constant", "Pump constant", "", 1.0),
    ("vcf", "Volume correction factor (VCF)", "", 1.0),
    ("gasometer_factor", "Gasometer factor", "", 1.0),
]

FIELD_RANGES: dict[str, tuple[float, float | None]] = {
    "pump_initial_cc": (0.0, None),
    "pump_final_cc": (0.0, None),
    "v_sto_cc": (0.01, None),
    "oil_tare_g": (0.0, None),
    "oil_gross_g": (0.0, None),
    "gasometer_initial_cc": (0.0, None),
    "gasometer_final_cc": (0.0, None),
    # validate.py Rules 5-7 are strictly EXCLUSIVE bands (-10 < t < 60, etc.);
    # a plain min_value/max_value on st.number_input is inclusive, so typing
    # exactly the boundary would pass the widget but fail validate() one
    # click later. Tightened by 0.01 (a value no realistic lab reading needs)
    # so the widget itself can't submit the excluded boundary.
    "gas_temp_c": (-9.99, 59.99),  # validate.py Rule 7: -10 < t < 60
    "gas_abs_pressure_mbar": (500.01, 1499.99),  # validate.py Rule 6: 500 < p < 1500
    "gas_gravity": (0.51, 2.99),  # validate.py Rule 5: 0.5 < g < 3.0
    "pump_constant": (0.01, None),
    "vcf": (0.01, None),
    "gasometer_factor": (0.01, None),
}

_COMPOSITION_COLUMNS = ["Code", "Gas Mol%", "Gas Wt%", "Oil Mol%", "Oil Wt%"]

MANUAL_SAMPLE = Sample(
    sample_id="Manual Entry", well="", field_name="", reservoir="",
    depth_ft_md=None, fluid_type="", cylinder="",
)


def seed_composition_df() -> pd.DataFrame:
    """Seed the manual-entry composition editor: one row per Katz-Firoozabadi
    component code, zeroed mol%/wt% columns for both streams."""
    return pd.DataFrame(
        {
            "Code": list(KF.codes),
            "Gas Mol%": [0.0] * len(KF.codes),
            "Gas Wt%": [0.0] * len(KF.codes),
            "Oil Mol%": [0.0] * len(KF.codes),
            "Oil Wt%": [0.0] * len(KF.codes),
        }
    )


def _clean_composition_cell(value: Any, label: str, code: str, errors: list[str]) -> float | None:
    """Normalize one composition-editor cell to a `float`, or `None` when it
    should be treated as absent.

    `st.data_editor` hands back `float('nan')` for a cell the user cleared
    (NaN is truthy in Python, so a naive `if value:` guard would silently
    write it into the composition dict as-is, corrupting every downstream
    sum). Dropped here, same treatment as a blank Excel-import cell (final
    review carry-forward, mirroring `flash_v61._read_compositions`'s
    None-guard). A negative value is collected into `errors` (mirroring that
    same importer's negative-composition guard) rather than silently
    accepted -- `CompositionStream` itself does not validate value sign.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    value = float(value)
    if value < 0:
        errors.append(f"Composition editor ({code}): negative {label} value {value}")
        return None
    return value


def streams_from_composition_df(
    df: pd.DataFrame,
) -> tuple[CompositionStream | None, CompositionStream | None]:
    """Build (oil_stream, gas_stream) from the composition editor's
    DataFrame, mirroring `flash_v61._read_compositions`'s convention: only
    non-zero cells become dict entries. A stream is `None` when none of its
    two columns (mol%/wt%) carry any non-zero entry -- "not entered" rather
    than "entered as an all-zero (invalid) composition".

    Raises:
        InputValidationError: any cell in the four composition columns is
            negative -- lists every offending cell (mirroring the Excel
            importers' import-boundary guard).
    """
    gas_mol: dict[str, float] = {}
    gas_wt: dict[str, float] = {}
    oil_mol: dict[str, float] = {}
    oil_wt: dict[str, float] = {}
    errors: list[str] = []
    # dict records (not itertuples): "Gas Mol%" etc. aren't valid Python
    # identifiers, so itertuples silently renames them to positional `_1`,
    # `_2`, ... -- fragile to get right and to keep right under edits.
    for row in df[_COMPOSITION_COLUMNS].to_dict("records"):
        code = str(row["Code"])
        for label, target in (
            ("Gas Mol%", gas_mol), ("Gas Wt%", gas_wt),
            ("Oil Mol%", oil_mol), ("Oil Wt%", oil_wt),
        ):
            value = _clean_composition_cell(row[label], label, code, errors)
            if value:
                target[code] = value

    if errors:
        raise InputValidationError(errors)

    oil_stream = (
        CompositionStream(library=KF, mol_pct=oil_mol, wt_pct=oil_wt)
        if (oil_mol or oil_wt)
        else None
    )
    gas_stream = (
        CompositionStream(library=KF, mol_pct=gas_mol, wt_pct=gas_wt)
        if (gas_mol or gas_wt)
        else None
    )
    return oil_stream, gas_stream


def hoffman_overlap_codes(gas_stream: CompositionStream, oil_stream: CompositionStream) -> set[str]:
    """Component codes with a positive mole fraction in BOTH streams'
    normalized mol% bases -- the same "qualifying component" test
    `pvt.qc.checks.hoffman_crump.check` applies internally (one crossplot
    point per such code).

    Exposed here so the page can precheck this *before* calling into the
    engine: with fewer than two qualifying codes, `hoffman_crump.check`'s
    least-squares fit divides by `n` (0 or 1 points) or, degenerately, by an
    `ss_xx` of zero (e.g. two points that happen to share an F-factor) --
    both `ZeroDivisionError`, not the `InputValidationError` the rest of
    this page's QC calls catch. A manual-entry composition with little or no
    overlap between the two streams (e.g. gas all `C1`, oil all `C10`) is a
    realistic way to reach this, not just a contrived one.

    Callers must only pass streams that already carry a mol% basis (i.e.
    ones that survived a prior `mw_consistency.check` or equivalent) --
    `normalized_mol()` itself raises `InputValidationError` on a stream with
    no mol% basis at all, which this function does not catch.
    """
    gas_mol = gas_stream.normalized_mol()
    oil_mol = oil_stream.normalized_mol()
    return {code for code, y in gas_mol.items() if y > 0 and oil_mol.get(code, 0.0) > 0}


def upload_identity(uploaded_file: Any) -> str:
    """Stable identity for an `st.file_uploader` return value, used to gate
    the (re-)parse + session-state write to only run when the attached file
    actually changes.

    `st.file_uploader` returns a non-`None` `UploadedFile` on EVERY script
    rerun while a file remains attached to the widget -- not just the run it
    was newly attached on -- so a naive `if uploaded is not None:` guard
    re-parses the workbook (and re-writes `st.session_state["flash.active"]`)
    on every unrelated widget interaction elsewhere on the page. Prefers
    Streamlit's own `file_id` (stable per attached file; changes when the
    user detaches/reattaches or picks a different file); falls back to a
    content hash for any uploaded-file-shaped object that doesn't carry one.
    """
    file_id = getattr(uploaded_file, "file_id", None)
    if file_id:
        return str(file_id)
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()


def read_uploaded_bytes(data: bytes) -> flash_v61.FlashImport:
    """Parse a filled ADRIC Flash v6.1 workbook from raw bytes.

    `st.file_uploader` yields an `UploadedFile` (a BytesIO-like); `flash_v61.
    read` takes `str | Path` because it hands the path straight to
    `openpyxl.load_workbook`. Rather than widen that importer's contract for
    this one UI call site, spool the upload to a `NamedTemporaryFile` and
    read from its path -- simplest, and keeps the importer's file-shaped
    boundary intact for its other (path-based) callers.
    """
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        return flash_v61.read(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
