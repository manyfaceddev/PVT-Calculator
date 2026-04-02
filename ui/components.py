"""
ui/components.py — Reusable HTML component builders for the PVT Calculator UI.

Each function returns an HTML string.  Render with:
    st.markdown(component(...), unsafe_allow_html=True)

Keeping HTML construction here keeps page modules clean and makes styling
changes easy to locate.
"""

from pvt.recombination.models import MultiStageResults, StageResult


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
# Hero card (charge instructions)
# ===========================================================================

def hero_card(
    res:        MultiStageResults,
    v_live:     float,
    n_stages:   int,
    stage_labels: list[str],
    gor_unit:   str,
    gas_unit:   str,
    gor_err_pct: float,
) -> str:
    """Full charge-instructions hero card."""
    gor_check_str = (
        f"{res.GOR_check:.1f} {gor_unit} ✓"
        if gor_err_pct < 0.1
        else f"{res.GOR_check:.1f} {gor_unit} ⚠"
    )

    # Per-stage gas rows
    gas_rows = ""
    for sr in res.stage_results:
        pct = f" ({sr.pct_of_total:.0f}% of GOR)" if n_stages > 1 else ""
        gas_rows += (
            f'<div class="charge-row"><div>'
            f'<span class="charge-val">{sr.V_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit">cc gas @ recomb</span>'
            f'<div class="charge-label">Stage {sr.stage_num} ({sr.label})'
            f' · {sr.V_gas_std_cc:,.1f} cc @ std'
            f' · {sr.V_gas_std_unit:.4f} {gas_unit}{pct}</div>'
            f'</div></div>'
        )

    # Total gas row (multi-stage only)
    total_gas_row = ""
    if n_stages > 1:
        total_gas_row = (
            f'<hr class="hero-divider">'
            f'<div class="charge-row"><div>'
            f'<span class="charge-val">{res.total_V_gas_recomb_cc:,.1f}</span>'
            f'<span class="charge-unit">cc total gas @ recomb</span>'
            f'<div class="charge-label">{res.total_V_gas_std_cc:,.1f} cc @ std'
            f' · {res.total_V_gas_std_unit:.4f} {gas_unit} · all stages</div>'
            f'</div></div>'
        )

    oil_pct = 100.0 / (1.0 + res.cylinder_mix_ratio)

    return (
        f'<div class="pvt-hero">'
        f'<div class="hero-title">⚗️ Charge Instructions'
        f' — {v_live:.0f} cc live fluid'
        f' @ {res.T_recomb_F:.0f}°F / {res.P_recomb_psia:.0f} psia</div>'
        f'<div class="charge-row"><div>'
        f'<span class="charge-val">{res.V_oil_sep:,.1f}</span>'
        f'<span class="charge-unit">cc oil</span>'
        f'<div class="charge-label">Separator oil · {stage_labels[-1]}'
        f' · ({oil_pct:.1f}% of live fluid)</div>'
        f'</div></div>'
        f'<hr class="hero-divider">'
        f'{gas_rows}'
        f'{total_gas_row}'
        f'<hr class="hero-divider">'
        f'<div class="charge-row"><div>'
        f'<span class="charge-val">{res.cylinder_mix_ratio:.4f}</span>'
        f'<span class="charge-unit">cc/cc</span>'
        f'<div class="charge-label">Cylinder mix ratio'
        f' — cc gas @ recomb P&amp;T per cc separator oil</div>'
        f'</div></div>'
        f'<hr class="hero-divider">'
        f'<div class="hero-sub">'
        f'GOR: {res.R_total_input:.1f} {gor_unit} &nbsp;·&nbsp;'
        f'Recomb: {res.P_recomb_psia:.0f} psia / {res.T_recomb_F:.0f}°F'
        f' / Z={res.Z_recomb:.3f} &nbsp;·&nbsp;'
        f'GOR check: {gor_check_str}'
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


def metric_cards_row(res: MultiStageResults, gor_unit: str, pb_html: str = "") -> str:
    cards = (
        metric_card(f"{res.V_oil_sep:,.1f}",            "cc oil",        "Oil to Charge",   accent=True)
        + metric_card(f"{res.total_V_gas_recomb_cc:,.1f}", "cc @ recomb", "Gas to Charge",   accent=True)
        + metric_card(f"{res.cylinder_mix_ratio:.4f}",   "cc/cc",         "Mix Ratio")
        + metric_card(f"{res.total_V_gas_std_cc:,.1f}",  "cc @ std",      "Gas @ Std")
        + metric_card(f"{res.R_total_input:,.1f}",        gor_unit,        "Total GOR")
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
    sr:         StageResult,
    P_input:    float,
    T_input:    float,
    pres_unit:  str,
    temp_unit:  str,
    gor_unit:   str,
    gas_unit:   str,
    n_stages:   int,
) -> str:
    pct_str = (
        f'&nbsp;<span style="font-weight:400;color:#4a6080;font-size:0.8rem;">'
        f'({sr.pct_of_total:.1f}% of GOR)</span>'
        if n_stages > 1 else ""
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
    res:         MultiStageResults,
    stages:      list,
    v_live:      float,
    bo_sep:      float,
    n_stages:    int,
    gor_unit:    str,
    pres_unit:   str,
    temp_unit:   str,
    gas_unit:    str,
    gor_err_pct: float,
    show_pb:     bool = False,
    Pb_disp:     float = 0.0,
    Pb_lo:       float = 0.0,
    Pb_hi:       float = 0.0,
    Pb_unit:     str = "",
    gamma_g:     float = 0.0,
    api_gravity: float = 0.0,
    T_for_pb:    float = 0.0,
) -> str:
    rows = ""
    rows += _tsect("SETUP")
    rows += _trow("Live Fluid Volume", f"{v_live:.2f}",  "cc")
    rows += _trow("Bo (separator)",    f"{bo_sep:.4f}",  "res/STO")
    rows += _trow("Stages",            str(n_stages))
    rows += _trow("Units",             res.units)

    rows += _tsect("STANDARD CONDITIONS")
    rows += _trow("P_std", "14.696", "psia")
    rows += _trow("T_std", "60.0 °F / 519.67 °R")

    rows += _tsect("RECOMBINATION CONDITIONS")
    rows += _trow("Pressure",    f"{res.P_recomb_psia:.2f}", "psia")
    rows += _trow("Temperature", f"{res.T_recomb_F:.1f}",    "°F")
    rows += _trow("Z-factor",    f"{res.Z_recomb:.4f}")

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

    rows += _tsect("CHARGE VOLUMES")
    rows += _trow("Separator Oil",      f"{res.V_oil_sep:.4f}",             "cc")
    rows += _trow("STO Oil Equiv.",     f"{res.V_oil_STO:.4f}",             "cc")
    rows += _trow("Total Gas @ recomb", f"{res.total_V_gas_recomb_cc:.4f}", "cc")
    rows += _trow("Total Gas @ std",    f"{res.total_V_gas_std_cc:.4f}",    "cc")
    rows += _trow("Total Gas @ std",    f"{res.total_V_gas_std_unit:.6f}",  gas_unit)
    rows += _trow("Cylinder Mix Ratio", f"{res.cylinder_mix_ratio:.6f}",    "cc gas @ recomb / cc oil")

    rows += _tsect("VERIFICATION")
    rows += _trow("GOR (input)",      f"{res.R_total_input:.4f}", gor_unit)
    rows += _trow("GOR (back-calc.)", f"{res.GOR_check:.4f}",     gor_unit)
    rows += _trow("GOR match error",  f"{gor_err_pct:.5f}",       "%")

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
