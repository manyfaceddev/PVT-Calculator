"""
ui/pages/flash_page.py — Flash Separation (SSF) page.

Task 10 lands this as a minimal boot-able placeholder (`page_header` only)
so the `st.navigation` shell in `app.py` boots. Task 11 builds out the real
page: file upload / manual-entry flash inputs, metric cards, QC pills, the
Hoffmann plot, a calc-steps expander, and the Excel report download.
"""

from __future__ import annotations

from ui.common import page_header

page_header(
    "Flash Separation (SSF)",
    "Module 2 — Single-Stage Flash Separation & Recombination",
)
