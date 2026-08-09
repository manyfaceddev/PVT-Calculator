# Abstract

This manual documents the ADRIC PVT Lab Platform: an ADNOC-internal
laboratory system for reservoir-fluid property calculations, built around a
pure-Python calculation engine (`pvt/`) with a Streamlit front-end
(`app.py`, `ui/`) and a parity command-line interface (`cli.py`). The
lab's validated Excel workbooks are treated throughout as specifications
and golden test fixtures, never as the calculator itself; every place the
engine's output deliberately departs from a source workbook is recorded,
with cell-level proof, in a deviations ledger.

**Version covered by this manual:** `v0.2.0-flash-recomb`

As of this version, the platform implements Phase 0 (repository
restructure, core data model, units and constants, a 100% branch-coverage
test gate on `pvt/`), Phase 1 (a 13-correlation library covering gas
Z-factor, pseudo-critical properties, bubble point, and viscosity), and
Phase 2 (Flash Separation and Live Oil Preparation/Recombination,
end to end: engine, QC checks, Excel import of both ADRIC lab templates,
a two-page Streamlit UI, ADRIC-styled report export, and CLI parity).

The chapters that follow walk through the platform's purpose and
architecture, an at-the-bench application guide to the Streamlit app, the
core data model, the correlations library, the flash and recombination
workflow, Excel import, the QC engine, reporting, and the testing strategy
that backs all of it. The closing chapter documents the
deviations-ledger discipline in full — every current entry, the open
rulings awaiting a decision from the PVT domain owner, and the Phase 3-5
roadmap read against what the full formula-level dissection of the ADRIC
workbook set already tells us about the modules still to come.

Design reference: `docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`.
