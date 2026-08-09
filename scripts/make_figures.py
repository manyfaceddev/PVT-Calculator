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
re-measuring string widths. A floor of MIN_FONTSIZE (or, for the compact
screen-map figure, MIN_FONTSIZE_COMPACT) keeps everything readable once
the manual build downscales the figure to print width.

Print-scale sizing: these figures are embedded in the PDF manual at
`{width=100%}`, i.e. scaled to the page text width (~6.3in). Each figure
below is authored close to that final size (<=10in wide; the portrait
screen-map <=7.5in wide) rather than at a much larger native size, so the
downscale ratio stays mild and point-size text doesn't shrink below
readability. The MIN_FONTSIZE floors are chosen so that, after the
downscale from this authored width to 6.3in, no label renders below 7pt:
  MIN_FONTSIZE (landscape figures, authored <=10in wide):
      11.5pt * (6.3/10in) = 7.25pt final >= 7pt
  MIN_FONTSIZE_COMPACT (screen-map, authored <=7.5in wide):
      8.6pt * (6.3/7.5in) = 7.22pt final >= 7pt
300 dpi at that authored size is what keeps the raster sharp; we are not
relying on native pixel count to carry legibility, print size does.
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
MIN_FONTSIZE = 11.5         # floor for the three landscape figures (see module
                             # docstring: >=7pt after downscale from <=10in to 6.3in)
MIN_FONTSIZE_COMPACT = 8.6  # floor for the portrait screen-map figure (>=7pt
                             # after downscale from <=7.5in to 6.3in); kept as
                             # low as legibility allows so autofit has the most
                             # room to shrink text into the figure's small boxes
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
    linestyle="-", autofit=True, min_fontsize=MIN_FONTSIZE,
):
    """Rounded process box, centered at (x, y), width w, height h. Text is
    auto-shrunk to fit (see `_autofit_text`) unless autofit=False. Pass
    min_fontsize=MIN_FONTSIZE_COMPACT for the screen-map figure."""
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
        _autofit_text(ax, t, w, h, min_fontsize=min_fontsize)
    return p


def note_box(ax, x, y, w, h, text, fontsize=13, min_fontsize=MIN_FONTSIZE):
    """A 'note' box: white fill, dashed navy border, navy text — visually
    distinct from a process box (used for measurements/inputs that are not
    part of the main physical flow, e.g. gas gravity determination)."""
    return box(
        ax, x, y, w, h, text, fontsize=fontsize, fill=WHITE, textcolor=NAVY,
        edge=NAVY, lw=1.6, linestyle="--", weight="bold", min_fontsize=min_fontsize,
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
    style="normal", weight="normal", zorder=2, min_fontsize=MIN_FONTSIZE,
):
    ax.text(
        x, y, text, ha=ha, va=va, fontsize=max(fontsize, min_fontsize),
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
    # Authored close to final print size (<=10in wide, see module docstring)
    # so the 300dpi raster stays sharp without relying on a large native
    # size that would then need aggressive downscaling to fit the page.
    fig, ax = new_axes((9.6, 5.2), xlim=(0, 140), ylim=(0, 74))

    ax.text(70, 68, "Atmospheric Flash Apparatus — Water-Pump Method",
            ha="center", va="center", fontsize=19, weight="bold", color=NAVY)
    ax.text(70, 62, "ADRIC Flash v6.1 — single-stage flash separation (SSF)",
            ha="center", va="center", fontsize=12.5, color=DARK_GRAY, style="italic")

    y_main, h_main, w_box = 30, 20, 25
    # Box centers; gaps are uneven on purpose — the pump-water and
    # flask-gasometer gaps (arrows only) are trimmed to 6/4 units so the
    # flask->gasometer gap can stay wide (21 units) for the "LIBERATED GAS
    # LINE" label, which needs more clearance now that the boxes
    # themselves are wider (see MIN_FONTSIZE / module docstring).
    xs = [15, 46, 75, 121]

    # Every multi-word line below is broken short (down to a manual
    # "DISPLACE-/MENT" hyphenation in one case): at this figure's compact,
    # <=10in-wide print scale, a line like "SAMPLE CYLINDER" or "(atm.
    # flash)" needs more width than these boxes have even at the
    # MIN_FONTSIZE floor, so line breaks — not just auto-fit shrink — keep
    # text inside its box.
    box(ax, xs[0], y_main, w_box, h_main,
        "HIGH-\nPRESSURE\nSAMPLE\nCYLINDER\n(live oil)", fontsize=13.5)
    box(ax, xs[1], y_main, w_box, h_main,
        "POSITIVE-\nDISPLACE-\nMENT\nWATER\nPUMP", fontsize=13.5)
    box(ax, xs[2], y_main, w_box, h_main,
        "FLASH\nFLASK\nON BALANCE\n(atm.\nflash)", fontsize=13.5)
    box(ax, xs[3], y_main, w_box, h_main,
        "GASOMETER", fontsize=14.5)

    # Main flow arrows between adjacent box edges
    for xa, xb in zip(xs, xs[1:]):
        arrow(ax, (xa + w_box / 2, y_main), (xb - w_box / 2, y_main))

    # "Liberated gas line" sits centered in the gap between flask & gasometer
    # (kept short/two-line so it doesn't spill onto the neighboring boxes).
    gap_mid = (xs[2] + w_box / 2 + xs[3] - w_box / 2) / 2
    label(ax, gap_mid, y_main, "LIBERATED\nGAS LINE", fontsize=11, weight="bold")

    # Pump reading -> V_press (above the pump). y is pushed up from the
    # box's shared top edge (y_main + h_main/2 = 40) to clear it now that
    # the boxes are taller than a first pass would suggest.
    label(
        ax, xs[1], y_main + 18,
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

    # Gasometer readings (above the gasometer); pushed up for the same
    # reason as the pump-reading label above.
    label(
        ax, xs[3], y_main + 18,
        "Gasometer reading: initial → final\n"
        "Gas temperature T  (°C)\n"
        "Absolute pressure P  (mbar)",
        fontsize=12,
    )

    # Gas-gravity note box — a separate measurement, not part of the
    # physical apparatus train, feeding the same GOR/density calculation.
    note_box(ax, xs[3], 8, 32, 15,
             "Gas gravity —\nfrom GC\ncomposition or\ngravity balance", fontsize=12)
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
    ax.text(x, y + h / 2 + 2.0, "RECOMBINATION\nCELL", ha="center", va="bottom",
            fontsize=12.5, color=NAVY, weight="bold", linespacing=1.2)
    # top_note/bottom_note are passed pre-wrapped to two lines (see callers):
    # at this figure's compact canvas a single-line "P_recomb / T_recomb /
    # Z_recomb" or "V_live = ... + ..." is wide enough to run off the
    # panel edge, so both are split at a natural word boundary.
    label(ax, x, y + h / 2 + 17, top_note, fontsize=11.5, weight="bold", zorder=6)
    label(ax, x, y - h / 2 - 7.2, bottom_note, fontsize=11.5, zorder=6)


def _case1_panel(ax):
    ax.set_xlim(0, 100)
    # ylim extends 8 units above the panel content (which is unchanged and
    # stays within 0-100) purely to give the panel title more vertical
    # room: at this figure's compact canvas the title text is wide enough
    # that it must wrap to three lines (see below) to stay within the
    # panel's own width, and three lines need more height than the
    # original two-line title had room for above the topmost box.
    ax.set_ylim(0, 108)
    ax.axis("off")
    ax.text(50, 105, "Case 1 — Separator Oil\n+ Separator Gas →\nRecombination Cell",
            ha="center", va="top", fontsize=12,
            weight="bold", color=NAVY, linespacing=1.15)

    # Sources stacked so their vertical order MATCHES the cell layers they
    # feed (gas cylinder -> GAS on top, separator -> OIL below) — avoids an
    # X-crossing between the two feed arrows. Boxes/cell are widened (vs.
    # the source-column gaps trimmed) relative to the figure's data range
    # so label text still has room at this figure's compact, print-scale
    # canvas (see MIN_FONTSIZE / make_recombination_scheme).
    box(ax, 23, 72, 40, 15, "SEPARATOR\nGAS\nCYLINDER", fontsize=13)
    box(ax, 23, 32, 40, 17, "SEPARATOR\n(single stage)", fontsize=13.5)
    label(ax, 23, 20, "SF = V_STO / V_sep_oil", fontsize=11)

    _recomb_cell(
        ax, 79, 48, 36, 44, gas_frac=0.32,
        top_note="P_recomb / T_recomb\n/ Z_recomb",
        bottom_note="V_live = V_oil_sep +\nV_gas_recomb",
    )

    # Separator -> gas cylinder (R feeds the cylinder)
    arrow(ax, (23, 40.5), (23, 64.5))
    # zorder=6 so this (and the other annotation labels below) always
    # render above the boxes/cell (zorder 3-5) even where the compact
    # canvas leaves little horizontal clearance between them.
    label(ax, 33, 52, "R (stage GOR,\nscf/STB STO)", fontsize=10.8, ha="left", zorder=6)

    # Separator -> cell OIL layer. Label sits just above the "SEPARATOR"
    # box's top edge (y=40.5) rather than beside the arrowhead — the gap
    # between that box and the cell (43-61) is too narrow for this label
    # at this figure's compact canvas, but the row just above the box is
    # clear across the full box-to-cell width.
    arrow(ax, (43, 36), (61, 34), connectionstyle="arc3,rad=-0.12")
    label(ax, 60, 44, "V_oil_sep", fontsize=11.5, weight="bold", color=NAVY,
          ha="right", zorder=6)

    # Gas cylinder -> cell GAS layer. Label is right-anchored just left of
    # the cell, level with the arrowhead, clear of the "SEPARATOR GAS
    # CYLINDER" box above and the cell's notes above that.
    arrow(ax, (43, 72), (61, 62), connectionstyle="arc3,rad=0.12")
    label(ax, 60, 62, "V_gas_recomb", fontsize=11.5, weight="bold", color=NAVY,
          ha="right", zorder=6)


def _case2_panel(ax):
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 108)  # extra headroom for the title, see _case1_panel
    ax.axis("off")
    ax.text(
        50, 105,
        "Case 2 — Stock-Tank Oil + Sep. Gas\n"
        "(incl. flash-factor gas)\n"
        "→ Recombination Cell",
        ha="center", va="top", fontsize=12, weight="bold", color=NAVY, linespacing=1.15,
    )

    # Vertical stack: separator (feeds gas cylinder) -> gas cylinder (feeds
    # GAS layer) -> stock tank (feeds OIL layer). Order again matches the
    # cell's GAS-over-OIL layering, so no arrow needs to cross another box.
    # Boxes/cell widened to match _case1_panel's compact-canvas treatment.
    box(ax, 20, 80, 36, 14, "SEPARATOR\n(single stage)", fontsize=12.5)
    box(ax, 20, 48, 36, 20, "SEPARATOR\nGAS\nCYLINDER\n(R + FF)", fontsize=12)
    box(ax, 20, 14, 36, 20, "STOCK TANK\nOIL (STO),\nfully\ndegassed", fontsize=11.5)

    _recomb_cell(
        ax, 79, 48, 36, 44, gas_frac=0.36,
        top_note="P_recomb / T_recomb\n/ Z_recomb",
        bottom_note="V_live = V_oil_STO +\nV_gas_recomb",
    )

    # Separator -> gas cylinder (metered stage GOR). The box_top-to-box_mid
    # gap (y 58-73) is clear of boxes across the full panel width, so this
    # label and the gas-cylinder-to-cell label below share it, stacked by
    # height (y=69 vs y=60) rather than competing for the same row.
    # zorder=6 so annotation labels always render above the boxes/cell.
    arrow(ax, (20, 73), (20, 58))
    label(ax, 24, 69, "R per stage\n(scf/STB STO)", fontsize=10.8, ha="left", zorder=6)

    # Stock tank -> gas cylinder: the flash-factor gas conceptually comes
    # from the STO flash, but per the docstring is loaded from the SAME
    # separator gas cylinder (a standard lab simplification) — shown dashed.
    # Shares the box_mid-to-box_bottom gap (y 24-38) with the
    # stock-tank-to-cell label below, stacked by height for the same reason.
    arrow(ax, (20, 24), (20, 38), color=NAVY, ls="--", lw=2.0)
    label(ax, 24, 31, "FF: flash-factor gas\n(via gas cylinder,\nsimplified)",
          fontsize=10, ha="left", zorder=6)

    # Gas cylinder -> cell GAS layer. Right-anchored just left of the cell,
    # low enough (y=60) to clear both the "R per stage" label above and the
    # box_mid top edge (y=58).
    arrow(ax, (38, 50), (61, 62), connectionstyle="arc3,rad=0.15")
    label(ax, 60, 60, "V_gas_recomb\n(R + FF)", fontsize=11.5, weight="bold", color=NAVY,
          ha="right", zorder=6)

    # Stock tank -> cell OIL layer. Centered (not right-anchored) in the
    # narrow box-to-bottom_note gap: this label's own navy bold text would
    # be unreadable against the navy source box if it touched it even
    # slightly, so it needs margin on both sides rather than hugging one edge.
    arrow(ax, (38, 17), (61, 34), connectionstyle="arc3,rad=-0.12")
    label(ax, 48, 21, "V_oil_STO", fontsize=11.5, weight="bold", color=NAVY, zorder=6)


def make_recombination_scheme():
    # Authored close to final print size (<=10in wide total for both
    # panels, see module docstring) rather than a large native size.
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11.0, 5.67))
    _case1_panel(axL)
    _case2_panel(axR)
    # Wrapped to two lines: a single-line suptitle at a legible fontsize is
    # a figure-wide (not per-panel) element wide enough on its own to pin
    # the whole figure's tight-bbox width well past the 10in cap.
    fig.suptitle(
        "Separator Recombination — Two Oil-Charging Cases\n(Carlsen & Whitson, 2020)",
        fontsize=18, weight="bold", color=NAVY, y=1.04, linespacing=1.25,
    )
    fig.subplots_adjust(wspace=0.14)
    save(fig, "recombination-scheme.png")


# ===========================================================================
# Figure 3 — app-workflow.png
# ===========================================================================

def make_app_workflow():
    # Authored close to final print size (<=10in wide, see module docstring).
    # ylim extends above the box/label content (which stays within 0-62)
    # purely to give the title more clearance above the "fix and resubmit"
    # feedback-loop label — at this figure's compact canvas the title's
    # own text needs more headroom than it did at a larger native size.
    fig, ax = new_axes((9.6, 4.17), xlim=(0, 210), ylim=(0, 68))

    ax.text(105, 65, "PVT Lab Platform — App Data Flow", ha="center",
            va="center", fontsize=20, weight="bold", color=NAVY)

    y_chain = 29

    # Box widths/heights below are wider and taller than a first pass would
    # suggest, and every label is wrapped to short (mostly single-word)
    # lines: at this figure's compact, <=10in-wide print scale, a two-word
    # line like "EXCEL TEMPLATE" or "QC CHECKS (PASS / REVIEW / FAIL)"
    # needs more width than these chain boxes have even at the
    # MIN_FONTSIZE floor, so the line breaks do the work the auto-fit
    # shrink alone can't.
    excel = box(ax, 17, 42, 30, 18, "FILLED\nADRIC\nEXCEL\nTEMPLATE", fontsize=13)
    manual = box(ax, 17, 16, 30, 18, "MANUAL\nENTRY\nIN FORM", fontsize=13)

    validation = box(ax, 55, y_chain, 34, 26,
                      "VALIDATION\n(typed\nerrors\nname the\ncell/field)", fontsize=13)
    engine = box(ax, 93, y_chain, 28, 18, "ENGINE\nCALC\n(pvt/)", fontsize=13)
    qc = box(ax, 129, y_chain, 32, 21, "QC\nCHECKS\n(PASS /\nREVIEW /\nFAIL)", fontsize=12.5)
    results = box(ax, 165, y_chain, 30, 18, "RESULTS\nCARDS +\nCHARTS", fontsize=13)
    report = box(ax, 199, y_chain, 28, 18, "EXCEL\nREPORT\nDOWN-\nLOAD", fontsize=13)

    # Merge both inputs into validation
    arrow(ax, (17 + 15, 42), (55 - 17, y_chain + 5), connectionstyle="arc3,rad=-0.18")
    arrow(ax, (17 + 15, 16), (55 - 17, y_chain - 5), connectionstyle="arc3,rad=0.18")

    # Main chain
    for a, wa, b, wb in [
        (55, 34, 93, 28), (93, 28, 129, 32), (129, 32, 165, 30), (165, 30, 199, 28),
    ]:
        arrow(ax, (a + wa / 2, y_chain), (b - wb / 2, y_chain))

    # Feedback loop: validation -> back to the user (inputs)
    arrow(
        ax, (55 - 8, y_chain + 12), (17, 42 + 9 + 3.5),
        connectionstyle="arc3,rad=0.5", color=NAVY, ls="--", lw=2.2,
    )
    label(ax, 34, 56, "fix and resubmit", fontsize=13, weight="bold", color=NAVY)

    save(fig, "app-workflow.png")


# ===========================================================================
# Figure 4 — screen-map.png
#
# Reference: app.py (page titles / st.navigation) and section order read
# top-to-bottom from ui/pages/flash_page.py and ui/pages/recombination_page.py.
# ===========================================================================

def make_screen_map():
    # Authored close to final print size (<=7.5in wide — this figure is
    # portrait, see module docstring). Every box()/label() call below
    # passes min_fontsize=MIN_FONTSIZE_COMPACT so autofit has room to
    # shrink text into this figure's small boxes while staying >=7pt
    # after the print-time downscale.
    fig, ax = new_axes((9.0, 9.29), xlim=(0, 170), ylim=(0, 158))

    ax.text(80, 153, "ADRIC PVT Platform — Screen Map", ha="center", va="center",
            fontsize=19, weight="bold", color=NAVY)
    ax.text(80, 148, "Sidebar navigation → per-page section order (top to bottom)",
            ha="center", va="center", fontsize=12, color=DARK_GRAY, style="italic")

    # ---- Sidebar (self-contained; no long connector arrows needed — each
    # column's own header repeats its nav item's page title) --------------
    sidebar = FancyBboxPatch(
        (12 - 11, 88 - 62), 22, 124, boxstyle="round,pad=0.3,rounding_size=2",
        edgecolor=NAVY, facecolor=PANEL_BG, linewidth=1.8, zorder=1,
    )
    ax.add_patch(sidebar)
    ax.text(12, 147, "ADRIC PVT\nPLATFORM", ha="center", va="top", fontsize=10.5,
            color=NAVY, weight="bold", linespacing=1.2)
    ax.text(12, 137, "SIDEBAR\nNAVIGATION", ha="center", va="top", fontsize=9.5,
            color=DARK_GRAY, style="italic", linespacing=1.2)
    # "Separation"/"Recombination" are hyphenated across lines — at this
    # figure's compact canvas neither word fits whole in an 18-wide pill
    # even at the MIN_FONTSIZE_COMPACT floor.
    box(ax, 12, 118, 21, 18, "Flash\nSepara-\ntion\n(SSF)", fontsize=11, fill=BLUE, edge=BLUE,
        min_fontsize=MIN_FONTSIZE_COMPACT)
    box(ax, 12, 95, 21, 20, "Recombi-\nnation /\nLive Oil", fontsize=11, fill=BLUE, edge=BLUE,
        min_fontsize=MIN_FONTSIZE_COMPACT)

    # ---- Column x-ranges. The sidebar and the gaps between columns were
    # trimmed to the minimum that still reads as separated (down from the
    # original design's much larger margins) so the reclaimed width could
    # go to the columns themselves — at this figure's <=7.5in-wide print
    # scale, box text needs most of the available data-range to stay
    # readable at the MIN_FONTSIZE_COMPACT floor (see module docstring).
    flash_x, flash_w = 54, 50          # edges [29, 79]
    vol_x, vol_w = 103.5, 37           # edges [85, 122]
    molar_x, molar_w = 146, 36         # edges [128, 164]
    # Header-row box center; kept well clear of the subtitle above it
    # (subtitle at y=147, header top edge at top_y+6=142 -> 5-unit gap).
    top_y = 136

    # ---- Flash Separation (SSF) column -----------------------------------
    box(ax, flash_x, top_y, flash_w, 15,
        "FLASH SEPARATION (SSF)\nModule 2 — Single-\nStage Flash &\nRecombination",
        fontsize=11.5, min_fontsize=MIN_FONTSIZE_COMPACT)
    # Every item is wrapped so no single line runs much past ~20 characters
    # — at this figure's compact canvas even the MIN_FONTSIZE_COMPACT floor
    # cannot shrink a long unwrapped line into these column widths, so the
    # line breaks (not just the fontsize floor) are what keeps text inside
    # its box. Item heights below are sized for their line count.
    flash_items = [
        ("Input mode tabs:\nUpload Workbook |\nManual Entry", 15),
        ("GC composition editor\n(optional,\nKatz-Firoozabadi)", 15),
        ("Results: metric cards\n(GOR, Bo, Shrinkage,\nDensity, API)", 15),
        ("Composition QC\npanel", 10.5),
        ("Hoffmann-Crump plot\n(K-value\nconsistency)", 15),
        ("Calculation steps", 8.5),
        ("Report download\n(.xlsx)", 10.5),
    ]
    flow_column(ax, flash_x, flash_w - 4, top_y - 6 - 3, flash_items, vgap=2.6, fontsize=11,
                box_kwargs={"min_fontsize": MIN_FONTSIZE_COMPACT})

    # ---- Recombination / Live Oil columns --------------------------------
    recomb_center = (vol_x + molar_x) / 2
    recomb_w = (molar_x + molar_w / 2) - (vol_x - vol_w / 2)
    box(ax, recomb_center, top_y, recomb_w, 12,
        "RECOMBINATION / LIVE OIL\nModule 1 — Separator Fluid Recombination\n"
        "& PVT Cell Charging", fontsize=11.5, min_fontsize=MIN_FONTSIZE_COMPACT)

    vol_tab_y = top_y - 6 - 3 - 4.25
    box(ax, vol_x, vol_tab_y, vol_w, 8.5, "Volumetric\n(SF/FF) tab", fontsize=10.5,
        min_fontsize=MIN_FONTSIZE_COMPACT)
    box(ax, molar_x, vol_tab_y, molar_w, 8.5, "Molar\n(composition) tab", fontsize=10.5,
        min_fontsize=MIN_FONTSIZE_COMPACT)
    arrow(ax, (recomb_center - 8, top_y - 6), (vol_x, vol_tab_y + 4.25),
          connectionstyle="arc3,rad=-0.15")
    arrow(ax, (recomb_center + 8, top_y - 6), (molar_x, vol_tab_y + 4.25),
          connectionstyle="arc3,rad=0.15")

    vol_items = [
        ("Form: Case 1/2\noil source,\nrecomb.\nconditions,\nseparator stage,\noil charging\n(c_o)", 29),
        ("Results: metric\ncards (oil charge\nvol., gas @\nrecomb, mix ratio,\nGOR check)", 22),
        ("Calculation steps", 8.5),
        ("Report download\n(.xlsx)", 10.5),
    ]
    flow_column(ax, vol_x, vol_w - 2, vol_tab_y - 4.25 - 3, vol_items, vgap=2.4, fontsize=10,
                box_kwargs={"min_fontsize": MIN_FONTSIZE_COMPACT})

    molar_items = [
        ("Sub-tabs:\nUpload LiveOil\nWorkbook |\nManual Entry", 17),
        ("Results: metric\ncards (gas/oil\nmole fraction,\nwellstream MW,\nGOR eff.)", 22),
        ("Composition QC\npanel", 10.5),
        ("Wellstream\ncomposition table", 10),
        ("Loading plan\n(metric cards)", 10),
        ("Actual-GOR\nverification\n(QC form + panel)", 15),
        ("Report download\n(.xlsx)", 10.5),
    ]
    flow_column(ax, molar_x, molar_w - 2, vol_tab_y - 4.25 - 3, molar_items, vgap=2.2, fontsize=10,
                box_kwargs={"min_fontsize": MIN_FONTSIZE_COMPACT})

    save(fig, "screen-map.png")


# ===========================================================================
def main():
    make_flash_apparatus()
    make_recombination_scheme()
    make_app_workflow()
    make_screen_map()


if __name__ == "__main__":
    main()
