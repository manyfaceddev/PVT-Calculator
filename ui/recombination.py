"""
ui/recombination.py — Streamlit page for separator fluid recombination.

Entry point: call render() from app.py.
Owns: session state, sidebar inputs, output layout.
Does not contain: calculation logic (pvt.recombination) or CSS (ui.styles).

Two oil-source cases:
  Case 1 — Separator Oil + Separator Gas
  Case 2 — Stock Tank Oil + Separator Gas  (adds Flash Factor FF input)
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
        "units": "field", "v_live": 2000.0, "sf": 0.92,
        "p_recomb": 5000.0, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 850.0, "p_sep_1": 800.0, "t_sep_1": 140.0, "z_sep_1": 0.865,
        "show_pb": True, "gamma_g": 0.72, "api_gravity": 42.0, "t_res": 210.0,
        "oil_source": "separator", "ff": 0.0,
        "p_charge_oil": 2000.0,
    },
    "Medium oil, Middle East (moderate GOR)": {
        "units": "field", "v_live": 2000.0, "sf": 0.95,
        "p_recomb": 5000.0, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 583.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
        "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
        "oil_source": "separator", "ff": 0.0,
        "p_charge_oil": 2000.0,
    },
    "Heavy oil, Offshore (low GOR)": {
        "units": "field", "v_live": 2000.0, "sf": 0.97,
        "p_recomb": 5000.0, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 100.0, "p_sep_1":  60.0, "t_sep_1": 100.0, "z_sep_1": 0.972,
        "show_pb": True, "gamma_g": 0.82, "api_gravity": 22.0, "t_res": 155.0,
        "oil_source": "separator", "ff": 0.0,
        "p_charge_oil": 2000.0,
    },
    "Stock tank oil example (Case 2 — with Flash Factor)": {
        "units": "field", "v_live": 2000.0, "sf": 0.88,
        "p_recomb": 5000.0, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 400.0, "p_sep_1": 250.0, "t_sep_1": 100.0, "z_sep_1": 0.910,
        "show_pb": True, "gamma_g": 0.74, "api_gravity": 36.0, "t_res": 180.0,
        "oil_source": "stock_tank", "ff": 60.0,
        "p_charge_oil": 2000.0,
    },
}

# ASCII process-flow diagrams — rendered in the pvt-ascii monospace block.
# Case 1: separator oil goes directly to cell.
# Case 2: oil passes through stock tank (SF/FF shrinkage), then STO to cell.
_DIAGRAMS: dict[str, str] = {
    "separator": """\
  ┌────────────┐───gas ─────────────────►┐
  │ SEPARATOR  │                 ┌───────▼──────┐
  │ P1, T1, Z1 │                 │  CELL        │
  └─────┬──────┘  oil ──────────►│  ░░ GAS ░░░  │
        └───────────────────────►|  ▓▓ OIL ▓▓▓  │
                                 └──────────────┘""",
    "stock_tank": """\
  ┌────────────┐─┌────gas ─────────────────────────►┐
  │ SEPARATOR  │ |                         ┌────────▼─────┐
  │ P1, T1, Z1 │ |    ┌─────────────────┐  │  CELL        │
  └─────┬──────┘ |    │ STOCK TANK OIL  │  │  ░░ GAS ░░░  │
        └────────┘───►│  P_atm  SF  FF  ├─►│  ▓▓ STO ▓▓▓  │
                      │  ↑ STO gas vent │  └──────────────┘
                      └─────────────────┘""",
}

_SS_DEFAULTS: dict = {
    "units": "field", "_units_prev": "field",
    "v_live": 2000.0,
    "sf": 0.95,                  # Separator-Oil Shrinkage Factor (V_STO / V_sep_oil)
    "p_recomb": 5000.0, "t_recomb": 70.0, "z_recomb": 1.00,
    "p_charge_oil": 2000.0,      # Pressure at which oil is loaded into cell (psia)
    "c_o_mode": "constant",      # "constant" or "spline_fit"
    "c_o_const": 100e-6,         # Oil compressibility for constant mode (1/psia)
    "c_o_a0": 100e-6, "c_o_a1": 0.0, "c_o_a2": 0.0, "c_o_a3": 0.0,  # Spline fit polynomial coefficients
    "r_sep_1": 583.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
    "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
    "example_sel": "— select an example —",
    "oil_source": "separator",
    "ff":         0.0,           # Flash Factor (scf/STB STO or sm³/sm³); Case 2 only
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

    # Separator stage (always 1 stage now)
    p = st.session_state.get("p_sep_1", 0.0)
    t = st.session_state.get("t_sep_1", 0.0)
    r = st.session_state.get("r_sep_1", 0.0)
    if to_si:
        st.session_state["p_sep_1"] = round(p / BARA_TO_PSIA,     2)
        st.session_state["t_sep_1"] = round((t - 32.0) * 5 / 9,   1)
        st.session_state["r_sep_1"] = round(r * SCF_STB_TO_CC_CC, 2)
    elif to_field:
        st.session_state["p_sep_1"] = round(p * BARA_TO_PSIA,     1)
        st.session_state["t_sep_1"] = round(t * 9 / 5 + 32.0,     1)
        st.session_state["r_sep_1"] = round(r / SCF_STB_TO_CC_CC, 1)

    for key in ("p_recomb", "p_charge_oil"):
        pv = st.session_state.get(key, P_STD_PSIA)
        if to_si:
            st.session_state[key] = round(pv / BARA_TO_PSIA, 2)
        elif to_field:
            st.session_state[key] = round(pv * BARA_TO_PSIA, 1)

    # Oil compressibility: constant mode
    c_o_const = st.session_state.get("c_o_const", 100e-6)
    if to_si:
        st.session_state["c_o_const"] = c_o_const / BARA_TO_PSIA
    elif to_field:
        st.session_state["c_o_const"] = c_o_const * BARA_TO_PSIA

    # Oil compressibility: spline fit coefficients (polynomial in pressure)
    # c_o(P) = a0 + a1*P + a2*P^2 + a3*P^3
    # When converting pressure units, coefficients must be adjusted:
    # a0: 1/pressure unit → multiply by pressure conversion
    # a1: 1/(pressure unit)^2 → multiply by pressure conversion^2
    # etc.
    cf = BARA_TO_PSIA
    for i, key in enumerate(("c_o_a0", "c_o_a1", "c_o_a2", "c_o_a3"), 0):
        av = st.session_state.get(key, 0.0)
        if to_si:
            st.session_state[key] = av / (cf ** (i + 1))
        elif to_field:
            st.session_state[key] = av * (cf ** (i + 1))

    tr = st.session_state.get("t_recomb", T_STD_F)
    if to_si:
        st.session_state["t_recomb"] = round((tr - 32.0) * 5 / 9, 1)
    elif to_field:
        st.session_state["t_recomb"] = round(tr * 9 / 5 + 32.0,   1)

    t_res = st.session_state.get("t_res", 200.0)
    if to_si:
        st.session_state["t_res"] = round((t_res - 32.0) * 5 / 9, 1)
    elif to_field:
        st.session_state["t_res"] = round(t_res * 9 / 5 + 32.0,   1)

    # Flash Factor (scf/STB ↔ sm³/sm³); SF and c_o are dimensionless/unit-invariant
    ff = st.session_state.get("ff", 0.0)
    if to_si:
        st.session_state["ff"] = round(ff * SCF_STB_TO_CC_CC, 4)
    elif to_field:
        st.session_state["ff"] = round(ff / SCF_STB_TO_CC_CC, 1)

    st.session_state["_units_prev"] = cur


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## ⚙️ Inputs")
        st.markdown("---")

        # ── Examples ──────────────────────────────────────────────────────────
        st.markdown("### 📂 Load Example")
        st.selectbox(
            "Example", options=list(_EXAMPLES.keys()),
            key="example_sel", on_change=_on_example_change,
            label_visibility="collapsed",
        )
        st.markdown("---")

        # ── Unit system ───────────────────────────────────────────────────────
        st.selectbox(
            "Unit System",
            options=["field", "si"],
            format_func=lambda x: "Field  (psia · °F · scf/STB)" if x == "field"
                                  else "SI  (bara · °C · sm³/sm³)",
            key="units", on_change=_on_units_change,
        )
        st.markdown("---")

        units = st.session_state["units"]

        # ── Oil Source ────────────────────────────────────────────────────────
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

        oil_source = st.session_state["oil_source"]

        # ── Cell & Fluid Setup ────────────────────────────────────────────────
        st.markdown("### 📐 Cell & Fluid Setup")
        st.number_input(
            "Target Live Fluid Volume (cc)", min_value=1.0, max_value=10000.0, step=100.0,
            key="v_live",
            help="Total volume of recombined fluid in the cell at P_recomb and T_recomb.",
        )

        if oil_source == "separator":
            st.number_input(
                "Shrinkage Factor SF  (V_STO / V_sep_oil)",
                min_value=0.50, max_value=1.00, step=0.01, format="%.3f", key="sf",
                help=(
                    "Separator-Oil Shrinkage Factor (Carlsen & Whitson 2020).\n\n"
                    "Fraction of metered separator oil volume that becomes stock-tank oil "
                    "after the final pressure drop to atmospheric conditions.\n\n"
                    "SF = V_STO / V_sep_oil = 1 / Bo_sep\n\n"
                    "Typical range: 0.65 – 0.99 (lower SF = more gas shrinkage)"
                ),
            )
        else:
            st.info(
                "**Case 2:** You are charging stock-tank oil directly.  "
                "Enter the Flash Factor (FF) below — this is the gas liberated "
                "when separator oil shrinks to STO conditions."
            )
            ff_lbl = "Flash Factor FF (scf/STB STO)" if units == "field" else "Flash Factor FF (sm³/sm³)"
            st.number_input(
                ff_lbl,
                min_value=0.0, max_value=2000.0,
                step=10.0 if units == "field" else 0.1,
                key="ff",
                help=(
                    "Flash Factor FF (Carlsen & Whitson 2020).\n\n"
                    "Gas liberated per STB STO when separator oil is brought to "
                    "atmospheric stock-tank conditions (1 atm, 60°F). "
                    "This equals Rₛ,sep — the solution GOR of the separator oil.\n\n"
                    "Total producing GOR: Rp = R_sep + FF\n\n"
                    "Typical range: 5 – 1000 scf/STB STO"
                ),
            )
        st.markdown("---")

        # ── Recombination Conditions ──────────────────────────────────────────
        p_lbl = "Recomb. Pressure (psia)" if units == "field" else "Recomb. Pressure (bara)"
        t_lbl = "Recomb. Temperature (°F)" if units == "field" else "Recomb. Temperature (°C)"
        st.markdown("### 🔩 Recombination Conditions")
        st.number_input(
            p_lbl, min_value=14.7, max_value=30000.0, step=100.0, key="p_recomb",
            help="Final cell pressure — typically downhole reservoir or wellhead conditions.",
        )
        st.number_input(
            t_lbl, step=1.0, key="t_recomb",
            help="Temperature at recombination conditions (downhole or wellhead).",
        )
        st.number_input(
            "Z-factor @ Recomb. P & T", min_value=0.01, max_value=2.00,
            step=0.001, format="%.3f", key="z_recomb",
            help="Gas compressibility factor at recombination conditions.",
        )
        st.markdown("---")

        # ── Oil Charging Conditions ───────────────────────────────────────────
        p_charge_lbl = "Oil Charging Pressure (psia)" if units == "field" else "Oil Charging Pressure (bara)"
        st.markdown("### 🧪 Oil Charging Conditions")
        st.number_input(
            p_charge_lbl,
            min_value=0.1, max_value=10000.0,
            step=5.0 if units == "field" else 0.2,
            key="p_charge_oil",
            help=(
                "Pressure at which the oil is physically loaded into the recombination cell.\n\n"
                "Oil is charged first (at this pressure), then separator gas is added "
                "at recombination pressure to bring the cell to target conditions.\n\n"
                "The charging volume is adjusted for oil compressibility between "
                "charging pressure and recombination pressure."
            ),
        )

        # Oil compressibility mode selector
        st.markdown("**Oil Isothermal Compressibility**")
        c_o_mode = st.radio(
            "Compressibility model",
            options=["constant", "spline_fit"],
            format_func=lambda x: "Constant value" if x == "constant" else "Pressure-dependent (spline fit)",
            key="c_o_mode",
            label_visibility="collapsed",
        )

        if c_o_mode == "constant":
            c_o_lbl = "c_o (1/psia)" if units == "field" else "c_o (1/bara)"
            st.number_input(
                c_o_lbl,
                min_value=0.0, max_value=500e-6 if units == "field" else 500e-6 / BARA_TO_PSIA,
                step=10e-6 if units == "field" else 10e-6 / BARA_TO_PSIA,
                format="%.2e",
                key="c_o_const",
                help=(
                    "Oil isothermal compressibility (constant).\n\n"
                    "Typical range: 5e-6 to 20e-6 1/psi (field) or 3.4e-7 to 1.4e-6 1/bara (SI).\n\n"
                    "Set to 0 for incompressible oil."
                ),
            )
        else:
            # Spline fit mode: polynomial coefficients
            st.markdown("*Polynomial model: c_o(P) = a₀ + a₁·P + a₂·P² + a₃·P³*")
            a0_lbl = "a₀ (1/psia constant term)" if units == "field" else "a₀ (1/bara constant term)"
            a1_lbl = "a₁ (1/psia² linear coeff)" if units == "field" else "a₁ (1/bara² linear coeff)"
            a2_lbl = "a₂ (1/psia³ quad coeff)" if units == "field" else "a₂ (1/bara³ quad coeff)"
            a3_lbl = "a₃ (1/psia⁴ cubic coeff)" if units == "field" else "a₃ (1/bara⁴ cubic coeff)"
            
            col1, col2 = st.columns(2)
            with col1:
                st.number_input(a0_lbl, format="%.2e", key="c_o_a0")
                st.number_input(a2_lbl, format="%.2e", key="c_o_a2")
            with col2:
                st.number_input(a1_lbl, format="%.2e", key="c_o_a1")
                st.number_input(a3_lbl, format="%.2e", key="c_o_a3")
            
            st.caption(
                "Provide coefficients in your current unit system. "
                "When switching units, coefficients will be adjusted accordingly."
            )

        st.markdown("---")

        # ── Separator Stage ───────────────────────────────────────────────────
        gor_lbl  = "GOR (scf/STB)"    if units == "field" else "GOR (sm³/sm³)"
        pres_lbl = "Pressure (psia)"  if units == "field" else "Pressure (bara)"
        temp_lbl = "Temperature (°F)" if units == "field" else "Temperature (°C)"
        st.markdown("### Stage — Separator")
        st.number_input(
            gor_lbl, min_value=0.1,
            step=10.0 if units == "field" else 0.5, key="r_sep_1",
        )
        st.number_input(
            pres_lbl, min_value=0.1,
            step=5.0 if units == "field" else 0.2, key="p_sep_1",
        )
        st.number_input(temp_lbl, step=1.0, key="t_sep_1")
        st.number_input(
            "Z-factor", min_value=0.01, max_value=2.00,
            step=0.001, format="%.3f", key="z_sep_1",
            help="Compressibility factor at separator conditions.",
        )
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
# Helper functions
# ---------------------------------------------------------------------------

def _compute_compressibility(ss: dict, p_psia: float) -> float:
    """
    Compute oil compressibility at a given pressure based on the mode.
    
    Args:
        ss: session state dictionary
        p_psia: pressure in psia
    
    Returns:
        c_o in 1/psia (internal units)
    """
    c_o_mode = ss.get("c_o_mode", "constant")
    
    if c_o_mode == "constant":
        c_o = ss.get("c_o_const", 100e-6)
        if ss.get("units") == "si":
            c_o = c_o * BARA_TO_PSIA  # convert from 1/bara to 1/psia
    else:
        # spline_fit mode: evaluate polynomial c_o(P) = a0 + a1*P + a2*P^2 + a3*P^3
        a0 = ss.get("c_o_a0", 100e-6)
        a1 = ss.get("c_o_a1", 0.0)
        a2 = ss.get("c_o_a2", 0.0)
        a3 = ss.get("c_o_a3", 0.0)
        
        # Convert coefficients from current units to internal (1/psia)
        if ss.get("units") == "si":
            cf = BARA_TO_PSIA
            a0 = a0 * cf
            a1 = a1 * cf**2
            a2 = a2 * cf**3
            a3 = a3 * cf**4
        
        # Evaluate polynomial at p_psia
        c_o = a0 + a1*p_psia + a2*p_psia**2 + a3*p_psia**3
    
    return c_o


# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

def _render_content() -> None:
    ss = st.session_state
    units       = ss["units"]
    v_live      = ss["v_live"]
    sf          = ss.get("sf",           0.95)   # Separator-Oil Shrinkage Factor (Case 1)
    p_recomb    = ss["p_recomb"]
    t_recomb    = ss["t_recomb"]
    z_recomb    = ss["z_recomb"]
    show_pb     = ss["show_pb"]
    gamma_g     = ss.get("gamma_g",     0.72)
    api_gravity = ss.get("api_gravity", 40.0)
    t_res_raw   = ss.get("t_res",       200.0)
    oil_source  = ss.get("oil_source",  "separator")
    ff          = ss.get("ff",          0.0)    # Flash Factor (Case 2 only)
    p_charge    = ss.get("p_charge_oil", 14.696)
    
    # Compute oil compressibility at charging pressure
    p_charge_psia_for_c_o = p_charge if units == "field" else p_charge * BARA_TO_PSIA
    c_o = _compute_compressibility(ss, p_charge_psia_for_c_o)
    
    n_stages    = 1                              # always 1 separator stage

    stages = [
        SeparatorStage(
            R=ss["r_sep_1"], P=ss["p_sep_1"],
            T=ss["t_sep_1"], Z=ss["z_sep_1"],
            label="Separator",
        )
    ]

    # ── Validation ─────────────────────────────────────────────────────────
    errors = validate_multistage(
        stages, v_live, sf, p_recomb, t_recomb, z_recomb, units,
        oil_source=oil_source, FF=ff,
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
        stages, v_live, sf, p_recomb, t_recomb, z_recomb, units,
        oil_source=oil_source, FF=ff, p_charge=p_charge, c_o=c_o,
    )

    gor_unit  = "scf/STB" if units == "field" else "sm³/sm³"
    pres_unit = "psia"    if units == "field" else "bara"
    temp_unit = "°F"      if units == "field" else "°C"
    gas_unit  = "scf"     if units == "field" else "sm³"

    # ── Oil charging pressure (adjusted for compressibility) ──
    p_charge_psia = p_charge if units == "field" else p_charge * BARA_TO_PSIA

    # GOR error: compare GOR_check (back-calc) against total Rp = R_sep + FF
    R_total_eff_input = res.R_total_input + res.FF_input   # Case 1: FF_input=0 so same as R_total_input
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

    # ── ASCII cell diagram ───────────────────────────────────────────────────
    st.markdown(C.section_label("Cell Diagram"), unsafe_allow_html=True)
    st.markdown(
        f'<div class="pvt-ascii">{_DIAGRAMS[oil_source]}</div>',
        unsafe_allow_html=True,
    )

    # ── Hero charge card ──────────────────────────────────────────────────────
    st.markdown(
        C.hero_card(res, v_live, p_charge_psia,
                    gor_unit, gas_unit, gor_err_pct, R_total_eff_input, pres_unit),
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
                n_stages=1,
                R_total_eff_cc=res.Rp_total_cc,
            ),
            unsafe_allow_html=True,
        )

    # Case 2: show flash gas card
    if oil_source == "stock_tank" and res.FF_cc > 0:
        st.markdown(
            C.sto_gas_card(res, gor_unit, gas_unit),
            unsafe_allow_html=True,
        )

    # ── Calculation steps ──────────────────────────────────────────────────
    with st.expander("📐 Calculation Steps", expanded=False):
        factor_r = res.factor_recomb
        Rp_total_cc = res.Rp_total_cc

        st.markdown(
            C.calc_step(
                "Step 1 — Recombination factor",
                f"factor_recomb = (P_std/P_recomb) × (T_recomb/T_std) × Z_recomb<br>"
                f"&nbsp;&nbsp;&nbsp;= ({P_STD_PSIA:.3f}/{res.P_recomb_psia:.2f})"
                f" × ({res.T_recomb_R:.2f}/{T_STD_R:.2f})"
                f" × {res.Z_recomb:.3f}"
                f" = <b>{factor_r:.6f} cc recomb / cc std</b>",
            ),
            unsafe_allow_html=True,
        )

        # Show effective GOR breakdown for Case 2
        if oil_source == "stock_tank":
            ff_gor_conv = (
                f"{res.FF_input:.2f} {gor_unit} × {SCF_STB_TO_CC_CC:.6f} = <b>{res.FF_cc:.6f} cc/cc</b>"
                if units == "field"
                else f"FF_cc = <b>{res.FF_cc:.6f} cc/cc</b>"
            )
            st.markdown(
                C.calc_step(
                    "Step 1b — Total producing GOR (Case 2: Rp = R_sep + FF)",
                    f"R_sep_total = {res.R_total_cc:.6f} cc/cc<br>"
                    f"FF (Flash Factor): {ff_gor_conv}<br>"
                    f"Rp = R_sep + FF = {res.R_total_cc:.6f} + {res.FF_cc:.6f}"
                    f" = <b>{Rp_total_cc:.6f} cc/cc</b>",
                ),
                unsafe_allow_html=True,
            )

        sf_str = f"{sf:.4f}" + (" (Case 2: STO charged directly)" if oil_source == "stock_tank" else "")
        bo_eff = 1.0 / sf if oil_source == "separator" else 1.0
        st.markdown(
            C.calc_step(
                "Step 2 — Cylinder mix ratio & oil volume at recombination conditions",
                f"mix_ratio = Rp_cc × factor / (1/SF)"
                f" = {Rp_total_cc:.5f} × {factor_r:.6f} / {bo_eff:.4f}"
                f" = <b>{res.cylinder_mix_ratio:.6f} cc gas / cc oil</b><br>"
                f"V_oil_sep = V_live / (1 + mix_ratio)"
                f" = {v_live:.1f} / (1 + {res.cylinder_mix_ratio:.4f})"
                f" = <b>{res.V_oil_sep:.2f} cc  (oil volume at P_recomb)</b><br>"
                f"SF = {sf_str} &nbsp;→&nbsp; V_oil_STO = V_oil_sep × SF"
                f" = {res.V_oil_sep:.2f} × {sf:.4f} = <b>{res.V_oil_STO:.2f} cc</b>",
            ),
            unsafe_allow_html=True,
        )

        step_offset = 3
        for sr in res.stage_results:
            gor_conv = (
                f"{sr.R_input:.1f} scf/STB × {SCF_STB_TO_CC_CC:.6f} = <b>{sr.R_cc:.5f} cc/cc</b>"
                if units == "field"
                else f"R_cc = <b>{sr.R_cc:.5f} cc/cc</b>"
            )
            st.markdown(
                C.calc_step(
                    f"Step {step_offset + sr.stage_num - 1} — Stage {sr.stage_num} ({sr.label}) gas",
                    f"{gor_conv}<br>"
                    f"V_gas_std = {sr.R_cc:.5f} × {res.V_oil_STO:.2f}"
                    f" = <b>{sr.V_gas_std_cc:.2f} cc</b>"
                    f" ({sr.V_gas_std_unit:.5f} {gas_unit})<br>"
                    f"V_gas_recomb = V_gas_std × factor"
                    f" = {sr.V_gas_std_cc:.2f} × {factor_r:.6f}"
                    f" = <b>{sr.V_gas_recomb_cc:.2f} cc</b>",
                ),
                unsafe_allow_html=True,
            )

        if oil_source == "stock_tank" and res.FF_cc > 0:
            ff_conv = (
                f"{res.FF_input:.1f} scf/STB × {SCF_STB_TO_CC_CC:.6f} = <b>{res.FF_cc:.5f} cc/cc</b>"
                if units == "field"
                else f"FF_cc = <b>{res.FF_cc:.5f} cc/cc</b>"
            )
            st.markdown(
                C.calc_step(
                    f"Step {step_offset + n_stages} — Flash gas (FF, Case 2)",
                    f"{ff_conv}<br>"
                    f"V_FF_gas_std = FF_cc × V_oil_STO = {res.FF_cc:.5f} × {res.V_oil_STO:.2f}"
                    f" = <b>{res.V_FF_gas_std_cc:.2f} cc</b>"
                    f" ({res.V_FF_gas_std_unit:.5f} {gas_unit})<br>"
                    f"V_FF_gas_recomb = V_FF_gas_std × factor"
                    f" = {res.V_FF_gas_std_cc:.2f} × {factor_r:.6f}"
                    f" = <b>{res.V_FF_gas_recomb_cc:.2f} cc</b><br>"
                    f"<em>Loaded from separator gas cylinder (standard lab convention)</em>",
                ),
                unsafe_allow_html=True,
            )

        if oil_source == "stock_tank" and res.FF_cc > 0:
            st.markdown(
                C.calc_step(
                    f"Step {step_offset + n_stages + (1 if oil_source == 'stock_tank' else 0)} — Total gas @ recomb",
                    " + ".join(f"{sr.V_gas_recomb_cc:.2f}" for sr in res.stage_results)
                    + (f" + {res.V_FF_gas_recomb_cc:.2f} (FF flash)" if oil_source == "stock_tank" else "")
                    + f" = <b>{res.total_V_gas_recomb_cc:.2f} cc @ recomb</b>"
                    f" ({res.total_V_gas_std_cc:.2f} cc @ std)",
                ),
                unsafe_allow_html=True,
            )

        gor_ref_str = (
            f"{res.R_total_input:.4f} + {res.FF_input:.4f} (FF) = {R_total_eff_input:.4f}"
            if oil_source == "stock_tank"
            else f"{res.R_total_input:.4f}"
        )
        gor_cls = "gor-ok" if gor_err_pct < 0.1 else "gor-warn"
        gor_sym = "✓" if gor_err_pct < 0.1 else "⚠"
        st.markdown(
            C.calc_step(
                "GOR Verification",
                f"Back-calc: {res.GOR_check:.4f} {gor_unit}"
                f" — input: {gor_ref_str} {gor_unit}<br>"
                f'<span class="{gor_cls}">{gor_sym} error = {gor_err_pct:.5f}%</span>',
            ),
            unsafe_allow_html=True,
        )

    # ── Lab report ─────────────────────────────────────────────────────────
    with st.expander("📋 Lab Report — Full Data Sheet", expanded=False):
        st.markdown(
            C.lab_report_table(
                res=res, stages=stages, v_live=v_live, sf=sf,
                n_stages=n_stages, gor_unit=gor_unit, pres_unit=pres_unit,
                temp_unit=temp_unit, gas_unit=gas_unit, gor_err_pct=gor_err_pct,
                R_total_eff_input=R_total_eff_input,
                p_charge_psia=p_charge_psia,
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
