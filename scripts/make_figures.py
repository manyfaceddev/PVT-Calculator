#!/usr/bin/env python3
"""
scripts/make_figures.py — Generates the four schematic figures for the
ADRIC PVT Lab Platform software manual.

Run:
    python scripts/make_figures.py

Regenerates, at 300 dpi, into docs/manual/figures/:
    flash-apparatus.png        Atmospheric flash, water-pump method
    recombination-scheme.png   Separator recombination, Case 1 vs Case 2
    app-workflow.png           App data-flow (input -> validation -> ... -> report)
    screen-map.png             Sidebar navigation + per-page section map

Visual language (shared across all four figures):
    - Boxes:      ADRIC navy (#00205B) fill, white text, rounded corners.
    - Arrows:     ADRIC blue (#0047BB).
    - Annotations/labels/notes: dark gray (#333333).

The flash-apparatus and recombination-scheme figures are drawn from the
engine's actual physics/nomenclature (see pvt/experiments/flash/calc.py,
pvt/experiments/flash/models.py and pvt/experiments/recombination/calc.py's
docstring) so the labeled quantities match the variable names used in the
Streamlit app's calc-steps panels (e.g. V_press, m_oil, V_sto, SF, FF, R,
V_live, P_recomb/T_recomb/Z_recomb).

Text fitting: every box's text is auto-shrunk (never enlarged) to fit
inside its box using matplotlib's own rendered text extents (see
`_autofit_text`), so box geometry can be tuned without manually
re-measuring string widths. A floor of MIN_FONTSIZE keeps everything
readable at the figure's native (print) size.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless — no display needed to render PNGs

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

# ---------------------------------------------------------------------------
# Shared style
# ---------------------------------------------------------------------------
NAVY = "#00205B"       # ADRIC navy — box fill
BLUE = "#0047BB"       # ADRIC blue — arrows
DARK_GRAY = "#333333"  # annotations / captions
WHITE = "#FFFFFF"
PANEL_BG = "#EDEFF5"   # faint panel background (sidebar / cell interior)

DPI = 300
MIN_FONTSIZE = 9.5     # floor for all rendered text (spec: >= 9 pt at print size)
FIG_DIR = Path(__file__).resolve().parent.parent / "docs" / "manual" / "figures"

plt.rcParams["font.family"] = "DejaVu Sans"


def new_axes(figsize: tuple[float, float], xlim=(0, 100), ylim=(0, 100)):
    """Create a single blank (no-axis) canvas in data coordinates."""
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return fig, ax


# ---------------------------------------------------------------------------
# Auto-fit text: shrink a box's text (never below MIN_FONTSIZE) until its
# rendered bounding box fits inside the box's data-space width/height. This
# is what keeps every box's label inside its border regardless of exact
# string length, without hand-measuring character widths.
# ---------------------------------------------------------------------------

def _text_fits(ax, text_obj, w_data, h_data, pad=0.86):
    fig = ax.figure
    renderer = fig.canvas.get_renderer()
    bbox = text_obj.get_window_extent(renderer=renderer)
    p0 = ax.transData.transform((0, 0))
    p1 = ax.transData.transform((w_data, h_data))
    box_w_px = abs(p1[0] - p0[0])
    box_h_px = abs(p1[1] - p0[1])
    return bbox.width <= box_w_px * pad and bbox.height <= box_h_px * pad


def _autofit_text(ax, text_obj, w_data, h_data, min_fontsize=MIN_FONTSIZE):
    fig = ax.figure
    fig.canvas.draw()
    size = text_obj.get_fontsize()
    # Multiplicative shrink converges in a handful of steps.
    while size > min_fontsize and not _text_fits(ax, text_obj, w_data, h_data):
        size = max(min_fontsize, size * 0.92)
        text_obj.set_fontsize(size)
        fig.canvas.draw()
    return size


# ---------------------------------------------------------------------------
# Drawing primitives
# ---------------------------------------------------------------------------

def box(
    ax, x, y, w, h, text,
    fontsize=15, fill=NAVY, textcolor=WHITE, edge=NAVY, lw=1.8,
    boxstyle="round,pad=0.35,rounding_size=2.2", weight="bold", zorder=3,
    linestyle="-", autofit=True,
):
    """Rounded process box, centered at (x, y), width w, height h. Text is
    auto-shrunk to fit (see `_autofit_text`) unless autofit=False."""
    p = FancyBboxPatch(
        (x - w / 2, y - h / 2), w, h,
        boxstyle=boxstyle, linewidth=lw, edgecolor=edge, facecolor=fill,
        linestyle=linestyle, zorder=zorder,
    )
    ax.add_patch(p)
    t = ax.text(
        x, y, text, ha="center", va="center", fontsize=fontsize,
        color=textcolor, weight=weight, zorder=zorder + 1, linespacing=1.28,
    )
    if autofit and text:
        _autofit_text(ax, t, w, h)
    return p


def note_box(ax, x, y, w, h, text, fontsize=13):
    """A 'note' box: white fill, dashed navy border, navy text — visually
    distinct from a process box (used for measurements/inputs that are not
    part of the main physical flow, e.g. gas gravity determination)."""
    return box(
        ax, x, y, w, h, text, fontsize=fontsize, fill=WHITE, textcolor=NAVY,
        edge=NAVY, lw=1.6, linestyle="--", weight="bold",
    )


def arrow(
    ax, start, end, color=BLUE, lw=2.4, style="-|>",
    connectionstyle="arc3,rad=0.0", zorder=2, ls="-",
):
    a = FancyArrowPatch(
        start, end, arrowstyle=style, mutation_scale=20, color=color, lw=lw,
        connectionstyle=connectionstyle, zorder=zorder, linestyle=ls,
    )
    ax.add_patch(a)
    return a


def label(
    ax, x, y, text, fontsize=12, color=DARK_GRAY, ha="center", va="center",
    style="normal", weight="normal", zorder=2,
):
    ax.text(
        x, y, text, ha=ha, va=va, fontsize=max(fontsize, MIN_FONTSIZE),
        color=color, style=style, weight=weight, linespacing=1.3, zorder=zorder,
    )


def flow_column(ax, x, w, top_y, items, vgap=3.5, fontsize=12, box_kwargs=None):
    """Draw a vertical stack of boxes centered at x, connected by downward
    arrows. `items` is a list of (text, height) tuples. Returns the y of
    the bottom edge of the last box drawn (for chaining further arrows)."""
    box_kwargs = box_kwargs or {}
    cursor_top = top_y
    prev_center = prev_h = None
    for text, h in items:
        center = cursor_top - h / 2
        box(ax, x, center, w, h, text, fontsize=fontsize, **box_kwargs)
        if prev_center is not None:
            arrow(ax, (x, prev_center - prev_h / 2), (x, center + h / 2))
        prev_center, prev_h = center, h
        cursor_top = center - h / 2 - vgap
    return prev_center - prev_h / 2


def save(fig, name: str):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / name
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    size = out.stat().st_size
    print(f"wrote {out}  ({size:,} bytes)")


# ===========================================================================
# Figure 1 — flash-apparatus.png
#
# Physics reference: pvt/experiments/flash/calc.py
#   v_press   = (pump_final_cc - pump_initial_cc) * pump_constant * vcf
#   m_oil     = oil_gross_g - oil_tare_g
#   v_gas_std = (gasometer_final_cc - gasometer_initial_cc) * gasometer_factor
#               * (gas_abs_pressure_mbar / P_STD_MBAR) * (T_STD_K / (gas_temp_c + 273.15))
#   gas_density = gas_gravity * AIR_DENSITY_STD_G_CC
# ===========================================================================

def make_flash_apparatus():
    fig, ax = new_axes((14, 7.6), xlim=(0, 140), ylim=(0, 74))

    ax.text(70, 68, "Atmospheric Flash Apparatus — Water-Pump Method",
            ha="center", va="center", fontsize=19, weight="bold", color=NAVY)
    ax.text(70, 62, "ADRIC Flash v6.1 — single-stage flash separation (SSF)",
            ha="center", va="center", fontsize=12.5, color=DARK_GRAY, style="italic")

    y_main, h_main, w_box = 30, 17, 22
    # Box centers; the flask->gasometer gap is widened (19 units) to leave
    # room for the "LIBERATED GAS LINE" label without touching either box.
    xs = [15, 47, 79, 120]

    box(ax, xs[0], y_main, w_box, h_main,
        "HIGH-PRESSURE\nSAMPLE CYLINDER\n(live oil)", fontsize=13.5)
    box(ax, xs[1], y_main, w_box, h_main,
        "POSITIVE-\nDISPLACEMENT\nWATER PUMP", fontsize=13.5)
    box(ax, xs[2], y_main, w_box, h_main,
        "FLASH FLASK\nON BALANCE\n(atm. flash)", fontsize=13.5)
    box(ax, xs[3], y_main, w_box, h_main,
        "GASOMETER", fontsize=14.5)

    # Main flow arrows between adjacent box edges
    for xa, xb in zip(xs, xs[1:]):
        arrow(ax, (xa + w_box / 2, y_main), (xb - w_box / 2, y_main))

    # "Liberated gas line" sits centered in the gap between flask & gasometer
    # (kept short/two-line so it doesn't spill onto the neighboring boxes).
    gap_mid = (xs[2] + w_box / 2 + xs[3] - w_box / 2) / 2
    label(ax, gap_mid, y_main, "LIBERATED\nGAS LINE", fontsize=11, weight="bold")

    # Pump reading -> V_press (above the pump)
    label(
        ax, xs[1], y_main + 15,
        "Pump reading: initial → final\n"
        "displaced volume × pump constant × VCF\n"
        "= V_press  (live-oil volume before flash)",
        fontsize=12,
    )

    # Balance + STO volume (below the flash flask) — kept well clear of the
    # gas-gravity note box further right.
    label(
        ax, xs[2] - 4, y_main - 15.5,
        "Balance: tare → gross weight\n"
        "m_oil = oil_gross − oil_tare  (g)\n"
        "Measured STO volume: V_sto  (cc)",
        fontsize=11.5, ha="center",
    )

    # Gasometer readings (above the gasometer)
    label(
        ax, xs[3], y_main + 15,
        "Gasometer reading: initial → final\n"
        "Gas temperature T  (°C)\n"
        "Absolute pressure P  (mbar)",
        fontsize=12,
    )

    # Gas-gravity note box — a separate measurement, not part of the
    # physical apparatus train, feeding the same GOR/density calculation.
    note_box(ax, xs[3], 9, 32, 12,
             "Gas gravity — from GC\ncomposition or gravity balance", fontsize=12)
    arrow(ax, (xs[3], y_main - h_main / 2), (xs[3], 9 + 6), color=NAVY, lw=1.8, ls="--")

    save(fig, "flash-apparatus.png")


# ===========================================================================
# Figure 2 — recombination-scheme.png
#
# Physics reference: pvt/experiments/recombination/calc.py module docstring.
#   Case 1 ("separator"): separator oil + separator gas -> recombination
#       cell. SF = V_STO / V_sep_oil converts separator-oil volume to a
#       stock-tank-oil (STO) equivalent for the gas-volume calculation.
#   Case 2 ("stock_tank"): stock-tank oil (STO, fully degassed) + separator
#       gas -> recombination cell. FF (flash factor) is the extra stock-tank
#       flash gas; by standard lab practice ALL gas (separator-stage R +
#       flash FF) is loaded from the separator gas cylinder.
#   Common: factor_recomb = (P_std/P_recomb) x (T_recomb_R/T_std_R) x Z_recomb
#           V_live = V_oil + V_gas_recomb  (cell is charged to this total)
# ===========================================================================

def _recomb_cell(ax, x, y, w, h, gas_frac, top_note, bottom_note):
    """Draw the recombination-cell vessel: outer border, GAS layer on top,
    OIL layer on bottom, plus condition/volume notes above and below."""
    left, bottom = x - w / 2, y - h / 2
    outer = FancyBboxPatch(
        (left, bottom), w, h, boxstyle="round,pad=0.15,rounding_size=1.5",
        linewidth=2.4, edgecolor=NAVY, facecolor=PANEL_BG, zorder=3,
    )
    ax.add_patch(outer)
    inset = 1.1
    fill_w = w - 2 * inset
    oil_h = (h - 2 * inset) * (1 - gas_frac)
    gas_h = (h - 2 * inset) * gas_frac
    ax.add_patch(Rectangle((left + inset, bottom + inset), fill_w, oil_h,
                            facecolor=NAVY, edgecolor="none", zorder=4))
    ax.add_patch(Rectangle((left + inset, bottom + inset + oil_h), fill_w, gas_h,
                            facecolor=BLUE, edgecolor="none", zorder=4))
    ax.text(x, bottom + inset + oil_h + gas_h / 2, "GAS", ha="center", va="center",
            fontsize=13, color=WHITE, weight="bold", zorder=5)
    ax.text(x, bottom + inset + oil_h / 2, "OIL", ha="center", va="center",
            fontsize=13, color=WHITE, weight="bold", zorder=5)
    ax.text(x, y + h / 2 + 3.3, "RECOMBINATION\nCELL", ha="center", va="bottom",
            fontsize=12.5, color=NAVY, weight="bold", linespacing=1.2)
    label(ax, x, y + h / 2 + 13.2, top_note, fontsize=11.5, weight="bold")
    label(ax, x, y - h / 2 - 7.2, bottom_note, fontsize=11.5)


def _case1_panel(ax):
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(50, 97, "Case 1 — Separator Oil + Separator Gas\n→ Recombination Cell",
            ha="center", va="top", fontsize=15,
            weight="bold", color=NAVY, linespacing=1.3)

    # Sources stacked so their vertical order MATCHES the cell layers they
    # feed (gas cylinder -> GAS on top, separator -> OIL below) — avoids an
    # X-crossing between the two feed arrows.
    box(ax, 18, 72, 30, 14, "SEPARATOR GAS\nCYLINDER", fontsize=13)
    box(ax, 18, 32, 30, 16, "SEPARATOR\n(single stage)", fontsize=13.5)
    label(ax, 18, 21, "SF = V_STO / V_sep_oil", fontsize=11)

    _recomb_cell(
        ax, 74, 48, 30, 44, gas_frac=0.32,
        top_note="P_recomb / T_recomb / Z_recomb",
        bottom_note="V_live = V_oil_sep + V_gas_recomb",
    )

    # Separator -> gas cylinder (R feeds the cylinder)
    arrow(ax, (18, 40), (18, 65))
    label(ax, 34, 52, "R (stage GOR,\nscf/STB STO)", fontsize=10.8, ha="left")

    # Separator -> cell OIL layer
    arrow(ax, (33, 36), (58, 34), connectionstyle="arc3,rad=-0.12")
    label(ax, 44, 27, "V_oil_sep", fontsize=13, weight="bold", color=NAVY)

    # Gas cylinder -> cell GAS layer. Label sits at the arrow's own
    # midpoint (left of the cell) so it stays clear of the cell's
    # "P_recomb / T_recomb / Z_recomb" note directly above the cell.
    arrow(ax, (33, 72), (58, 62), connectionstyle="arc3,rad=0.12")
    label(ax, 40, 70, "V_gas_recomb", fontsize=13, weight="bold", color=NAVY)


def _case2_panel(ax):
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.text(
        50, 97,
        "Case 2 — Stock-Tank Oil + Separator Gas\n"
        "(incl. flash-factor gas) → Recombination Cell",
        ha="center", va="top", fontsize=15, weight="bold", color=NAVY, linespacing=1.3,
    )

    # Vertical stack: separator (feeds gas cylinder) -> gas cylinder (feeds
    # GAS layer) -> stock tank (feeds OIL layer). Order again matches the
    # cell's GAS-over-OIL layering, so no arrow needs to cross another box.
    box(ax, 15, 80, 28, 13, "SEPARATOR\n(single stage)", fontsize=12.5)
    box(ax, 15, 48, 28, 16, "SEPARATOR GAS\nCYLINDER\n(R + FF)", fontsize=12)
    box(ax, 15, 15, 28, 15, "STOCK TANK OIL\n(STO), fully degassed", fontsize=11.5)

    _recomb_cell(
        ax, 74, 48, 30, 44, gas_frac=0.36,
        top_note="P_recomb / T_recomb / Z_recomb",
        bottom_note="V_live = V_oil_STO + V_gas_recomb",
    )

    # Separator -> gas cylinder (metered stage GOR). Label hugs its own
    # (short, vertical) arrow, well left of the gas-cylinder-to-cell label.
    arrow(ax, (15, 73.5), (15, 56))
    label(ax, 17, 65, "R per stage\n(scf/STB STO)", fontsize=10.8, ha="left")

    # Stock tank -> gas cylinder: the flash-factor gas conceptually comes
    # from the STO flash, but per the docstring is loaded from the SAME
    # separator gas cylinder (a standard lab simplification) — shown dashed.
    # Label likewise hugs its own short arrow, left of the oil/gas labels.
    arrow(ax, (15, 22.5), (15, 40), color=NAVY, ls="--", lw=2.0)
    label(ax, 17, 31, "FF: flash-factor gas\n(charged via gas\ncylinder — simplified)",
          fontsize=10, ha="left")

    # Gas cylinder -> cell GAS layer. Label sits at the arrow's own
    # midpoint, well below the cell's "P_recomb / T_recomb / Z_recomb" /
    # "RECOMBINATION CELL" notes and clear of the R-per-stage label above it.
    arrow(ax, (29, 50), (58, 62), connectionstyle="arc3,rad=0.15")
    label(ax, 47, 68, "V_gas_recomb\n(R + FF)", fontsize=12.5, weight="bold", color=NAVY)

    # Stock tank -> cell OIL layer. Label sits low, near the arrow's start
    # (right of the stock-tank box), clear of both the FF label above it
    # and the cell's bottom_note (which is centered on the cell, further
    # right, and doesn't reach this far left).
    arrow(ax, (29, 17), (58, 34), connectionstyle="arc3,rad=-0.12")
    label(ax, 38, 17, "V_oil_STO", fontsize=13, weight="bold", color=NAVY)


def make_recombination_scheme():
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(17, 8.8))
    _case1_panel(axL)
    _case2_panel(axR)
    fig.suptitle(
        "Separator Recombination — Two Oil-Charging Cases (Carlsen & Whitson, 2020)",
        fontsize=18, weight="bold", color=NAVY, y=1.02,
    )
    fig.subplots_adjust(wspace=0.08)
    save(fig, "recombination-scheme.png")


# ===========================================================================
# Figure 3 — app-workflow.png
# ===========================================================================

def make_app_workflow():
    fig, ax = new_axes((17.5, 7.6), xlim=(0, 210), ylim=(0, 62))

    ax.text(105, 58, "PVT Lab Platform — App Data Flow", ha="center",
            va="center", fontsize=20, weight="bold", color=NAVY)

    y_chain = 29

    excel = box(ax, 16, 42, 26, 15, "FILLED ADRIC\nEXCEL TEMPLATE", fontsize=13)
    manual = box(ax, 16, 16, 26, 15, "MANUAL ENTRY\nIN FORM", fontsize=13)

    validation = box(ax, 54, y_chain, 30, 22,
                      "VALIDATION\n(typed errors name\nthe cell/field)", fontsize=13)
    engine = box(ax, 91, y_chain, 26, 15, "ENGINE\nCALCULATION\n(pvt/)", fontsize=13)
    qc = box(ax, 126, y_chain, 30, 15, "QC CHECKS\n(PASS / REVIEW / FAIL)", fontsize=12.5)
    results = box(ax, 161, y_chain, 28, 15, "RESULTS CARDS\n+ CHARTS", fontsize=13)
    report = box(ax, 194, y_chain, 26, 15, "EXCEL REPORT\nDOWNLOAD", fontsize=13)

    # Merge both inputs into validation
    arrow(ax, (16 + 13, 42), (54 - 15, y_chain + 5), connectionstyle="arc3,rad=-0.18")
    arrow(ax, (16 + 13, 16), (54 - 15, y_chain - 5), connectionstyle="arc3,rad=0.18")

    # Main chain
    for a, wa, b, wb in [
        (54, 30, 91, 26), (91, 26, 126, 30), (126, 30, 161, 28), (161, 28, 194, 26),
    ]:
        arrow(ax, (a + wa / 2, y_chain), (b - wb / 2, y_chain))

    # Feedback loop: validation -> back to the user (inputs)
    arrow(
        ax, (54 - 7, y_chain + 11), (16, 42 + 7.5 + 3.5),
        connectionstyle="arc3,rad=0.5", color=NAVY, ls="--", lw=2.2,
    )
    label(ax, 33, 56, "fix and resubmit", fontsize=13, weight="bold", color=NAVY)

    save(fig, "app-workflow.png")


# ===========================================================================
# Figure 4 — screen-map.png
#
# Reference: app.py (page titles / st.navigation) and section order read
# top-to-bottom from ui/pages/flash_page.py and ui/pages/recombination_page.py.
# ===========================================================================

def make_screen_map():
    fig, ax = new_axes((16.5, 17), xlim=(0, 170), ylim=(0, 158))

    ax.text(80, 153, "ADRIC PVT Platform — Screen Map", ha="center", va="center",
            fontsize=19, weight="bold", color=NAVY)
    ax.text(80, 148, "Sidebar navigation → per-page section order (top to bottom)",
            ha="center", va="center", fontsize=12, color=DARK_GRAY, style="italic")

    # ---- Sidebar (self-contained; no long connector arrows needed — each
    # column's own header repeats its nav item's page title) --------------
    sidebar = FancyBboxPatch(
        (13 - 12, 88 - 62), 24, 124, boxstyle="round,pad=0.3,rounding_size=2",
        edgecolor=NAVY, facecolor=PANEL_BG, linewidth=1.8, zorder=1,
    )
    ax.add_patch(sidebar)
    ax.text(13, 147, "ADRIC PVT\nPLATFORM", ha="center", va="top", fontsize=13,
            color=NAVY, weight="bold", linespacing=1.25)
    ax.text(13, 136, "SIDEBAR NAVIGATION", ha="center", va="top", fontsize=10,
            color=DARK_GRAY, style="italic")
    box(ax, 13, 121, 19, 16, "Flash Separation\n(SSF)", fontsize=11.5, fill=BLUE, edge=BLUE)
    box(ax, 13, 98, 19, 18, "Recombination /\nLive Oil", fontsize=11.5, fill=BLUE, edge=BLUE)

    # ---- Column x-ranges (non-overlapping, generous >=9-unit gaps; vol/
    # molar are wider than a plain 26 units so their longer form/results
    # lines have room to fit even at the auto-fit font floor) -------------
    flash_x, flash_w = 56, 44          # edges [34, 78]
    vol_x, vol_w = 104, 30             # edges [89, 119]
    molar_x, molar_w = 144, 30         # edges [129, 159]
    # Header-row box center; kept well clear of the subtitle above it
    # (subtitle at y=147, header top edge at top_y+6=142 -> 5-unit gap).
    top_y = 136

    # ---- Flash Separation (SSF) column -----------------------------------
    box(ax, flash_x, top_y, flash_w, 12,
        "FLASH SEPARATION (SSF)\nModule 2 — Single-Stage Flash\n& Recombination",
        fontsize=11.5)
    flash_items = [
        ("Input mode tabs:\nUpload Workbook | Manual Entry", 11),
        ("GC composition editor\n(optional, Katz-Firoozabadi)", 10.5),
        ("Results: metric cards\n(GOR, Bo, Shrinkage, Density, API)", 11.5),
        ("Composition QC panel", 8.5),
        ("Hoffmann-Crump plot\n(K-value consistency)", 10.5),
        ("Calculation steps", 8.5),
        ("Report download (.xlsx)", 8.5),
    ]
    flow_column(ax, flash_x, flash_w - 4, top_y - 6 - 3, flash_items, vgap=3.2, fontsize=11)

    # ---- Recombination / Live Oil columns --------------------------------
    recomb_center = (vol_x + molar_x) / 2
    recomb_w = (molar_x + molar_w / 2) - (vol_x - vol_w / 2)
    box(ax, recomb_center, top_y, recomb_w, 12,
        "RECOMBINATION / LIVE OIL\nModule 1 — Separator Fluid Recombination\n"
        "& PVT Cell Charging", fontsize=11.5)

    vol_tab_y = top_y - 6 - 3 - 4.25
    box(ax, vol_x, vol_tab_y, vol_w, 8.5, "Volumetric (SF/FF) tab", fontsize=10.5)
    box(ax, molar_x, vol_tab_y, molar_w, 8.5, "Molar (composition) tab", fontsize=10.5)
    arrow(ax, (recomb_center - 8, top_y - 6), (vol_x, vol_tab_y + 4.25),
          connectionstyle="arc3,rad=-0.15")
    arrow(ax, (recomb_center + 8, top_y - 6), (molar_x, vol_tab_y + 4.25),
          connectionstyle="arc3,rad=0.15")

    vol_items = [
        ("Form: Case 1/2 oil source,\nrecomb. conditions,\nseparator stage,\noil charging (c_o)", 18),
        ("Results: metric cards\n(oil charge vol.,\ngas @ recomb, mix ratio,\nGOR check)", 17),
        ("Calculation steps", 8.5),
        ("Report download (.xlsx)", 8.5),
    ]
    flow_column(ax, vol_x, vol_w - 2, vol_tab_y - 4.25 - 3, vol_items, vgap=3.0, fontsize=10)

    molar_items = [
        ("Sub-tabs: Upload LiveOil\nWorkbook | Manual Entry", 10.5),
        ("Results: metric cards\n(gas/oil mole fraction,\nwellstream MW, GOR eff.)", 13),
        ("Composition QC panel", 8),
        ("Wellstream\ncomposition table", 10),
        ("Loading plan\n(metric cards)", 10),
        ("Actual-GOR verification\n(QC form + panel)", 10),
        ("Report download (.xlsx)", 8),
    ]
    flow_column(ax, molar_x, molar_w - 2, vol_tab_y - 4.25 - 3, molar_items, vgap=2.6, fontsize=10)

    save(fig, "screen-map.png")


# ===========================================================================
def main():
    make_flash_apparatus()
    make_recombination_scheme()
    make_app_workflow()
    make_screen_map()


if __name__ == "__main__":
    main()
