"""
ui/pages/home_page_logic.py — Pure (no `streamlit` widget calls) helper logic
for `ui/pages/home_page.py`, the Dashboard landing page.

Why the split: same rationale as `flash_page_logic.py`/`recombination_page_
logic.py` (see either module's docstring) — page modules run widget code at
import time by design, so anything that must stay plain-`import`-safe (and
unit-testable without an `AppTest`/`ScriptRunContext`) lives here instead.

Two kinds of content live in this module:

- **Catalogues** (`LIVE_MODULES`, `ROADMAP_MODULES`): static, hand-written
  metadata for the dashboard's module grid. `ROADMAP_MODULES` is transcribed
  verbatim from the Phase 3/4 scope in
  `docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md` §2 — update
  both together if the roadmap changes.
- **Platform-status counts** (`count_import_templates`, `count_qc_checks`,
  `count_correlation_modules`): computed at call time from the real `pvt`
  package tree via `pkgutil`, never hardcoded, so the dashboard's stat tiles
  can't silently drift from what the platform actually ships.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass

import pvt.correlations as correlations_pkg
import pvt.io.excel_import as excel_import_pkg
import pvt.qc.checks as qc_checks_pkg


@dataclass(frozen=True)
class ModuleCard:
    """One live, navigable module shown on the dashboard's module grid."""

    title: str
    description: str
    badge_emoji: str
    icon: str
    page_path: str
    slug: str


@dataclass(frozen=True)
class RoadmapCard:
    """One not-yet-built module: shown grayed out with its target phase."""

    title: str
    phase: str
    description: str


LIVE_MODULES: list[ModuleCard] = [
    ModuleCard(
        title="Flash Separation",
        description="Single-stage atmospheric flash: GOR, Bo, shrinkage, API, mass recombination.",
        badge_emoji="\U0001f9ea",  # test tube
        icon=":material/science:",
        page_path="ui/pages/flash_page.py",
        slug="flash",
    ),
    ModuleCard(
        title="Recombination / Live Oil",
        description="Volumetric SF/FF or molar recombination, cylinder loading plan, GOR verification.",
        badge_emoji="⚗️",  # alembic
        icon=":material/merge_type:",
        page_path="ui/pages/recombination_page.py",
        slug="recombination",
    ),
]

# Phase 3/4 roadmap, transcribed verbatim from
# docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md §2 ("Scope").
ROADMAP_MODULES: list[RoadmapCard] = [
    RoadmapCard(
        "CCE", "Phase 3",
        "Constant composition expansion: relative volume, Y-function, compressibility.",
    ),
    RoadmapCard(
        "Differential Vaporization", "Phase 3",
        "Stage-wise depletion with Amyx/Carlson flash-basis adjustment and endpoint re-anchoring.",
    ),
    RoadmapCard(
        "Multi-Stage Separator", "Phase 3",
        "Multi-stage separator test and optimum separator selection.",
    ),
    RoadmapCard(
        "Density HPHT", "Phase 3",
        "High-pressure, high-temperature oil density measurement.",
    ),
    RoadmapCard(
        "Viscosity HPHT", "Phase 3",
        "High-pressure, high-temperature oil viscosity measurement.",
    ),
    RoadmapCard(
        "CVD", "Phase 4",
        "Constant volume depletion, Whitson-style material balance.",
    ),
    RoadmapCard(
        "MMP", "Phase 4",
        "Slim-tube minimum miscibility pressure, two-line-intersection solver.",
    ),
]


def count_import_templates() -> int:
    """Number of filled ADRIC Excel templates the platform can import today
    — one `read()` entry point per module living directly under
    `pvt.io.excel_import` (currently `flash_v61`, `liveoil_v41`). Counted
    via `pkgutil.iter_modules` rather than hardcoded so this number tracks
    the package exactly."""
    return sum(
        1 for _, _, is_pkg in pkgutil.iter_modules(excel_import_pkg.__path__) if not is_pkg
    )


def count_qc_checks() -> int:
    """Number of QC checks implemented: every module `pvt.qc.checks`
    exports (composition normalization, Hoffmann-Crump K-value consistency,
    MW consistency — see its `__all__`), plus the Actual-GOR verification
    check (`pvt.experiments.recombination.loading.verify_actual_gor`,
    `check_id="gor_actual_vs_target_pct"`). That check lives with the
    recombination experiment rather than under `pvt.qc.checks` (it needs a
    loading plan, not just a stream), but it is graded through the same
    `pvt.qc.engine.QCResult`/`ThresholdRegistry` machinery as every other
    check counted here."""
    return len(qc_checks_pkg.__all__) + 1


def count_correlation_modules() -> int:
    """Number of individual correlation modules available across every
    `pvt.correlations` subpackage (bubble_point, pseudocritical, viscosity,
    zfactor as of this writing). Walked via `pkgutil.iter_modules` two
    levels deep (subpackages, then the modules inside each) so this count
    tracks the package tree exactly rather than being transcribed by hand."""
    total = 0
    for _, name, is_pkg in pkgutil.iter_modules(correlations_pkg.__path__):
        if not is_pkg:
            continue
        subpackage = importlib.import_module(f"pvt.correlations.{name}")
        total += sum(
            1 for _, _, sub_is_pkg in pkgutil.iter_modules(subpackage.__path__)
            if not sub_is_pkg
        )
    return total
