"""
ui/pages/recombination_page.py — Recombination / Live Oil page.

Task 10 lands this as a minimal boot-able placeholder (`page_header` only)
so the `st.navigation` shell in `app.py` boots. Task 12 rebuilds the real
page against the new molar-split/loading-plan engine (superseding the
retired `ui/recombination.py` module).
"""

from __future__ import annotations

from ui.common import page_header

page_header(
    "Recombination / Live Oil",
    "Module 1 — Separator Fluid Recombination & PVT Cell Charging",
)
