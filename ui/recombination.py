"""
ui/recombination.py — Streamlit page for separator fluid recombination.

Entry point: call render() from app.py.
Owns: session state, sidebar inputs, output layout.
Does not contain: calculation logic (pvt.recombination) or CSS (ui.styles).
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
    },
    "Medium oil, Middle East (moderate GOR)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.01,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 380.0, "p_sep_1": 150.0, "t_sep_1": 120.0, "z_sep_1": 0.921,
        "r_sep_2":  20.0, "p_sep_2":  50.0, "t_sep_2":  90.0, "z_sep_2": 0.986,
        "r_sep_3":  10.0, "p_sep_3":  20.0, "t_sep_3":  75.0, "z_sep_3": 0.994,
        "show_pb": True, "gamma_g": 0.76, "api_gravity": 34.0, "t_res": 175.0,
    },
    "Heavy oil, Offshore (low GOR)": {
        "units": "field", "n_stages": 1, "v_live": 2000.0, "bo_sep": 1.03,
        "p_recomb": 5014.73, "t_recomb": 70.0, "z_recomb": 1.00,
        "r_sep_1": 100.0, "p_sep_1":  60.0, "t_sep_1": 100.0, "z_sep_1": 0.972,
        "r_sep_2":  10.0, "p_sep_2":  20.0, "t_sep_2":  75.0, "z_sep_2": 0.990,
        "r_sep_3":   5.0, "p_sep_3":  10.0, "t_sep_3":  60.0, "z_sep_3": 0.995,
        "show_pb": True, "gamma_g": 0.82, "api_gravity": 22.0, "t_res": 155.0,
    },
}

_STAGE_LABELS: dict[int, list[str]] = {
    1: ["Separator"],
    2: ["HP Separator", "LP Separator"],
    3: ["HP Separator", "MP Separator", "LP Separator"],
}

_DIAGRAMS: dict[int, str] = {
    1: """\
  ┌────────────┐  gas ──────────────────►┐
  │ SEPARATOR  │                 ┌───────▼──────┐
  │ P1, T1, Z1 │                 │  CELL        │
  └─────┬──────┘  oil ──────────►│  ░░ GAS ░░░ │
        └────────────────────────►  ▓▓ OIL ▓▓▓ │
                                 └──────────────┘""",
    2: """\
  ┌──────────┐  G1 ─────────────────────►┐
  │ STAGE 1  │                   ┌────────▼──────┐
  │ HP Sep   │         ┌──────┐  │  CELL         │
  └────┬─────┘  oil   │STAGE2│G2►  ░░ G1+G2 ░░ │
       └─────────────►│LP Sep│  │  ▓▓▓ OIL ▓▓▓ │
                       └──────┘  └───────────────┘""",
    3: """\
  ┌──────┐G1►┐   ┌──────┐G2►┤   ┌──────┐G3►┤
  │ HP   │   │   │  MP  │   │   │  LP  │   │  ┌────────────┐
  │ Sep  │oil└──►│  Sep │oil└──►│  Sep │oil└─►│ CELL       │
  └──────┘       └──────┘       └──┬───┘      │ ░ G1+G2+G3 │
                                    └─────────►│ ▓▓▓ OIL ▓▓ │
                                              └────────────┘""",
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

        # Live fluid & Bo
        units = st.session_state["units"]
        st.markdown("### 🛢️ Live Fluid")
        st.number_input(
            "Live Fluid Volume (cc)", min_value=1.0, max_value=10000.0, step=100.0,
            key="v_live",
            help="Total volume of recombined fluid to prepare (oil + gas at recomb P & T)",
        )
        st.number_input(
            "Bo at Separator (res vol / STO vol)",
            min_value=0.80, max_value=3.00, step=0.01, key="bo_sep",
        )
        st.markdown("---")

        # Recombination conditions
        p_lbl = "Recomb. Pressure (psia)" if units == "field" else "Recomb. Pressure (bara)"
        t_lbl = "Recomb. Temperature (°F)" if units == "field" else "Recomb. Temperature (°C)"
        st.markdown("### 🔩 Recombination Conditions")
        st.number_input(
            p_lbl, min_value=14.7, max_value=30000.0, step=100.0, key="p_recomb",
            help="Cell charging pressure — typically 3 000–10 000 psia. Enter absolute pressure.",
        )
        st.number_input(
            t_lbl, step=1.0, key="t_recomb",
            help="Temperature at which gas cylinder and PVT cell are charged",
        )
        st.number_input(
            "Z-factor @ Recomb. P & T", min_value=0.01, max_value=2.00,
            step=0.001, format="%.3f", key="z_recomb",
            help="Gas compressibility factor at recombination conditions",
        )
        st.markdown("---")

        # Per-stage separator inputs
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
                help="Compressibility factor at separator conditions",
            )
            if n < n_stages:
                st.markdown("---")

        st.markdown("---")

        # Bubble point
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
                    help="Use reservoir temperature, not separator temperature",
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

    stages = [
        SeparatorStage(
            R=ss[f"r_sep_{n}"], P=ss[f"p_sep_{n}"],
            T=ss[f"t_sep_{n}"], Z=ss[f"z_sep_{n}"],
            label=labels[n - 1],
        )
        for n in range(1, n_stages + 1)
    ]

    # ── Validation ───────────────────────────────────────────────────────────
    errors = validate_multistage(stages, v_live, bo_sep, p_recomb, t_recomb, z_recomb, units)
    if errors:
        st.markdown(C.page_header("🛢️ PVT Recombination", "Module 1 — Separator Fluid Recombination"),
                    unsafe_allow_html=True)
        for e in errors:
            st.error(f"**Input error:** {e}")
        st.info("Open the sidebar (☰) to fix the inputs.")
        st.stop()

    # ── Calculate ────────────────────────────────────────────────────────────
    res = calculate_multistage(stages, v_live, bo_sep, p_recomb, t_recomb, z_recomb, units)

    gor_unit  = "scf/STB" if units == "field" else "sm³/sm³"
    pres_unit = "psia"    if units == "field" else "bara"
    temp_unit = "°F"      if units == "field" else "°C"
    gas_unit  = "scf"     if units == "field" else "sm³"

    gor_err_pct = (
        abs(res.GOR_check - res.R_total_input) / res.R_total_input * 100
        if res.R_total_input > 0 else 0.0
    )

    # ── Bubble point ─────────────────────────────────────────────────────────
    Pb_disp = Pb_lo = Pb_hi = T_for_pb = R_for_pb = 0.0
    Pb_unit = ""
    if show_pb:
        R_for_pb = (
            res.R_total_input if units == "field"
            else res.R_total_input / SCF_STB_TO_CC_CC
        )
        T_for_pb = t_res_raw if units == "field" else t_res_raw * 9 / 5 + 32.0
        Pb_psia  = standing_bubble_point(R_for_pb, gamma_g, T_for_pb, api_gravity)
        Pb_disp  = Pb_psia if units == "field" else Pb_psia / BARA_TO_PSIA
        Pb_unit  = "psia"  if units == "field" else "bara"
        Pb_lo    = Pb_disp * 0.85
        Pb_hi    = Pb_disp * 1.15

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(
        C.page_header(
            "🛢️ PVT Recombination",
            "Module 1 — Separator Fluid Recombination &nbsp;|&nbsp; Open ☰ for inputs",
        ),
        unsafe_allow_html=True,
    )

    # ── Hero charge card ─────────────────────────────────────────────────────
    st.markdown(
        C.hero_card(res, v_live, n_stages, labels, gor_unit, gas_unit, gor_err_pct),
        unsafe_allow_html=True,
    )

    # ── Metric cards ─────────────────────────────────────────────────────────
    pb_metric = (
        C.bubble_point_metric_card(Pb_disp, Pb_unit)
        if show_pb else ""
    )
    st.markdown(C.metric_cards_row(res, gor_unit, pb_metric), unsafe_allow_html=True)

    # ── Bubble point card (expanded) ──────────────────────────────────────────
    if show_pb:
        st.markdown(
            C.bubble_point_card(Pb_disp, Pb_unit, Pb_lo, Pb_hi,
                                R_for_pb, gamma_g, T_for_pb, api_gravity),
            unsafe_allow_html=True,
        )

    # ── Per-stage breakdown ───────────────────────────────────────────────────
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
            ),
            unsafe_allow_html=True,
        )

    # ── Calculation steps ─────────────────────────────────────────────────────
    with st.expander("📐 Calculation Steps", expanded=False):
        factor_r = (P_STD_PSIA / res.P_recomb_psia) * (res.T_recomb_R / T_STD_R) * res.Z_recomb

        st.markdown(
            C.calc_step(
                "Step 1 — Cylinder mix ratio",
                f"factor_recomb = (P_std/P_recomb) × (T_recomb/T_std) × Z_recomb<br>"
                f"&nbsp;&nbsp;&nbsp;= ({P_STD_PSIA:.3f}/{res.P_recomb_psia:.2f})"
                f" × ({res.T_recomb_R:.2f}/{T_STD_R:.2f})"
                f" × {res.Z_recomb:.3f}"
                f" = <b>{factor_r:.6f} cc recomb/cc std</b><br>"
                f"mix_ratio = R_total_cc × factor / Bo"
                f" = {res.R_total_cc:.5f} × {factor_r:.6f} / {bo_sep:.3f}"
                f" = <b>{res.cylinder_mix_ratio:.6f} cc gas/cc oil</b>",
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            C.calc_step(
                "Step 2 — Separator oil charge",
                f"V_oil_sep = V_live / (1 + mix_ratio)"
                f" = {v_live:.1f} / (1 + {res.cylinder_mix_ratio:.4f})"
                f" = <b>{res.V_oil_sep:.2f} cc</b><br>"
                f"V_oil_STO = {res.V_oil_sep:.2f} / {bo_sep:.3f}"
                f" = <b>{res.V_oil_STO:.2f} cc</b>",
            ),
            unsafe_allow_html=True,
        )
        for sr in res.stage_results:
            gor_conv = (
                f"{sr.R_input:.1f} scf/STB × 0.178107 = <b>{sr.R_cc:.5f} cc/cc</b>"
                if units == "field"
                else f"R_cc = <b>{sr.R_cc:.5f} cc/cc</b>"
            )
            st.markdown(
                C.calc_step(
                    f"Step {sr.stage_num + 2} — Stage {sr.stage_num} ({sr.label}) gas",
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
        if n_stages > 1:
            st.markdown(
                C.calc_step(
                    f"Step {n_stages + 3} — Total gas",
                    " + ".join(f"{sr.V_gas_recomb_cc:.2f}" for sr in res.stage_results)
                    + f" = <b>{res.total_V_gas_recomb_cc:.2f} cc @ recomb</b>"
                    f" ({res.total_V_gas_std_cc:.2f} cc @ std)",
                ),
                unsafe_allow_html=True,
            )
        gor_cls = "gor-ok" if gor_err_pct < 0.1 else "gor-warn"
        gor_sym = "✓" if gor_err_pct < 0.1 else "⚠"
        st.markdown(
            C.calc_step(
                "GOR Verification",
                f"Back-calc: {res.GOR_check:.4f} {gor_unit}"
                f" — input: {res.R_total_input:.4f}<br>"
                f'<span class="{gor_cls}">{gor_sym} error = {gor_err_pct:.5f}%</span>',
            ),
            unsafe_allow_html=True,
        )

        st.markdown(C.section_label("Cell Diagram"), unsafe_allow_html=True)
        st.markdown(
            f'<div class="pvt-ascii">{_DIAGRAMS[n_stages]}</div>',
            unsafe_allow_html=True,
        )

    # ── Lab report ────────────────────────────────────────────────────────────
    with st.expander("📋 Lab Report — Full Data Sheet", expanded=False):
        st.markdown(
            C.lab_report_table(
                res=res, stages=stages, v_live=v_live, bo_sep=bo_sep,
                n_stages=n_stages, gor_unit=gor_unit, pres_unit=pres_unit,
                temp_unit=temp_unit, gas_unit=gas_unit, gor_err_pct=gor_err_pct,
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

    # ── Footer ────────────────────────────────────────────────────────────────
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
