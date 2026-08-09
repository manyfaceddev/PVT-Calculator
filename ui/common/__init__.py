"""
ui.common — Streamlit components shared across every ADRIC PVT Platform page.

Re-exports `ui.common.components` so pages can do
`from ui.common import page_header, metric_card, ...`.
"""

from ui.common.components import (
    calc_steps,
    metric_card,
    page_header,
    qc_panel,
    qc_pill,
    report_download,
)

__all__ = [
    "calc_steps",
    "metric_card",
    "page_header",
    "qc_panel",
    "qc_pill",
    "report_download",
]
