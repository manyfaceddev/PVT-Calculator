"""
PVT Separator Recombination Calculator
Module 1 of the PVT Calculator Suite — mobile-optimised UI

Run locally:    streamlit run app.py
Run on network: ./launch.sh
"""

import streamlit as st
from pvt_calc import (
    SeparatorStage,
    validate_multistage,
    calculate_multistage,
    standing_bubble_point,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
    P_STD_PSIA,
    T_STD_R,
)

# ---------------------------------------------------------------------------
# Page config — centered layout works best on mobile
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="PVT Recombination",
    page_icon="🛢️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS — mobile-first, large touch targets, readable cards
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* ── global ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #f0f4f8;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* ── header ── */
.pvt-header {
    background: linear-gradient(135deg, #0a1628 0%, #1a3a6b 100%);
    color: #fff;
    padding: 1.2rem 1.4rem 1rem 1.4rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
}
.pvt-header h1 {
    margin: 0;
    font-size: 1.35rem;
    letter-spacing: 0.3px;
    line-height: 1.3;
}
.pvt-header p {
    margin: 0.3rem 0 0 0;
    color: #90b8e8;
    font-size: 0.82rem;
}

/* ── charge summary — hero card ── */
.pvt-hero {
    background: linear-gradient(135deg, #0a3d62, #1a6dad);
    color: #fff;
    border-radius: 14px;
    padding: 1.4rem 1.4rem 1.2rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
}
.pvt-hero .hero-title {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #90c8f0;
    margin-bottom: 0.8rem;
}
.pvt-hero .charge-row {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin: 0.55rem 0;
}
.pvt-hero .charge-val {
    font-size: 2rem;
    font-weight: 800;
    color: #fff;
    line-height: 1;
}
.pvt-hero .charge-unit {
    font-size: 1rem;
    color: #b0d8f8;
    font-weight: 400;
}
.pvt-hero .charge-label {
    font-size: 0.82rem;
    color: #90b8e0;
    margin-top: -0.1rem;
}
.pvt-hero .hero-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.15);
    margin: 0.9rem 0;
}
.pvt-hero .hero-sub {
    font-size: 0.8rem;
    color: #90b8e0;
}

/* ── metric cards (stacked, full-width on mobile) ── */
.pvt-card-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    margin-bottom: 1rem;
}
.pvt-metric-card {
    background: #fff;
    border-radius: 10px;
    padding: 0.9rem 1rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.pvt-metric-card .m-val  { font-size: 1.55rem; font-weight: 700; color: #0a3d62; line-height: 1.1; }
.pvt-metric-card .m-unit { font-size: 0.78rem; color: #1a6dad; font-weight: 600; }
.pvt-metric-card .m-lbl  { font-size: 0.72rem; color: #6a7f96; text-transform: uppercase; letter-spacing: 0.4px; margin-top: 0.2rem; }
.pvt-metric-card.accent  { background: #e8f2fd; border: 2px solid #1a6dad; }

/* ── bubble point card ── */
.pb-card {
    background: #fffbea;
    border: 1px solid #f0c040;
    border-left: 5px solid #e8900a;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
.pb-card .pb-title  { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.8px; color: #7a5000; margin-bottom: 0.5rem; }
.pb-card .pb-val    { font-size: 2rem; font-weight: 800; color: #7a3800; line-height: 1.1; }
.pb-card .pb-unit   { font-size: 1rem; font-weight: 400; color: #9a6010; }
.pb-card .pb-range  { font-size: 0.82rem; color: #9a7010; margin-top: 0.3rem; }
.pb-card .pb-note   { font-size: 0.75rem; color: #aa8020; margin-top: 0.6rem; font-style: italic; line-height: 1.45; }

/* ── section heading ── */
.pvt-section {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #4a6080;
    margin: 1.2rem 0 0.5rem 0;
    font-weight: 700;
}

/* ── stage breakdown card ── */
.stage-card {
    background: #fff;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.7rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-left: 4px solid #1a6dad;
}
.stage-card .sc-title { font-size: 0.88rem; font-weight: 700; color: #0a3d62; margin-bottom: 0.5rem; }
.stage-card .sc-row   { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.15rem 0; }
.stage-card .sc-lbl   { color: #6a7f96; }
.stage-card .sc-val   { font-weight: 600; color: #1a2b45; }

/* ── step blocks (inside expander) ── */
.pvt-step {
    background: #f4f8fc;
    border: 1px solid #d0dcea;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.55rem;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: #2c3e50;
    line-height: 1.5;
}
.pvt-step .step-label {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 0.75rem;
    font-weight: 700;
    color: #1a6dad;
    margin-bottom: 0.25rem;
}

/* ── lab report table ── */
.pvt-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.pvt-table th { background: #0a3d62; color: #fff; padding: 0.5rem 0.8rem; text-align: left; }
.pvt-table td { padding: 0.4rem 0.8rem; border-bottom: 1px solid #e0e8f0; }
.pvt-table tr:nth-child(even) td { background: #f4f8fc; }
.pvt-table .tbl-section td {
    background: #1a3a6b; color: #90c8f0;
    font-weight: 700; font-size: 0.72rem; letter-spacing: 0.8px;
    padding: 0.35rem 0.8rem;
}

/* ── ASCII diagram ── */
.pvt-ascii {
    background: #0a1628;
    color: #60b0e0;
    font-family: 'Courier New', monospace;
    font-size: 0.72rem;
    padding: 0.9rem 1rem;
    border-radius: 8px;
    white-space: pre;
    line-height: 1.5;
    overflow-x: auto;
}

/* ── gor check ── */
.gor-ok   { color: #147a3a; font-weight: 700; }
.gor-warn { color: #b03010; font-weight: 700; }

/* ── sidebar ── */
[data-testid="stSidebar"] { background: #0a1628; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label { color: #c0d8f0 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #60b0e0 !important; }
[data-testid="stSidebar"] hr { border-color: #1a3a6b; }

/* ── make number inputs easier to tap on mobile ── */
input[type="number"] { font-size: 1rem !important; min-height: 44px; }
div[data-testid="stNumberInput"] input { font-size: 1rem !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pre-loaded examples (field units)
# ---------------------------------------------------------------------------
EXAMPLES: dict[str, dict | None] = {
    "— select an example —": None,
    "Light oil, North Sea (high GOR)": {
        "units": "field", "n_stages": 1,
        "v_cell": 300.0, "oil_fraction": 0.72, "bo_sep": 1.00,
        "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
        "r_sep_2":  50.0, "p_sep_2":  65.0, "t_sep_2": 100.0, "z_sep_2": 0.977,
        "r_sep_3":  20.0, "p_sep_3":  35.0, "t_sep_3":  75.0, "z_sep_3": 0.991,
        "show_pb": True, "gamma_g": 0.72, "api_gravity": 42.0, "t_res": 210.0,
    },
    "Medium oil, Middle East (moderate GOR)": {
        "units": "field", "n_stages": 1,
        "v_cell": 250.0, "oil_fraction": 0.70, "bo_sep": 1.01,
        "r_sep_1": 380.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
        "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  90.0, "z_sep_2": 0.986,
        "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  75.0, "z_sep_3": 0.994,
        "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
    },
    "Heavy oil, Offshore (low GOR)": {
        "units": "field", "n_stages": 1,
        "v_cell": 200.0, "oil_fraction": 0.68, "bo_sep": 1.03,
        "r_sep_1": 100.0, "p_sep_1":  60.0, "t_sep_1": 100.0, "z_sep_1": 0.972,
        "r_sep_2":  10.0, "p_sep_2":  20.0, "t_sep_2":  75.0, "z_sep_2": 0.990,
        "r_sep_3":   5.0, "p_sep_3":  10.0, "t_sep_3":  60.0, "z_sep_3": 0.995,
        "show_pb": True, "gamma_g": 0.82, "api_gravity": 22.0, "t_res": 155.0,
    },
}

STAGE_LABELS = {
    1: ["Separator"],
    2: ["HP Separator", "LP Separator"],
    3: ["HP Separator", "MP Separator", "LP Separator"],
}

DIAGRAM_1 = """\
  ┌────────────┐  gas ──────────────────►┐
  │ SEPARATOR  │                 ┌───────▼──────┐
  │ P1, T1, Z1 │                 │  CELL        │
  └─────┬──────┘  oil ──────────►│  ░░ GAS ░░░ │
        └────────────────────────►  ▓▓ OIL ▓▓▓ │
                                 └──────────────┘"""

DIAGRAM_2 = """\
  ┌──────────┐  G1 ─────────────────────►┐
  │ STAGE 1  │                   ┌────────▼──────┐
  │ HP Sep   │         ┌──────┐  │  CELL         │
  └────┬─────┘  oil   │STAGE2│G2►  ░░ G1+G2 ░░ │
       └─────────────►│LP Sep│  │  ▓▓▓ OIL ▓▓▓ │
                       └──────┘  └───────────────┘"""

DIAGRAM_3 = """\
  ┌──────┐G1►┐   ┌──────┐G2►┤   ┌──────┐G3►┤
  │ HP   │   │   │  MP  │   │   │  LP  │   │  ┌────────────┐
  │ Sep  │oil└──►│  Sep │oil└──►│  Sep │oil└─►│ CELL       │
  └──────┘       └──────┘       └──┬───┘      │ ░ G1+G2+G3 │
                                    └─────────►│ ▓▓▓ OIL ▓▓ │
                                              └────────────┘"""

DIAGRAMS = {1: DIAGRAM_1, 2: DIAGRAM_2, 3: DIAGRAM_3}

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
SS_DEFAULTS: dict = {
    "units": "field", "_units_prev": "field",
    "n_stages": 1, "v_cell": 300.0, "oil_fraction": 0.70, "bo_sep": 1.00,
    "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
    "r_sep_2":  50.0, "p_sep_2":  65.0, "t_sep_2": 100.0, "z_sep_2": 0.977,
    "r_sep_3":  20.0, "p_sep_3":  35.0, "t_sep_3":  75.0, "z_sep_3": 0.991,
    "show_pb": True, "gamma_g": 0.72, "api_gravity": 42.0, "t_res": 210.0,
    "example_sel": "— select an example —",
}
for k, v in SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def _on_example_change() -> None:
    ex = EXAMPLES.get(st.session_state["example_sel"])
    if ex is None:
        return
    for k, v in ex.items():
        st.session_state[k] = v
    st.session_state["_units_prev"] = "field"


def _on_units_change() -> None:
    cur  = st.session_state["units"]
    prev = st.session_state.get("_units_prev", cur)
    if cur == prev:
        return
    to_si    = (prev == "field" and cur == "si")
    to_field = (prev == "si"    and cur == "field")
    for n in (1, 2, 3):
        p = st.session_state.get(f"p_sep_{n}", 0.0)
        t = st.session_state.get(f"t_sep_{n}", 0.0)
        r = st.session_state.get(f"r_sep_{n}", 0.0)
        if to_si:
            st.session_state[f"p_sep_{n}"] = round(p / BARA_TO_PSIA,    2)
            st.session_state[f"t_sep_{n}"] = round((t - 32.0) * 5/9,    1)
            st.session_state[f"r_sep_{n}"] = round(r * SCF_STB_TO_CC_CC, 2)
        elif to_field:
            st.session_state[f"p_sep_{n}"] = round(p * BARA_TO_PSIA,    1)
            st.session_state[f"t_sep_{n}"] = round(t * 9/5 + 32.0,      1)
            st.session_state[f"r_sep_{n}"] = round(r / SCF_STB_TO_CC_CC, 1)
    tr = st.session_state.get("t_res", 200.0)
    if to_si:
        st.session_state["t_res"] = round((tr - 32.0) * 5/9, 1)
    elif to_field:
        st.session_state["t_res"] = round(tr * 9/5 + 32.0, 1)
    st.session_state["_units_prev"] = cur

# ---------------------------------------------------------------------------
# Sidebar — all inputs
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Inputs")
    st.markdown("---")

    st.markdown("### 📂 Load Example")
    st.selectbox(
        "Example", options=list(EXAMPLES.keys()),
        key="example_sel", on_change=_on_example_change,
        label_visibility="collapsed",
    )
    st.markdown("---")

    st.selectbox(
        "Unit System",
        options=["field", "si"],
        format_func=lambda x: "Field  (psia · °F · scf/STB)" if x == "field" else "SI  (bara · °C · sm³/sm³)",
        key="units", on_change=_on_units_change,
    )
    st.radio(
        "Separator Stages", options=[1, 2, 3], horizontal=True, key="n_stages",
    )
    st.markdown("---")

    st.markdown("### 🛢️ Cell & Oil")
    st.number_input("Cell Volume (cc)", min_value=1.0, max_value=5000.0, step=10.0, key="v_cell")
    st.slider("Oil Fraction", min_value=0.40, max_value=0.90, step=0.01, key="oil_fraction",
              help="Fraction of cell to fill with separator oil (0.65–0.80 typical)")
    st.number_input("Bo at Separator (res vol/STO vol)", min_value=0.80, max_value=3.00,
                    step=0.01, key="bo_sep")
    st.markdown("---")

    units    = st.session_state["units"]
    n_stages = st.session_state["n_stages"]
    labels   = STAGE_LABELS[n_stages]

    gor_lbl  = "GOR (scf/STB)"    if units == "field" else "GOR (sm³/sm³)"
    pres_lbl = "Pressure (psia)"  if units == "field" else "Pressure (bara)"
    temp_lbl = "Temperature (°F)" if units == "field" else "Temperature (°C)"

    for n in range(1, n_stages + 1):
        st.markdown(f"### Stage {n} — {labels[n-1]}")
        st.number_input(gor_lbl,  min_value=0.1,
                        step=10.0 if units == "field" else 0.5, key=f"r_sep_{n}")
        st.number_input(pres_lbl, min_value=0.1,
                        step=5.0  if units == "field" else 0.2, key=f"p_sep_{n}")
        st.number_input(temp_lbl, step=1.0, key=f"t_sep_{n}")
        st.number_input("Z-factor", min_value=0.01, max_value=2.00,
                        step=0.001, format="%.3f", key=f"z_sep_{n}",
                        help="Compressibility factor at separator conditions")
        if n < n_stages:
            st.markdown("---")

    st.markdown("---")
    with st.expander("🔴 Bubble Point (Standing 1947)", expanded=False):
        st.checkbox("Enable Pb estimate", key="show_pb")
        if st.session_state["show_pb"]:
            st.number_input("Gas Specific Gravity γg (air=1.0)",
                            min_value=0.50, max_value=1.80, step=0.01, format="%.3f",
                            key="gamma_g")
            st.number_input("API Gravity (°API)",
                            min_value=5.0, max_value=60.0, step=0.5, key="api_gravity")
            t_res_lbl = "Reservoir Temperature (°F)" if units == "field" else "Reservoir Temperature (°C)"
            st.number_input(t_res_lbl, step=1.0, key="t_res",
                            help="Use reservoir temperature, not separator temperature")

    st.markdown("---")
    st.button("Calculate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Read session state
# ---------------------------------------------------------------------------
units        = st.session_state["units"]
n_stages     = st.session_state["n_stages"]
v_cell       = st.session_state["v_cell"]
oil_fraction = st.session_state["oil_fraction"]
bo_sep       = st.session_state["bo_sep"]
show_pb      = st.session_state["show_pb"]
gamma_g      = st.session_state.get("gamma_g",     0.72)
api_gravity  = st.session_state.get("api_gravity", 40.0)
t_res_raw    = st.session_state.get("t_res",       200.0)
labels       = STAGE_LABELS[n_stages]

stages = [
    SeparatorStage(
        R=st.session_state[f"r_sep_{n}"],
        P=st.session_state[f"p_sep_{n}"],
        T=st.session_state[f"t_sep_{n}"],
        Z=st.session_state[f"z_sep_{n}"],
        label=labels[n - 1],
    )
    for n in range(1, n_stages + 1)
]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
errors = validate_multistage(stages, v_cell, bo_sep, oil_fraction, units)
if errors:
    st.markdown("""
    <div class="pvt-header">
        <h1>🛢️ PVT Recombination</h1>
        <p>Module 1 — Separator Fluid Recombination</p>
    </div>
    """, unsafe_allow_html=True)
    for e in errors:
        st.error(f"**Input error:** {e}")
    st.info("Open the sidebar (☰) to fix the inputs.")
    st.stop()

# ---------------------------------------------------------------------------
# Calculate
# ---------------------------------------------------------------------------
res = calculate_multistage(stages, v_cell, bo_sep, oil_fraction, units)

if units == "field":
    gor_unit  = "scf/STB"
    pres_unit = "psia"
    temp_unit = "°F"
    gas_unit  = "scf"
else:
    gor_unit  = "sm³/sm³"
    pres_unit = "bara"
    temp_unit = "°C"
    gas_unit  = "sm³"

gor_err_pct = (
    abs(res.GOR_check - res.R_total_input) / res.R_total_input * 100
    if res.R_total_input > 0 else 0.0
)

# Pb
Pb_disp = Pb_lo = Pb_hi = T_for_pb = R_for_pb = 0.0
Pb_unit = ""
if show_pb:
    if units == "field":
        R_for_pb = res.R_total_input
        T_for_pb = t_res_raw
    else:
        R_for_pb = res.R_total_input / SCF_STB_TO_CC_CC
        T_for_pb = t_res_raw * 9/5 + 32.0
    Pb_psia  = standing_bubble_point(R_for_pb, gamma_g, T_for_pb, api_gravity)
    Pb_disp  = Pb_psia if units == "field" else Pb_psia / BARA_TO_PSIA
    Pb_unit  = "psia" if units == "field" else "bara"
    Pb_lo    = Pb_disp * 0.85
    Pb_hi    = Pb_disp * 1.15

# ===========================================================================
# MAIN CONTENT — stacked vertically, mobile-first
# ===========================================================================

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="pvt-header">
    <h1>🛢️ PVT Recombination</h1>
    <p>Module 1 — Separator Fluid Recombination &nbsp;|&nbsp; Open ☰ for inputs</p>
</div>
""", unsafe_allow_html=True)

# ── HERO — Charge Summary ────────────────────────────────────────────────────
gas_rows_html = ""
for sr in res.stage_results:
    pct = f" ({sr.pct_of_total:.0f}% of GOR)" if n_stages > 1 else ""
    gas_rows_html += (
        f'<div class="charge-row"><div>'
        f'<span class="charge-val">{sr.V_gas_std_cc:,.1f}</span>'
        f'<span class="charge-unit">cc gas</span>'
        f'<div class="charge-label">Stage {sr.stage_num} ({sr.label})'
        f' · {sr.V_gas_std_unit:.4f} {gas_unit} · std cond.'
        f' · {sr.V_gas_sep:.1f} cc @ sep cond.{pct}</div>'
        f'</div></div>'
    )

total_gas_row = ""
if n_stages > 1:
    total_gas_row = (
        f'<hr class="hero-divider">'
        f'<div class="charge-row"><div>'
        f'<span class="charge-val">{res.total_V_gas_std_cc:,.1f}</span>'
        f'<span class="charge-unit">cc total gas</span>'
        f'<div class="charge-label">{res.total_V_gas_std_unit:.4f} {gas_unit}'
        f' · all stages combined · std cond.</div>'
        f'</div></div>'
    )

gor_check_str = f"{res.GOR_check:.1f} {gor_unit} ✓" if gor_err_pct < 0.1 else f"{res.GOR_check:.1f} {gor_unit} ⚠"

st.markdown(f"""
<div class="pvt-hero">
    <div class="hero-title">⚗️ Charge Instructions</div>
    <div class="charge-row">
        <div>
            <span class="charge-val">{res.V_oil_sep:,.1f}</span>
            <span class="charge-unit">cc oil</span>
            <div class="charge-label">Separator oil to charge · {labels[-1]}</div>
        </div>
    </div>
    <hr class="hero-divider">
    {gas_rows_html}
    {total_gas_row}
    <hr class="hero-divider">
    <div class="hero-sub">
        GOR: {res.R_total_input:.1f} {gor_unit} &nbsp;·&nbsp;
        Cell: {v_cell:.0f} cc &nbsp;·&nbsp;
        Oil fill: {oil_fraction*100:.0f}% &nbsp;·&nbsp;
        GOR check: {gor_check_str}
    </div>
</div>
""", unsafe_allow_html=True)

# ── Metric cards ─────────────────────────────────────────────────────────────
pb_card_html = ""
if show_pb:
    pb_card_html = f"""
    <div class="pvt-metric-card accent">
        <div class="m-val">{Pb_disp:,.0f}</div>
        <div class="m-unit">{Pb_unit}</div>
        <div class="m-lbl">Est. Bubble Point</div>
    </div>"""

st.markdown(f"""
<div class="pvt-card-row">
    <div class="pvt-metric-card">
        <div class="m-val">{res.V_oil_sep:,.1f}</div>
        <div class="m-unit">cc</div>
        <div class="m-lbl">Sep. Oil Charge</div>
    </div>
    <div class="pvt-metric-card">
        <div class="m-val">{res.V_oil_STO:,.1f}</div>
        <div class="m-unit">cc</div>
        <div class="m-lbl">STO Oil Equiv.</div>
    </div>
    <div class="pvt-metric-card">
        <div class="m-val">{res.total_V_gas_std_cc:,.1f}</div>
        <div class="m-unit">cc @ std</div>
        <div class="m-lbl">Total Gas</div>
    </div>
    <div class="pvt-metric-card">
        <div class="m-val">{res.R_total_input:,.1f}</div>
        <div class="m-unit">{gor_unit}</div>
        <div class="m-lbl">Total GOR</div>
    </div>
    {pb_card_html}
</div>
""", unsafe_allow_html=True)

# ── Bubble point card ────────────────────────────────────────────────────────
if show_pb:
    st.markdown(f"""
    <div class="pb-card">
        <div class="pb-title">🔴 Bubble Point Estimate — Standing (1947)</div>
        <div>
            <span class="pb-val">{Pb_disp:,.0f}</span>
            <span class="pb-unit"> {Pb_unit}</span>
        </div>
        <div class="pb-range">±15% confidence range: {Pb_lo:,.0f} – {Pb_hi:,.0f} {Pb_unit}</div>
        <div class="pb-note">
            Pb = 18.2 × [(R/γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]<br>
            R = {R_for_pb:.0f} scf/STB &nbsp;|&nbsp; γg = {gamma_g:.3f} &nbsp;|&nbsp;
            T = {T_for_pb:.0f} °F &nbsp;|&nbsp; API = {api_gravity:.0f}°<br>
            ⚠ Estimate only. Standing (1947) calibrated on California crude data.
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Per-stage breakdown ───────────────────────────────────────────────────────
st.markdown('<div class="pvt-section">Separator Conditions &amp; Gas Volumes</div>', unsafe_allow_html=True)
for sr in res.stage_results:
    p_disp = f"{stages[sr.stage_num-1].P:.1f} {pres_unit}"
    t_disp = f"{stages[sr.stage_num-1].T:.1f} {temp_unit}"
    pct_str = f'&nbsp;<span style="font-weight:400; color:#4a6080; font-size:0.8rem;">({sr.pct_of_total:.1f}% of GOR)</span>' if n_stages > 1 else ""
    st.markdown(
        f'<div class="stage-card">'
        f'<div class="sc-title">Stage {sr.stage_num} — {sr.label}{pct_str}</div>'
        f'<div class="sc-row"><span class="sc-lbl">GOR</span><span class="sc-val">{sr.R_input:.1f} {gor_unit}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">P / T / Z</span><span class="sc-val">{p_disp} · {t_disp} · {sr.Z:.3f}</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ std cond.</span><span class="sc-val">{sr.V_gas_std_cc:,.2f} cc &nbsp;({sr.V_gas_std_unit:.5f} {gas_unit})</span></div>'
        f'<div class="sc-row"><span class="sc-lbl">Gas @ sep cond.</span><span class="sc-val">{sr.V_gas_sep:,.2f} cc</span></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Calculation steps (collapsible) ─────────────────────────────────────────
with st.expander("📐 Calculation Steps", expanded=False):

    def _step(label: str, body: str) -> None:
        st.markdown(
            f'<div class="pvt-step"><div class="step-label">{label}</div>{body}</div>',
            unsafe_allow_html=True,
        )

    _step("Step 1 — Separator oil charge",
          f"V_oil_sep = {oil_fraction:.2f} × {v_cell:.1f} = <b>{res.V_oil_sep:.2f} cc</b><br>"
          f"V_oil_STO = {res.V_oil_sep:.2f} / {bo_sep:.3f} = <b>{res.V_oil_STO:.2f} cc</b>")

    for sr in res.stage_results:
        if units == "field":
            gor_conv = f"{sr.R_input:.1f} scf/STB × 0.178107 = <b>{sr.R_cc:.5f} cc/cc</b>"
        else:
            gor_conv = f"R_cc = <b>{sr.R_cc:.5f} cc/cc</b>"
        _step(f"Step {sr.stage_num + 1} — Stage {sr.stage_num} ({sr.label}) gas",
              f"{gor_conv}<br>"
              f"V_gas_std = {sr.R_cc:.5f} × {res.V_oil_STO:.2f} = <b>{sr.V_gas_std_cc:.2f} cc</b>"
              f" ({sr.V_gas_std_unit:.5f} {gas_unit})<br>"
              f"V_gas_sep = V_gas_std × (P_std/P) × (T/T_std) × Z<br>"
              f"&nbsp;&nbsp;&nbsp;= {sr.V_gas_std_cc:.2f}"
              f" × ({P_STD_PSIA:.3f}/{sr.P_psia:.2f})"
              f" × ({sr.T_R:.2f}/{T_STD_R:.2f})"
              f" × {sr.Z:.3f}"
              f" = <b>{sr.V_gas_sep:.2f} cc</b>")

    if n_stages > 1:
        _step(f"Step {n_stages + 2} — Total gas",
              " + ".join(f"{sr.V_gas_std_cc:.2f}" for sr in res.stage_results)
              + f" = <b>{res.total_V_gas_std_cc:.2f} cc</b>"
              f" ({res.total_V_gas_std_unit:.5f} {gas_unit})")

    gor_cls = "gor-ok" if gor_err_pct < 0.1 else "gor-warn"
    gor_sym = "✓" if gor_err_pct < 0.1 else "⚠"
    _step("GOR Verification",
          f"Back-calc: {res.GOR_check:.4f} {gor_unit} — input: {res.R_total_input:.4f}<br>"
          f'<span class="{gor_cls}">{gor_sym} error = {gor_err_pct:.5f}%</span>')

    # Diagram
    st.markdown('<div class="pvt-section">Cell Diagram</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pvt-ascii">{DIAGRAMS[n_stages]}</div>', unsafe_allow_html=True)

# ── Lab Report (collapsible) ─────────────────────────────────────────────────
with st.expander("📋 Lab Report — Full Data Sheet", expanded=False):

    def _tsect(title: str) -> str:
        return (f'<tr class="tbl-section"><td colspan="3">{title}</td></tr>')

    def _trow(name: str, val: str, unit_lbl: str = "") -> str:
        return (
            f"<tr><td>{name}</td>"
            f'<td style="text-align:right; font-weight:600; color:#0a3d62;">{val}</td>'
            f'<td style="color:#6a7f96; font-size:0.78rem;">{unit_lbl}</td></tr>'
        )

    rows = ""
    rows += _tsect("CELL SETUP")
    rows += _trow("Cell Volume",      f"{v_cell:.2f}",      "cc")
    rows += _trow("Oil Fraction",     f"{oil_fraction:.2f}", "")
    rows += _trow("Bo (separator)",   f"{bo_sep:.4f}",       "res/STO")
    rows += _trow("Stages",           str(n_stages))
    rows += _trow("Units",            units)

    rows += _tsect("STANDARD CONDITIONS")
    rows += _trow("P_std", "14.696", "psia")
    rows += _trow("T_std", "60.0 °F / 519.67 °R")

    for sr in res.stage_results:
        p_in = stages[sr.stage_num - 1].P
        t_in = stages[sr.stage_num - 1].T
        rows += _tsect(f"STAGE {sr.stage_num} — {sr.label}")
        rows += _trow("GOR",         f"{sr.R_input:.2f}",  gor_unit)
        rows += _trow("Pressure",    f"{p_in:.2f}",         pres_unit)
        rows += _trow("Temperature", f"{t_in:.2f}",         temp_unit)
        rows += _trow("Z-factor",    f"{sr.Z:.4f}")
        rows += _trow("GOR (cc/cc)", f"{sr.R_cc:.6f}",     "cc/cc")
        rows += _trow("Gas @ std",   f"{sr.V_gas_std_cc:.4f}", "cc")
        rows += _trow("Gas @ std",   f"{sr.V_gas_std_unit:.6f}", gas_unit)
        rows += _trow("Gas @ stage", f"{sr.V_gas_sep:.4f}", "cc")
        rows += _trow("% of GOR",    f"{sr.pct_of_total:.2f}", "%")

    rows += _tsect("CHARGES — OIL")
    rows += _trow("Separator Oil", f"{res.V_oil_sep:.4f}", "cc")
    rows += _trow("STO Oil Equiv.", f"{res.V_oil_STO:.4f}", "cc")

    rows += _tsect("CHARGES — GAS (TOTAL)")
    rows += _trow("Total Gas @ std", f"{res.total_V_gas_std_cc:.4f}", "cc")
    rows += _trow("Total Gas @ std", f"{res.total_V_gas_std_unit:.6f}", gas_unit)

    rows += _tsect("VERIFICATION")
    rows += _trow("GOR (input)",      f"{res.R_total_input:.4f}", gor_unit)
    rows += _trow("GOR (back-calc.)", f"{res.GOR_check:.4f}",     gor_unit)
    rows += _trow("GOR match error",  f"{gor_err_pct:.5f}",       "%")

    if show_pb:
        rows += _tsect("BUBBLE POINT (Standing 1947)")
        rows += _trow("Est. Pb",       f"{Pb_disp:.1f}", Pb_unit)
        rows += _trow("Range (±15%)",  f"{Pb_lo:.0f} – {Pb_hi:.0f}", Pb_unit)
        rows += _trow("γg",            f"{gamma_g:.3f}")
        rows += _trow("API",           f"{api_gravity:.1f}", "°API")
        rows += _trow("T (for Pb)",    f"{T_for_pb:.1f}", "°F")

    st.markdown(f"""
    <table class="pvt-table">
        <thead>
            <tr>
                <th>Parameter</th>
                <th style="text-align:right;">Value</th>
                <th>Unit</th>
            </tr>
        </thead>
        <tbody>{rows}</tbody>
    </table>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if gor_err_pct < 0.01:
        st.success(f"GOR verification passed — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.5f}% error)")
    elif gor_err_pct < 0.5:
        st.info(f"GOR within tolerance — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.3f}% error)")
    else:
        st.error(f"GOR mismatch — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.2f}% error) — review inputs.")

# ── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<hr style="margin-top:1.5rem; border-color:#d0dcea;">
<p style="text-align:center; color:#8fa3b8; font-size:0.75rem; line-height:1.6;">
    PVT Calculator Suite · Module 1: Separator Recombination<br>
    Std: 14.696 psia / 60°F &nbsp;·&nbsp;
    <em>Verify with a qualified reservoir engineer before laboratory use.</em>
</p>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Local runner — allows `python app.py` in VSCode / terminal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import subprocess
    import sys
    import os
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)],
        check=False,
    )
