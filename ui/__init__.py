"""
ui — Streamlit UI layer for the PVT Calculator (ADRIC PVT Platform).

`app.py` is a thin `st.navigation` shell over the page modules in
`ui.pages`; shared look-and-feel and widgets live in `ui.theme` and
`ui.common`.

Modules
-------
ui.theme            Design tokens (v8 palette) + `inject()` CSS
ui.common           Shared components (page_header, metric_card, qc_pill, ...)
ui.pages            One module per `st.Page` registered in `app.py`
"""
