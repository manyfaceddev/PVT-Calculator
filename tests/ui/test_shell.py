"""
tests/ui/test_shell.py — Smoke tests for the Streamlit app shell (Task 10).

`ui/` sits outside the `pvt` coverage gate (pyproject's `--cov=pvt`); these
tests only need to prove the shell boots cleanly under Streamlit's
`AppTest` harness and that the two navigation pages render something, not
exercise every code path.

What `AppTest` actually exercises here: empirically, `AppTest.from_file
("app.py").run()` *does* drive `st.navigation` in the installed Streamlit
version (1.54.0) — it runs `app.py` top to bottom (picking up
`st.set_page_config` + `theme.inject()`) and then renders the default
(first) `st.Page`'s script body inline, despite `AppTest`'s own docstring
disclaiming multipage/`st.navigation` support ("not yet compatible").
`test_shell_renders_default_page_header` below pins that behaviour down.
As a belt-and-braces fallback per the brief, each placeholder page module
is also exercised standalone via its own `AppTest.from_file(...).run()`.
"""

from __future__ import annotations

from streamlit.testing.v1 import AppTest

from ui.theme import TOKENS


def test_shell_boots_without_exception() -> None:
    """Brief's Step-1 smoke test, verbatim: the shell boots without raising."""
    at = AppTest.from_file("app.py").run()
    assert not at.exception


def test_shell_renders_default_page_header() -> None:
    """`app.py` drives `st.navigation`; the default (first) page is now the
    Dashboard (`ui/pages/home_page.py`) -- its `.pvt-banner` welcome banner
    shows up in the rendered markdown tree. (Standalone-boot and richer
    content checks for the Dashboard itself live in
    `tests/ui/test_home_page.py`.)"""
    at = AppTest.from_file("app.py").run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "ADRIC PVT Platform" in rendered


def test_flash_page_boots_standalone() -> None:
    """`ui/pages/flash_page.py` is independently boot-able (not just via
    the navigation shell) and renders its page_header title."""
    at = AppTest.from_file("ui/pages/flash_page.py").run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Flash Separation" in rendered


def test_recombination_page_boots_standalone() -> None:
    """`ui/pages/recombination_page.py` is independently boot-able and
    renders its page_header title."""
    at = AppTest.from_file("ui/pages/recombination_page.py").run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Recombination" in rendered


def test_tokens_match_v8_design_spec() -> None:
    """`ui.theme.TOKENS` carries exactly the v8 palette named in the brief."""
    assert TOKENS == {
        "navy": "#00205B",
        "blue": "#0047BB",
        "tint": "#e8f0fe",
        "hover": "#f0f5ff",
        "bg": "#f0f2f5",
        "qc_red": "#e53e3e",
        "qc_green": "#38a169",
        "qc_amber": "#dd9a0a",
    }
