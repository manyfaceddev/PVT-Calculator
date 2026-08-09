"""
ui/theme.py — ADRIC PVT Platform design tokens (v8) and global CSS injection.

`TOKENS` is the single source of truth for the platform's colour palette;
`inject()` turns it into one `st.markdown` CSS block, called once per page
(from `app.py`, before `st.navigation(...).run()`) so every page — and any
component in `ui.common.components` — shares the same look.
"""

from __future__ import annotations

import streamlit as st

TOKENS: dict[str, str] = {
    "navy": "#00205B",
    "blue": "#0047BB",
    "tint": "#e8f0fe",
    "hover": "#f0f5ff",
    "bg": "#f0f2f5",
    "qc_red": "#e53e3e",
    "qc_green": "#38a169",
    "qc_amber": "#dd9a0a",
}


def inject() -> None:
    """Inject the ADRIC PVT Platform (v8) stylesheet into the current page.

    Styles, in one `st.markdown` CSS block, roughly in this order:

    1. Page background, native headings (navy), primary buttons.
    2. `.pvt-page-header` / `.pvt-metric-card` — used by
       `ui.common.components` on every page.
    3. `.pvt-banner` — the Dashboard's gradient welcome banner.
    4. Module-card grid (`ui/pages/home_page.py`): live modules are
       `st.container(key="home-module-<slug>")`, matched here via a
       `[class*=...]` attribute selector on the `st-key-<key>` class
       Streamlit assigns (documented behaviour of `st.container`'s `key`
       argument — see its docstring — chosen over `data-testid` overrides
       precisely because it's a stable, public part of the API rather than
       an internal implementation detail); `.pvt-roadmap-card` is a plain
       (non-widget) grayed-out placeholder for Phase 3/4 modules.
    5. Sidebar navigation polish, scoped to `[data-testid="stSidebarNav*"]`
       — there is no public `key`-based hook for Streamlit's own nav, so
       this one block is the deliberate exception to (4)'s preference;
       tested against Streamlit 1.54.0, re-check these testids after any
       major Streamlit upgrade.
    6. QC pill dot colours (`.pvt-qc-dot-*`, consumed by
       `ui.common.components.qc_pill`).
    """
    st.markdown(
        f"""
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            background: {TOKENS["bg"]};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {TOKENS["navy"]};
        }}
        .stButton > button, .stDownloadButton > button {{
            background-color: {TOKENS["blue"]};
            color: #ffffff;
            border: 1px solid {TOKENS["blue"]};
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {TOKENS["hover"]};
            color: {TOKENS["blue"]};
            border: 1px solid {TOKENS["blue"]};
        }}
        .pvt-page-header {{
            background: {TOKENS["navy"]};
            color: #ffffff;
            padding: 1.2rem 1.4rem;
            border-radius: 12px;
            margin-bottom: 1.2rem;
        }}
        .pvt-page-header h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 1.4rem;
            letter-spacing: 0.3px;
        }}
        .pvt-page-header p {{
            margin: 0.3rem 0 0 0;
            color: {TOKENS["tint"]};
            font-size: 0.85rem;
        }}
        .pvt-metric-card {{
            background: {TOKENS["tint"]};
            border-radius: 12px;
            padding: 0.9rem 1rem;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,.06);
            transition: transform .15s ease, box-shadow .15s ease;
        }}
        .pvt-metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(0,71,187,.12);
        }}
        .pvt-metric-card .pvt-metric-value {{
            font-size: 1.55rem;
            font-weight: 700;
            color: {TOKENS["navy"]};
            line-height: 1.1;
        }}
        .pvt-metric-card .pvt-metric-unit {{
            font-size: 0.78rem;
            color: {TOKENS["blue"]};
            font-weight: 600;
        }}
        .pvt-metric-card .pvt-metric-label {{
            font-size: 0.72rem;
            color: #6a7f96;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            margin-top: 0.2rem;
        }}

        /* -----------------------------------------------------------
         * Dashboard welcome banner (ui/pages/home_page.py)
         * --------------------------------------------------------- */
        .pvt-banner {{
            background: linear-gradient(135deg, {TOKENS["navy"]} 0%, {TOKENS["blue"]} 55%, #1a6bdb 100%);
            color: #ffffff;
            border-radius: 14px;
            padding: 2rem 2.2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,.06);
        }}
        .pvt-banner h1 {{
            margin: 0;
            color: #ffffff;
            font-size: 2rem;
            letter-spacing: 0.3px;
        }}
        .pvt-banner p {{
            margin: 0.4rem 0 0 0;
            color: {TOKENS["tint"]};
            font-size: 1rem;
        }}

        /* -----------------------------------------------------------
         * Live module cards -- st.container(key="home-module-<slug>");
         * see the docstring above for why the selector is scoped this way.
         * --------------------------------------------------------- */
        [class*="st-key-home-module-"] {{
            background: linear-gradient(135deg, {TOKENS["navy"]}, {TOKENS["blue"]});
            border-radius: 14px;
            padding: 1.3rem 1.2rem 1.1rem;
            color: #ffffff;
            transition: transform .2s ease, box-shadow .2s ease;
            border: none !important;
        }}
        [class*="st-key-home-module-"]:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 14px rgba(0,71,187,.12);
        }}
        [class*="st-key-home-module-"] .pvt-module-icon {{
            font-size: 1.8rem;
            line-height: 1;
            margin-bottom: 0.4rem;
        }}
        [class*="st-key-home-module-"] .pvt-module-title {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 0.3rem;
        }}
        [class*="st-key-home-module-"] .pvt-module-desc {{
            font-size: 0.82rem;
            color: rgba(255,255,255,.85);
            line-height: 1.4;
            margin-bottom: 0.8rem;
        }}
        [class*="st-key-home-module-"] .stButton > button {{
            background: rgba(255,255,255,.15);
            color: #ffffff;
            border: 1px solid rgba(255,255,255,.6);
        }}
        [class*="st-key-home-module-"] .stButton > button:hover {{
            background: #ffffff;
            color: {TOKENS["navy"]};
            border: 1px solid #ffffff;
        }}

        /* Phase 3/4 roadmap placeholders -- plain markdown, not a widget. */
        .pvt-roadmap-card {{
            background: #f5f6f8;
            border: 1px dashed #c7cfdb;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            opacity: 0.75;
            min-height: 100%;
        }}
        .pvt-roadmap-card .pvt-roadmap-badge {{
            display: inline-block;
            background: #dfe4ec;
            color: #5a6b82;
            font-size: 0.62rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.4px;
            padding: 0.15rem 0.5rem;
            border-radius: 999px;
            margin-bottom: 0.4rem;
        }}
        .pvt-roadmap-card .pvt-roadmap-title {{
            color: {TOKENS["navy"]};
            font-weight: 700;
            font-size: 0.9rem;
            margin-bottom: 0.2rem;
        }}
        .pvt-roadmap-card .pvt-roadmap-desc {{
            color: #7c8aa0;
            font-size: 0.76rem;
            line-height: 1.4;
            margin: 0;
        }}

        /* -----------------------------------------------------------
         * Sidebar navigation polish -- data-testid selectors, tested
         * against Streamlit 1.54.0. `stSidebarNavLink` carries
         * `aria-current="page"` on the active entry (standard React
         * Router behaviour), used here instead of a Streamlit-internal
         * "active"/"selected" class, which does not exist as a stable
         * hook in this version.
         * --------------------------------------------------------- */
        [data-testid="stSidebarNavLink"] {{
            border-radius: 8px;
            transition: background .15s ease, color .15s ease;
        }}
        [data-testid="stSidebarNavLink"]:hover {{
            background: {TOKENS["hover"]};
        }}
        [data-testid="stSidebarNavLink"][aria-current="page"] {{
            background: {TOKENS["tint"]};
            font-weight: 600;
        }}

        /* -----------------------------------------------------------
         * QC pill dot colours -- consumed by ui.common.components.qc_pill.
         * --------------------------------------------------------- */
        .pvt-qc-dot {{
            height: 10px;
            width: 10px;
            min-width: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        .pvt-qc-dot-pass {{ background: {TOKENS["qc_green"]}; }}
        .pvt-qc-dot-review {{ background: {TOKENS["qc_amber"]}; }}
        .pvt-qc-dot-fail {{ background: {TOKENS["qc_red"]}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )
