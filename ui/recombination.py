"""
ui/recombination.py — Streamlit page for separator fluid recombination.

Entry point: call render() from app.py.
Owns: session state, sidebar inputs, output layout.
Does not contain: calculation logic (pvt.recombination) or CSS (ui.styles).

Two oil-source cases:
  Case 1 — Separator Oil + Separator Gas
  Case 2 — Stock Tank Oil + Separator Gas  (adds R_STO input)
"""

import streamlit as st

from pvt.constants import P_STD_PSIA, T_STD_F, T_STD_R, SCF_STB_TO_CC_CC, BARA_TO_PSIA
from pvt.correlations.standing import bubble_point as standing_bubble_point
from pvt.recombination import SeparatorStage, validate_multistage, calculate_multistage

import ui.components as C

# ---------------------------------------------------------------------------
# Static data
# ---------------------------------------------------------------------------

_EXAMPLES: dict[str, dict | None] = {
    "— select an example —": None,
    "Light oil, North Sea (high GOR)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.00,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
        "r_sep_2":  50.0, "p_sep_2":  65.0, "t_sep_2": 100.0, "z_sep_2": 0.977,
        "r_sep_3":  20.0, "p_sep_3":  35.0, "t_sep_3":  75.0, "z_sep_3": 0.991,
        "show_pb": True, "gamma_g": 0.72, "api_gravity": 42.0, "t_res": 210.0,
        "oil_source": "separator", "r_sto": 0.0,
        "p_charge_oil": 2014.73, "c_o": 10.0,
    },
    "Medium oil, Middle East (moderate GOR)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.01,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 380.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
        "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  90.0, "z_sep_2": 0.986,
        "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  75.0, "z_sep_3": 0.994,
        "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
        "oil_source": "separator", "r_sto": 0.0,
        "p_charge_oil": 2014.73, "c_o": 10.0,
    },
    "Heavy oil, Offshore (low GOR)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.03,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 100.0, "p_sep_1":  60.0, "t_sep_1": 100.0, "z_sep_1": 0.972,
        "r_sep_2":  10.0, "p_sep_2":  20.0, "t_sep_2":  75.0, "z_sep_2": 0.990,
        "r_sep_3":   5.0, "p_sep_3":  10.0, "t_sep_3":  60.0, "z_sep_3": 0.995,
        "show_pb": True, "gamma_g": 0.82, "api_gravity": 22.0, "t_res": 155.0,
        "oil_source": "separator", "r_sto": 0.0,
        "p_charge_oil": 2014.73, "c_o": 10.0,
    },
    "Stock tank oil example (Case 2)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.00,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 400.0, "p_sep_1": 250.0, "t_sep_1": 100.0, "z_sep_1": 0.910,
        "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  80.0, "z_sep_2": 0.985,
        "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  70.0, "z_sep_3": 0.993,
        "show_pb": True, "gamma_g": 0.74, "api_gravity": 36.0, "t_res": 180.0,
        "oil_source": "stock_tank", "r_sto": 60.0,
        "p_charge_oil": 2014.73, "c_o": 10.0,
    },
}

_STAGE_LABELS: dict[int, list[str]] = {
    1: ["Separator"],
    2: ["HP Separator", "LP Separator"],
    3: ["HP Separator", "MP Separator", "LP Separator"],
}

_SS_DEFAULTS: dict = {
    "units": "field", "_units_prev": "field",
    "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.00,
    "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
    "r_sep_1": 583.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
    "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  90.0, "z_sep_2": 0.986,
    "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  75.0, "z_sep_3": 0.994,
    "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
    "example_sel": "— select an example —",
    # New fields
    "oil_source":   "separator",
    "r_sto":        0.0,        # stock tank GOR (scf/STB field; sm³/sm³ SI)
    "p_charge_oil": 2014.73,    # oil charging pressure (psia field; bara SI)
    "c_o":          10.0,       # oil compressibility × 10⁻⁶ psi⁻¹  (stored as 10 → multiply by 1e-6 when passing)
}


# ---------------------------------------------------------------------------
# Session state helpers
# ---------------------------------------------------------------------------

def _init_state() -> None:
    for k, v in _SS_DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _on_example_change() -> None:
    ex = _EXAMPLES.get(st.session_state["example_sel"])
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
            st.session_state[f"p_sep_{n}"] = round(p / BARA_TO_PSIA,     2)
            st.session_state[f"t_sep_{n}"] = round((t - 32.0) * 5 / 9,   1)
            st.session_state[f"r_sep_{n}"] = round(r * SCF_STB_TO_CC_CC, 2)
        elif to_field:
            st.session_state[f"p_sep_{n}"] = round(p * BARA_TO_PSIA,     1)
            st.session_state[f"t_sep_{n}"] = round(t * 9 / 5 + 32.0,     1)
            st.session_state[f"r_sep_{n}"] = round(r / SCF_STB_TO_CC_CC, 1)

    pr = st.session_state.get("p_recomb", P_STD_PSIA)
    tr = st.session_state.get("t_recomb", T_STD_F)
    if to_si:
        st.session_state["p_recomb"] = round(pr / BARA_TO_PSIA,    2)
        st.session_state["t_recomb"] = round((tr - 32.0) * 5 / 9,  1)
    elif to_field:
        st.session_state["p_recomb"] = round(pr * BARA_TO_PSIA,    1)
        st.session_state["t_recomb"] = round(tr * 9 / 5 + 32.0,    1)

    t_res = st.session_state.get("t_res", 200.0)
    if to_si:
        st.session_state["t_res"] = round((t_res - 32.0) * 5 / 9, 1)
    elif to_field:
        st.session_state["t_res"] = round(t_res * 9 / 5 + 32.0,   1)

    # Convert oil charging pressure
    pc = st.session_state.get("p_charge_oil", 2014.73)
    if to_si:
        st.session_state["p_charge_oil"] = round(pc / BARA_TO_PSIA, 2)
    elif to_field:
        st.session_state["p_charge_oil"] = round(pc * BARA_TO_PSIA, 1)

    # r_sto conversion (if SI ↔ field)
    r_sto = st.session_state.get("r_sto", 0.0)
    if to_si:
        st.session_state["r_sto"] = round(r_sto * SCF_STB_TO_CC_CC, 4)
    elif to_field:
        st.session_state["r_sto"] = round(r_sto / SCF_STB_TO_CC_CC, 1)

    st.session_state["_units_prev"] = cur


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚙️ Inputs")
        st.markdown("---")

        # Examples
        st.markdown("### 📂 Load Example")
        st.selectbox(
            "Example", options=list(_EXAMPLES.keys()),
            key="example_sel", on_change=_on_example_change,
            label_visibility="collapsed",
        )
        st.markdown("---")

        # Unit system & stage count
        st.selectbox(
            "Unit System",
            options=["field", "si"],
            format_func=lambda x: "Field  (psia · °F · scf/STB)" if x == "field"
                                  else "SI  (bara · °C · sm³/sm³)",
            key="units", on_change=_on_units_change,
        )
        st.radio("Separator Stages", options=[1, 2, 3], horizontal=True, key="n_stages")
        st.markdown("---")

        # ── Oil Source ────────────────────────────────────────────────────────
        units = st.session_state["units"]
        st.markdown("### 🛢️ Oil Source")
        st.radio(
            "Oil source",
            options=["separator", "stock_tank"],
            format_func=lambda x: (
                "Case 1 — Separator Oil + Sep. Gas"
                if x == "separator"
                else "Case 2 — Stock Tank Oil + Sep. Gas"
            ),
            key="oil_source",
            label_visibility="collapsed",
        )
        st.markdown("---")

        # ── Live fluid & Bo ───────────────────────────────────────────────────
        oil_source = st.session_state["oil_source"]
        st.markdown("### 📐 Cell & Fluid Setup")
        st.number_input(
            "Target Live Fluid Volume (cc)", min_value=1.0, max_value=10000.0, step=100.0,
            key="v_live",
            help="Total volume of recombined fluid in the cell at P_recomb and T_recomb.",
        )

        if oil_source == "separator":
            st.number_input(
                "Bo at Separator (res vol / STO vol)",
                min_value=0.80, max_value=3.00, step=0.01, key="bo_sep",
                help="Oil formation volume factor at separator conditions. Converts separator oil volume to STO equivalent.",
            )
        else:
            # Case 2: Bo_sep not needed (STO is the reference volume)
            st.info("Bo not required for Case 2 — stock tank oil is the volume reference.")

        # Case 2 — stock tank GOR
        if oil_source == "stock_tank":
            sto_gor_lbl = "Stock Tank GOR (scf/STB)" if units == "field" else "Stock Tank GOR (sm³/sm³)"
            st.number_input(
                sto_gor_lbl, min_value=0.0, step=5.0 if units == "field" else 0.1,
                key="r_sto",
                help=(
                    "Gas that flashes from the separator oil as pressure drops from "
                    "separator to stock tank (atmospheric). Shrinkage factor SF = R_STO / R_sep_total."
                ),
            )
        st.markdown("---")

        # ── Recombination conditions ──────────────────────────────────────────
        p_lbl = "Recomb. Pressure (psia)" if units == "field" else "Recomb. Pressure (bara)"
        t_lbl = "Recomb. Temperature (°F)" if units == "field" else "Recomb. Temperature (°C)"
        st.markdown("### 🔩 Recombination Conditions")
        st.number_input(
            p_lbl, min_value=14.7, max_value=30000.0, step=100.0, key="p_recomb",
            help="Final cell pressure — typically reservoir or separator conditions.",
        )
        st.number_input(
            t_lbl, step=1.0, key="t_recomb",
            help="Temperature at which the cell will be held during and after charging.",
        )
        st.number_input(
            "Z-factor @ Recomb. P & T", min_value=0.01, max_value=2.00,
            step=0.001, format="%.3f", key="z_recomb",
            help="Gas compressibility factor at recombination conditions.",
        )
        st.markdown("---")

        # ── Oil charging conditions ───────────────────────────────────────────
        p_charge_lbl = (
            "Oil Charging Pressure (psia)" if units == "field"
            else "Oil Charging Pressure (bara)"
        )
        st.markdown("### ⚡ Oil Charging Conditions")
        st.number_input(
            p_charge_lbl, min_value=14.7, max_value=20000.0, step=100.0,
            key="p_charge_oil",
            help=(
                "Pressure at which oil is loaded into the cell before gas is added. "
                "Must be less than P_recomb. Typical lab value: ~2000 psig (2014.7 psia). "
                "Oil at this lower pressure occupies a slightly larger volume than at P_recomb."
            ),
        )
        st.number_input(
            "Oil Compressibility c_o (× 10⁻⁶ psi⁻¹)",
            min_value=0.0, max_value=500.0, step=1.0, format="%.1f",
            key="c_o",
            help=(
                "Isothermal oil compressibility used to correct the charging volume "
                "from P_recomb to P_charge. Typical range: 5–20 × 10⁻⁶ psi⁻¹. "
                "Set to 0 to skip the correction."
            ),
        )
        st.markdown("---")

        # ── Per-stage separator inputs ────────────────────────────────────────
        n_stages = st.session_state["n_stages"]
        labels   = _STAGE_LABELS[n_stages]
        gor_lbl  = "GOR (scf/STB)"    if units == "field" else "GOR (sm³/sm³)"
        pres_lbl = "Pressure (psia)"  if units == "field" else "Pressure (bara)"
        temp_lbl = "Temperature (°F)" if units == "field" else "Temperature (°C)"

        for n in range(1, n_stages + 1):
            st.markdown(f"### Stage {n} — {labels[n - 1]}")
            st.number_input(
                gor_lbl, min_value=0.1,
                step=10.0 if units == "field" else 0.5, key=f"r_sep_{n}",
            )
            st.number_input(
                pres_lbl, min_value=0.1,
                step=5.0 if units == "field" else 0.2, key=f"p_sep_{n}",
            )
            st.number_input(temp_lbl, step=1.0, key=f"t_sep_{n}")
            st.number_input(
                "Z-factor", min_value=0.01, max_value=2.00,
                step=0.001, format="%.3f", key=f"z_sep_{n}",
                help="Compressibility factor at separator conditions.",
            )
            if n < n_stages:
                st.markdown("---")

        st.markdown("---")

        # ── Bubble point ──────────────────────────────────────────────────────
        with st.expander("🔴 Bubble Point (Standing 1947)", expanded=False):
            st.checkbox("Enable Pb estimate", key="show_pb")
            if st.session_state["show_pb"]:
                st.number_input(
                    "Gas Specific Gravity γg (air=1.0)",
                    min_value=0.50, max_value=1.80, step=0.01, format="%.3f",
                    key="gamma_g",
                )
                st.number_input(
                    "API Gravity (°API)", min_value=5.0, max_value=60.0, step=0.5,
                    key="api_gravity",
                )
                t_res_lbl = (
                    "Reservoir Temperature (°F)" if units == "field"
                    else "Reservoir Temperature (°C)"
                )
                st.number_input(
                    t_res_lbl, step=1.0, key="t_res",
                    help="Use reservoir temperature, not separator temperature.",
                )

        st.markdown("---")
        st.button("Calculate", type="primary", use_container_width=True)


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

def _render_content() -> None:
    ss = st.session_state
    units       = ss["units"]
    n_stages    = ss["n_stages"]
    v_live      = ss["v_live"]
    bo_sep      = ss["bo_sep"]
    p_recomb    = ss["p_recomb"]
    t_recomb    = ss["t_recomb"]
    z_recomb    = ss["z_recomb"]
    show_pb     = ss["show_pb"]
    gamma_g     = ss.get("gamma_g",     0.72)
    api_gravity = ss.get("api_gravity", 40.0)
    t_res_raw   = ss.get("t_res",       200.0)
    labels      = _STAGE_LABELS[n_stages]
    oil_source  = ss.get("oil_source",   "separator")
    r_sto       = ss.get("r_sto",        0.0)
    p_charge    = ss.get("p_charge_oil", 2014.73)
    c_o_x1e6   = ss.get("c_o",          10.0)   # stored as 10 → means 10 × 10⁻⁶
    c_o         = c_o_x1e6 * 1.0e-6

    # Case 2 forces Bo_sep = 1.0 internally
    bo_sep_eff = bo_sep if oil_source == "separator" else 1.0

    stages = [
        SeparatorStage(
            R=ss[f"r_sep_{n}"], P=ss[f"p_sep_{n}"],
            T=ss[f"t_sep_{n}"], Z=ss[f"z_sep_{n}"],
            label=labels[n - 1],
        )
        for n in range(1, n_stages + 1)
    ]

    # ── Validation ─────────────────────────────────────────────────────────
    errors = validate_multistage(
        stages, v_live, bo_sep_eff, p_recomb, t_recomb, z_recomb, units,
        oil_source=oil_source, R_STO=r_sto,
        P_charge_oil=p_charge, c_o=c_o,
    )
    if errors:
        st.markdown(C.page_header("🛢️ PVT Recombination", "Module 1 — Separator Fluid Recombination"),
                    unsafe_allow_html=True)
        for e in errors:
            st.error(f"**Input error:** {e}")
        st.info("Open the sidebar (☰) to fix the inputs.")
        st.stop()

    # ── Calculate ──────────────────────────────────────────────────────────
    res = calculate_multistage(
        stages, v_live, bo_sep_eff, p_recomb, t_recomb, z_recomb, units,
        oil_source=oil_source, R_STO=r_sto,
        P_charge_oil=p_charge, c_o=c_o,
    )

    gor_unit  = "scf/STB" if units == "field" else "sm³/sm³"
    pres_unit = "psia"    if units == "field" else "bara"
    temp_unit = "°F"      if units == "field" else "°C"
    gas_unit  = "scf"     if units == "field" else "sm³"

    # GOR error: for Case 2 compare against R_sep + R_STO; for Case 1 just R_sep
    R_total_eff_input = res.R_total_input + res.R_STO_input  # Case 1: same as R_total_input
    gor_err_pct = (
        abs(res.GOR_check - R_total_eff_input) / R_total_eff_input * 100
        if R_total_eff_input > 0 else 0.0
    )

    # ── Bubble point ────────────────────────────────────────────────────────
    Pb_disp = Pb_lo = Pb_hi = T_for_pb = R_for_pb = 0.0
    Pb_unit = ""
    if show_pb:
        R_for_pb = (
            R_total_eff_input if units == "field"
            else R_total_eff_input / SCF_STB_TO_CC_CC
        )
        T_for_pb = t_res_raw if units == "field" else t_res_raw * 9 / 5 + 32.0
        Pb_psia  = standing_bubble_point(R_for_pb, gamma_g, T_for_pb, api_gravity)
        Pb_disp  = Pb_psia if units == "field" else Pb_psia / BARA_TO_PSIA
        Pb_unit  = "psia"  if units == "field" else "bara"
        Pb_lo    = Pb_disp * 0.85
        Pb_hi    = Pb_disp * 1.15

    # ── Header ──────────────────────────────────────────────────────────────
    st.markdown(
        C.page_header(
            "🛢️ PVT Recombination",
            "Module 1 — Separator Fluid Recombination &nbsp;|&nbsp; Open ☰ for inputs",
        ),
        unsafe_allow_html=True,
    )

    # ── INPUT SUMMARY SECTION ────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-section-input-banner">📋 Input Summary — values used for this calculation</div>',
        unsafe_allow_html=True,
    )

    # Process diagram (now SVG-based)
    st.markdown(
        C.process_diagram(oil_source, n_stages, labels, stages, units, pres_unit, temp_unit),
        unsafe_allow_html=True,
    )

    # Input summary card echoing all key inputs
    st.markdown(
        C.input_summary_card(
            res=res, stages=stages, v_live=v_live, bo_sep=bo_sep_eff,
            n_stages=n_stages, oil_source=oil_source, r_sto=r_sto,
            p_charge=p_charge, c_o_x1e6=c_o_x1e6,
            gor_unit=gor_unit, pres_unit=pres_unit, temp_unit=temp_unit,
        ),
        unsafe_allow_html=True,
    )

    # ── OUTPUT SECTION BANNER ─────────────────────────────────────────────────
    st.markdown(
        '<div class="pvt-section-output-banner">⚗️ Calculation Results — lab charge instructions</div>',
        unsafe_allow_html=True,
    )

    # ── Hero charge card ──────────────────────────────────────────────────────
    st.markdown(
        C.hero_card(res, v_live, n_stages, labels, gor_unit, gas_unit, gor_err_pct,
                    R_total_eff_input, pres_unit),
        unsafe_allow_html=True,
    )

    # ── Metric cards ────────────────────────────────────────────────────────
    pb_metric = (
        C.bubble_point_metric_card(Pb_disp, Pb_unit)
        if show_pb else ""
    )
    st.markdown(C.metric_cards_row(res, gor_unit, pb_metric), unsafe_allow_html=True)

    # ── Bubble point card (expanded) ─────────────────────────────────────────
    if show_pb:
        st.markdown(
            C.bubble_point_card(Pb_disp, Pb_unit, Pb_lo, Pb_hi,
                                R_for_pb, gamma_g, T_for_pb, api_gravity),
            unsafe_allow_html=True,
        )

    # ── Per-stage breakdown ──────────────────────────────────────────────────
    st.markdown(
        C.section_label("Separator Conditions &amp; Gas Volumes"),
        unsafe_allow_html=True,
    )
    for sr in res.stage_results:
        st.markdown(
            C.stage_card(
                sr,
                P_input=stages[sr.stage_num - 1].P,
                T_input=stages[sr.stage_num - 1].T,
                pres_unit=pres_unit, temp_unit=temp_unit,
                gor_unit=gor_unit,   gas_unit=gas_unit,
                n_stages=n_stages,
                R_total_eff_cc=res.R_total_cc + res.R_STO_cc,
            ),
            unsafe_allow_html=True,
        )

    # Case 2: show stock tank flash card
    if oil_source == "stock_tank" and res.R_STO_cc > 0:
        st.markdown(
            C.sto_gas_card(res, gor_unit, gas_unit),
            unsafe_allow_html=True,
        )

    # ── Calculation steps ──────────────────────────────────────────────────
    with st.expander("📐 Calculation Steps (show/hide)", expanded=False):
        factor_r = (P_STD_PSIA / res.P_recomb_psia) * (res.T_recomb_R / T_STD_R) * res.Z_recomb
        R_total_eff_cc = res.R_total_cc + res.R_STO_cc

        # Unit conversion reference box
        conv_ref = (
            f'<div class="conv-table">'
            f'<b>Key unit conversions:</b><br>'
            f'1 scf/STB = {SCF_STB_TO_CC_CC:.6f} sm³/sm³ (cc gas std / cc STO)<br>'
            f'1 STB = 158,987 cc &nbsp;|&nbsp; 1 scf = 28,316.8 cc<br>'
            f'P_std = {P_STD_PSIA:.3f} psia &nbsp;|&nbsp; T_std = 60 °F = {T_STD_R:.2f} °R &nbsp;|&nbsp; T(°R) = T(°F) + 459.67'
            f'</div>'
        ) if units == "field" else (
            f'<div class="conv-table">'
            f'<b>Key unit conversions:</b><br>'
            f'1 sm³/sm³ = {1/SCF_STB_TO_CC_CC:.4f} scf/STB<br>'
            f'P_std = 1.01325 bara &nbsp;|&nbsp; T_std = 15 °C = 288.15 K<br>'
            f'T(K) = T(°C) + 273.15 &nbsp;|&nbsp; T(°R) = T(°F) + 459.67'
            f'</div>'
        )
        st.markdown(
            C.calc_step("Reference — Unit Conversions", conv_ref),
            unsafe_allow_html=True,
        )

        t_recomb_f_display = res.T_recomb_F
        st.markdown(
            C.calc_step(
                "Step 1 — Recombination factor  (converts std conditions → recomb conditions)",
                f"Purpose: converts volumes measured at standard conditions (P_std={P_STD_PSIA:.3f} psia, T_std=60°F) "
                f"to the actual volume at recombination conditions (P={res.P_recomb_psia:.2f} psia, T={t_recomb_f_display:.1f}°F).<br>"
                f"<br>"
                f"factor = (P_std / P_recomb) × (T_recomb_R / T_std_R) × Z_recomb<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= ({P_STD_PSIA:.3f} / {res.P_recomb_psia:.2f})"
                f" × ({res.T_recomb_R:.2f} / {T_STD_R:.2f})"
                f" × {res.Z_recomb:.3f}<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {P_STD_PSIA/res.P_recomb_psia:.6f} × {res.T_recomb_R/T_STD_R:.6f} × {res.Z_recomb:.4f}<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{factor_r:.6f} cc gas @ recomb per cc gas @ std</b><br>"
                f"<em style='font-size:0.75rem;color:#6a7090;'>"
                f"Note: T_recomb_R = {t_recomb_f_display:.1f}°F + 459.67 = {res.T_recomb_R:.2f} °R</em>",
            ),
            unsafe_allow_html=True,
        )

        # Show effective GOR breakdown for Case 2
        if oil_source == "stock_tank":
            sto_gor_conv = (
                f"{res.R_STO_input:.2f} scf/STB × {SCF_STB_TO_CC_CC:.6f} cc/cc per scf/STB = <b>{res.R_STO_cc:.6f} cc/cc</b>"
                if units == "field"
                else f"R_STO_cc = <b>{res.R_STO_cc:.6f} cc/cc</b>"
            )
            sep_gor_conv = (
                f"{res.R_total_input:.2f} scf/STB × {SCF_STB_TO_CC_CC:.6f} = {res.R_total_cc:.6f} cc/cc"
                if units == "field"
                else f"R_sep = {res.R_total_cc:.6f} cc/cc"
            )
            st.markdown(
                C.calc_step(
                    "Step 1b — Total effective GOR (Case 2: separator GOR + stock tank flash GOR)",
                    f"Sep. GOR:  {sep_gor_conv}<br>"
                    f"STO GOR:   {sto_gor_conv}<br>"
                    f"R_total_eff = R_sep + R_STO = {res.R_total_cc:.6f} + {res.R_STO_cc:.6f}"
                    f" = <b>{R_total_eff_cc:.6f} cc/cc</b><br>"
                    f"<br>"
                    f"Shrinkage factor SF = R_STO / R_sep = {res.R_STO_cc:.6f} / {res.R_total_cc:.6f}"
                    f" = <b>{res.shrinkage_factor:.6f}</b><br>"
                    f"<em style='font-size:0.75rem;color:#6a7090;'>"
                    f"Verification: R_sep × SF = {res.R_total_cc:.6f} × {res.shrinkage_factor:.6f} ≈ {res.R_total_cc * res.shrinkage_factor:.6f} cc/cc (= R_STO: {res.R_STO_cc:.6f})</em>",
                ),
                unsafe_allow_html=True,
            )

        bo_str = f"{bo_sep_eff:.4f}" + (" &nbsp;(Case 2: Bo=1.0, stock tank oil is the volume reference)" if oil_source == "stock_tank" else "")
        oil_sto_note = (
            f"<em style='font-size:0.75rem;color:#6a7090;'>V_oil_STO = V_oil_recomb / Bo = {res.V_oil_sep:.4f} / {bo_sep_eff:.4f} = {res.V_oil_STO:.4f} cc (stock-tank reference volume)</em>"
            if oil_source == "separator" else
            f"<em style='font-size:0.75rem;color:#6a7090;'>V_oil_STO = V_oil_recomb (Bo=1 for stock tank oil)</em>"
        )
        st.markdown(
            C.calc_step(
                "Step 2 — Cylinder mix ratio & oil volume at recombination pressure",
                f"mix_ratio = R_total_eff_cc × factor / Bo<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {R_total_eff_cc:.6f} × {factor_r:.6f} / {bo_str}<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{res.cylinder_mix_ratio:.6f} cc gas @ recomb per cc oil @ recomb</b><br>"
                f"<br>"
                f"V_oil_at_recomb = V_live / (1 + mix_ratio)<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {v_live:.2f} / (1 + {res.cylinder_mix_ratio:.6f})<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{res.V_oil_sep:.4f} cc</b><br>"
                f"{oil_sto_note}",
            ),
            unsafe_allow_html=True,
        )

        oil_label = "STO oil" if oil_source == "stock_tank" else "separator oil"
        delta_p = res.P_recomb_psia - res.P_charge_oil_psia
        charge_diff_pct = (res.V_oil_charge / res.V_oil_sep - 1.0) * 100.0 if res.V_oil_sep > 0 else 0.0
        st.markdown(
            C.calc_step(
                "Step 3 — Oil charging volume at P_charge  (isothermal compressibility correction)",
                f"Oil is loaded into the cell at P_charge ({res.P_charge_oil_psia:.1f} psia), which is "
                f"lower than P_recomb ({res.P_recomb_psia:.1f} psia). At lower pressure the oil "
                f"expands slightly — more oil must be loaded to yield the correct volume at P_recomb.<br>"
                f"<br>"
                f"ΔP = P_recomb − P_charge = {res.P_recomb_psia:.2f} − {res.P_charge_oil_psia:.2f} = {delta_p:.2f} psi<br>"
                f"c_o = {c_o_x1e6:.1f} × 10⁻⁶ psi⁻¹<br>"
                f"<br>"
                f"V_oil_charge = V_oil_recomb × (1 + c_o × ΔP)<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.V_oil_sep:.4f} × (1 + {c_o_x1e6:.2f}×10⁻⁶ × {delta_p:.2f})<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.V_oil_sep:.4f} × {1 + c_o_x1e6*1e-6*delta_p:.8f}<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{res.V_oil_charge:.4f} cc {oil_label} at P_charge = {res.P_charge_oil_psia:.0f} psia</b><br>"
                f"<em style='font-size:0.75rem;color:#6a7090;'>"
                f"Volume difference: {charge_diff_pct:+.4f}% — oil occupies {abs(charge_diff_pct):.4f}% "
                f"{'more' if charge_diff_pct > 0 else 'less'} at P_charge vs P_recomb</em>",
            ),
            unsafe_allow_html=True,
        )

        step_offset = 4
        for sr in res.stage_results:
            if units == "field":
                gor_conv = (
                    f"GOR = {sr.R_input:.2f} scf/STB<br>"
                    f"R_cc = {sr.R_input:.2f} scf/STB × {SCF_STB_TO_CC_CC:.6f} sm³/sm³ per scf/STB "
                    f"= <b>{sr.R_cc:.6f} cc gas(std) / cc STO</b>"
                )
            else:
                gor_conv = f"R_cc = <b>{sr.R_cc:.6f} cc gas(std) / cc STO</b>"

            st.markdown(
                C.calc_step(
                    f"Step {step_offset + sr.stage_num - 1} — Stage {sr.stage_num} ({sr.label}): gas volumes",
                    f"{gor_conv}<br>"
                    f"<br>"
                    f"V_gas_std = R_cc × V_oil_STO = {sr.R_cc:.6f} × {res.V_oil_STO:.4f} = <b>{sr.V_gas_std_cc:.4f} cc @ std</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {sr.V_gas_std_unit:.6f} {gas_unit} "
                    f"<em style='color:#6a7090;'>(= {sr.V_gas_std_cc:.4f} / {1/SCF_STB_TO_CC_CC*1000:.4f} × 1000)</em><br>"
                    f"<br>"
                    f"V_gas_recomb = V_gas_std × factor = {sr.V_gas_std_cc:.4f} × {factor_r:.6f} = <b>{sr.V_gas_recomb_cc:.4f} cc @ recomb</b><br>"
                    f"<em style='font-size:0.75rem;color:#6a7090;'>"
                    f"This stage contributes {sr.pct_of_total:.2f}% of total GOR — gas separator at {sr.Z:.4f} Z-factor</em>",
                ),
                unsafe_allow_html=True,
            )

        if oil_source == "stock_tank" and res.R_STO_cc > 0:
            if units == "field":
                sto_conv = (
                    f"Stock tank GOR = {res.R_STO_input:.2f} scf/STB<br>"
                    f"R_STO_cc = {res.R_STO_input:.2f} × {SCF_STB_TO_CC_CC:.6f} = <b>{res.R_STO_cc:.6f} cc/cc</b>"
                )
            else:
                sto_conv = f"R_STO_cc = <b>{res.R_STO_cc:.6f} cc/cc</b>"

            st.markdown(
                C.calc_step(
                    f"Step {step_offset + n_stages} — Stock tank flash gas (Case 2)",
                    f"{sto_conv}<br>"
                    f"<br>"
                    f"V_STO_gas_std = R_STO_cc × V_oil_STO = {res.R_STO_cc:.6f} × {res.V_oil_STO:.4f} = <b>{res.V_STO_gas_std_cc:.4f} cc @ std</b><br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.V_STO_gas_std_unit:.6f} {gas_unit}<br>"
                    f"<br>"
                    f"V_STO_gas_recomb = V_STO_gas_std × factor = {res.V_STO_gas_std_cc:.4f} × {factor_r:.6f} = <b>{res.V_STO_gas_recomb_cc:.4f} cc @ recomb</b><br>"
                    f"<em style='font-size:0.75rem;color:#6a7090;'>"
                    f"Lab convention: STO flash gas is charged from the same gas cylinder as separator gas.</em>",
                ),
                unsafe_allow_html=True,
            )

        if n_stages > 1 or (oil_source == "stock_tank" and res.R_STO_cc > 0):
            gas_parts = " + ".join(f"{sr.V_gas_recomb_cc:.4f}" for sr in res.stage_results)
            sto_part  = f" + {res.V_STO_gas_recomb_cc:.4f} (STO flash)" if oil_source == "stock_tank" else ""
            st.markdown(
                C.calc_step(
                    f"Step {step_offset + n_stages + (1 if oil_source == 'stock_tank' else 0)} — Total gas @ recombination",
                    f"V_gas_total_recomb = {gas_parts}{sto_part}<br>"
                    f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= <b>{res.total_V_gas_recomb_cc:.4f} cc @ recomb</b><br>"
                    f"V_gas_total_std    = <b>{res.total_V_gas_std_cc:.4f} cc @ std</b> = {res.total_V_gas_std_unit:.6f} {gas_unit}",
                ),
                unsafe_allow_html=True,
            )

        gor_ref_str = (
            f"{res.R_total_input:.4f} + {res.R_STO_input:.4f} = {R_total_eff_input:.4f}"
            if oil_source == "stock_tank"
            else f"{res.R_total_input:.4f}"
        )
        gor_cls = "gor-ok" if gor_err_pct < 0.1 else "gor-warn"
        gor_sym = "✓" if gor_err_pct < 0.1 else "⚠"
        st.markdown(
            C.calc_step(
                "GOR Verification  (back-calculate GOR from charged volumes)",
                f"Back-calc GOR = V_gas_total_std / (V_oil_STO × {SCF_STB_TO_CC_CC:.6f})" + (" [field→SI conv.]" if units == "field" else "") + "<br>"
                f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;= {res.GOR_check:.6f} {gor_unit}<br>"
                f"Input GOR:   {gor_ref_str} {gor_unit}<br>"
                f'<span class="{gor_cls}">{gor_sym} Relative error = {gor_err_pct:.6f}%</span>'
                + (" &nbsp;← ✓ within 0.1% tolerance" if gor_err_pct < 0.1 else " &nbsp;← ⚠ exceeds 0.1% tolerance"),
            ),
            unsafe_allow_html=True,
        )

    # ── Lab report ─────────────────────────────────────────────────────────
    with st.expander("📋 Lab Report — Full Data Sheet", expanded=False):
        st.markdown(
            C.lab_report_table(
                res=res, stages=stages, v_live=v_live, bo_sep=bo_sep_eff,
                n_stages=n_stages, gor_unit=gor_unit, pres_unit=pres_unit,
                temp_unit=temp_unit, gas_unit=gas_unit, gor_err_pct=gor_err_pct,
                R_total_eff_input=R_total_eff_input, c_o_x1e6=c_o_x1e6,
                show_pb=show_pb, Pb_disp=Pb_disp, Pb_lo=Pb_lo, Pb_hi=Pb_hi,
                Pb_unit=Pb_unit, gamma_g=gamma_g, api_gravity=api_gravity,
                T_for_pb=T_for_pb,
            ),
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if gor_err_pct < 0.01:
            st.success(f"GOR verification passed — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.5f}% error)")
        elif gor_err_pct < 0.5:
            st.info(f"GOR within tolerance — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.3f}% error)")
        else:
            st.error(f"GOR mismatch — {res.GOR_check:.4f} {gor_unit} ({gor_err_pct:.2f}% error) — review inputs.")

    # ── Footer ─────────────────────────────────────────────────────────────
    st.markdown(
        '<hr style="margin-top:1.5rem; border-color:#d0dcea;">'
        '<p style="text-align:center; color:#8fa3b8; font-size:0.75rem; line-height:1.6;">'
        "PVT Calculator Suite · Module 1: Separator Recombination<br>"
        "Std: 14.696 psia / 60°F &nbsp;·&nbsp;"
        "<em>Verify with a qualified reservoir engineer before laboratory use.</em>"
        "</p>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render() -> None:
    """Render the full recombination page. Call from app.py."""
    _init_state()
    _render_sidebar()
    _render_content()
