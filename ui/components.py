"""
ui/components.py — Reusable HTML component builders for the PVT Calculator UI.

Each function returns an HTML string.  Render with:
    st.markdown(component(...), unsafe_allow_html=True)

Keeping HTML construction here keeps page modules clean and makes styling
changes easy to locate.
"""

from pvt.recombination.models import MultiStageResults, StageResult, SeparatorStage
from pvt.constants import SCF_STB_TO_CC_CC, BARA_TO_PSIA, P_STD_PSIA, T_STD_R


# ===========================================================================
# Page-level components
# ===========================================================================

def page_header(title: str, subtitle: str) -> str:
    return (
        f'<div class="pvt-header">'
        f'<h1>{title}</h1>'
        f'<p>{subtitle}</p>'
        f'</div>'
    )


def section_label(text: str) -> str:
    return f'<div class="pvt-section">{text}</div>'


def results_header() -> str:
    return '<div class="pvt-results-header">📊 Calculation Results</div>'


# ===========================================================================
# Input summary card (echoes sidebar values in main area)
# ===========================================================================

def input_summary_card(
    res:         MultiStageResults,
    stages:      list,
    v_live:      float,
    bo_sep:      float,
    n_stages:    int,
    oil_source:  str,
    r_sto:       float,
    p_charge:    float,
    c_o_x1e6:   float,
    gor_unit:    str,
    pres_unit:   str,
    temp_unit:   str,
) -> str:
    """Small card echoing the key inputs used for this calculation."""

    case_lbl = (
        "Case 1 — Separator Oil + Separator Gas"
        if oil_source == "separator"
        else "Case 2 — Stock Tank Oil + Separator Gas"
    )

    sep_rows = ""
    for i, s in enumerate(stages):
        sep_rows += (
            f'<div class="is-row">'
            f'<span class="is-lbl">Stage {i+1} GOR / P / T / Z</span>'
            f'<span class="is-val">'
            f'{s.R:.1f} {gor_unit} &nbsp;·&nbsp; {s.P:.1f} {pres_unit}'
            f' &nbsp;·&nbsp; {s.T:.1f} {temp_unit} &nbsp;·&nbsp; {s.Z:.3f}'
            f'</span></div>'
        )

    sto_row = (
        f'<div class="is-row"><span class="is-lbl">Stock Tank GOR</span>'
        f'<span class="is-val">{r_sto:.1f} {gor_unit}</span></div>'
        if oil_source == "stock_tank" else ""
    )
    bo_row = (
        f'<div class="is-row"><span class="is-lbl">Bo @ separator</span>'
        f'<span class="is-val">{bo_sep:.4f}</span></div>'
        if oil_source == "separator" else ""
    )

    return (
        f'<div class="pvt-input-summary">'
        f'<div class="is-title">📋 Inputs used — {case_lbl}</div>'
        f'<div>'
        f'<div class="is-row"><span class="is-lbl">Target live fluid volume</span>'
        f'<span class="is-val">{v_live:.0f} cc</span></div>'
        f'{bo_row}'
        f'{sep_rows}'
        f'{sto_row}'
        f'<div class="is-row"><span class="is-lbl">Recomb. conditions</span>'
        f'<span class="is-val">{res.P_recomb_psia:.1f} psia &nbsp;·&nbsp; {res.T_recomb_F:.1f} °F &nbsp;·&nbsp; Z = {res.Z_recomb:.3f}</span></div>'
        f'<div class="is-row"><span class="is-lbl">Oil charging pressure</span>'
        f'<span class="is-val">{res.P_charge_oil_psia:.1f} psia &nbsp;·&nbsp; c_o = {c_o_x1e6:.1f} × 10⁻⁶ psi⁻¹</span></div>'
        f'</div>'
        f'</div>'
    )


# ===========================================================================
# Process flow diagram — well → separator → (stock tank) → cell  [SVG]
# ===========================================================================

def process_diagram(
    oil_source:   str,
    n_stages:     int,
    stage_labels: list[str],
    stages:       list,
    units:        str,
    pres_unit:    str,
    temp_unit:    str,
) -> str:
    """
    Render an SVG process-flow schematic for Case 1 or Case 2.

    Case 1 — Separator Oil + Separator Gas
      Oil well → Separator  (gas exits top → cylinder → PVT cell)
                            (oil exits bottom → PVT cell)

    Case 2 — Stock Tank Oil + Separator Gas
      Oil well → Separator  (gas exits top → cylinder → PVT cell)
                            (oil exits bottom → Stock Tank → STO gas vented)
                                                          → STO oil → PVT cell
    """

    # ── Stage annotation text ─────────────────────────────────────────────────
    sep_info_lines = []
    for lbl, s in zip(stage_labels, stages):
        sep_info_lines.append(
            f"{lbl}: {s.P:.0f} {pres_unit} / {s.T:.0f} {temp_unit} / GOR={s.R:.0f}"
        )

    gor_label = "scf/STB" if units == "field" else "sm³/sm³"

    # ── Colour constants ──────────────────────────────────────────────────────
    C_WELL    = "#1a6644"   # petroleum green — well
    C_SEP     = "#1a4080"   # deep blue — separator
    C_GAS     = "#2060b0"   # blue — gas stream
    C_OIL     = "#b06010"   # amber — oil stream
    C_STO     = "#d97020"   # orange — stock tank / STO
    C_CELL    = "#0d3d2a"   # dark green — PVT cell
    C_CYL     = "#2a6aaa"   # mid blue — gas cylinder
    C_VENT    = "#888888"   # grey — vented gas

    # ── SVG arrow marker definitions ──────────────────────────────────────────
    defs = f"""
    <defs>
      <marker id="arr"     markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
        <polygon points="0 0,8 3,0 6" fill="#777"/></marker>
      <marker id="arr-gas" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
        <polygon points="0 0,8 3,0 6" fill="{C_GAS}"/></marker>
      <marker id="arr-oil" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
        <polygon points="0 0,8 3,0 6" fill="{C_OIL}"/></marker>
      <marker id="arr-sto" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
        <polygon points="0 0,8 3,0 6" fill="{C_STO}"/></marker>
      <marker id="arr-vent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
        <polygon points="0 0,8 3,0 6" fill="{C_VENT}"/></marker>
    </defs>"""

    def box(x, y, w, h, label, sublabel, color, bg, rx=5):
        """Styled equipment box."""
        lines = ""
        # Split sublabel by newline or | for multi-line
        if sublabel:
            parts = sublabel.replace("|", "\n").split("\n")
            dy = 14
            for i, p in enumerate(parts):
                lines += f'<text x="{x+w//2}" y="{y+h//2+dy+i*11}" text-anchor="middle" font-size="7.5" fill="{color}" opacity="0.85">{p.strip()}</text>'
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{bg}" stroke="{color}" stroke-width="1.8"/>'
            f'<text x="{x+w//2}" y="{y+h//2+4}" text-anchor="middle" font-size="9.5" '
            f'font-weight="700" fill="{color}">{label}</text>'
            f'{lines}'
        )

    def sep_vessel(x, y, w, h, info_lines, color_gas, color_oil, pres_unit_):
        """Draw a separator vessel with gas (top) and oil (bottom) zones."""
        mid_y = y + int(h * 0.50)
        nozzle_top_y  = y - 8
        nozzle_bot_y  = y + h
        sub = ""
        for i, ln in enumerate(info_lines):
            sub += f'<text x="{x+w//2}" y="{y+18+i*10}" text-anchor="middle" font-size="7.5" fill="{color_gas}" opacity="0.9">{ln}</text>'
        return (
            # Background vessel
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="white" stroke="{color_gas}" stroke-width="2"/>'
            # Gas zone (top)
            f'<rect x="{x+1}" y="{y+1}" width="{w-2}" height="{mid_y-y-1}" rx="5" fill="#deeafa"/>'
            # Oil zone (bottom)
            f'<rect x="{x+1}" y="{mid_y}" width="{w-2}" height="{y+h-mid_y-1}" rx="0" fill="#fff0d4"/>'
            # Liquid level dashed line
            f'<line x1="{x}" y1="{mid_y}" x2="{x+w}" y2="{mid_y}" stroke="{color_gas}" stroke-width="1" stroke-dasharray="4,3"/>'
            # GAS label
            f'<text x="{x+w//2}" y="{y+int((mid_y-y)/2)+5}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{color_gas}">GAS</text>'
            # OIL label
            f'<text x="{x+w//2}" y="{mid_y+int((y+h-mid_y)/2)+5}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{color_oil}">OIL</text>'
            # Vessel title (above gas zone)
            f'<text x="{x+w//2}" y="{y-12}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{color_gas}">SEPARATOR(S)</text>'
            # Top nozzle (gas outlet)
            f'<rect x="{x+w//2-4}" y="{nozzle_top_y}" width="8" height="9" fill="{color_gas}"/>'
            # Bottom nozzle (oil outlet)
            f'<rect x="{x+w//2-4}" y="{nozzle_bot_y}" width="8" height="9" fill="{color_oil}"/>'
            # Info text lines
            + sub
        )

    # ═══════════════════════════════════════════════════════════════
    # CASE 1 — separator oil (no stock tank)
    # ═══════════════════════════════════════════════════════════════
    if oil_source == "separator":
        W, H = 680, 210
        # ── Y coordinates ────────────────────────────────────────────────────
        gas_y     = 30    # gas stream y
        main_y    = 95    # main wellstream y
        oil_y     = 170   # oil delivery line y

        # ── X coordinates ─────────────────────────────────────────────────────
        well_x, well_w = 10, 68
        sep_x,  sep_w  = 110, 82
        cyl_x,  cyl_w  = 320, 80
        cell_x, cell_w = 500, 90
        sep_cy         = 55   # separator vessel top y
        sep_ch         = 110  # separator vessel height

        sep_mid_y = sep_cy + sep_ch // 2
        gas_noz_y = sep_cy            # top of separator
        oil_noz_y = sep_cy + sep_ch   # bottom of separator

        svg_body = f"""
        <!-- BACKGROUND -->
        <rect width="{W}" height="{H}" fill="#f9f8f5" rx="8"/>

        <!-- CASE BADGE -->
        <rect x="8" y="6" width="280" height="16" rx="4" fill="#d4f0e4"/>
        <text x="148" y="17.5" text-anchor="middle" font-size="9.5" font-weight="700" fill="{C_CELL}">CASE 1 — SEPARATOR OIL + SEPARATOR GAS</text>

        <!-- === OIL WELL === -->
        <!-- Derrick triangle -->
        <polygon points="{well_x+34},{sep_cy-20} {well_x+10},{sep_cy+40} {well_x+58},{sep_cy+40}"
                 fill="#e8f4ee" stroke="{C_WELL}" stroke-width="1.5"/>
        <line x1="{well_x+34}" y1="{sep_cy-20}" x2="{well_x+34}" y2="{sep_cy+40}"
              stroke="{C_WELL}" stroke-width="1.2" stroke-dasharray="3,2"/>
        <!-- Well box / wellhead -->
        <rect x="{well_x+18}" y="{sep_cy+40}" width="32" height="20" rx="3"
              fill="#c8e8d8" stroke="{C_WELL}" stroke-width="1.5"/>
        <text x="{well_x+34}" y="{sep_cy+53}" text-anchor="middle" font-size="7.5" font-weight="700" fill="{C_WELL}">WELL</text>
        <!-- Borehole -->
        <line x1="{well_x+34}" y1="{sep_cy+60}" x2="{well_x+34}" y2="{sep_cy+80}"
              stroke="{C_WELL}" stroke-width="3" stroke-dasharray="4,3"/>
        <!-- Well label -->
        <text x="{well_x+34}" y="{sep_cy+95}" text-anchor="middle" font-size="8" fill="{C_WELL}">Reservoir</text>
        <text x="{well_x+34}" y="{sep_cy+105}" text-anchor="middle" font-size="8" fill="{C_WELL}">P_res / T_res</text>

        <!-- === SEPARATOR VESSEL === -->
        {sep_vessel(sep_x, sep_cy, sep_w, sep_ch, sep_info_lines, C_SEP, C_OIL, pres_unit)}

        <!-- WELLSTREAM: well → separator -->
        <line x1="{well_x+58}" y1="{sep_cy+35}" x2="{sep_x}" y2="{sep_cy+35}"
              stroke="#777" stroke-width="2" marker-end="url(#arr)"/>
        <text x="{(well_x+58+sep_x)//2}" y="{sep_cy+30}" text-anchor="middle" font-size="8" fill="#666">wellstream</text>

        <!-- GAS line: separator top nozzle → right to gas cylinder -->
        <!-- Vertical up from nozzle to gas_y -->
        <line x1="{sep_x+sep_w//2}" y1="{gas_noz_y}" x2="{sep_x+sep_w//2}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2"/>
        <!-- Horizontal right to gas cylinder -->
        <line x1="{sep_x+sep_w//2}" y1="{gas_y}" x2="{cyl_x}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2" marker-end="url(#arr-gas)"/>
        <text x="{(sep_x+sep_w//2+cyl_x)//2}" y="{gas_y-4}" text-anchor="middle" font-size="8" fill="{C_GAS}">separator gas (top of vessel)</text>

        <!-- GAS CYLINDER box -->
        <rect x="{cyl_x}" y="{gas_y-14}" width="{cyl_w}" height="28" rx="12"
              fill="#deeafa" stroke="{C_CYL}" stroke-width="1.8"/>
        <text x="{cyl_x+cyl_w//2}" y="{gas_y+2}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{C_CYL}">GAS CYLINDER</text>
        <text x="{cyl_x+cyl_w//2}" y="{gas_y+12}" text-anchor="middle" font-size="7.5" fill="{C_CYL}">sep gas stored</text>

        <!-- Arrow: cylinder → PVT cell (gas line) -->
        <line x1="{cyl_x+cyl_w}" y1="{gas_y}" x2="{cell_x}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2" marker-end="url(#arr-gas)"/>
        <text x="{(cyl_x+cyl_w+cell_x)//2}" y="{gas_y-4}" text-anchor="middle" font-size="7.5" fill="{C_GAS}">gas charged to cell</text>

        <!-- PVT CELL box -->
        <rect x="{cell_x}" y="{gas_y-18}" width="{cell_w}" height="36" rx="5"
              fill="#d4f0e4" stroke="{C_CELL}" stroke-width="2"/>
        <text x="{cell_x+cell_w//2}" y="{gas_y+2}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{C_CELL}">PVT CELL</text>
        <text x="{cell_x+cell_w//2}" y="{gas_y+13}" text-anchor="middle" font-size="7.5" fill="{C_CELL}">P_recomb / T_recomb</text>

        <!-- OIL line: separator bottom nozzle → down to oil_y → right → into PVT cell -->
        <!-- Vertical down from oil nozzle -->
        <line x1="{sep_x+sep_w//2}" y1="{oil_noz_y+9}" x2="{sep_x+sep_w//2}" y2="{oil_y}"
              stroke="{C_OIL}" stroke-width="2"/>
        <!-- Horizontal right to cell -->
        <line x1="{sep_x+sep_w//2}" y1="{oil_y}" x2="{cell_x+cell_w//2}" y2="{oil_y}"
              stroke="{C_OIL}" stroke-width="2"/>
        <!-- Vertical up into cell bottom -->
        <line x1="{cell_x+cell_w//2}" y1="{oil_y}" x2="{cell_x+cell_w//2}" y2="{gas_y+18}"
              stroke="{C_OIL}" stroke-width="2" marker-end="url(#arr-oil)"/>
        <text x="{(sep_x+sep_w//2+cell_x+cell_w//2)//2}" y="{oil_y-4}" text-anchor="middle" font-size="8" fill="{C_OIL}">separator oil (bottom of vessel) → cell</text>
        <!-- Bo label on oil line -->
        <text x="{sep_x+sep_w//2+60}" y="{oil_y+12}" text-anchor="middle" font-size="7.5" fill="{C_OIL}">Bo adjustment (sep vol → STO equiv)</text>
        """

        note = (
            f"<b style='color:{C_GAS}'>Separator gas</b> exits the <b>top</b> of the vessel → collected in gas cylinder → charged to PVT cell. &nbsp;"
            f"<b style='color:{C_OIL}'>Separator oil</b> exits the <b>bottom</b> → charged directly to the PVT cell. &nbsp;"
            f"Bo at separator conditions relates the separator oil volume to stock-tank oil (STO) equivalent. &nbsp;"
            f"<b>Technician loads oil first at P_charge (oil charging pressure), then pumps gas until P_recomb is reached.</b>"
        )
        badge_html = (
            f'<div style="display:inline-block;padding:3px 12px;border-radius:4px;'
            f'font-size:0.72rem;font-weight:700;letter-spacing:0.4px;margin-bottom:8px;'
            f'background:#d4f0e4;color:{C_CELL};border:1px solid {C_WELL};">CASE 1 — Separator Oil + Separator Gas</div>'
        )

    # ═══════════════════════════════════════════════════════════════
    # CASE 2 — stock tank oil
    # ═══════════════════════════════════════════════════════════════
    else:
        W, H = 680, 270
        # ── Y coordinates ────────────────────────────────────────────────────
        gas_y     = 30    # gas stream y (top)
        sep_cy    = 50    # separator top y
        sep_ch    = 110   # separator height
        tank_cy   = 195   # stock tank top y
        tank_ch   = 60    # stock tank height
        sto_oil_y = 260   # STO oil delivery line y (at bottom of SVG)
        vent_y    = tank_cy  # vent arrow from tank top

        # ── X coordinates ─────────────────────────────────────────────────────
        well_x, well_w = 10, 68
        sep_x,  sep_w  = 120, 82
        tank_x, tank_w = sep_x + 10, sep_w - 10  # tank roughly under separator
        cyl_x,  cyl_w  = 320, 80
        cell_x, cell_w = 500, 90

        sep_mid_y  = sep_cy + sep_ch // 2
        gas_noz_y  = sep_cy
        oil_noz_y  = sep_cy + sep_ch

        svg_body = f"""
        <!-- BACKGROUND -->
        <rect width="{W}" height="{H}" fill="#f9f8f5" rx="8"/>

        <!-- CASE BADGE -->
        <rect x="8" y="6" width="300" height="16" rx="4" fill="#fff3e0"/>
        <text x="158" y="17.5" text-anchor="middle" font-size="9.5" font-weight="700" fill="{C_STO}">CASE 2 — STOCK TANK OIL + SEPARATOR GAS</text>

        <!-- === OIL WELL === -->
        <polygon points="{well_x+34},{sep_cy-20} {well_x+10},{sep_cy+40} {well_x+58},{sep_cy+40}"
                 fill="#e8f4ee" stroke="{C_WELL}" stroke-width="1.5"/>
        <line x1="{well_x+34}" y1="{sep_cy-20}" x2="{well_x+34}" y2="{sep_cy+40}"
              stroke="{C_WELL}" stroke-width="1.2" stroke-dasharray="3,2"/>
        <rect x="{well_x+18}" y="{sep_cy+40}" width="32" height="20" rx="3"
              fill="#c8e8d8" stroke="{C_WELL}" stroke-width="1.5"/>
        <text x="{well_x+34}" y="{sep_cy+53}" text-anchor="middle" font-size="7.5" font-weight="700" fill="{C_WELL}">WELL</text>
        <line x1="{well_x+34}" y1="{sep_cy+60}" x2="{well_x+34}" y2="{sep_cy+80}"
              stroke="{C_WELL}" stroke-width="3" stroke-dasharray="4,3"/>
        <text x="{well_x+34}" y="{sep_cy+95}" text-anchor="middle" font-size="8" fill="{C_WELL}">Reservoir</text>
        <text x="{well_x+34}" y="{sep_cy+105}" text-anchor="middle" font-size="8" fill="{C_WELL}">P_res / T_res</text>

        <!-- === SEPARATOR VESSEL === -->
        {sep_vessel(sep_x, sep_cy, sep_w, sep_ch, sep_info_lines, C_SEP, C_OIL, pres_unit)}

        <!-- WELLSTREAM: well → separator -->
        <line x1="{well_x+58}" y1="{sep_cy+35}" x2="{sep_x}" y2="{sep_cy+35}"
              stroke="#777" stroke-width="2" marker-end="url(#arr)"/>
        <text x="{(well_x+58+sep_x)//2}" y="{sep_cy+30}" text-anchor="middle" font-size="8" fill="#666">wellstream</text>

        <!-- GAS line: top nozzle → up → right to gas cylinder -->
        <line x1="{sep_x+sep_w//2}" y1="{gas_noz_y}" x2="{sep_x+sep_w//2}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2"/>
        <line x1="{sep_x+sep_w//2}" y1="{gas_y}" x2="{cyl_x}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2" marker-end="url(#arr-gas)"/>
        <text x="{(sep_x+sep_w//2+cyl_x)//2}" y="{gas_y-4}" text-anchor="middle" font-size="8" fill="{C_GAS}">separator gas (top of vessel)</text>

        <!-- GAS CYLINDER box -->
        <rect x="{cyl_x}" y="{gas_y-14}" width="{cyl_w}" height="28" rx="12"
              fill="#deeafa" stroke="{C_CYL}" stroke-width="1.8"/>
        <text x="{cyl_x+cyl_w//2}" y="{gas_y+2}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{C_CYL}">GAS CYLINDER</text>
        <text x="{cyl_x+cyl_w//2}" y="{gas_y+12}" text-anchor="middle" font-size="7.5" fill="{C_CYL}">ALL gas (sep + STO GOR)</text>

        <!-- Arrow: cylinder → PVT cell -->
        <line x1="{cyl_x+cyl_w}" y1="{gas_y}" x2="{cell_x}" y2="{gas_y}"
              stroke="{C_GAS}" stroke-width="2" marker-end="url(#arr-gas)"/>
        <text x="{(cyl_x+cyl_w+cell_x)//2}" y="{gas_y-4}" text-anchor="middle" font-size="7.5" fill="{C_GAS}">all gas charged to cell</text>

        <!-- PVT CELL box -->
        <rect x="{cell_x}" y="{gas_y-18}" width="{cell_w}" height="36" rx="5"
              fill="#d4f0e4" stroke="{C_CELL}" stroke-width="2"/>
        <text x="{cell_x+cell_w//2}" y="{gas_y+2}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{C_CELL}">PVT CELL</text>
        <text x="{cell_x+cell_w//2}" y="{gas_y+13}" text-anchor="middle" font-size="7.5" fill="{C_CELL}">P_recomb / T_recomb</text>

        <!-- OIL line: separator bottom → down to stock tank -->
        <line x1="{sep_x+sep_w//2}" y1="{oil_noz_y+9}" x2="{sep_x+sep_w//2}" y2="{tank_cy}"
              stroke="{C_OIL}" stroke-width="2" marker-end="url(#arr-oil)"/>
        <text x="{sep_x+sep_w//2+30}" y="{(oil_noz_y+9+tank_cy)//2}" font-size="8" fill="{C_OIL}">sep oil (bottom)</text>
        <text x="{sep_x+sep_w//2+30}" y="{(oil_noz_y+9+tank_cy)//2+10}" font-size="7.5" fill="{C_OIL}">P_sep → P_atm</text>

        <!-- === STOCK TANK === -->
        <!-- Tank shape (flat-bottomed) -->
        <rect x="{tank_x}" y="{tank_cy}" width="{tank_w}" height="{tank_ch}" rx="4"
              fill="#fff3e0" stroke="{C_STO}" stroke-width="2"/>
        <text x="{tank_x+tank_w//2}" y="{tank_cy-10}" text-anchor="middle" font-size="9.5" font-weight="700" fill="{C_STO}">STOCK TANK</text>
        <text x="{tank_x+tank_w//2}" y="{tank_cy+18}" text-anchor="middle" font-size="8.5" font-weight="700" fill="{C_STO}">P_atm (14.7 psia)</text>
        <!-- Oil level line in tank -->
        <rect x="{tank_x+1}" y="{tank_cy+tank_ch-22}" width="{tank_w-2}" height="21" rx="0" fill="#ffe4b0"/>
        <line x1="{tank_x}" y1="{tank_cy+tank_ch-22}" x2="{tank_x+tank_w}" y2="{tank_cy+tank_ch-22}"
              stroke="{C_STO}" stroke-width="1" stroke-dasharray="4,3"/>
        <text x="{tank_x+tank_w//2}" y="{tank_cy+tank_ch-8}" text-anchor="middle" font-size="7.5" fill="{C_STO}">STO oil (degassed)</text>
        <!-- Shrinkage annotation -->
        <text x="{tank_x+tank_w+5}" y="{tank_cy+25}" font-size="7.5" fill="{C_STO}">Shrinkage:</text>
        <text x="{tank_x+tank_w+5}" y="{tank_cy+36}" font-size="7.5" fill="{C_STO}">SF = R_STO/R_sep</text>

        <!-- VENTED GAS: arrow up from tank top -->
        <line x1="{tank_x+12}" y1="{tank_cy}" x2="{tank_x+12}" y2="{tank_cy-30}"
              stroke="{C_VENT}" stroke-width="1.5" stroke-dasharray="3,2" marker-end="url(#arr-vent)"/>
        <text x="{tank_x+18}" y="{tank_cy-18}" font-size="7.5" fill="{C_VENT}">STO gas</text>
        <text x="{tank_x+18}" y="{tank_cy-8}" font-size="7.5" fill="{C_VENT}">vented ↑</text>

        <!-- STO OIL line: stock tank bottom → right → up into PVT cell -->
        <!-- Down from tank bottom -->
        <line x1="{tank_x+tank_w//2}" y1="{tank_cy+tank_ch}" x2="{tank_x+tank_w//2}" y2="{sto_oil_y-4}"
              stroke="{C_STO}" stroke-width="2"/>
        <!-- Right to cell x -->
        <line x1="{tank_x+tank_w//2}" y1="{sto_oil_y-4}" x2="{cell_x+cell_w//2}" y2="{sto_oil_y-4}"
              stroke="{C_STO}" stroke-width="2"/>
        <!-- Up into cell -->
        <line x1="{cell_x+cell_w//2}" y1="{sto_oil_y-4}" x2="{cell_x+cell_w//2}" y2="{gas_y+18}"
              stroke="{C_STO}" stroke-width="2" marker-end="url(#arr-sto)"/>
        <text x="{(tank_x+tank_w//2+cell_x+cell_w//2)//2}" y="{sto_oil_y-8}" text-anchor="middle" font-size="8" fill="{C_STO}">STO oil (degassed) → PVT cell</text>
        <text x="{(tank_x+tank_w//2+cell_x+cell_w//2)//2}" y="{sto_oil_y+4}" text-anchor="middle" font-size="7.5" fill="{C_STO}">loaded at oil charging pressure (P_charge)</text>
        """

        note = (
            f"<b style='color:{C_GAS}'>Separator gas</b> exits the <b>top</b> of the vessel → gas cylinder → PVT cell. &nbsp;"
            f"<b style='color:{C_OIL}'>Separator oil</b> exits the <b>bottom</b> → flows to the stock tank at atmospheric pressure. &nbsp;"
            f"As pressure drops (P_sep → P_atm), more gas flashes out (<b>STO gas</b>, vented) — oil <b>shrinks</b> (SF = R_STO / R_sep). &nbsp;"
            f"<b style='color:{C_STO}'>Fully-degassed STO oil</b> is charged to the PVT cell. &nbsp;"
            f"All gas (separator GOR + stock tank GOR) is charged from the gas cylinder. &nbsp;"
            f"<b>Technician loads STO oil at P_charge, then pumps gas until P_recomb is reached.</b>"
        )
        badge_html = (
            f'<div style="display:inline-block;padding:3px 12px;border-radius:4px;'
            f'font-size:0.72rem;font-weight:700;letter-spacing:0.4px;margin-bottom:8px;'
            f'background:#fff3e0;color:#6b3d00;border:1px solid {C_STO};">CASE 2 — Stock Tank Oil + Separator Gas</div>'
        )

    # ── Assemble final HTML ───────────────────────────────────────────────────
    svg_html = (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
        f'style="width:100%;max-width:{W}px;font-family:\'Segoe UI\',system-ui,Arial,sans-serif;">'
        f'{defs}'
        f'{svg_body}'
        f'</svg>'
    )

    return (
        f'<div class="pvt-flow-wrap">'
        f'{badge_html}'
        f'{svg_html}'
        f'<div class="pfd-note">{note}</div>'
        f'</div>'
    )


# ===========================================================================
# Hero card (charge instructions)
# ===========================================================================

def hero_card(
    res:               MultiStageResults,
    v_live:            float,
    n_stages:          int,
    stage_labels:      list[str],
    gor_unit:          str,
    gas_unit:          str,
    gor_err_pct:       float,
    R_total_eff_input: float,
    pres_unit:         str,
) -> str:
    """Full charge-instructions hero card with numbered steps."""

    gor_check_str = (
        f"{res.GOR_check:.1f} {gor_unit} ✓"
        if gor_err_pct < 0.1
        else f"{res.GOR_check:.1f} {gor_unit} ⚠"
    )

    oil_label  = "STO oil"       if res.oil_source == "stock_tank" else "separator oil"
    oil_lbl_s  = "Stock Tank Oil" if res.oil_source == "stock_tank" else "Separator Oil"
    charge_diff_pct = (res.V_oil_charge / res.V_oil_sep - 1.0) * 100.0 if res.V_oil_sep > 0 else 0.0

    # ── Step 1 — charge oil ───────────────────────────────────────────────────
    step1_html = (
        f'<div style="display:flex;align-items:baseline;gap:0.5rem;margin:0.5rem 0;">'
        f'<span class="hero-step-num">1</span>'
        f'<div>'
        f'<span class="charge-val highlight">{res.V_oil_charge:,.1f}</span>'
        f'<span class="charge-unit"> cc {oil_label}</span>'
        f'<div class="charge-label highlight">'
        f'⭐ Load into cell at <strong>{res.P_charge_oil_psia:.0f} psia</strong> (oil charging pressure)'
        f'</div>'
        f'<div class="charge-label" style="font-size:0.72rem;margin-top:2px;">'
        f'At recomb P ({res.P_recomb_psia:.0f} psia) oil occupies {res.V_oil_sep:,.1f} cc '
        f'— {abs(charge_diff_pct):.2f}% {"larger" if charge_diff_pct > 0 else "smaller"} at P_charge due to compressibility'
        f'</div>'
        f'</div></div>'
    )

    # ── Shrinkage banner (Case 2) ─────────────────────────────────────────────
    shrink_html = ""
    if res.oil_source == "stock_tank" and res.shrinkage_factor > 0:
        shrink_html = (
            f'<div class="shrink-banner">'
            f'Shrinkage factor SF = R_STO / R_sep = '
            f'{res.R_STO_input:.1f} / {res.R_total_input:.1f} = '
            f'<strong>{res.shrinkage_factor:.4f}</strong>'
            f'&nbsp;·&nbsp; (separator GOR × SF = stock tank GOR: '
            f'{res.R_total_input:.1f} × {res.shrinkage_factor:.4f} ≈ {res.R_total_input * res.shrinkage_factor:.1f} {gor_unit})'
            f'</div>'
        )

    # ── Step 2 — charge gas ───────────────────────────────────────────────────
    step2_parts = ""
    for sr in res.stage_results:
        pct_total = res.R_total_cc + res.R_STO_cc
        pct = sr.R_cc / pct_total * 100.0 if pct_total > 0 else 0.0
        show_pct = n_stages > 1 or res.oil_source == "stock_tank"
        pct_str = f" ({pct:.0f}% of GOR)" if show_pct else ""
        step2_parts += (
            f'<div class="charge-row">'
            f'<span class="charge-val">{sr.V_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit"> cc sep gas @ recomb</span>'
            f'<div class="charge-label">Stage {sr.stage_num} ({sr.label})'
            f' · {sr.V_gas_std_cc:,.1f} cc @ std · {sr.V_gas_std_unit:.4f} {gas_unit}{pct_str}</div>'
            f'</div>'
        )

    # STO flash gas row (Case 2)
    if res.oil_source == "stock_tank" and res.R_STO_cc > 0:
        pct_total = res.R_total_cc + res.R_STO_cc
        sto_pct = res.R_STO_cc / pct_total * 100.0 if pct_total > 0 else 0.0
        step2_parts += (
            f'<div class="charge-row">'
            f'<span class="charge-val">{res.V_STO_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit"> cc STO flash gas @ recomb</span>'
            f'<div class="charge-label">Stock tank flash · {res.V_STO_gas_std_cc:,.1f} cc @ std'
            f' · {res.V_STO_gas_std_unit:.4f} {gas_unit} · ({sto_pct:.0f}% of GOR)'
            f'<br><em style="font-size:0.7rem;">Charged as separator gas (lab convention)</em></div>'
            f'</div>'
        )

    # Multi-stage total gas row
    show_total = n_stages > 1 or (res.oil_source == "stock_tank" and res.R_STO_cc > 0)
    total_gas_html = ""
    if show_total:
        total_gas_html = (
            f'<div class="charge-row" style="margin-top:0.4rem;padding-top:0.4rem;border-top:1px solid rgba(255,255,255,0.1);">'
            f'<span class="charge-val" style="font-size:1.5rem;">{res.total_V_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit"> cc total gas @ recomb</span>'
            f'<div class="charge-label">{res.total_V_gas_std_cc:,.1f} cc @ std · {res.total_V_gas_std_unit:.4f} {gas_unit} · all stages</div>'
            f'</div>'
        )

    step2_html = (
        f'<div style="margin:0.5rem 0 0 0;">'
        f'<div style="display:flex;align-items:flex-start;gap:6px;">'
        f'<span class="hero-step-num">2</span>'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.72rem;color:#a0e0c0;margin-bottom:4px;">Add separator gas to cell (pump to reach P_recomb)</div>'
        f'{step2_parts}'
        f'{total_gas_html}'
        f'</div></div></div>'
    )

    # ── Step 3 — seal ─────────────────────────────────────────────────────────
    step3_html = (
        f'<div style="display:flex;align-items:center;gap:6px;margin:0.5rem 0;">'
        f'<span class="hero-step-num">3</span>'
        f'<div style="font-size:0.78rem;color:#a0e0c0;">'
        f'Seal cell and equilibrate at <strong style="color:#fff;">{res.P_recomb_psia:.0f} psia / {res.T_recomb_F:.0f}°F</strong>'
        f' — total cell: <strong style="color:#fff;">{v_live:.0f} cc</strong> live fluid'
        f'</div></div>'
    )

    oil_pct = 100.0 / (1.0 + res.cylinder_mix_ratio)

    return (
        f'<div class="pvt-hero">'
        f'<div class="hero-title">⚗️ Charge Instructions — {v_live:.0f} cc live fluid'
        f' @ {res.T_recomb_F:.0f}°F / {res.P_recomb_psia:.0f} {pres_unit}</div>'
        f'{shrink_html}'
        f'{step1_html}'
        f'<hr class="hero-divider">'
        f'{step2_html}'
        f'<hr class="hero-divider">'
        f'{step3_html}'
        f'<hr class="hero-divider">'
        f'<div class="charge-row">'
        f'<span class="charge-val" style="font-size:1.6rem;">{res.cylinder_mix_ratio:.4f}</span>'
        f'<span class="charge-unit"> cc/cc</span>'
        f'<div class="charge-label">Cylinder mix ratio — cc total gas @ recomb per cc {oil_label}'
        f' &nbsp;·&nbsp; oil is {oil_pct:.1f}% of final live-fluid volume</div>'
        f'</div>'
        f'<hr class="hero-divider">'
        f'<div class="hero-sub">'
        f'Total GOR: {R_total_eff_input:.1f} {gor_unit}'
        + (f' (sep {res.R_total_input:.1f} + STO {res.R_STO_input:.1f})' if res.oil_source == "stock_tank" else '')
        + f' &nbsp;·&nbsp; Z_recomb = {res.Z_recomb:.3f}'
        f' &nbsp;·&nbsp; GOR check: {gor_check_str}'
        f'</div>'
        f'</div>'
    )


# ===========================================================================
# Metric cards row
# ===========================================================================

def metric_card(value: str, unit: str, label: str, accent: str = "") -> str:
    """accent: "" | "accent-green" | "accent-blue" | "accent-amber" """
    cls = f"pvt-metric-card {accent}".strip()
    return (
        f'<div class="{cls}">'
        f'<div class="m-val">{value}</div>'
        f'<div class="m-unit">{unit}</div>'
        f'<div class="m-lbl">{label}</div>'
        f'</div>'
    )


def metric_cards_row(res: MultiStageResults, gor_unit: str, pb_html: str = "") -> str:
    oil_label = "STO Oil Charge" if res.oil_source == "stock_tank" else "Oil Charge"
    cards = (
        metric_card(f"{res.V_oil_charge:,.1f}",            "cc @ P_charge",  oil_label,          "accent-amber")
        + metric_card(f"{res.total_V_gas_recomb_cc:,.1f}", "cc @ recomb",    "Gas to Charge",     "accent-blue")
        + metric_card(f"{res.cylinder_mix_ratio:.4f}",     "cc gas / cc oil","Mix Ratio",          "accent-green")
        + metric_card(f"{res.total_V_gas_std_cc:,.1f}",    "cc @ std",       "Total Gas @ Std",    "")
        + metric_card(f"{res.R_total_input:,.1f}",          gor_unit,         "Sep. Stage GOR",     "")
        + (metric_card(f"{res.R_STO_input:,.1f}", gor_unit, "Stock Tank GOR", "accent-amber")
           if res.oil_source == "stock_tank" else "")
        + pb_html
    )
    return f'<div class="pvt-card-row">{cards}</div>'


# ===========================================================================
# Bubble point card
# ===========================================================================

def bubble_point_card(
    Pb_disp:    float,
    Pb_unit:    str,
    Pb_lo:      float,
    Pb_hi:      float,
    R_for_pb:   float,
    gamma_g:    float,
    T_for_pb:   float,
    api_gravity: float,
) -> str:
    return (
        f'<div class="pb-card">'
        f'<div class="pb-title">🔴 Bubble Point Estimate — Standing (1947)</div>'
        f'<div><span class="pb-val">{Pb_disp:,.0f}</span>'
        f'<span class="pb-unit"> {Pb_unit}</span></div>'
        f'<div class="pb-range">±15% confidence range: {Pb_lo:,.0f} – {Pb_hi:,.0f} {Pb_unit}</div>'
        f'<div class="pb-note">'
        f'Pb = 18.2 × [(R/γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]<br>'
        f'R = {R_for_pb:.0f} scf/STB &nbsp;|&nbsp; γg = {gamma_g:.3f}'
        f' &nbsp;|&nbsp; T = {T_for_pb:.0f} °F &nbsp;|&nbsp; API = {api_gravity:.0f}°<br>'
        f'⚠ Estimate only — Standing (1947) was calibrated on California crude data.'
        f'</div></div>'
    )


def bubble_point_metric_card(Pb_disp: float, Pb_unit: str) -> str:
    return metric_card(f"{Pb_disp:,.0f}", Pb_unit, "Est. Bubble Point", "accent-amber")


# ===========================================================================
# Stage breakdown card
# ===========================================================================

def stage_card(
    sr:              StageResult,
    P_input:         float,
    T_input:         float,
    pres_unit:       str,
    temp_unit:       str,
    gor_unit:        str,
    gas_unit:        str,
    n_stages:        int,
    R_total_eff_cc:  float = 0.0,
) -> str:
    pct_str = (
        f'&nbsp;<span style="font-weight:400;color:#7a7a72;font-size:0.77rem;">'
        f'({sr.pct_of_total:.1f}% of total GOR)</span>'
        if R_total_eff_cc > 0 else ""
    )
    return (
        f'<div class="stage-card">'
        f'<div class="sc-title">Stage {sr.stage_num} — {sr.label}{pct_str}</div>'
        f'<div class="sc-row"><span class="sc-lbl">Separator GOR</span>'
        f'<span class="sc-val">{sr.R_input:.2f} {gor_unit}'
        f' &nbsp;= {sr.R_cc:.5f} cc/cc</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Sep. P / T / Z</span>'
        f'<span class="sc-val">{P_input:.1f} {pres_unit}'
        f' · {T_input:.1f} {temp_unit} · Z = {sr.Z:.3f}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ std (14.696 psia / 60°F)</span>'
        f'<span class="sc-val">{sr.V_gas_std_cc:,.2f} cc'
        f' = {sr.V_gas_std_unit:.5f} {gas_unit}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ sep. conditions</span>'
        f'<span class="sc-val">{sr.V_gas_sep:,.2f} cc</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ recomb. conditions</span>'
        f'<span class="sc-val gas-recomb">{sr.V_gas_recomb_cc:,.2f} cc ← charged to cell</span></div>'
        f'</div>'
    )


# ===========================================================================
# Stock tank flash gas card (Case 2)
# ===========================================================================

def sto_gas_card(res: MultiStageResults, gor_unit: str, gas_unit: str) -> str:
    sto_pct = (
        res.R_STO_cc / (res.R_total_cc + res.R_STO_cc) * 100.0
        if (res.R_total_cc + res.R_STO_cc) > 0 else 0.0
    )
    return (
        f'<div class="stage-card sto-stage">'
        f'<div class="sc-title">Stock Tank Flash Gas'
        f'&nbsp;<span style="font-weight:400;color:#7a7a72;font-size:0.77rem;">'
        f'({sto_pct:.1f}% of total GOR)</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Stock Tank GOR</span>'
        f'<span class="sc-val">{res.R_STO_input:.2f} {gor_unit}'
        f' = {res.R_STO_cc:.5f} cc/cc</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Shrinkage factor SF</span>'
        f'<span class="sc-val">{res.shrinkage_factor:.5f}'
        f'&nbsp;<span style="font-size:0.73rem;color:#7a7a72;">(= R_STO / R_sep)</span></span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ std (14.696 psia / 60°F)</span>'
        f'<span class="sc-val">{res.V_STO_gas_std_cc:,.2f} cc'
        f' = {res.V_STO_gas_std_unit:.5f} {gas_unit}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ recomb. conditions</span>'
        f'<span class="sc-val sto-recomb">{res.V_STO_gas_recomb_cc:,.2f} cc ← charged as sep gas</span></div>'
        f'</div>'
    )


# ===========================================================================
# Calculation step block
# ===========================================================================

def calc_step(label: str, body: str) -> str:
    return (
        f'<div class="pvt-step">'
        f'<div class="step-label">{label}</div>'
        f'{body}'
        f'</div>'
    )


def conv_box(text: str) -> str:
    """Inline unit-conversion reference box for use inside calc_step body."""
    return f'<span class="conv-box">ⓘ {text}</span>'


# ===========================================================================
# Lab report table helpers
# ===========================================================================

def _trow(name: str, val: str, unit_lbl: str = "", highlight: bool = False) -> str:
    cls = ' class="tbl-highlight"' if highlight else ""
    return (
        f"<tr{cls}><td>{name}</td>"
        f'<td style="text-align:right;font-weight:600;color:#0d3d2a;">{val}</td>'
        f'<td style="color:#7a7a72;font-size:0.76rem;">{unit_lbl}</td></tr>'
    )


def _tsect(title: str) -> str:
    return f'<tr class="tbl-section"><td colspan="3">{title}</td></tr>'


def lab_report_table(
    res:               MultiStageResults,
    stages:            list,
    v_live:            float,
    bo_sep:            float,
    n_stages:          int,
    gor_unit:          str,
    pres_unit:         str,
    temp_unit:         str,
    gas_unit:          str,
    gor_err_pct:       float,
    R_total_eff_input: float = 0.0,
    c_o_x1e6:         float = 10.0,
    show_pb:           bool  = False,
    Pb_disp:           float = 0.0,
    Pb_lo:             float = 0.0,
    Pb_hi:             float = 0.0,
    Pb_unit:           str   = "",
    gamma_g:           float = 0.0,
    api_gravity:       float = 0.0,
    T_for_pb:          float = 0.0,
) -> str:
    rows = ""

    # ── Setup ─────────────────────────────────────────────────────────────────
    rows += _tsect("A. SETUP")
    rows += _trow("Oil Source",
                  "Separator Oil (Case 1)" if res.oil_source == "separator" else "Stock Tank Oil / STO (Case 2)")
    rows += _trow("Target Live Fluid Volume", f"{v_live:.2f}", "cc")
    if res.oil_source == "separator":
        rows += _trow("Bo at Separator Conditions", f"{bo_sep:.4f}", "res bbl / STB")
    rows += _trow("Separator Stages", str(n_stages))
    rows += _trow("Unit System", res.units)

    # ── Standard conditions ───────────────────────────────────────────────────
    rows += _tsect("B. STANDARD CONDITIONS")
    rows += _trow("P_std",                   "14.696",           "psia")
    rows += _trow("T_std",                   "60.0 °F / 519.67 °R")
    rows += _trow("1 scf/STB in cc/cc",      f"{SCF_STB_TO_CC_CC:.6f}", "cc gas (std) / cc STO")
    rows += _trow("1 STB in cc",             "158,987",           "cc (= 42 US gal)")
    rows += _trow("1 scf in cc",             "28,316.8",          "cc")

    # ── Recombination conditions ──────────────────────────────────────────────
    rows += _tsect("C. RECOMBINATION CONDITIONS")
    rows += _trow("Pressure",              f"{res.P_recomb_psia:.2f}", "psia (absolute)")
    rows += _trow("Temperature",           f"{res.T_recomb_F:.1f}",   "°F")
    rows += _trow("Temperature (Rankine)", f"{res.T_recomb_R:.2f}",   "°R = °F + 459.67")
    rows += _trow("Z-factor",              f"{res.Z_recomb:.4f}")
    factor_r = (P_STD_PSIA / res.P_recomb_psia) * (res.T_recomb_R / T_STD_R) * res.Z_recomb
    rows += _trow("Recomb. factor f",
                  f"= (14.696 / {res.P_recomb_psia:.2f}) × ({res.T_recomb_R:.2f} / 519.67) × {res.Z_recomb:.3f} = {factor_r:.6f}",
                  "cc gas@recomb per cc gas@std")

    # ── Oil charging conditions ───────────────────────────────────────────────
    rows += _tsect("D. OIL CHARGING CONDITIONS")
    rows += _trow("Oil Charging Pressure",    f"{res.P_charge_oil_psia:.2f}", "psia (absolute)")
    rows += _trow("ΔP (recomb − charge)",
                  f"{res.P_recomb_psia:.2f} − {res.P_charge_oil_psia:.2f} = {res.P_recomb_psia - res.P_charge_oil_psia:.2f}",
                  "psi")
    rows += _trow("Oil Compressibility c_o",  f"{c_o_x1e6:.1f} × 10⁻⁶", "psi⁻¹")
    oil_label = "STO Oil" if res.oil_source == "stock_tank" else "Separator Oil"
    rows += _trow(f"{oil_label} volume at P_recomb",  f"{res.V_oil_sep:.4f}", "cc")
    rows += _trow(
        f"{oil_label} volume at P_charge  ⭐",
        f"{res.V_oil_sep:.4f} × (1 + {c_o_x1e6:.1f}×10⁻⁶ × {res.P_recomb_psia - res.P_charge_oil_psia:.1f}) = {res.V_oil_charge:.4f}",
        "cc  ← CHARGE THIS AMOUNT",
        highlight=True,
    )

    # ── Per-stage separator data ──────────────────────────────────────────────
    for sr in res.stage_results:
        p_in = stages[sr.stage_num - 1].P
        t_in = stages[sr.stage_num - 1].T
        conv_note = f"× {SCF_STB_TO_CC_CC:.6f} cc/cc per scf/STB" if res.units == "field" else "(SI: cc/cc directly)"
        rows += _tsect(f"E{sr.stage_num}. STAGE {sr.stage_num} — {sr.label}")
        rows += _trow("GOR (input)",           f"{sr.R_input:.2f}",         gor_unit)
        rows += _trow("GOR (cc/cc)",           f"{sr.R_input:.2f} {conv_note} = {sr.R_cc:.6f}", "cc/cc")
        rows += _trow("Separator Pressure",    f"{p_in:.2f}",               pres_unit)
        rows += _trow("Separator Temperature", f"{t_in:.2f}",               temp_unit)
        rows += _trow("Z-factor at sep.",      f"{sr.Z:.4f}")
        rows += _trow("V_oil_STO",             f"{res.V_oil_STO:.4f}",      "cc")
        rows += _trow("V_gas_std = R_cc × V_STO",
                      f"{sr.R_cc:.6f} × {res.V_oil_STO:.4f} = {sr.V_gas_std_cc:.4f}", "cc @ std")
        rows += _trow("V_gas_std (display units)", f"{sr.V_gas_std_unit:.6f}", gas_unit)
        rows += _trow("V_gas_sep (at sep P,T)",    f"{sr.V_gas_sep:.4f}",  "cc")
        rows += _trow("V_gas_recomb = V_std × f",
                      f"{sr.V_gas_std_cc:.4f} × {factor_r:.6f} = {sr.V_gas_recomb_cc:.4f}",
                      "cc @ recomb  ← charge this gas", highlight=True)
        rows += _trow("% of total solution GOR", f"{sr.pct_of_total:.2f}", "%")

    # ── Stock tank flash (Case 2) ─────────────────────────────────────────────
    if res.oil_source == "stock_tank":
        conv_note = f"× {SCF_STB_TO_CC_CC:.6f}" if res.units == "field" else "(SI)"
        rows += _tsect("F. STOCK TANK FLASH (Case 2)")
        rows += _trow("Stock Tank GOR (input)",    f"{res.R_STO_input:.2f}",     gor_unit)
        rows += _trow("Stock Tank GOR (cc/cc)",    f"{res.R_STO_input:.2f} {conv_note} = {res.R_STO_cc:.6f}", "cc/cc")
        rows += _trow("Shrinkage factor SF",
                      f"R_STO / R_sep = {res.R_STO_cc:.6f} / {res.R_total_cc:.6f} = {res.shrinkage_factor:.6f}",
                      "(R_sep × SF = R_STO)")
        rows += _trow("V_STO_gas_std",             f"{res.V_STO_gas_std_cc:.4f}", "cc @ std")
        rows += _trow("V_STO_gas_std",             f"{res.V_STO_gas_std_unit:.6f}", gas_unit)
        rows += _trow("V_STO_gas_recomb",
                      f"{res.V_STO_gas_std_cc:.4f} × {factor_r:.6f} = {res.V_STO_gas_recomb_cc:.4f}",
                      "cc @ recomb  ← charged as sep gas", highlight=True)

    # ── Charge volumes summary ────────────────────────────────────────────────
    rows += _tsect("G. CHARGE VOLUMES SUMMARY")
    rows += _trow(f"{oil_label} at P_recomb",       f"{res.V_oil_sep:.4f}",             "cc")
    rows += _trow(f"{oil_label} at P_charge ⭐",    f"{res.V_oil_charge:.4f}",          "cc  ← load into cell", highlight=True)
    rows += _trow("STO Oil Equivalent",             f"{res.V_oil_STO:.4f}",             "cc")
    rows += _trow("Total Gas @ recomb  ⭐",         f"{res.total_V_gas_recomb_cc:.4f}", "cc  ← pump into cell", highlight=True)
    rows += _trow("Total Gas @ std",                f"{res.total_V_gas_std_cc:.4f}",    "cc")
    rows += _trow("Total Gas @ std",                f"{res.total_V_gas_std_unit:.6f}",  gas_unit)
    rows += _trow("Cylinder Mix Ratio",             f"{res.cylinder_mix_ratio:.6f}",
                  f"cc gas@recomb / cc {oil_label.lower()}")
    rows += _trow("Cell volume check (oil + gas)",
                  f"{res.V_oil_sep:.4f} + {res.total_V_gas_recomb_cc:.4f} = {res.V_oil_sep + res.total_V_gas_recomb_cc:.4f}",
                  f"cc (target: {v_live:.1f} cc)")

    # ── Verification ──────────────────────────────────────────────────────────
    rows += _tsect("H. VERIFICATION")
    rows += _trow("Sep. GOR (input)",         f"{res.R_total_input:.4f}",  gor_unit)
    if res.oil_source == "stock_tank":
        rows += _trow("STO GOR (input)",      f"{res.R_STO_input:.4f}",   gor_unit)
        rows += _trow("Total effective GOR",  f"{R_total_eff_input:.4f}", gor_unit)
    rows += _trow("GOR back-calculated",
                  f"V_gas_std ({res.total_V_gas_std_cc:.4f} cc) / V_STO ({res.V_oil_STO:.4f} cc)"
                  + (f" / {SCF_STB_TO_CC_CC:.6f}" if res.units == "field" else "")
                  + f" = {res.GOR_check:.4f}", gor_unit)
    rows += _trow("GOR match error",          f"{gor_err_pct:.5f}", "%")

    # ── Bubble point ──────────────────────────────────────────────────────────
    if show_pb:
        rows += _tsect("I. BUBBLE POINT — STANDING (1947)")
        rows += _trow("Formula",
                      "Pb = 18.2 × [(R/γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]")
        rows += _trow("Est. Pb",      f"{Pb_disp:.1f}",              Pb_unit)
        rows += _trow("Range (±15%)", f"{Pb_lo:.0f} – {Pb_hi:.0f}", Pb_unit)
        rows += _trow("γg input",     f"{gamma_g:.3f}")
        rows += _trow("API input",    f"{api_gravity:.1f}",          "°API")
        rows += _trow("T input",      f"{T_for_pb:.1f}",             "°F (reservoir temperature)")

    # ── Unit conversion reference ─────────────────────────────────────────────
    rows += _tsect("J. UNIT CONVERSION REFERENCE")
    rows += _trow("1 scf/STB → cc/cc",    f"{SCF_STB_TO_CC_CC:.6f}", "multiply scf/STB by this")
    rows += _trow("1 cc/cc → scf/STB",    f"{1.0 / SCF_STB_TO_CC_CC:.4f}", "divide cc/cc by factor above")
    rows += _trow("1 bara → psia",         f"{BARA_TO_PSIA:.4f}",    "multiply bara by this")
    rows += _trow("1 psia → bara",         f"{1.0/BARA_TO_PSIA:.6f}", "divide psia by factor above")
    rows += _trow("T(°R) = T(°F) + 459.67",    "add 459.67",  "°F → °R conversion")
    rows += _trow("T(°F) = T(°C) × 9/5 + 32", "multiply × 1.8 + 32", "°C → °F conversion")
    rows += _trow("1 STB",                 "158,987",                "cc")
    rows += _trow("1 scf",                 "28,316.8",               "cc")

    return (
        f'<table class="pvt-table">'
        f'<thead><tr>'
        f'<th>Parameter / Formula</th>'
        f'<th style="text-align:right;">Value</th>'
        f'<th>Unit / Note</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )
