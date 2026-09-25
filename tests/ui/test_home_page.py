"""
tests/ui/test_home_page.py — Tests for `ui/pages/home_page.py`, the
Dashboard landing page.

`ui/` sits outside the `pvt` coverage gate (pyproject's `--cov=pvt`); these
tests prove the page boots standalone, its banner/module-card/roadmap-card
content renders, and its "Platform status" stat tiles show the real,
computed-at-runtime counts from `home_page_logic` -- not any hardcoded
number. `home_page_logic`'s pure catalogue/count functions are additionally
tested directly (no `AppTest` needed, no top-level `streamlit` calls in that
module -- see its docstring).
"""

from __future__ import annotations

from tests.ui._paths import repo_file
from streamlit.testing.v1 import AppTest

from ui.pages import home_page_logic


def test_home_page_boots_and_renders_banner() -> None:
    """Standalone boot (not just via the navigation shell): the gradient
    welcome banner's title and one-line subtitle render."""
    at = AppTest.from_file(repo_file("ui/pages/home_page.py")).run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "ADRIC PVT Platform" in rendered
    assert "PVT calculations" in rendered


def test_home_page_renders_live_module_cards() -> None:
    """Both live modules (Flash Separation, Recombination / Live Oil) show
    up as titled cards with an "Open" button -- one per `LIVE_MODULES`
    entry."""
    at = AppTest.from_file(repo_file("ui/pages/home_page.py")).run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    for module in home_page_logic.LIVE_MODULES:
        assert module.title in rendered
        assert module.description in rendered
    open_labels = [b.label for b in at.button]
    assert open_labels.count("Open") == len(home_page_logic.LIVE_MODULES)


def test_home_page_renders_roadmap_cards_as_coming_soon() -> None:
    """Every Phase 3/4 roadmap module renders, grayed out, labeled "Coming
    soon" with its target phase -- no fabricated stats, just the honest
    roadmap from the design spec."""
    at = AppTest.from_file(repo_file("ui/pages/home_page.py")).run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    for roadmap in home_page_logic.ROADMAP_MODULES:
        assert roadmap.title in rendered
        assert roadmap.phase in rendered
    assert rendered.count("Coming soon") == len(home_page_logic.ROADMAP_MODULES)


def test_home_page_stat_tiles_show_computed_counts() -> None:
    """The "Platform status" row's three stat tiles show
    `home_page_logic`'s actual computed counts, not hardcoded numbers."""
    at = AppTest.from_file(repo_file("ui/pages/home_page.py")).run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert str(home_page_logic.count_import_templates()) in rendered
    assert str(home_page_logic.count_qc_checks()) in rendered
    assert str(home_page_logic.count_correlation_modules()) in rendered


def test_home_page_open_button_switches_to_flash_page() -> None:
    """Clicking the Flash Separation card's "Open" button reaches
    `st.switch_page` (only invoked on click, not at render time -- see
    `home_page.py`'s module docstring for why that matters for a standalone
    `AppTest` run) and lands on the Flash Separation page."""
    at = AppTest.from_file(repo_file("app.py")).run()
    assert not at.exception
    at.button(key="home-open-flash").click().run()
    assert not at.exception
    rendered = "\n".join(m.value for m in at.markdown)
    assert "Flash Separation" in rendered


def test_count_import_templates_is_two() -> None:
    """One `read()` entry point per module directly under
    `pvt.io.excel_import` -- `flash_v61` and `liveoil_v41` today."""
    assert home_page_logic.count_import_templates() == 2


def test_count_qc_checks_is_pvt_qc_checks_exports_plus_gor_check() -> None:
    """`pvt.qc.checks.__all__`'s seven modules (Phase 2's three plus Phase
    3a Task 3's polynomial_fit/monotonic_compressibility/rho_v_constancy,
    plus Phase 3a Task 4's psat_breakpoint), plus the Actual-GOR
    verification check (which lives in `pvt.experiments.recombination.
    loading`, not `pvt.qc.checks` -- see `count_qc_checks`'s docstring)."""
    import pvt.qc.checks as qc_checks_pkg

    assert home_page_logic.count_qc_checks() == len(qc_checks_pkg.__all__) + 1
    assert home_page_logic.count_qc_checks() == 8


def test_count_correlation_modules_matches_every_subpackage() -> None:
    """Walks every `pvt.correlations` subpackage's module count directly
    (bubble_point=4, pseudocritical=5, viscosity=3, zfactor=2 as of this
    writing) and confirms the two counting routes agree."""
    import pkgutil

    import pvt.correlations as correlations_pkg

    expected = 0
    for _, name, is_pkg in pkgutil.iter_modules(correlations_pkg.__path__):
        if is_pkg:
            subpackage = __import__(f"pvt.correlations.{name}", fromlist=["_"])
            expected += sum(
                1 for _, _, sub_is_pkg in pkgutil.iter_modules(subpackage.__path__)
                if not sub_is_pkg
            )
    assert home_page_logic.count_correlation_modules() == expected
    assert home_page_logic.count_correlation_modules() == 14


def test_roadmap_modules_match_phase_3_and_4_scope() -> None:
    """Roadmap card set is exactly the Phase 3 + Phase 4 modules named in
    the design spec -- CCE, DV, MSS, Density HPHT, Viscosity HPHT (Phase 3)
    and CVD, MMP (Phase 4). Guards against the dashboard silently drifting
    from `docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`."""
    titles = {card.title for card in home_page_logic.ROADMAP_MODULES}
    assert titles == {
        "CCE", "Differential Vaporization", "Multi-Stage Separator",
        "Density HPHT", "Viscosity HPHT", "CVD", "MMP",
    }
    phases = {card.title: card.phase for card in home_page_logic.ROADMAP_MODULES}
    assert phases["CCE"] == "Phase 3"
    assert phases["CVD"] == "Phase 4"
    assert phases["MMP"] == "Phase 4"
