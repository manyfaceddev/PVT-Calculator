"""
ui/pages/home_page.py — Dashboard landing page (v8 design upgrade).

The first page in `app.py`'s `st.navigation` — a welcome banner, a grid of
the modules the platform actually ships (Flash Separation, Recombination /
Live Oil, each a real `st.button` + `st.switch_page` card), the Phase 3/4
roadmap grayed out beside them, and a "Platform status" row of stat tiles
computed from the real `pvt` package tree (see `home_page_logic.py`).

Live module cards deliberately use `st.button(...) + st.switch_page(...)`
rather than `st.page_link(...)`: `st.page_link` resolves its target against
`st.navigation`'s registered pages *at render time*, unconditionally — that
crashes (`KeyError`/`StreamlitPageNotFoundError`) when this module is run
standalone (`AppTest.from_file("ui/pages/home_page.py").run()`, the same
pattern `tests/ui/test_shell.py` uses for the other two pages), because no
navigation context is registered for a single-page run. `st.switch_page`
only resolves its target when the button is actually clicked, so a
render-only test never reaches that check.
"""

from __future__ import annotations

import streamlit as st

from ui.common import metric_card
from ui.pages.home_page_logic import (
    LIVE_MODULES,
    ROADMAP_MODULES,
    count_correlation_modules,
    count_import_templates,
    count_qc_checks,
)

st.markdown(
    '<div class="pvt-banner">'
    "<h1>ADRIC PVT Platform</h1>"
    "<p>Pure-engine PVT calculations, QC, and reporting for the lab's full scope of work.</p>"
    "</div>",
    unsafe_allow_html=True,
)

st.subheader("Modules")
module_cols = st.columns(len(LIVE_MODULES))
for col, module in zip(module_cols, LIVE_MODULES):
    with col:
        with st.container(key=f"home-module-{module.slug}"):
            st.markdown(
                f'<div class="pvt-module-icon">{module.badge_emoji}</div>'
                f'<div class="pvt-module-title">{module.title}</div>'
                f'<div class="pvt-module-desc">{module.description}</div>',
                unsafe_allow_html=True,
            )
            if st.button(
                "Open", key=f"home-open-{module.slug}", icon=module.icon, width="stretch"
            ):
                st.switch_page(module.page_path)

st.caption("More modules are on the roadmap — grayed out below until they ship.")
roadmap_cols = st.columns(4)
for i, roadmap in enumerate(ROADMAP_MODULES):
    with roadmap_cols[i % 4]:
        st.markdown(
            '<div class="pvt-roadmap-card">'
            f'<span class="pvt-roadmap-badge">{roadmap.phase} · Coming soon</span>'
            f'<div class="pvt-roadmap-title">{roadmap.title}</div>'
            f'<div class="pvt-roadmap-desc">{roadmap.description}</div>'
            "</div>",
            unsafe_allow_html=True,
        )

st.subheader("Platform status")
stat_cols = st.columns(3)
with stat_cols[0]:
    metric_card("Import Templates Supported", str(count_import_templates()), "")
with stat_cols[1]:
    metric_card("QC Checks Implemented", str(count_qc_checks()), "")
with stat_cols[2]:
    metric_card("Correlations Available", str(count_correlation_modules()), "")
