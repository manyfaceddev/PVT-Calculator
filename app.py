"""
PVT Separator Recombination Calculator
Module 1 of the PVT Calculator Suite

Streamlit app — run with:  streamlit run app.py
"""

import streamlit as st
from pvt_calc import (
    RecombinationInputs,
    calculate,
    validate,
    SCF_STB_TO_CC_CC,
    P_STD_PSIA,
    T_STD_R,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PVT Separator Recombination",
    page_icon="🛢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS — professional dark-accent petroleum theme
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ── global ── */
    html, body, [data-testid="stAppViewContainer"] {
        background: #f5f7fa;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    /* ── header banner ── */
    .pvt-header {
        background: linear-gradient(135deg, #1a2b45 0%, #243b5e 60%, #2e5082 100%);
        color: #fff;
        padding: 1.6rem 2rem 1.2rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .pvt-header h1 { margin: 0; font-size: 1.9rem; letter-spacing: 0.5px; }
    .pvt-header p  { margin: 0.3rem 0 0 0; color: #b0c8e8; font-size: 0.95rem; }
    /* ── section cards ── */
    .pvt-card {
        background: #fff;
        border: 1px solid #dde3ea;
        border-left: 4px solid #2e5082;
        border-radius: 8px;
        padding: 1.1rem 1.4rem;
        margin-bottom: 1.2rem;
    }
    .pvt-card h3 {
        color: #1a2b45;
        margin: 0 0 0.8rem 0;
        font-size: 1.05rem;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    /* ── summary box ── */
    .pvt-summary {
        background: linear-gradient(135deg, #1a2b45, #243b5e);
        color: #fff;
        border-radius: 10px;
        padding: 1.4rem 1.8rem;
        margin-bottom: 1.4rem;
    }
    .pvt-summary h2 { color: #7ec8e3; margin: 0 0 0.5rem 0; font-size: 1.1rem; }
    .pvt-summary .charge { font-size: 1.45rem; font-weight: 700; margin: 0.4rem 0; }
    .pvt-summary .sub    { color: #b0c8e8; font-size: 0.9rem; margin-top: 0.6rem; }
    /* ── metric tiles ── */
    .pvt-metrics { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .pvt-metric {
        flex: 1; min-width: 160px;
        background: #f0f4fa;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        text-align: center;
    }
    .pvt-metric .val  { font-size: 1.6rem; font-weight: 700; color: #1a2b45; }
    .pvt-metric .lbl  { font-size: 0.78rem; color: #5a6e85; text-transform: uppercase; letter-spacing: 0.5px; }
    .pvt-metric .unit { font-size: 0.82rem; color: #2e5082; font-weight: 600; }
    /* ── step-by-step ── */
    .pvt-step {
        background: #f8fafc;
        border: 1px solid #dde3ea;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin-bottom: 0.6rem;
        font-family: 'Courier New', monospace;
        font-size: 0.88rem;
        color: #2c3e50;
    }
    .pvt-step .step-label { color: #2e5082; font-weight: 700; font-family: 'Segoe UI', Arial, sans-serif; font-size: 0.82rem; }
    /* ── table ── */
    .pvt-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
    .pvt-table th { background: #1a2b45; color: #fff; padding: 0.5rem 0.9rem; text-align: left; }
    .pvt-table td { padding: 0.45rem 0.9rem; border-bottom: 1px solid #e5eaf0; }
    .pvt-table tr:nth-child(even) td { background: #f4f7fb; }
    /* ── ascii art ── */
    .pvt-ascii {
        background: #1a2b45;
        color: #7ec8e3;
        font-family: 'Courier New', monospace;
        font-size: 0.8rem;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        white-space: pre;
        line-height: 1.45;
    }
    /* ── gor check badge ── */
    .gor-ok  { color: #1a7a4a; font-weight: 700; }
    .gor-warn{ color: #c0392b; font-weight: 700; }
    /* ── sidebar ── */
    [data-testid="stSidebar"] { background: #1a2b45; }
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stSelectbox label { color: #d0dff0 !important; }
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #7ec8e3 !important; }
    /* divider in sidebar */
    [data-testid="stSidebar"] hr { border-color: #2e5082; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="pvt-header">
        <h1>🛢️ PVT Separator Recombination Calculator</h1>
        <p>Module 1 — Separator Fluid Recombination &nbsp;|&nbsp; PVT Calculator Suite</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Input Parameters")
    st.markdown("---")

    units = st.selectbox(
        "Unit System",
        options=["field", "si"],
        format_func=lambda x: "Field  (psia · °F · scf/STB)" if x == "field" else "SI  (bara · °C · sm³/sm³)",
        index=0,
    )

    st.markdown("---")
    st.markdown("### Cell & Oil")

    V_cell = st.number_input(
        "Cell Volume (cc)",
        min_value=1.0, max_value=5000.0, value=300.0, step=10.0,
        help="Total internal volume of the recombination cell in cubic centimetres.",
    )

    oil_fraction = st.slider(
        "Oil Fraction (fraction of cell)",
        min_value=0.40, max_value=0.90, value=0.70, step=0.01,
        help="Fraction of the cell volume to fill with separator liquid. Typical range 0.65–0.80.",
    )

    Bo_sep = st.number_input(
        "Bo at Separator Conditions (res bbl/STB)",
        min_value=0.80, max_value=3.00, value=1.00, step=0.01,
        help="Oil formation volume factor at separator P & T. Usually ~1.0 for separator oil.",
    )

    st.markdown("---")
    st.markdown("### Separator Conditions")

    if units == "field":
        R_sep = st.number_input("GOR (scf/STB)", min_value=0.0, value=850.0, step=10.0)
        P_sep = st.number_input("Separator Pressure (psia)", min_value=0.0, value=815.0, step=5.0)
        T_sep = st.number_input("Separator Temperature (°F)", value=145.0, step=1.0)
    else:
        R_sep = st.number_input("GOR (sm³/sm³)", min_value=0.0, value=151.0, step=1.0)
        P_sep = st.number_input("Separator Pressure (bara)", min_value=0.0, value=56.0, step=0.5)
        T_sep = st.number_input("Separator Temperature (°C)", value=62.8, step=0.5)

    st.markdown("---")
    st.markdown("### Gas Properties")

    Z_sep = st.number_input(
        "Z-factor at Separator (dimensionless)",
        min_value=0.01, max_value=2.00, value=0.855, step=0.001, format="%.3f",
        help="Compressibility factor of separator gas measured in the lab at P_sep, T_sep.",
    )

    st.markdown("---")
    calculate_btn = st.button("Calculate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# ASCII diagram
# ---------------------------------------------------------------------------
DIAGRAM = """\
    SEPARATOR RECOMBINATION CELL
    ─────────────────────────────────────────────

       ┌──────────────────────────────────┐
       │  RECOMBINATION CELL  (V_cell)    │
       │                                  │
       │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │ ← gas headspace
       │  ░░ SEPARATOR GAS (V_gas_sep) ░░ │
       │  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ │
       │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │ ─── oil_fraction
       │  ▓▓ SEPARATOR OIL (V_oil_sep) ▓▓│
       │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
       └──────────────────────────────────┘

     Gas injected at P_sep, T_sep via gas pump
     (or compressed from standard conditions)
    ─────────────────────────────────────────────
     GOR maintained so reservoir fluid is
     reproduced at original separator GOR
"""

# ---------------------------------------------------------------------------
# Calculation & results
# ---------------------------------------------------------------------------
inp = RecombinationInputs(
    V_cell=V_cell,
    R_sep=R_sep,
    P_sep=P_sep,
    T_sep=T_sep,
    Z_sep=Z_sep,
    Bo_sep=Bo_sep,
    oil_fraction=oil_fraction,
    units=units,
)

errors = validate(inp)

if errors:
    for e in errors:
        st.error(f"**Input Error:** {e}")
    st.stop()

# Run calculation (always live; button just acts as explicit trigger)
res = calculate(inp)

# ── unit labels ──────────────────────────────────────────────────────────────
if units == "field":
    gor_unit   = "scf/STB"
    pres_unit  = "psia"
    temp_unit  = "°F"
    gas_unit   = "scf"
    pres_disp  = f"{P_sep:.1f} psia"
    temp_disp  = f"{T_sep:.1f} °F"
else:
    gor_unit   = "sm³/sm³"
    pres_unit  = "bara"
    temp_unit  = "°C"
    gas_unit   = "sm³"
    pres_disp  = f"{P_sep:.2f} bara"
    temp_disp  = f"{T_sep:.1f} °C"

gor_err_pct = abs(res.GOR_check - res.GOR_input) / res.GOR_input * 100 if res.GOR_input else 0

# ===========================================================================
# LAYOUT: two columns — left = diagram + steps | right = results
# ===========================================================================
left_col, right_col = st.columns([1, 1.4], gap="large")

# ── LEFT ────────────────────────────────────────────────────────────────────
with left_col:
    st.markdown(
        f'<div class="pvt-ascii">{DIAGRAM}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Calculation steps ───────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-card"><h3>📐 Calculation Steps</h3></div>',
        unsafe_allow_html=True,
    )

    if units == "field":
        step1_txt = (
            f"GOR conversion: R_cc = {R_sep:.1f} scf/STB "
            f"× 0.178107 = <b>{res.R_cc:.4f} cc/cc</b>"
        )
    else:
        step1_txt = f"GOR (SI already cc/cc ratio): R_cc = <b>{res.R_cc:.4f} cc/cc</b>"

    steps = [
        ("Step 1 — GOR → cc/cc", step1_txt),
        (
            "Step 2 — Separator oil charge",
            f"V_oil_sep = oil_fraction × V_cell = {oil_fraction:.2f} × {V_cell:.1f} = <b>{res.V_oil_sep:.2f} cc</b>",
        ),
        (
            "Step 3 — Stock-tank oil volume",
            f"V_oil_STO = V_oil_sep / Bo_sep = {res.V_oil_sep:.2f} / {Bo_sep:.3f} = <b>{res.V_oil_STO:.2f} cc</b>",
        ),
        (
            "Step 4 — Gas at standard conditions",
            (
                f"V_gas_std = R_cc × V_oil_STO = {res.R_cc:.4f} × {res.V_oil_STO:.2f}"
                f" = <b>{res.V_gas_std_cc:.2f} cc</b>"
                f" = <b>{res.V_gas_std_unit:.5f} {gas_unit}</b>"
            ),
        ),
        (
            "Step 5 — Gas at separator conditions (real-gas law)",
            (
                f"V_gas_sep = V_gas_std × (P_std/P_sep) × (T_sep/T_std) × Z<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.V_gas_std_cc:.2f} "
                f"× ({P_STD_PSIA:.3f}/{res.P_sep_psia:.2f}) "
                f"× ({res.T_sep_R:.2f}/{T_STD_R:.2f}) "
                f"× {Z_sep:.3f}<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{res.V_gas_sep:.2f} cc</b>"
            ),
        ),
        (
            "Step 6 — GOR verification",
            (
                f"GOR_check = V_gas_std / V_oil_STO = "
                f"{res.V_gas_std_cc:.2f} / {res.V_oil_STO:.2f} (cc/cc)"
                f" → {res.GOR_check:.2f} {gor_unit} "
                + (
                    f'<span class="gor-ok">✓ matches input ({gor_err_pct:.3f}% error)</span>'
                    if gor_err_pct < 0.1
                    else f'<span class="gor-warn">⚠ {gor_err_pct:.2f}% deviation</span>'
                )
            ),
        ),
    ]

    for label, body in steps:
        st.markdown(
            f"""<div class="pvt-step">
                <div class="step-label">{label}</div>
                {body}
            </div>""",
            unsafe_allow_html=True,
        )

# ── RIGHT ────────────────────────────────────────────────────────────────────
with right_col:

    # ── Summary charge box ──────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="pvt-summary">
            <h2>CHARGE SUMMARY</h2>
            <div class="charge">
                🟤 {res.V_oil_sep:.2f} cc &nbsp;separator oil
            </div>
            <div class="charge">
                💨 {res.V_gas_std_cc:.2f} cc &nbsp;separator gas
                &nbsp;<span style="font-size:1.1rem; font-weight:400;">({res.V_gas_std_unit:.5f} {gas_unit})</span>
                &nbsp;@ std conditions
            </div>
            <div class="sub">
                → Equivalent to {res.V_gas_sep:.2f} cc at separator conditions
                ({pres_disp}, {temp_disp}, Z = {Z_sep:.3f})
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Metric tiles ────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="pvt-metrics">
            <div class="pvt-metric">
                <div class="val">{res.V_oil_sep:.1f}</div>
                <div class="unit">cc</div>
                <div class="lbl">Separator Oil Charge</div>
            </div>
            <div class="pvt-metric">
                <div class="val">{res.V_oil_STO:.1f}</div>
                <div class="unit">cc</div>
                <div class="lbl">Stock-Tank Oil Equiv.</div>
            </div>
            <div class="pvt-metric">
                <div class="val">{res.V_gas_std_cc:.1f}</div>
                <div class="unit">cc @ std</div>
                <div class="lbl">Gas — Std Conditions</div>
            </div>
            <div class="pvt-metric">
                <div class="val">{res.V_gas_sep:.1f}</div>
                <div class="unit">cc @ sep</div>
                <div class="lbl">Gas — Sep Conditions</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Lab Report Table ────────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-card"><h3>📋 Lab Report — Recombination Data Sheet</h3></div>',
        unsafe_allow_html=True,
    )

    if units == "field":
        temp_std_disp = "60 °F / 519.67 °R"
    else:
        temp_std_disp = "15.56 °C / 60 °F"

    table_rows = [
        # ── Operating conditions ──
        ("SEPARATOR CONDITIONS", "", ""),
        ("Separator Pressure",   pres_disp,                         pres_unit),
        ("Separator Temperature",temp_disp,                         temp_unit),
        ("Z-factor (separator)", f"{Z_sep:.4f}",                   "—"),
        ("Standard Conditions",  f"{P_STD_PSIA} psia / {temp_std_disp}", "—"),
        # ── Inputs ──
        ("INPUT GOR",            f"{R_sep:.2f}",                    gor_unit),
        ("GOR (cc/cc)",          f"{res.R_cc:.6f}",                 "cc/cc"),
        ("Bo at separator",      f"{Bo_sep:.4f}",                   "res vol / STO vol"),
        # ── Cell ──
        ("CELL SETUP", "", ""),
        ("Cell Volume",          f"{V_cell:.2f}",                   "cc"),
        ("Oil Fraction",         f"{oil_fraction:.2f}",             "fraction"),
        # ── Charges ──
        ("CHARGES — LIQUID", "", ""),
        ("Separator Oil to Charge",   f"{res.V_oil_sep:.4f}",       "cc"),
        ("Stock-Tank Oil Equivalent", f"{res.V_oil_STO:.4f}",       "cc"),
        ("CHARGES — GAS", "", ""),
        (f"Gas at Standard Conditions",
                                 f"{res.V_gas_std_cc:.4f}",         "cc"),
        (f"Gas at Standard Conditions",
                                 f"{res.V_gas_std_unit:.6f}",       gas_unit),
        (f"Gas at Separator Conditions",
                                 f"{res.V_gas_sep:.4f}",            "cc"),
        # ── Verification ──
        ("VERIFICATION", "", ""),
        ("Back-calc GOR",        f"{res.GOR_check:.4f}",            gor_unit),
        ("GOR Match Error",      f"{gor_err_pct:.4f}",              "%"),
    ]

    rows_html = ""
    for name, val, unit_lbl in table_rows:
        if val == "" and unit_lbl == "":
            # Section header row
            rows_html += (
                f'<tr><td colspan="3" style="background:#243b5e; color:#7ec8e3;'
                f'font-weight:700; font-size:0.8rem; letter-spacing:0.8px; '
                f'padding:0.4rem 0.9rem;">{name}</td></tr>'
            )
        else:
            rows_html += (
                f"<tr><td>{name}</td>"
                f'<td style="text-align:right; font-weight:600; color:#1a2b45;">{val}</td>'
                f'<td style="color:#5a6e85;">{unit_lbl}</td></tr>'
            )

    st.markdown(
        f"""
        <table class="pvt-table">
            <thead>
                <tr>
                    <th>Parameter</th>
                    <th style="text-align:right;">Value</th>
                    <th>Unit</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

    # ── GOR verification callout ────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if gor_err_pct < 0.01:
        st.success(
            f"GOR verification passed — back-calculated GOR = {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.4f}%)"
        )
    elif gor_err_pct < 0.5:
        st.info(
            f"GOR verification within tolerance — back-calculated GOR = {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.3f}%)"
        )
    else:
        st.error(
            f"GOR mismatch — back-calculated GOR = {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.2f}%) — review inputs."
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <hr style="margin-top:2rem; border-color:#dde3ea;">
    <p style="text-align:center; color:#8fa3b8; font-size:0.8rem;">
        PVT Calculator Suite — Module 1: Separator Recombination &nbsp;|&nbsp;
        Standard conditions: 14.696 psia / 60°F &nbsp;|&nbsp;
        <em>Always verify results with a qualified reservoir engineer before laboratory use.</em>
    </p>
    """,
    unsafe_allow_html=True,
)
