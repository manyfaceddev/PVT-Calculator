"""
PVT Separator Recombination Calculator
Module 1 of the PVT Calculator Suite

Streamlit app — run with:  streamlit run app.py
"""

import streamlit as st
from pvt_calc import (
    SeparatorStage,
    MultiStageResults,
    validate_multistage,
    calculate_multistage,
    standing_bubble_point,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
    P_STD_PSIA,
    T_STD_R,
    SCF_TO_CC,
    CC_TO_SM3,
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
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: #f5f7fa;
    font-family: 'Segoe UI', Arial, sans-serif;
}
.pvt-header {
    background: linear-gradient(135deg, #1a2b45 0%, #243b5e 60%, #2e5082 100%);
    color: #fff;
    padding: 1.6rem 2rem 1.2rem 2rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
}
.pvt-header h1 { margin: 0; font-size: 1.9rem; letter-spacing: 0.5px; }
.pvt-header p  { margin: 0.3rem 0 0 0; color: #b0c8e8; font-size: 0.95rem; }
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
.pvt-summary {
    background: linear-gradient(135deg, #1a2b45, #243b5e);
    color: #fff;
    border-radius: 10px;
    padding: 1.4rem 1.8rem;
    margin-bottom: 1.4rem;
}
.pvt-summary h2  { color: #7ec8e3; margin: 0 0 0.5rem 0; font-size: 1.1rem; }
.pvt-summary .charge { font-size: 1.3rem; font-weight: 700; margin: 0.35rem 0; }
.pvt-summary .charge-sub { font-size: 0.95rem; font-weight: 400; color: #b0c8e8; }
.pvt-summary .sub { color: #b0c8e8; font-size: 0.88rem; margin-top: 0.5rem; }
.pvt-summary .divider { border-top: 1px solid #2e5082; margin: 0.7rem 0; }
.pvt-metrics { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
.pvt-metric {
    flex: 1; min-width: 150px;
    background: #f0f4fa;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    text-align: center;
}
.pvt-metric .val  { font-size: 1.55rem; font-weight: 700; color: #1a2b45; }
.pvt-metric .lbl  { font-size: 0.75rem; color: #5a6e85; text-transform: uppercase; letter-spacing: 0.5px; }
.pvt-metric .unit { font-size: 0.8rem; color: #2e5082; font-weight: 600; }
.pvt-metric.highlight { background: #e8f0fb; border: 2px solid #2e5082; }
.pvt-step {
    background: #f8fafc;
    border: 1px solid #dde3ea;
    border-radius: 6px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.6rem;
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
    color: #2c3e50;
}
.pvt-step .step-label {
    color: #2e5082; font-weight: 700;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 0.8rem; margin-bottom: 0.2rem;
}
.pvt-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.pvt-table th { background: #1a2b45; color: #fff; padding: 0.5rem 0.9rem; text-align: left; }
.pvt-table td { padding: 0.4rem 0.9rem; border-bottom: 1px solid #e5eaf0; }
.pvt-table tr:nth-child(even) td { background: #f4f7fb; }
.stage-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.stage-table th { background: #243b5e; color: #7ec8e3; padding: 0.45rem 0.8rem; text-align: center; }
.stage-table td { padding: 0.4rem 0.8rem; border-bottom: 1px solid #e5eaf0; text-align: center; }
.stage-table tr:nth-child(even) td { background: #f4f7fb; }
.stage-table td:first-child { text-align: left; font-weight: 600; color: #1a2b45; }
.pb-card {
    background: #fff8e8;
    border: 1px solid #e8c84a;
    border-left: 4px solid #e8a00a;
    border-radius: 8px;
    padding: 1rem 1.3rem;
    margin-bottom: 1.2rem;
}
.pb-card h3 { color: #7a5800; margin: 0 0 0.5rem 0; font-size: 1rem; }
.pb-value { font-size: 1.8rem; font-weight: 700; color: #7a5800; }
.pb-range { font-size: 0.88rem; color: #9a7010; }
.pb-note  { font-size: 0.8rem; color: #a08030; margin-top: 0.5rem; font-style: italic; }
.pvt-ascii {
    background: #1a2b45;
    color: #7ec8e3;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    white-space: pre;
    line-height: 1.5;
}
.gor-ok  { color: #1a7a4a; font-weight: 700; }
.gor-warn{ color: #c0392b; font-weight: 700; }
[data-testid="stSidebar"] { background: #1a2b45; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stSelectbox label { color: #d0dff0 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #7ec8e3 !important; }
[data-testid="stSidebar"] hr { border-color: #2e5082; }
[data-testid="stSidebar"] .stExpander { border-color: #2e5082 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pre-loaded examples (all in field units)
# ---------------------------------------------------------------------------
EXAMPLES: dict[str, dict | None] = {
    "— select an example —": None,
    "Light oil, North Sea (high GOR)": {
        "units":       "field",
        "n_stages":    2,
        "v_cell":      300.0,
        "oil_fraction": 0.72,
        "bo_sep":      1.00,
        "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
        "r_sep_2":  50.0, "p_sep_2":  65.0, "t_sep_2": 100.0, "z_sep_2": 0.977,
        "r_sep_3":  20.0, "p_sep_3":  35.0, "t_sep_3":  75.0, "z_sep_3": 0.991,
        "show_pb":   True,
        "gamma_g":   0.72,
        "api_gravity": 42.0,
        "t_res":     210.0,
    },
    "Medium oil, Middle East (moderate GOR)": {
        "units":       "field",
        "n_stages":    2,
        "v_cell":      250.0,
        "oil_fraction": 0.70,
        "bo_sep":      1.01,
        "r_sep_1": 380.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
        "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  90.0, "z_sep_2": 0.986,
        "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  75.0, "z_sep_3": 0.994,
        "show_pb":   True,
        "gamma_g":   0.76,
        "api_gravity": 34.0,
        "t_res":     175.0,
    },
    "Heavy oil, Offshore (low GOR)": {
        "units":       "field",
        "n_stages":    1,
        "v_cell":      200.0,
        "oil_fraction": 0.68,
        "bo_sep":      1.03,
        "r_sep_1": 100.0, "p_sep_1":  60.0, "t_sep_1": 100.0, "z_sep_1": 0.972,
        "r_sep_2":  10.0, "p_sep_2":  20.0, "t_sep_2":  75.0, "z_sep_2": 0.990,
        "r_sep_3":   5.0, "p_sep_3":  10.0, "t_sep_3":  60.0, "z_sep_3": 0.995,
        "show_pb":   True,
        "gamma_g":   0.82,
        "api_gravity": 22.0,
        "t_res":     155.0,
    },
}

# Stage labels per stage count
STAGE_LABELS = {
    1: ["Separator"],
    2: ["HP Separator", "LP Separator"],
    3: ["HP Separator", "MP Separator", "LP Separator"],
}

# ---------------------------------------------------------------------------
# ASCII diagrams  (chosen by n_stages)
# ---------------------------------------------------------------------------
DIAGRAM_1 = """\
  SINGLE-STAGE SEPARATOR RECOMBINATION
  ──────────────────────────────────────────

  ┌─────────────┐  gas (G1)
  │  SEPARATOR  │──────────────────────────►┐
  │  P1, T1, Z1 │                           │
  └──────┬──────┘                   ┌───────▼──────────────┐
         │ separator oil             │  RECOMBINATION CELL  │
         └──────────────────────────►  ░░░░ GAS  ░░░░░░░░  │
                                    │  ▓▓▓▓ OIL  ▓▓▓▓▓▓▓  │
                                    └──────────────────────┘
   Gas injected at separator P & T via gas pump
  ──────────────────────────────────────────
"""

DIAGRAM_2 = """\
  TWO-STAGE SEPARATOR RECOMBINATION
  ──────────────────────────────────────────────────

  ┌──────────────┐  gas (G1)
  │   STAGE 1    │─────────────────────────────────►┐
  │  HP Sep      │                                  │
  └──────┬───────┘  ┌──────────────┐  gas (G2)      │
         │ oil      │   STAGE 2    │───────────────►┤
         └─────────►│  LP Sep      │                │
                    └──────┬───────┘       ┌─────────▼───────────────┐
                           │ sep. oil      │   RECOMBINATION CELL     │
                           └──────────────►│   ░░░░ G1+G2 GAS ░░░░  │
                                           │   ▓▓▓▓▓ OIL ▓▓▓▓▓▓▓▓  │
                                           └────────────────────────┘
  Each stage gas charged separately at its own P, T, Z
  ──────────────────────────────────────────────────
"""

DIAGRAM_3 = """\
  THREE-STAGE SEPARATOR RECOMBINATION
  ───────────────────────────────────────────────────────────

  ┌──────────────┐  gas (G1)
  │   STAGE 1    │────────────────────────────────────────►┐
  │  HP Sep      │                                         │
  └──────┬───────┘  ┌──────────────┐  gas (G2)             │
         │ oil      │   STAGE 2    │──────────────────────►┤
         └─────────►│  MP Sep      │                       │
                    └──────┬───────┘  ┌──────────────┐ gas │
                           │ oil      │   STAGE 3    │ (G3)│
                           └─────────►│  LP Sep      │────►┤
                                      └──────┬───────┘     │
                                             │ sep. oil   ┌─▼──────────────────────┐
                                             └───────────►│  RECOMBINATION CELL    │
                                                          │  ░░░ G1+G2+G3 GAS ░░  │
                                                          │  ▓▓▓▓▓▓ OIL ▓▓▓▓▓▓▓  │
                                                          └────────────────────────┘
  ───────────────────────────────────────────────────────────
"""

DIAGRAMS = {1: DIAGRAM_1, 2: DIAGRAM_2, 3: DIAGRAM_3}

# ---------------------------------------------------------------------------
# Session state — initialise defaults (runs once on first load)
# ---------------------------------------------------------------------------
SS_DEFAULTS: dict = {
    "units":       "field",
    "_units_prev": "field",
    "n_stages":    2,
    "v_cell":      300.0,
    "oil_fraction": 0.70,
    "bo_sep":      1.00,
    # Stage 1 — HP Separator
    "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
    # Stage 2 — LP Separator (or 2nd stage)
    "r_sep_2":  50.0, "p_sep_2":  65.0, "t_sep_2": 100.0, "z_sep_2": 0.977,
    # Stage 3 — 3rd stage
    "r_sep_3":  20.0, "p_sep_3":  35.0, "t_sep_3":  75.0, "z_sep_3": 0.991,
    # Bubble point
    "show_pb":    True,
    "gamma_g":    0.72,
    "api_gravity": 42.0,
    "t_res":      210.0,
    # Example tracking
    "example_sel": "— select an example —",
}
for k, v in SS_DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------
def _on_example_change() -> None:
    """Populate all input fields from the selected example."""
    ex_name = st.session_state["example_sel"]
    ex = EXAMPLES.get(ex_name)
    if ex is None:
        return
    for k, v in ex.items():
        st.session_state[k] = v
    st.session_state["_units_prev"] = "field"   # examples always ship as field


def _on_units_change() -> None:
    """Convert all P/T/GOR session-state values when the unit system changes."""
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
            st.session_state[f"p_sep_{n}"] = round(p / BARA_TO_PSIA,   2)
            st.session_state[f"t_sep_{n}"] = round((t - 32.0) * 5/9,   1)
            st.session_state[f"r_sep_{n}"] = round(r * SCF_STB_TO_CC_CC, 2)
        elif to_field:
            st.session_state[f"p_sep_{n}"] = round(p * BARA_TO_PSIA,   1)
            st.session_state[f"t_sep_{n}"] = round(t * 9/5 + 32.0,     1)
            st.session_state[f"r_sep_{n}"] = round(r / SCF_STB_TO_CC_CC, 1)

    tr = st.session_state.get("t_res", 200.0)
    if to_si:
        st.session_state["t_res"] = round((tr - 32.0) * 5/9, 1)
    elif to_field:
        st.session_state["t_res"] = round(tr * 9/5 + 32.0, 1)

    st.session_state["_units_prev"] = cur


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="pvt-header">
    <h1>🛢️ PVT Separator Recombination Calculator</h1>
    <p>Module 1 — Multi-Stage Separator Fluid Recombination &nbsp;|&nbsp; PVT Calculator Suite</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ Input Parameters")
    st.markdown("---")

    # ── Example loader ───────────────────────────────────────────────────────
    st.markdown("### 📂 Load Example")
    st.selectbox(
        "Pre-loaded examples",
        options=list(EXAMPLES.keys()),
        key="example_sel",
        on_change=_on_example_change,
        label_visibility="collapsed",
    )
    st.markdown("---")

    # ── Configuration ────────────────────────────────────────────────────────
    st.markdown("### ⚙️ Configuration")

    st.selectbox(
        "Unit System",
        options=["field", "si"],
        format_func=lambda x: "Field  (psia · °F · scf/STB)" if x == "field" else "SI  (bara · °C · sm³/sm³)",
        key="units",
        on_change=_on_units_change,
    )

    st.radio(
        "Number of Separator Stages",
        options=[1, 2, 3],
        horizontal=True,
        key="n_stages",
    )

    st.markdown("---")

    # ── Cell & Oil ───────────────────────────────────────────────────────────
    st.markdown("### 🛢️ Cell & Oil")

    st.number_input(
        "Cell Volume (cc)",
        min_value=1.0, max_value=5000.0, step=10.0,
        key="v_cell",
        help="Total internal volume of the recombination cell.",
    )
    st.slider(
        "Oil Fraction (fraction of cell)",
        min_value=0.40, max_value=0.90, step=0.01,
        key="oil_fraction",
        help="Fraction of cell volume to fill with separator oil. Typical: 0.65–0.80.",
    )
    st.number_input(
        "Bo at Separator (res vol / STO vol)",
        min_value=0.80, max_value=3.00, step=0.01,
        key="bo_sep",
        help="Oil FVF at separator conditions. Usually ≈ 1.0 for separator liquid.",
    )

    st.markdown("---")

    # ── Per-stage inputs ─────────────────────────────────────────────────────
    n_stages = st.session_state["n_stages"]
    units    = st.session_state["units"]

    gor_lbl  = "GOR (scf/STB)"   if units == "field" else "GOR (sm³/sm³)"
    pres_lbl = "Pressure (psia)" if units == "field" else "Pressure (bara)"
    temp_lbl = "Temperature (°F)" if units == "field" else "Temperature (°C)"

    labels = STAGE_LABELS[n_stages]

    for n in range(1, n_stages + 1):
        lbl = labels[n - 1]
        st.markdown(f"### Stage {n} — {lbl}")
        st.number_input(gor_lbl,  min_value=0.1, step=10.0 if units == "field" else 0.5, key=f"r_sep_{n}")
        st.number_input(pres_lbl, min_value=0.1, step=5.0  if units == "field" else 0.2, key=f"p_sep_{n}")
        st.number_input(temp_lbl, step=1.0, key=f"t_sep_{n}")
        st.number_input(
            "Z-factor (dimensionless)",
            min_value=0.01, max_value=2.00, step=0.001, format="%.3f",
            key=f"z_sep_{n}",
            help=f"Compressibility factor of separator gas at Stage {n} conditions.",
        )
        if n < n_stages:
            st.markdown("---")

    st.markdown("---")

    # ── Bubble Point estimate (optional) ─────────────────────────────────────
    with st.expander("🔴 Bubble Point Estimate (Standing 1947)", expanded=True):
        st.checkbox("Enable Pb estimation", key="show_pb")

        if st.session_state["show_pb"]:
            st.number_input(
                "Gas Specific Gravity γg (air = 1.0)",
                min_value=0.50, max_value=1.80, step=0.01, format="%.3f",
                key="gamma_g",
                help="Weighted-average specific gravity of separator gas across all stages.",
            )
            st.number_input(
                "Stock-Tank Oil API Gravity (°API)",
                min_value=5.0, max_value=60.0, step=0.5,
                key="api_gravity",
            )
            t_res_lbl = "Reservoir Temperature (°F)" if units == "field" else "Reservoir Temperature (°C)"
            st.number_input(
                t_res_lbl,
                step=1.0,
                key="t_res",
                help="Reservoir temperature for Standing correlation. Use °F internally regardless of unit toggle.",
            )

    st.markdown("---")
    st.button("Calculate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Read all values from session state
# ---------------------------------------------------------------------------
units       = st.session_state["units"]
n_stages    = st.session_state["n_stages"]
v_cell      = st.session_state["v_cell"]
oil_fraction = st.session_state["oil_fraction"]
bo_sep      = st.session_state["bo_sep"]
show_pb     = st.session_state["show_pb"]
gamma_g     = st.session_state.get("gamma_g",    0.72)
api_gravity = st.session_state.get("api_gravity", 40.0)
t_res_raw   = st.session_state.get("t_res",      200.0)

labels = STAGE_LABELS[n_stages]

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
    for e in errors:
        st.error(f"**Input Error:** {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Calculation
# ---------------------------------------------------------------------------
res: MultiStageResults = calculate_multistage(stages, v_cell, bo_sep, oil_fraction, units)

# Unit labels
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

# Bubble point — always computed in field units
if show_pb:
    if units == "field":
        R_for_pb = res.R_total_input
        T_for_pb = t_res_raw
    else:
        R_for_pb = res.R_total_input / SCF_STB_TO_CC_CC   # sm³/sm³ → scf/STB
        T_for_pb = t_res_raw * 9/5 + 32.0                 # °C → °F
    Pb_psia = standing_bubble_point(R_for_pb, gamma_g, T_for_pb, api_gravity)
    Pb_disp = Pb_psia if units == "field" else Pb_psia / BARA_TO_PSIA
    Pb_unit = "psia" if units == "field" else "bara"
    Pb_lo   = Pb_disp * 0.85
    Pb_hi   = Pb_disp * 1.15

# ---------------------------------------------------------------------------
# Layout: two columns
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([1, 1.45], gap="large")

# ===========================================================================
# LEFT COLUMN — diagram + calculation steps
# ===========================================================================
with left_col:

    # ── ASCII diagram ────────────────────────────────────────────────────────
    st.markdown(
        f'<div class="pvt-ascii">{DIAGRAMS[n_stages]}</div>',
        unsafe_allow_html=True,
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Calculation steps ────────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-card"><h3>📐 Calculation Steps</h3></div>',
        unsafe_allow_html=True,
    )

    def step_html(label: str, body: str) -> str:
        return (
            f'<div class="pvt-step">'
            f'<div class="step-label">{label}</div>'
            f'{body}'
            f'</div>'
        )

    step_blocks = []

    # Step 1 — Oil volumes
    step_blocks.append(step_html(
        "Step 1 — Separator oil charge",
        (
            f"V_oil_sep = oil_fraction × V_cell = "
            f"{oil_fraction:.2f} × {v_cell:.1f} = <b>{res.V_oil_sep:.2f} cc</b><br>"
            f"V_oil_STO = V_oil_sep / Bo_sep = "
            f"{res.V_oil_sep:.2f} / {bo_sep:.3f} = <b>{res.V_oil_STO:.2f} cc</b>"
        ),
    ))

    # Steps 2+N — Per-stage gas volumes
    for sr in res.stage_results:
        if units == "field":
            gor_conv = f"{sr.R_input:.1f} scf/STB × 0.178107 = <b>{sr.R_cc:.5f} cc/cc</b>"
        else:
            gor_conv = f"GOR already a ratio: R_cc = <b>{sr.R_cc:.5f} cc/cc</b>"

        step_blocks.append(step_html(
            f"Step {sr.stage_num + 1} — Stage {sr.stage_num} ({sr.label}) gas",
            (
                f"{gor_conv}<br>"
                f"V_gas_std = R_cc × V_oil_STO = "
                f"{sr.R_cc:.5f} × {res.V_oil_STO:.2f} = <b>{sr.V_gas_std_cc:.2f} cc</b>"
                f" ({sr.V_gas_std_unit:.5f} {gas_unit})<br>"
                f"V_gas_sep = V_gas_std × (P_std/P) × (T/T_std) × Z<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {sr.V_gas_std_cc:.2f}"
                f" × ({P_STD_PSIA:.3f}/{sr.P_psia:.2f})"
                f" × ({sr.T_R:.2f}/{T_STD_R:.2f})"
                f" × {sr.Z:.3f}"
                f" = <b>{sr.V_gas_sep:.2f} cc</b>"
            ),
        ))

    # Total gas (only if multi-stage)
    if n_stages > 1:
        step_blocks.append(step_html(
            f"Step {n_stages + 2} — Total gas (all stages)",
            (
                f"V_gas_std_total = "
                + " + ".join(f"{sr.V_gas_std_cc:.2f}" for sr in res.stage_results)
                + f" = <b>{res.total_V_gas_std_cc:.2f} cc</b>"
                f" ({res.total_V_gas_std_unit:.5f} {gas_unit})"
            ),
        ))

    # GOR verification
    gor_check_cls = "gor-ok" if gor_err_pct < 0.1 else "gor-warn"
    gor_check_sym = "✓" if gor_err_pct < 0.1 else "⚠"
    step_blocks.append(step_html(
        f"Step {n_stages + 2 + (1 if n_stages > 1 else 0)} — GOR verification",
        (
            f"GOR_check = V_gas_std_total / V_oil_STO (→ input units)<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.total_V_gas_std_cc:.2f} / {res.V_oil_STO:.2f}"
            f" → <b>{res.GOR_check:.3f} {gor_unit}</b> "
            f'<span class="{gor_check_cls}">{gor_check_sym} {gor_err_pct:.4f}% error</span>'
        ),
    ))

    for blk in step_blocks:
        st.markdown(blk, unsafe_allow_html=True)

# ===========================================================================
# RIGHT COLUMN — summary, tiles, tables
# ===========================================================================
with right_col:

    # ── Charge summary box ───────────────────────────────────────────────────
    oil_line = f"🟤 <span class='charge'>{res.V_oil_sep:.2f} cc</span> separator oil ({labels[-1]})"

    gas_lines = ""
    for sr in res.stage_results:
        pct_str = f"{sr.pct_of_total:.1f}% of GOR"
        gas_lines += (
            f"💨 <span class='charge'>{sr.V_gas_std_cc:.2f} cc</span>"
            f" &nbsp;<span class='charge-sub'>({sr.V_gas_std_unit:.5f} {gas_unit})</span>"
            f"&nbsp; Stage {sr.stage_num} gas @ std — <span class='charge-sub'>{pct_str}</span><br>"
        )

    total_gas_line = ""
    if n_stages > 1:
        total_gas_line = (
            f"<div class='divider'></div>"
            f"📦 <span class='charge'>Total gas: {res.total_V_gas_std_cc:.2f} cc</span>"
            f" &nbsp;<span class='charge-sub'>({res.total_V_gas_std_unit:.5f} {gas_unit} @ std conditions)</span>"
        )

    st.markdown(f"""
    <div class="pvt-summary">
        <h2>CHARGE SUMMARY</h2>
        {oil_line}<br>
        <div class="divider"></div>
        {gas_lines}
        {total_gas_line}
        <div class="sub" style="margin-top:0.8rem;">
            Total GOR: {res.R_total_input:.2f} {gor_unit}
            &nbsp;|&nbsp; Cell: {v_cell:.0f} cc &nbsp;|&nbsp; Oil fill: {oil_fraction*100:.0f}%
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Metric tiles ─────────────────────────────────────────────────────────
    pb_tile = ""
    if show_pb:
        pb_tile = (
            f'<div class="pvt-metric highlight">'
            f'<div class="val">{Pb_disp:.0f}</div>'
            f'<div class="unit">{Pb_unit}</div>'
            f'<div class="lbl">Est. Bubble Point (Standing)</div>'
            f'</div>'
        )

    st.markdown(f"""
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
            <div class="val">{res.total_V_gas_std_cc:.1f}</div>
            <div class="unit">cc @ std</div>
            <div class="lbl">Total Gas — Std Conditions</div>
        </div>
        <div class="pvt-metric">
            <div class="val">{res.R_total_input:.1f}</div>
            <div class="unit">{gor_unit}</div>
            <div class="lbl">Total Solution GOR</div>
        </div>
        {pb_tile}
    </div>
    """, unsafe_allow_html=True)

    # ── Per-stage breakdown (only if multi-stage) ────────────────────────────
    if n_stages > 1:
        st.markdown(
            '<div class="pvt-card"><h3>⚗️ Per-Stage Gas Breakdown</h3></div>',
            unsafe_allow_html=True,
        )

        stage_rows = ""
        for sr in res.stage_results:
            p_disp = f"{sr.P_psia:.1f}" if units == "field" else f"{sr.P_psia/BARA_TO_PSIA:.2f}"
            t_disp = f"{sr.T_F:.1f}" if units == "field" else f"{(sr.T_F-32)*5/9:.1f}"
            stage_rows += (
                f"<tr>"
                f"<td>Stage {sr.stage_num} — {sr.label}</td>"
                f"<td>{sr.R_input:.1f}</td>"
                f"<td>{sr.R_cc:.5f}</td>"
                f"<td>{sr.V_gas_std_cc:.2f}</td>"
                f"<td>{sr.V_gas_std_unit:.5f}</td>"
                f"<td>{sr.V_gas_sep:.2f}</td>"
                f"<td>{p_disp}</td>"
                f"<td>{t_disp}</td>"
                f"<td>{sr.Z:.3f}</td>"
                f"<td>{sr.pct_of_total:.1f}%</td>"
                f"</tr>"
            )
        # Total row
        stage_rows += (
            f'<tr style="background:#e8f0fb; font-weight:700; color:#1a2b45;">'
            f"<td>TOTAL</td>"
            f"<td>{res.R_total_input:.1f}</td>"
            f"<td>{res.R_total_cc:.5f}</td>"
            f"<td>{res.total_V_gas_std_cc:.2f}</td>"
            f"<td>{res.total_V_gas_std_unit:.5f}</td>"
            f"<td>—</td><td>—</td><td>—</td><td>—</td>"
            f"<td>100.0%</td>"
            f"</tr>"
        )

        st.markdown(f"""
        <table class="stage-table">
            <thead>
                <tr>
                    <th style="text-align:left;">Stage</th>
                    <th>GOR ({gor_unit})</th>
                    <th>GOR (cc/cc)</th>
                    <th>V_gas_std (cc)</th>
                    <th>V_gas_std ({gas_unit})</th>
                    <th>V_gas_sep (cc)</th>
                    <th>P ({pres_unit})</th>
                    <th>T ({temp_unit})</th>
                    <th>Z</th>
                    <th>% GOR</th>
                </tr>
            </thead>
            <tbody>{stage_rows}</tbody>
        </table>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Standing Pb estimate ─────────────────────────────────────────────────
    if show_pb:
        t_res_disp = f"{t_res_raw:.1f} {temp_unit}"
        t_res_F_disp = f"{T_for_pb:.1f} °F"

        st.markdown(f"""
        <div class="pb-card">
            <h3>🔴 Bubble Point Pressure — Standing (1947) Estimate</h3>
            <div class="pb-value">{Pb_disp:.1f} {Pb_unit}</div>
            <div class="pb-range">
                Confidence range (±15%):
                &nbsp; {Pb_lo:.0f} – {Pb_hi:.0f} {Pb_unit}
            </div>
            <div class="pb-note">
                Pb = 18.2 × [(R/γg)^0.83 × 10^(0.00091·T − 0.0125·API) − 1.4]<br>
                Inputs: R = {R_for_pb:.1f} scf/STB &nbsp;|&nbsp;
                γg = {gamma_g:.3f} &nbsp;|&nbsp;
                T = {t_res_F_disp} &nbsp;|&nbsp;
                API = {api_gravity:.1f}°<br>
                ⚠ Estimate only (±10–15%). Standing (1947) derived from California crude data.
                Use reservoir temperature, not separator temperature, for best accuracy.
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Lab Report Table ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-card"><h3>📋 Lab Report — Recombination Data Sheet</h3></div>',
        unsafe_allow_html=True,
    )

    std_cond_str = "14.696 psia / 60 °F / 519.67 °R"

    def tr_section(title: str) -> str:
        return (
            f'<tr><td colspan="3" style="background:#243b5e; color:#7ec8e3; '
            f'font-weight:700; font-size:0.78rem; letter-spacing:0.8px; '
            f'padding:0.4rem 0.9rem;">{title}</td></tr>'
        )

    def tr_row(name: str, val: str, unit_lbl: str) -> str:
        return (
            f"<tr><td>{name}</td>"
            f'<td style="text-align:right; font-weight:600; color:#1a2b45;">{val}</td>'
            f'<td style="color:#5a6e85;">{unit_lbl}</td></tr>'
        )

    rows_html = tr_section("CELL SETUP")
    rows_html += tr_row("Cell Volume",     f"{v_cell:.2f}",      "cc")
    rows_html += tr_row("Oil Fraction",    f"{oil_fraction:.2f}", "fraction")
    rows_html += tr_row("Bo at Separator", f"{bo_sep:.4f}",      "res vol / STO vol")
    rows_html += tr_section("STANDARD CONDITIONS")
    rows_html += tr_row("Standard Conditions", std_cond_str, "—")
    rows_html += tr_section("SEPARATOR STAGES")
    for sr in res.stage_results:
        p_in = st.session_state[f"p_sep_{sr.stage_num}"]
        t_in = st.session_state[f"t_sep_{sr.stage_num}"]
        rows_html += tr_row(f"Stage {sr.stage_num} — {sr.label} GOR",      f"{sr.R_input:.2f}", gor_unit)
        rows_html += tr_row(f"Stage {sr.stage_num} — {sr.label} Pressure", f"{p_in:.2f}",       pres_unit)
        rows_html += tr_row(f"Stage {sr.stage_num} — {sr.label} Temperature", f"{t_in:.2f}",    temp_unit)
        rows_html += tr_row(f"Stage {sr.stage_num} — {sr.label} Z-factor", f"{sr.Z:.4f}",       "—")
    rows_html += tr_section("OIL CHARGES")
    rows_html += tr_row("Separator Oil to Charge",   f"{res.V_oil_sep:.4f}", "cc")
    rows_html += tr_row("Stock-Tank Oil Equivalent", f"{res.V_oil_STO:.4f}", "cc")
    rows_html += tr_section("GAS CHARGES (PER STAGE)")
    for sr in res.stage_results:
        rows_html += tr_row(f"Stage {sr.stage_num} ({sr.label}) Gas @ Std", f"{sr.V_gas_std_cc:.4f}", "cc")
        rows_html += tr_row(f"Stage {sr.stage_num} ({sr.label}) Gas @ Std", f"{sr.V_gas_std_unit:.6f}", gas_unit)
        rows_html += tr_row(f"Stage {sr.stage_num} ({sr.label}) Gas @ Stage Conditions", f"{sr.V_gas_sep:.4f}", "cc")
    rows_html += tr_section("GAS CHARGES (TOTAL)")
    rows_html += tr_row("Total Gas @ Standard Conditions", f"{res.total_V_gas_std_cc:.4f}", "cc")
    rows_html += tr_row("Total Gas @ Standard Conditions", f"{res.total_V_gas_std_unit:.6f}", gas_unit)
    rows_html += tr_section("VERIFICATION")
    rows_html += tr_row("Total GOR (input)",    f"{res.R_total_input:.4f}", gor_unit)
    rows_html += tr_row("Back-Calculated GOR",  f"{res.GOR_check:.4f}",    gor_unit)
    rows_html += tr_row("GOR Match Error",      f"{gor_err_pct:.6f}",      "%")
    if show_pb:
        rows_html += tr_section("BUBBLE POINT ESTIMATE (Standing 1947)")
        rows_html += tr_row("Estimated Pb",            f"{Pb_disp:.1f}",  Pb_unit)
        rows_html += tr_row("Pb Range (±15%)",         f"{Pb_lo:.0f} – {Pb_hi:.0f}", Pb_unit)
        rows_html += tr_row("Gas Specific Gravity γg", f"{gamma_g:.3f}", "—")
        rows_html += tr_row("Oil API Gravity",         f"{api_gravity:.1f}", "°API")
        rows_html += tr_row("T (reservoir, for Pb)",   f"{T_for_pb:.1f}", "°F")

    st.markdown(f"""
    <table class="pvt-table">
        <thead>
            <tr>
                <th>Parameter</th>
                <th style="text-align:right;">Value</th>
                <th>Unit</th>
            </tr>
        </thead>
        <tbody>{rows_html}</tbody>
    </table>
    """, unsafe_allow_html=True)

    # ── GOR verification callout ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    if gor_err_pct < 0.01:
        st.success(
            f"GOR verification passed — back-calculated {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.5f}%)"
        )
    elif gor_err_pct < 0.5:
        st.info(
            f"GOR verification within tolerance — back-calculated {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.3f}%)"
        )
    else:
        st.error(
            f"GOR mismatch — back-calculated {res.GOR_check:.4f} {gor_unit} "
            f"(error = {gor_err_pct:.2f}%) — review inputs."
        )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("""
<hr style="margin-top:2rem; border-color:#dde3ea;">
<p style="text-align:center; color:#8fa3b8; font-size:0.8rem;">
    PVT Calculator Suite — Module 1: Separator Recombination &nbsp;|&nbsp;
    Standard conditions: 14.696 psia / 60°F &nbsp;|&nbsp;
    <em>Always verify results with a qualified reservoir engineer before laboratory use.</em>
</p>
""", unsafe_allow_html=True)
