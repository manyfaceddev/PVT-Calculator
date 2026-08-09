"""
ui/pages/flash_page.py — Flash Separation (SSF) page (Task 11).

Two input modes, both feeding the same downstream render (metric cards, QC
pills, Hoffmann plot, calc-steps, report download):

- **Upload**: `st.file_uploader` accepts a filled ADRIC Flash v6.1 workbook,
  parsed by `pvt.io.excel_import.flash_v61.read`.
- **Manual Entry**: `st.form` mirroring `FlashVolumetrics`'s 13 fields
  (number inputs, `pvt.experiments.flash.validate`'s explicit numeric bands
  as min/max where it has them), plus an optional `st.data_editor` GC
  composition table seeded with the 52 Katz-Firoozabadi codes.

Whichever mode last produced a valid result is cached in
`st.session_state["flash.active"]` and rendered below both tabs. `st.tabs`
runs *both* tab bodies on every script pass (only the active tab's content
is hidden client-side), so every widget above — in either tab — is always
instantiated; that's what lets `AppTest` reach the manual form's
`number_input`s without first "switching" to that tab.

Composition is optional in manual mode: composition QC pills, the Hoffmann
plot, and the mass-recombination report only render when both an oil and a
gas `CompositionStream` are available (uploaded, or assembled from the
composition editor).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from pvt.core import constants as c
from pvt.core import units as u
from pvt.core.exceptions import InputValidationError
from pvt.experiments.flash.calc import calculate
from pvt.experiments.flash.models import FlashVolumetrics
from pvt.experiments.flash.recombine import recombine_mass
from pvt.experiments.flash.validate import validate as validate_flash
from pvt.qc.checks import composition_normalization, hoffman_crump, mw_consistency
from pvt.qc.engine import QCResult
from pvt.reporting.tables import flash_tables
from ui.common import calc_steps, metric_card, page_header, qc_panel, report_download
from ui.pages.flash_page_logic import (
    FIELD_META,
    FIELD_RANGES,
    MANUAL_SAMPLE,
    read_uploaded_bytes,
    seed_composition_df,
    streams_from_composition_df,
)

page_header(
    "Flash Separation (SSF)",
    "Module 2 — Single-Stage Flash Separation & Recombination",
)

tab_upload, tab_manual = st.tabs(["Upload Workbook", "Manual Entry"])

with tab_upload:
    st.caption("Upload a filled ADRIC Flash v6.1 template (.xlsx).")
    uploaded = st.file_uploader(
        "Upload filled ADRIC Flash v6.1 template", type=["xlsx"], key="flash.uploaded_file"
    )
    if uploaded is not None:
        try:
            imp = read_uploaded_bytes(uploaded.getvalue())
        except InputValidationError as exc:
            st.error("; ".join(exc.errors))
        else:
            st.session_state["flash.active"] = {
                "volumetrics": imp.volumetrics,
                "oil_stream": imp.oil_stream,
                "gas_stream": imp.gas_stream,
                "sample": imp.sample,
            }
            st.success(f"Loaded {imp.sample.sample_id}.")

with tab_manual:
    st.caption("Mirrors the ADRIC Flash v6.1 Volumetrics_Master sheet.")
    with st.form("flash.manual_form"):
        values: dict[str, float] = {}
        for i in range(0, len(FIELD_META), 3):
            row_cols = st.columns(3)
            for col, (field, label, unit, default) in zip(row_cols, FIELD_META[i : i + 3]):
                lo, hi = FIELD_RANGES[field]
                with col:
                    values[field] = st.number_input(
                        f"{label} ({unit})" if unit else label,
                        min_value=lo, max_value=hi, value=default,
                        key=f"flash.{field}",
                    )
        submitted = st.form_submit_button("Calculate")

    st.markdown(
        "**GC Composition (optional)** — fill both mol% and wt% columns for "
        "each stream to enable composition QC and the Hoffmann plot; leave "
        "at zero to skip."
    )
    comp_df = st.data_editor(
        seed_composition_df(), key="flash.composition_editor", num_rows="fixed"
    )

    if submitted:
        volumetrics = FlashVolumetrics(**values)
        errors = validate_flash(volumetrics)
        if errors:
            for error in errors:
                st.error(error)
        else:
            oil_stream, gas_stream = streams_from_composition_df(comp_df)
            st.session_state["flash.active"] = {
                "volumetrics": volumetrics,
                "oil_stream": oil_stream,
                "gas_stream": gas_stream,
                "sample": MANUAL_SAMPLE,
            }

# ---------------------------------------------------------------------------
# Shared results area -- renders whichever mode last populated "flash.active"
# ---------------------------------------------------------------------------
active = st.session_state.get("flash.active")
if active is None:
    st.info("Upload a filled Flash v6.1 workbook, or fill in and submit the manual form.")
else:
    volumetrics = active["volumetrics"]
    oil_stream = active["oil_stream"]
    gas_stream = active["gas_stream"]
    sample = active["sample"]

    try:
        results = calculate(volumetrics)
    except InputValidationError as exc:
        st.error("; ".join(exc.errors))
    else:
        metric_cols = st.columns(5)
        with metric_cols[0]:
            metric_card("GOR", f"{results.gor_scf_bbl:.1f}", "scf/bbl")
        with metric_cols[1]:
            metric_card("Bo", f"{results.bo_flash:.4f}", "vol/vol")
        with metric_cols[2]:
            metric_card("Shrinkage", f"{results.shrinkage:.4f}", "")
        with metric_cols[3]:
            metric_card("Oil Density", f"{results.oil_density_60f_g_cc:.4f}", "g/cc")
        with metric_cols[4]:
            metric_card("API Gravity", f"{results.api:.1f}", "API")

        qc_results: list[QCResult] = []
        if oil_stream is not None and gas_stream is not None:
            try:
                qc_results = [
                    composition_normalization.check(gas_stream, "mol"),
                    composition_normalization.check(gas_stream, "wt"),
                    composition_normalization.check(oil_stream, "mol"),
                    composition_normalization.check(oil_stream, "wt"),
                    mw_consistency.check(gas_stream),
                    mw_consistency.check(oil_stream),
                ]
            except InputValidationError as exc:
                st.warning("Composition QC skipped: " + "; ".join(exc.errors))
            else:
                st.markdown("**Composition QC**")
                qc_panel(qc_results)

                hoffman = hoffman_crump.check(
                    gas_stream, oil_stream,
                    p_psia=u.mbar_to_psia(volumetrics.gas_abs_pressure_mbar),
                    t_f=u.c_to_f(volumetrics.gas_temp_c),
                )
                qc_results.append(hoffman.qc)
                st.markdown("**Hoffmann-Crump K-value Consistency**")
                qc_panel([hoffman.qc])
                if hoffman.points:
                    chart_df = pd.DataFrame(
                        {
                            "F": [p.f_factor for p in hoffman.points],
                            "log10(K*P)": [p.log10_kp for p in hoffman.points],
                        }
                    )
                    st.scatter_chart(chart_df, x="F", y="log10(K*P)")

        t_gas_k = volumetrics.gas_temp_c + 273.15
        steps = [
            ("V_press (Charge Pressure Volume)",
             "V_press = (pump_final &minus; pump_initial) &times; pump_constant &times; VCF<br>"
             f"= ({volumetrics.pump_final_cc:.4f} &minus; {volumetrics.pump_initial_cc:.4f}) "
             f"&times; {volumetrics.pump_constant:.4f} &times; {volumetrics.vcf:.4f} "
             f"= {results.v_press_cc:.4f} cc"),
            ("m_oil (Flashed Oil Mass)",
             "m_oil = oil_gross &minus; oil_tare<br>"
             f"= {volumetrics.oil_gross_g:.4f} &minus; {volumetrics.oil_tare_g:.4f} "
             f"= {results.m_oil_g:.4f} g"),
            ("V_gas_std (Gas Volume at Standard Conditions)",
             "V_gas_meas = (gasometer_final &minus; gasometer_initial) &times; gasometer_factor<br>"
             f"= ({volumetrics.gasometer_final_cc:.4f} &minus; "
             f"{volumetrics.gasometer_initial_cc:.4f}) &times; {volumetrics.gasometer_factor:.4f} "
             f"= {results.v_gas_meas_cc:.4f} cc<br>"
             "V_gas_std = V_gas_meas &times; (P/P_std) &times; (T_std/T)<br>"
             f"= {results.v_gas_meas_cc:.4f} &times; ({volumetrics.gas_abs_pressure_mbar:.2f}/"
             f"{c.P_STD_MBAR:.2f}) &times; ({c.T_STD_K:.2f}/{t_gas_k:.2f}) "
             f"= {results.v_gas_std_cc:.4f} cc"),
            ("GOR (Gas-Oil Ratio)",
             "GOR = V_gas_std / V_sto<br>"
             f"= {results.v_gas_std_cc:.4f} / {volumetrics.v_sto_cc:.4f} "
             f"= {results.gor_cc_cc:.4f} cc/cc = {results.gor_scf_bbl:.2f} scf/bbl"),
            ("Bo (Flash Formation Volume Factor)",
             "Bo = V_press / V_sto<br>"
             f"= {results.v_press_cc:.4f} / {volumetrics.v_sto_cc:.4f} "
             f"= {results.bo_flash:.4f} vol/vol"),
        ]
        calc_steps(steps)

        if oil_stream is not None and gas_stream is not None:
            try:
                recomb = recombine_mass(results.m_oil_g, results.m_gas_g, oil_stream, gas_stream)
            except InputValidationError as exc:
                st.warning("Report unavailable: " + "; ".join(exc.errors))
            else:
                tables = flash_tables(results, recomb, qc_results)
                report_download(tables, sample, "flash_separation_report.xlsx")
        else:
            st.info(
                "Enter/upload GC composition (mol% and wt%, both streams) to enable the "
                "mass-recombination report download."
            )
