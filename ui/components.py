"""
ui/components.py — Reusable HTML component builders for the PVT Calculator UI.

Each function returns an HTML string.  Render with:
    st.markdown(component(...), unsafe_allow_html=True)

Keeping HTML construction here keeps page modules clean and makes styling
changes easy to locate.
"""

from pvt.recombination.models import MultiStageResults, StageResult, SeparatorStage


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


# ===========================================================================
# Volume summary card — ASCII terminal-style, shown at top of page
# ===========================================================================

def volume_summary_card(
    res:               MultiStageResults,
    v_live:            float,
    V_oil_charge:      float,
    p_charge_psia:     float,
    oil_source:        str,
    gor_unit:          str,
    pres_unit:         str,
    gor_err_pct:       float,
    R_total_eff_input: float,
) -> str:
    """Compact monospace box showing all key charge volumes at a glance."""
    W = 67   # inner width (between │ chars, excluding 2-char left pad)
    case_lbl = (
        "Case 1 — Separator Oil + Sep. Gas"
        if oil_source == "separator"
        else "Case 2 — Stock Tank Oil + Sep. Gas"
    )
    hdr_info = (
        f"{v_live:.0f} cc live fluid  ·  "
        f"{res.P_recomb_psia:.0f} {pres_unit} / {res.T_recomb_F:.0f}°F / Z={res.Z_recomb:.3f}"
    )
    gor_sym = "✓" if gor_err_pct < 0.1 else "⚠"

    def ln(s: str = "") -> str:
        # pad to W chars inside │  …  │
        return f"│  {s:<{W}}│"

    def div() -> str:
        return f"├{'─' * (W + 2)}┤"

    oil_label = "STO oil" if oil_source == "stock_tank" else "separator oil"
    sf_line   = f"SF = {res.SF:.4f}  →  V_STO = {res.V_oil_STO:.1f} cc" if oil_source == "separator" else f"V_STO equiv = {res.V_oil_STO:.1f} cc"

    rows = [
        f"┌{'─' * (W + 2)}┐",
        ln(f"CHARGE RECIPE  ·  {case_lbl}"),
        ln(hdr_info),
        div(),
        ln("  OIL  (load first, at oil charging pressure)"),
        ln(f"    Volume to load:     {V_oil_charge:>9.2f} cc   @ {p_charge_psia:.1f} {pres_unit}  ←  CHARGE THIS"),
        ln(f"    Volume at P_recomb: {res.V_oil_sep:>9.2f} cc   @ {res.P_recomb_psia:.0f} {pres_unit}  (after pressure rise)"),
        ln(f"    {sf_line}"),
        div(),
        ln("  GAS  (add at recombination pressure, from gas cylinder)"),
        ln(f"    Volume @ recomb:    {res.total_V_gas_recomb_cc:>9.2f} cc   @ {res.P_recomb_psia:.0f} {pres_unit}  ←  CHARGE THIS"),
        ln(f"    Volume @ std:       {res.total_V_gas_std_cc:>9.2f} cc   ({res.total_V_gas_std_unit:.5f} {gor_unit.split('/')[1] if '/' in gor_unit else 'scf'})"),
        ln(f"    Mix ratio:          {res.cylinder_mix_ratio:>9.4f} cc gas / cc {oil_label} at P_recomb"),
        ln(f"    Total Rp:           {R_total_eff_input:>9.1f} {gor_unit}   GOR check: {res.GOR_check:.1f} {gor_sym}"),
        f"└{'─' * (W + 2)}┘",
    ]
    content = "\n".join(rows)
    return f'<div class="pvt-ascii">{content}</div>'


# ===========================================================================
# Process diagram — well → separator → (stock tank) → cell
# (kept for reference; no longer called from the UI)
# ===========================================================================

def process_diagram(
    oil_source:  str,
    n_stages:    int,
    stage_labels: list[str],
    stages:      list,       # list[SeparatorStage]
    units:       str,
    pres_unit:   str,
    temp_unit:   str,
) -> str:
    """
    Render a process-flow schematic for Case 1 or Case 2.

    Case 1 — Separator Oil + Separator Gas:
      Oil well at reservoir P, T → Separator(s) → oil out the bottom (to cell)
                                               → gas out the top (to gas cylinder, then cell)

    Case 2 — Stock Tank Oil + Separator Gas:
      Oil well at reservoir P, T → Separator(s) → gas out the top (to gas cylinder, then cell)
                                               → oil out the bottom → Stock Tank
                                                 (pressure drop: more gas flashes, oil shrinks)
                                                 → STO out the bottom (to cell)
    """
    # Build separator label(s)
    sep_lines = []
    for i, (label, stage) in enumerate(zip(stage_labels, stages)):
        P_lbl = f"{stage.P:.0f} {pres_unit}"
        T_lbl = f"{stage.T:.0f} {temp_unit}"
        sep_lines.append(f"{label}: {P_lbl} / {T_lbl} / Z={stage.Z:.3f} / GOR={stage.R:.0f}")
    sep_text = "<br>".join(sep_lines)

    # ── Shared node styles ────────────────────────────────────────────────────
    node = (
        'display:inline-block;padding:6px 10px;border-radius:6px;'
        'font-size:0.78rem;font-weight:600;line-height:1.4;text-align:center;'
    )
    well_style  = node + 'background:#0a3d62;color:#fff;min-width:100px;'
    sep_style   = node + 'background:#1a6dad;color:#fff;min-width:140px;'
    tank_style  = node + 'background:#4a6080;color:#fff;min-width:110px;'
    cell_style  = node + 'background:#155724;color:#fff;min-width:120px;'
    gas_style   = node + 'background:#7c5200;color:#fff;min-width:110px;'
    arrow       = '<span style="font-size:1rem;color:#4a6080;margin:0 4px;">→</span>'
    arrow_down  = '<div style="font-size:0.85rem;color:#4a6080;text-align:center;line-height:1;">↓</div>'
    arrow_up    = '<div style="font-size:0.85rem;color:#7c5200;text-align:center;line-height:1;">↑</div>'
    # ── Well node ─────────────────────────────────────────────────────────────
    well_node = f'<span style="{well_style}">🛢️ Oil Well<br><span style="font-weight:400;font-size:0.72rem;">Reservoir P, T</span></span>'

    # ── Separator node ────────────────────────────────────────────────────────
    sep_node = (
        f'<span style="{sep_style}">⚙️ Separator(s)<br>'
        f'<span style="font-weight:400;font-size:0.68rem;">{sep_text}</span></span>'
    )

    # ── Gas cylinder node ─────────────────────────────────────────────────────
    gas_node = f'<span style="{gas_style}">🔵 Gas Cylinder<br><span style="font-weight:400;font-size:0.72rem;">Sep. gas</span></span>'

    # ── Cell node ─────────────────────────────────────────────────────────────
    cell_node = f'<span style="{cell_style}">⚗️ PVT Cell<br><span style="font-weight:400;font-size:0.72rem;">Oil + Gas</span></span>'

    if oil_source == "separator":
        # Case 1: sep oil → directly to cell; sep gas → gas cylinder → cell
        oil_label = "Sep. oil (bottom)"
        gas_label = "Sep. gas (top)"
        diagram_html = (
            f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:4px;">'
            f'{well_node}{arrow}{sep_node}'
            f'</div>'
            f'<div style="display:flex;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-top:4px;">'
            # Gas arm
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
            f'<span style="font-size:0.68rem;color:#7c5200;">⬆ {gas_label}</span>'
            f'{arrow_up}'
            f'{gas_node}'
            f'<span style="font-size:0.68rem;color:#7c5200;">⬇ charged to cell</span>'
            f'{arrow_down}'
            f'</div>'
            # Oil arm
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
            f'<span style="font-size:0.68rem;color:#1a6dad;">⬇ {oil_label}</span>'
            f'{arrow_down}'
            f'</div>'
            # Cell
            f'<div style="display:flex;align-items:center;gap:4px;align-self:center;">'
            f'{arrow}{cell_node}'
            f'</div>'
            f'</div>'
        )
        case_badge = (
            '<span style="background:#e8f4fd;border:1px solid #1a6dad;color:#0a3d62;'
            'padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;">'
            'Case 1 — Separator Oil + Separator Gas</span>'
        )
        note = (
            'Separator oil (from the bottom of the separator) is charged to the PVT cell. '
            'Separator gas (from the top of the separator) is collected in a cylinder and pumped into the cell. '
            'Bo at separator conditions corrects for the difference between separator and stock-tank oil volumes.'
        )
    else:
        # Case 2: sep oil → stock tank (shrinkage + STO gas) → STO oil to cell; sep gas → cylinder → cell
        tank_node = (
            f'<span style="{tank_style}">🏭 Stock Tank<br>'
            f'<span style="font-weight:400;font-size:0.72rem;">P_atm · shrinkage<br>STO gas vented ↑</span></span>'
        )
        diagram_html = (
            f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:4px;margin-bottom:4px;">'
            f'{well_node}{arrow}{sep_node}'
            f'</div>'
            f'<div style="display:flex;align-items:flex-start;flex-wrap:wrap;gap:16px;margin-top:4px;">'
            # Gas arm
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
            f'<span style="font-size:0.68rem;color:#7c5200;">⬆ Sep. gas (top)</span>'
            f'{arrow_up}'
            f'{gas_node}'
            f'<span style="font-size:0.68rem;color:#7c5200;">⬇ all gas to cell</span>'
            f'{arrow_down}'
            f'</div>'
            # Oil → stock tank → STO arm
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:2px;">'
            f'<span style="font-size:0.68rem;color:#4a6080;">⬇ Sep. oil (bottom)</span>'
            f'{arrow_down}'
            f'{tank_node}'
            f'<span style="font-size:0.68rem;color:#4a6080;">⬇ STO oil (to cell)</span>'
            f'{arrow_down}'
            f'</div>'
            # Cell
            f'<div style="display:flex;align-items:center;gap:4px;align-self:center;">'
            f'{arrow}{cell_node}'
            f'</div>'
            f'</div>'
        )
        case_badge = (
            '<span style="background:#fff3e0;border:1px solid #7c5200;color:#7c5200;'
            'padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:600;">'
            'Case 2 — Stock Tank Oil + Separator Gas</span>'
        )
        note = (
            'Separator gas (top of separator) is collected and used as the only gas source for the PVT cell. '
            'Separator oil (bottom of separator) flows to the stock tank at atmospheric pressure: '
            'in this pressure drop the oil further shrinks and releases additional gas (stock tank gas / STO gas), '
            'which is vented or collected separately. '
            'The remaining fully-degassed stock tank oil (STO) is charged to the PVT cell. '
            'Both the separator GOR and the stock tank GOR are accounted for in the total gas charged.'
        )

    return (
        f'<div style="background:#f0f4f8;border:1px solid #c8d8e8;border-radius:8px;'
        f'padding:12px 16px;margin-bottom:12px;">'
        f'<div style="margin-bottom:8px;">{case_badge}</div>'
        f'<div style="margin-bottom:10px;">{diagram_html}</div>'
        f'<div style="font-size:0.75rem;color:#4a6080;line-height:1.5;border-top:1px solid #d0dcea;'
        f'padding-top:6px;">{note}</div>'
        f'</div>'
    )


# ===========================================================================
# Hero card (charge instructions)
# ===========================================================================

def hero_card(
    res:               MultiStageResults,
    v_live:            float,
    p_charge_psia:     float,
    gor_unit:          str,
    gas_unit:          str,
    gor_err_pct:       float,
    R_total_eff_input: float,
    pres_unit:         str,
) -> str:
    """Detailed charge-instructions hero card."""
    gor_check_str = (
        f"{res.GOR_check:.1f} {gor_unit} ✓"
        if gor_err_pct < 0.1
        else f"{res.GOR_check:.1f} {gor_unit} ⚠"
    )
    oil_label = "STO oil" if res.oil_source == "stock_tank" else "separator oil"

    # ── Oil row: volume to load (adjusted for compressibility) ─
    oil_row = (
        f'<div class="charge-row"><div>'
        f'<span class="charge-val" style="color:#7fffb8;">{res.V_oil_charge:,.1f}</span>'
        f'<span class="charge-unit">cc {oil_label}</span>'
        f'<div class="charge-label" style="color:#a0f0c8;font-weight:600;">'
        f'⭐ LOAD at P_charge = {p_charge_psia:.1f} {pres_unit}'
        f'</div>'
        f'</div></div>'
        # STO equivalent (for reference)
        f'<div class="charge-row" style="opacity:0.72;"><div>'
        f'<span class="charge-val" style="font-size:1.2rem;">{res.V_oil_STO:,.1f}</span>'
        f'<span class="charge-unit">cc STO equivalent</span>'
        f'<div class="charge-label">SF = {res.SF:.4f}</div>'
        f'</div></div>'
    )

    # ── Gas rows ──────────────────────────────────────────────────────────────
    gas_rows = ""
    for sr in res.stage_results:
        pct = f" ({sr.pct_of_total:.0f}% of Rp)" if res.oil_source == "stock_tank" else ""
        gas_rows += (
            f'<div class="charge-row"><div>'
            f'<span class="charge-val">{sr.V_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit">cc sep gas @ recomb</span>'
            f'<div class="charge-label">{sr.label}'
            f' · {sr.V_gas_std_cc:,.1f} cc @ std'
            f' · {sr.V_gas_std_unit:.4f} {gas_unit}{pct}</div>'
            f'</div></div>'
        )

    # Flash gas row (Case 2 only)
    sto_gas_row = ""
    if res.oil_source == "stock_tank" and res.FF_cc > 0:
        ff_pct = res.FF_cc / res.Rp_total_cc * 100.0 if res.Rp_total_cc > 0 else 0.0
        sto_gas_row = (
            f'<div class="charge-row"><div>'
            f'<span class="charge-val">{res.V_FF_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit">cc flash gas (FF) @ recomb</span>'
            f'<div class="charge-label">Flash Factor · {res.V_FF_gas_std_cc:,.1f} cc @ std'
            f' · ({ff_pct:.0f}% of Rp)'
            f'<br><em style="font-size:0.72rem;color:#6a7f96;">Loaded from sep. gas cylinder</em></div>'
            f'</div></div>'
        )

    # Case 2 banner
    ff_banner = ""
    if res.oil_source == "stock_tank" and res.FF_cc > 0:
        ff_banner = (
            f'<div style="background:rgba(249,168,37,0.15);border-left:3px solid #f9a825;'
            f'padding:5px 10px;margin:4px 0 8px 0;border-radius:0 4px 4px 0;font-size:0.78rem;color:#ffd060;">'
            f'FF = {res.FF_input:.1f} {gor_unit}'
            f' &nbsp;·&nbsp; Rp = {res.R_total_input:.1f} + {res.FF_input:.1f} = <b>{R_total_eff_input:.1f} {gor_unit}</b>'
            f'</div>'
        )

    return (
        f'<div class="pvt-hero">'
        f'<div class="hero-title">⚗️ Detailed Charge Instructions'
        f' — {v_live:.0f} cc live fluid'
        f' @ {res.T_recomb_F:.0f}°F / {res.P_recomb_psia:.0f} {pres_unit}</div>'
        f'{ff_banner}'
        f'{oil_row}'
        f'<hr class="hero-divider">'
        f'{gas_rows}'
        f'{sto_gas_row}'
        f'<hr class="hero-divider">'
        f'<div class="charge-row"><div>'
        f'<span class="charge-val">{res.cylinder_mix_ratio:.4f}</span>'
        f'<span class="charge-unit">cc/cc</span>'
        f'<div class="charge-label">Cylinder mix ratio — cc gas @ recomb P&amp;T per cc {oil_label} at P_recomb</div>'
        f'</div></div>'
        f'<hr class="hero-divider">'
        f'<div class="hero-sub">'
        f'Rp: {R_total_eff_input:.1f} {gor_unit}'
        + (f' (sep: {res.R_total_input:.1f} + FF: {res.FF_input:.1f})' if res.oil_source == "stock_tank" else '')
        + f' &nbsp;·&nbsp; Recomb: {res.P_recomb_psia:.0f} {pres_unit} / {res.T_recomb_F:.0f}°F / Z={res.Z_recomb:.3f}'
        + f' &nbsp;·&nbsp; GOR check: {gor_check_str}'
        f'</div>'
        f'</div>'
    )


# ===========================================================================
# Metric cards row
# ===========================================================================

def metric_card(value: str, unit: str, label: str, accent: bool = False) -> str:
    cls = "pvt-metric-card accent" if accent else "pvt-metric-card"
    return (
        f'<div class="{cls}">'
        f'<div class="m-val">{value}</div>'
        f'<div class="m-unit">{unit}</div>'
        f'<div class="m-lbl">{label}</div>'
        f'</div>'
    )


def metric_cards_row(
    res:          MultiStageResults,
    gor_unit:     str,
    pb_html:      str = "",
) -> str:
    oil_label = "STO Oil" if res.oil_source == "stock_tank" else "Sep. Oil"
    cards = (
        metric_card(f"{res.V_oil_sep:,.1f}",               "cc  (load this)", oil_label,             accent=True)
        + metric_card(f"{res.total_V_gas_recomb_cc:,.1f}", "cc @ recomb",    "Gas to Charge",        accent=True)
        + metric_card(f"{res.cylinder_mix_ratio:.4f}",     "cc/cc",          "Mix Ratio")
        + metric_card(f"{res.total_V_gas_std_cc:,.1f}",   "cc @ std",       "Total Gas @ Std")
        + metric_card(f"{res.R_total_input:,.1f}",         gor_unit,         "Sep. Stage GOR")
        + (metric_card(f"{res.FF_input:,.1f}", gor_unit, "Flash Factor FF") if res.oil_source == "stock_tank" else "")
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
        f'<div class="pb-range">±15% confidence range:'
        f' {Pb_lo:,.0f} – {Pb_hi:,.0f} {Pb_unit}</div>'
        f'<div class="pb-note">'
        f'Pb = 18.2 × [(R/γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]<br>'
        f'R = {R_for_pb:.0f} scf/STB &nbsp;|&nbsp; γg = {gamma_g:.3f}'
        f' &nbsp;|&nbsp; T = {T_for_pb:.0f} °F &nbsp;|&nbsp; API = {api_gravity:.0f}°<br>'
        f'⚠ Estimate only. Standing (1947) calibrated on California crude data.'
        f'</div>'
        f'</div>'
    )


def bubble_point_metric_card(Pb_disp: float, Pb_unit: str) -> str:
    return metric_card(f"{Pb_disp:,.0f}", Pb_unit, "Est. Bubble Point", accent=True)


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
        f'&nbsp;<span style="font-weight:400;color:#4a6080;font-size:0.8rem;">'
        f'({sr.pct_of_total:.1f}% of total GOR)</span>'
        if R_total_eff_cc > 0 else ""
    )
    return (
        f'<div class="stage-card">'
        f'<div class="sc-title">Stage {sr.stage_num} — {sr.label}{pct_str}</div>'
        f'<div class="sc-row"><span class="sc-lbl">GOR</span>'
        f'<span class="sc-val">{sr.R_input:.1f} {gor_unit}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Sep. P / T / Z</span>'
        f'<span class="sc-val">{P_input:.1f} {pres_unit}'
        f' · {T_input:.1f} {temp_unit} · {sr.Z:.3f}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ std cond.</span>'
        f'<span class="sc-val">{sr.V_gas_std_cc:,.2f} cc'
        f' &nbsp;({sr.V_gas_std_unit:.5f} {gas_unit})</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ sep cond.</span>'
        f'<span class="sc-val">{sr.V_gas_sep:,.2f} cc</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ recomb cond.</span>'
        f'<span class="sc-val" style="color:#1a6dad;font-size:1rem;">'
        f'{sr.V_gas_recomb_cc:,.2f} cc</span></div>'
        f'</div>'
    )


# ===========================================================================
# Stock tank flash gas card (Case 2)
# ===========================================================================

def sto_gas_card(res: MultiStageResults, gor_unit: str, gas_unit: str) -> str:
    ff_pct = (
        res.FF_cc / res.Rp_total_cc * 100.0
        if res.Rp_total_cc > 0 else 0.0
    )
    return (
        f'<div class="stage-card" style="border-left-color:#f9a825;">'
        f'<div class="sc-title">Flash Factor Gas (FF) — Case 2'
        f'&nbsp;<span style="font-weight:400;color:#4a6080;font-size:0.8rem;">'
        f'({ff_pct:.1f}% of total Rp)</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Flash Factor FF</span>'
        f'<span class="sc-val">{res.FF_input:.1f} {gor_unit}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">FF (cc/cc)</span>'
        f'<span class="sc-val">{res.FF_cc:.6f}'
        f'&nbsp;<span style="font-size:0.75rem;color:#6a7f96;">cc gas std / cc STO</span></span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ std cond.</span>'
        f'<span class="sc-val">{res.V_FF_gas_std_cc:,.2f} cc'
        f' &nbsp;({res.V_FF_gas_std_unit:.5f} {gas_unit})</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ recomb cond.</span>'
        f'<span class="sc-val" style="color:#f9a825;font-size:1rem;">'
        f'{res.V_FF_gas_recomb_cc:,.2f} cc</span></div>'
        f'<div class="sc-row" style="font-size:0.73rem;color:#6a7f96;">'
        f'<span class="sc-lbl">Note</span>'
        f'<span class="sc-val">Loaded from separator gas cylinder (lab convention)</span></div>'
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


# ===========================================================================
# Lab report table helpers
# ===========================================================================

def _trow(name: str, val: str, unit_lbl: str = "") -> str:
    return (
        f"<tr><td>{name}</td>"
        f'<td style="text-align:right;font-weight:600;color:#0a3d62;">{val}</td>'
        f'<td style="color:#6a7f96;font-size:0.78rem;">{unit_lbl}</td></tr>'
    )


def _tsect(title: str) -> str:
    return f'<tr class="tbl-section"><td colspan="3">{title}</td></tr>'


def lab_report_table(
    res:               MultiStageResults,
    stages:            list,
    v_live:            float,
    sf:                float,
    n_stages:          int,
    gor_unit:          str,
    pres_unit:         str,
    temp_unit:         str,
    gas_unit:          str,
    gor_err_pct:       float,
    R_total_eff_input: float = 0.0,
    p_charge_psia:     float = 14.696,
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

    rows += _tsect("SETUP")
    rows += _trow("Oil Source",           "Separator Oil" if res.oil_source == "separator" else "Stock Tank Oil (STO)")
    rows += _trow("Live Fluid Volume",    f"{v_live:.2f}",  "cc")
    rows += _trow("SF (Shrinkage Factor)", f"{sf:.4f}",     "V_STO / V_sep_oil  (Carlsen & Whitson 2020)")
    rows += _trow("Units",                res.units)

    rows += _tsect("STANDARD CONDITIONS")
    rows += _trow("P_std", "14.696", "psia")
    rows += _trow("T_std", "60.0 °F / 519.67 °R")

    rows += _tsect("RECOMBINATION CONDITIONS")
    rows += _trow("Pressure",    f"{res.P_recomb_psia:.2f}", "psia")
    rows += _trow("Temperature", f"{res.T_recomb_F:.1f}",    "°F")
    rows += _trow("Z-factor",    f"{res.Z_recomb:.4f}")

    oil_label = "STO Oil" if res.oil_source == "stock_tank" else "Separator Oil"
    rows += _tsect("OIL CHARGING CONDITIONS")
    rows += _trow("Oil Charging Pressure",    f"{p_charge_psia:.2f}",     "psia")
    rows += _trow(f"{oil_label} to Load ⭐",  f"{res.V_oil_charge:.4f}",  "cc  ← charge this volume at P_charge")
    rows += _trow("STO Oil Equivalent",       f"{res.V_oil_STO:.4f}",     "cc")

    for sr in res.stage_results:
        p_in = stages[sr.stage_num - 1].P
        t_in = stages[sr.stage_num - 1].T
        rows += _tsect(f"STAGE {sr.stage_num} — {sr.label}")
        rows += _trow("GOR",              f"{sr.R_input:.2f}",         gor_unit)
        rows += _trow("Sep. Pressure",    f"{p_in:.2f}",               pres_unit)
        rows += _trow("Sep. Temperature", f"{t_in:.2f}",               temp_unit)
        rows += _trow("Sep. Z-factor",    f"{sr.Z:.4f}")
        rows += _trow("GOR (cc/cc)",      f"{sr.R_cc:.6f}",            "cc/cc")
        rows += _trow("Gas @ std",        f"{sr.V_gas_std_cc:.4f}",    "cc")
        rows += _trow("Gas @ std",        f"{sr.V_gas_std_unit:.6f}",  gas_unit)
        rows += _trow("Gas @ sep cond.",  f"{sr.V_gas_sep:.4f}",       "cc")
        rows += _trow("Gas @ recomb",     f"{sr.V_gas_recomb_cc:.4f}", "cc")
        rows += _trow("% of GOR",         f"{sr.pct_of_total:.2f}",    "%")

    if res.oil_source == "stock_tank":
        rows += _tsect("FLASH FACTOR (Case 2)")
        rows += _trow("Flash Factor FF",    f"{res.FF_input:.2f}",          gor_unit)
        rows += _trow("Flash Factor FF",    f"{res.FF_cc:.6f}",             "cc/cc")
        rows += _trow("FF Gas @ std",       f"{res.V_FF_gas_std_cc:.4f}",   "cc")
        rows += _trow("FF Gas @ std",       f"{res.V_FF_gas_std_unit:.6f}", gas_unit)
        rows += _trow("FF Gas @ recomb",    f"{res.V_FF_gas_recomb_cc:.4f}", "cc")

    rows += _tsect("CHARGE VOLUMES")
    rows += _trow(f"{oil_label} at P_charge ⭐", f"{res.V_oil_charge:.4f}",       "cc  ← charge this amount")
    rows += _trow(f"{oil_label} at P_recomb",   f"{res.V_oil_sep:.4f}",          "cc  (after pressure rise)")
    rows += _trow("STO Oil Equiv.",              f"{res.V_oil_STO:.4f}",           "cc")
    rows += _trow("Total Gas @ recomb",          f"{res.total_V_gas_recomb_cc:.4f}", "cc")
    rows += _trow("Total Gas @ std",             f"{res.total_V_gas_std_cc:.4f}",  "cc")
    rows += _trow("Total Gas @ std",             f"{res.total_V_gas_std_unit:.6f}", gas_unit)
    rows += _trow("Cylinder Mix Ratio",          f"{res.cylinder_mix_ratio:.6f}",  f"cc gas @ recomb / cc {oil_label.lower()}")

    rows += _tsect("VERIFICATION")
    rows += _trow("Sep. GOR (input)",       f"{res.R_total_input:.4f}",    gor_unit)
    if res.oil_source == "stock_tank":
        rows += _trow("Flash Factor FF",    f"{res.FF_input:.4f}",        gor_unit)
        rows += _trow("Total Rp (sep+FF)",  f"{R_total_eff_input:.4f}",   gor_unit)
    rows += _trow("GOR (back-calc.)",       f"{res.GOR_check:.4f}",        gor_unit)
    rows += _trow("GOR match error",        f"{gor_err_pct:.5f}",          "%")

    if show_pb:
        rows += _tsect("BUBBLE POINT (Standing 1947)")
        rows += _trow("Est. Pb",      f"{Pb_disp:.1f}",              Pb_unit)
        rows += _trow("Range (±15%)", f"{Pb_lo:.0f} – {Pb_hi:.0f}", Pb_unit)
        rows += _trow("γg",           f"{gamma_g:.3f}")
        rows += _trow("API",          f"{api_gravity:.1f}",          "°API")
        rows += _trow("T (for Pb)",   f"{T_for_pb:.1f}",             "°F")

    return (
        f'<table class="pvt-table">'
        f'<thead><tr>'
        f'<th>Parameter</th>'
        f'<th style="text-align:right;">Value</th>'
        f'<th>Unit</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody>'
        f'</table>'
    )
