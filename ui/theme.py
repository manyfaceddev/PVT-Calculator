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

    Styles, in one `st.markdown` CSS block: the app background, native
    headings (navy), primary buttons (blue, tinted hover), and the
    `.pvt-page-header` / `.pvt-metric-card` classes used by
    `ui.common.components`.
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
            border-radius: 10px;
            padding: 0.9rem 1rem;
            text-align: center;
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
        </style>
        """,
        unsafe_allow_html=True,
    )
