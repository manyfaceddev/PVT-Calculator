"""
ui.pages — Streamlit page modules for the ADRIC PVT Platform navigation shell.

Each module is registered as an `st.Page` in `app.py` and is independently
boot-able (each has a `streamlit.testing.v1.AppTest.from_file(...)` smoke
test in `tests/ui/`).

Pages
-----
ui.pages.flash_page            Flash Separation (SSF) — Task 11
ui.pages.recombination_page    Recombination / Live Oil — Task 12

Task 10 lands both modules as minimal placeholders (`page_header` only) so
the navigation shell boots; Tasks 11-12 build out their real content.
"""
