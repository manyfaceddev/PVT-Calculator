"""
app.py — PVT Calculator entry point.

Thin launcher: configures the Streamlit page, injects the stylesheet,
and delegates all rendering to the ui.recombination page module.

Run locally:
    streamlit run app.py
    python app.py          (launches Streamlit automatically)

Deploy:
    Push to Streamlit Community Cloud (main branch).
"""

import streamlit as st

st.set_page_config(
    page_title="PVT Recombination",
    page_icon="🛢️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from ui.styles import inject           # noqa: E402  (must come after set_page_config)
from ui.recombination import render    # noqa: E402

inject()
render()


# ---------------------------------------------------------------------------
# Local-run shortcut: `python app.py` launches Streamlit automatically
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import subprocess
    import sys
    import os

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)],
        check=False,
    )
