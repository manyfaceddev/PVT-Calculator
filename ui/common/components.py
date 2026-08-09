"""
ui/common/components.py — Reusable Streamlit components shared across every
ADRIC PVT Platform page (Task 10; consumed by the flash/recombination pages
built in Tasks 11-12).

Each function renders directly (via `st.markdown` / `st.expander` /
`st.download_button`, ...) rather than returning an HTML string — pages call
these top to bottom to build their layout. Styling relies on the CSS classes
`ui.theme.inject()` defines (`.pvt-page-header`, `.pvt-metric-card`); colours
otherwise come straight from `ui.theme.TOKENS` so severity/brand colours stay
in one place.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import streamlit as st

from pvt.core.sample import Sample
from pvt.qc.engine import QCResult
from pvt.reporting.excel_export import write_report
from pvt.reporting.tables import ReportTable
from ui.theme import TOKENS

_QC_DOT_CLASSES: dict[str, str] = {
    "PASS": "pvt-qc-dot-pass",
    "REVIEW": "pvt-qc-dot-review",
    "FAIL": "pvt-qc-dot-fail",
}

# ui/common/components.py -> ui/common -> ui -> repo root. Anchored on this
# file's own path (not the current working directory) so figure_expander
# resolves correctly no matter where `streamlit run` is launched from.
_REPO_ROOT = Path(__file__).resolve().parents[2]

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def page_header(title: str, subtitle: str) -> None:
    """Render the navy page-header banner every page opens with."""
    st.markdown(
        f'<div class="pvt-page-header"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, unit: str = "") -> None:
    """Render a single tinted metric card (big value, unit, label)."""
    st.markdown(
        f'<div class="pvt-metric-card">'
        f'<div class="pvt-metric-value">{value}</div>'
        f'<div class="pvt-metric-unit">{unit}</div>'
        f'<div class="pvt-metric-label">{label}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def qc_pill(result: QCResult) -> None:
    """Render one `QCResult` as a coloured-dot pill: check id + message.

    The dot's colour comes from the `.pvt-qc-dot-*` classes `ui.theme.
    inject()` defines (one per `Severity`, each set from `TOKENS["qc_*"]`)
    rather than an inline `background:` style, so QC severity colour is
    defined in exactly one place (the stylesheet), not re-derived per call.
    """
    dot_class = _QC_DOT_CLASSES[result.severity.value]
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.5rem;padding:0.3rem 0;">'
        f'<span class="pvt-qc-dot {dot_class}"></span>'
        f'<span style="font-weight:600;">{result.check_id}</span>'
        f'<span style="color:#6a7f96;font-size:0.85rem;">{result.message}</span>'
        f"</div>",
        unsafe_allow_html=True,
    )


def qc_panel(results: list[QCResult]) -> None:
    """Render a stack of `qc_pill`s, one per `QCResult` in `results`."""
    for result in results:
        qc_pill(result)


def figure_expander(title: str, figure_relpath: str, explanation: str) -> None:
    """Render a collapsed `st.expander` holding one manual figure plus a
    short plain-language explanation of how it maps to the form above/
    beside it.

    Args:
        title: Expander title, e.g. "How the bench test maps to these
            fields".
        figure_relpath: Path to the figure, relative to the repo root (e.g.
            "docs/manual/figures/flash-apparatus.png") -- resolved against
            `_REPO_ROOT`, not the current working directory, so this is
            robust to where `streamlit run` is launched from.
        explanation: Plain-language text shown under the figure.

    A missing/renamed figure degrades to a caption instead of crashing the
    page: `st.image` raises on a nonexistent path, so the file's existence
    is checked first (`Path.exists()`), same guard rationale as every other
    "degrade, don't crash" boundary in `ui/pages/*_logic.py`.
    """
    with st.expander(title, expanded=False):
        figure_path = _REPO_ROOT / figure_relpath
        if figure_path.exists():
            st.image(str(figure_path), width="stretch")
        else:
            st.caption(f"Figure not available: {figure_relpath}")
        st.markdown(explanation)


def calc_steps(steps: list[tuple[str, str]]) -> None:
    """Render `(label, formula_html)` pairs as rows inside a collapsed
    "Calculation Steps" expander."""
    with st.expander("Calculation Steps", expanded=False):
        for label, formula in steps:
            st.markdown(
                f'<div style="background:#f4f8fc;border:1px solid #d0dcea;'
                f'border-radius:8px;padding:0.75rem 1rem;margin-bottom:0.55rem;'
                f'font-family:\'Courier New\',monospace;font-size:0.82rem;'
                f'color:#2c3e50;line-height:1.5;">'
                f'<div style="font-family:\'Segoe UI\',Arial,sans-serif;'
                f'font-size:0.75rem;font-weight:700;color:{TOKENS["blue"]};'
                f'margin-bottom:0.25rem;">{label}</div>'
                f"{formula}"
                f"</div>",
                unsafe_allow_html=True,
            )


def _derive_title(filename: str) -> str:
    """Fallback report title derived from `filename`: strip any directory
    prefix and extension, turn underscores into spaces, and Title-Case
    (e.g. "flash_separation_report.xlsx" -> "Flash Separation Report")."""
    stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0].replace("_", " ").strip()
    return stem.title() if stem else filename


def _prefixed_filename(filename: str, sample_id: str) -> str:
    """Embed `sample_id` into the front of `filename` (whitespace collapsed
    to underscores) so reports downloaded for different samples don't share
    a download name and silently clobber each other in a browser's
    downloads folder."""
    prefix = "_".join(sample_id.split()) or "sample"
    return f"{prefix}_{filename}"


def report_download(
    tables: list[ReportTable], sample: Sample, filename: str, *, title: str | None = None
) -> None:
    """Build an ADRIC-styled `.xlsx` report from `tables`/`sample` entirely
    in memory (`BytesIO`, via `pvt.reporting.excel_export.write_report`) and
    offer it as an `st.download_button`.

    Args:
        tables: Report sections to write (see `write_report`).
        sample: Sample metadata; `sample.sample_id` is also embedded into
            the download filename (see `_prefixed_filename`).
        filename: Base filename (e.g. "flash_separation_report.xlsx").
        title: Report title shown in the workbook's navy header banner.
            Defaults to `filename` Title-Cased (see `_derive_title`) when
            not given.
    """
    report_title = title if title is not None else _derive_title(filename)
    buffer = BytesIO()
    write_report(buffer, tables, title=report_title, sample=sample)
    buffer.seek(0)
    st.download_button(
        "Download Excel Report",
        data=buffer,
        file_name=_prefixed_filename(filename, sample.sample_id),
        mime=_XLSX_MIME,
    )
