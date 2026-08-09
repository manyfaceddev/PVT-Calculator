"""
app.py — ADRIC PVT Platform entry point.

Thin `st.navigation` shell: configures the Streamlit page, injects the v8
theme, and delegates all rendering to the page modules under `ui/pages/`.

Run locally:
    streamlit run app.py
    python app.py          (launches Streamlit automatically)

Deploy:
    Push to Streamlit Community Cloud (main branch).
"""

import streamlit as st

st.set_page_config(page_title="ADRIC PVT Platform", layout="wide")

from ui import theme  # noqa: E402  (must come after set_page_config)

theme.inject()

pages = [
    st.Page("ui/pages/home_page.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page(
        "ui/pages/flash_page.py", title="Flash Separation (SSF)", icon=":material/science:"
    ),
    st.Page(
        "ui/pages/recombination_page.py", title="Recombination / Live Oil",
        icon=":material/merge_type:",
    ),
]
nav = st.navigation(pages)
nav.run()


# ---------------------------------------------------------------------------
# Local-run shortcut: `python app.py` launches Streamlit automatically.
# The runtime guard is essential: under `streamlit run`, this script ALSO
# executes with __name__ == "__main__", and an unguarded spawn re-launches
# Streamlit from every script run (a fork bomb opening endless browser tabs).
# `runtime.exists()` is True only inside a running Streamlit server, so the
# spawn fires solely on a bare `python app.py` invocation.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from streamlit import runtime

    if not runtime.exists():
        import os
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)],
            check=False,
        )
