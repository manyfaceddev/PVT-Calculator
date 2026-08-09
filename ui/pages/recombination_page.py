"""
ui/pages/recombination_page.py — Recombination / Live Oil page (Task 12).

Two tabs, both bodies always instantiated (`st.tabs` runs both tab bodies on
every script pass — see `ui/pages/flash_page.py`'s module docstring for the
empirical basis):

- **Volumetric (SF/FF)**: `st.form` mirroring the Carlsen & Whitson (2020)
  `calculate_multistage` flow — Case 1/Case 2 oil-source selector, a single
  separator stage, recombination conditions, and oil-charging
  pressure/compressibility (`pvt.experiments.recombination.compressibility.
  effective_c_o`, constant or polynomial model).
- **Molar (composition)**: GOR/basis/shrinkage/density/MW manual inputs, OR
  an uploaded ADRIC LiveOil v4.1 workbook (`pvt.io.excel_import.liveoil_v41.
  read`, spooled through a tempfile exactly like Task 11's Flash-workbook
  upload) → `molar_split` + wellstream composition table (upload path only,
  since manual entry collects no composition) + `plan_loading` + a
  `verify_actual_gor` QC pill.

Whichever mode last produced a result is cached in `st.session_state` (keys
prefixed `recomb.`) and rendered below the relevant tab/form. Pure (no
top-level `streamlit` call) helpers live in `recombination_page_logic.py` —
see that module's docstring for why the split is required, not cosmetic.
"""

from __future__ import annotations

import streamlit as st

from pvt.core.exceptions import InputValidationError
from pvt.experiments.recombination.calc import calculate_multistage
from pvt.experiments.recombination.compressibility import effective_c_o
from pvt.experiments.recombination.loading import LoadingInputs, plan_loading, verify_actual_gor
from pvt.experiments.recombination.models import SeparatorStage
from pvt.experiments.recombination.molar import GorBasis, molar_split, wellstream
from pvt.experiments.recombination.validate import validate_multistage
from pvt.qc.checks import composition_normalization
from pvt.qc.engine import QCResult
from pvt.reporting.tables import recombination_tables
from ui.common import (
    calc_steps,
    figure_expander,
    metric_card,
    page_header,
    qc_panel,
    report_download,
)
from ui.pages.recombination_page_logic import (
    MANUAL_SAMPLE,
    read_uploaded_liveoil_bytes,
    upload_identity,
    volumetric_report_tables,
    wellstream_table,
)

page_header(
    "Recombination / Live Oil",
    "Module 1 — Separator Fluid Recombination & PVT Cell Charging",
)

tab_volumetric, tab_molar = st.tabs(["Volumetric (SF/FF)", "Molar (composition)"])

# ---------------------------------------------------------------------------
# Volumetric (SF/FF) tab
# ---------------------------------------------------------------------------
with tab_volumetric:
    st.caption(
        "Carlsen & Whitson (2020) multi-stage separator recombination — "
        "single separator stage, field units."
    )
    figure_expander(
        "How the bench test maps to these fields",
        "docs/manual/figures/recombination-scheme.png",
        "Separator oil and separator gas (or stock-tank oil and gas, for Case 2) are metered "
        "back together in the proportion this form computes, rebuilding a live sample that "
        "reproduces the reservoir fluid's gas-oil ratio. Oil source picks which oil you're "
        "recombining, and the Separator Stage/Oil Charging fields describe the metered gas "
        "and the pressure the recombined oil is charged into the cylinder at.",
    )
    with st.form("recomb.vol_form"):
        oil_source = st.radio(
            "Oil source",
            options=["separator", "stock_tank"],
            format_func=lambda x: (
                "Case 1 — Separator Oil + Separator Gas" if x == "separator"
                else "Case 2 — Stock Tank Oil + Separator Gas"
            ),
            key="recomb.vol_oil_source",
        )

        cols = st.columns(3)
        with cols[0]:
            v_live = st.number_input(
                "Live Fluid Volume (cc)", min_value=1.0, value=300.0, key="recomb.vol_v_live"
            )
        with cols[1]:
            sf = st.number_input(
                "Shrinkage Factor SF (V_STO/V_sep_oil) — Case 1",
                min_value=0.01, max_value=1.0, value=1.0, step=0.01, key="recomb.vol_sf",
            )
        with cols[2]:
            ff = st.number_input(
                "Flash Factor FF (scf/STB STO) — Case 2",
                min_value=0.0, value=0.0, key="recomb.vol_ff",
            )

        st.markdown("**Recombination Conditions**")
        rcols = st.columns(3)
        with rcols[0]:
            p_recomb = st.number_input(
                "Recombination Pressure (psia)", min_value=0.1, value=5014.7,
                key="recomb.vol_p_recomb",
            )
        with rcols[1]:
            t_recomb = st.number_input(
                "Recombination Temperature (F)", value=200.0, key="recomb.vol_t_recomb"
            )
        with rcols[2]:
            z_recomb = st.number_input(
                "Recombination Z-factor", min_value=0.01, max_value=2.0, value=0.82,
                step=0.001, format="%.3f", key="recomb.vol_z_recomb",
            )

        st.markdown("**Separator Stage**")
        scols = st.columns(4)
        with scols[0]:
            r_sep = st.number_input(
                "GOR (scf/STB)", min_value=0.1, value=850.0, key="recomb.vol_r_sep"
            )
        with scols[1]:
            p_sep = st.number_input(
                "Pressure (psia)", min_value=0.1, value=815.0, key="recomb.vol_p_sep"
            )
        with scols[2]:
            t_sep = st.number_input("Temperature (F)", value=145.0, key="recomb.vol_t_sep")
        with scols[3]:
            z_sep = st.number_input(
                "Z-factor", min_value=0.01, max_value=2.0, value=0.855,
                step=0.001, format="%.3f", key="recomb.vol_z_sep",
            )

        st.markdown("**Oil Charging**")
        p_charge = st.number_input(
            "Oil Charging Pressure (psia)", min_value=0.1, value=14.7,
            key="recomb.vol_p_charge",
        )
        c_o_model = st.radio(
            "Compressibility model", options=["constant", "polynomial"],
            format_func=lambda x: "Constant" if x == "constant" else "Polynomial (a0..a3)",
            key="recomb.vol_c_o_model", horizontal=True,
        )
        st.caption(
            "Constant: single c_o value (1/psia). Polynomial: "
            "c_o(P) = a0 + a1·P + a2·P² + a3·P³ "
            "(P = oil charging pressure, psia). Only the selected model above is used."
        )
        cvals = st.columns(5)
        with cvals[0]:
            c_o_const = st.number_input(
                "c_o constant (1/psia)", min_value=0.0, value=0.0, format="%.2e",
                key="recomb.vol_c_o_const",
            )
        with cvals[1]:
            c_o_a0 = st.number_input("a0", value=0.0, format="%.2e", key="recomb.vol_c_o_a0")
        with cvals[2]:
            c_o_a1 = st.number_input("a1", value=0.0, format="%.2e", key="recomb.vol_c_o_a1")
        with cvals[3]:
            c_o_a2 = st.number_input("a2", value=0.0, format="%.2e", key="recomb.vol_c_o_a2")
        with cvals[4]:
            c_o_a3 = st.number_input("a3", value=0.0, format="%.2e", key="recomb.vol_c_o_a3")

        vol_submitted = st.form_submit_button("Calculate", key="recomb.vol_submit")

    if vol_submitted:
        stage = SeparatorStage(R=r_sep, P=p_sep, T=t_sep, Z=z_sep, label="Separator")
        vol_errors = validate_multistage(
            [stage], v_live, sf, p_recomb, t_recomb, z_recomb, "field",
            oil_source=oil_source, FF=ff,
        )
        if vol_errors:
            # Invalid resubmit: clear any previously-rendered result rather
            # than leaving it on screen underneath the new errors.
            st.session_state.pop("recomb.vol_active", None)
            for error in vol_errors:
                st.error(error)
        else:
            try:
                c_o = (
                    effective_c_o("constant", c_o_const, p_charge)
                    if c_o_model == "constant"
                    else effective_c_o("polynomial", [c_o_a0, c_o_a1, c_o_a2, c_o_a3], p_charge)
                )
            except InputValidationError as exc:
                st.session_state.pop("recomb.vol_active", None)
                st.error("; ".join(exc.errors))
            else:
                st.session_state["recomb.vol_active"] = calculate_multistage(
                    [stage], v_live, sf, p_recomb, t_recomb, z_recomb, "field",
                    oil_source=oil_source, FF=ff, p_charge=p_charge, c_o=c_o,
                )

    vol_active = st.session_state.get("recomb.vol_active")
    if vol_active is None:
        st.info("Fill in the form above and click Calculate.")
    else:
        res = vol_active
        vol_gor_unit = "scf/STB" if res.units == "field" else "sm3/sm3"

        vol_metric_cols = st.columns(4)
        with vol_metric_cols[0]:
            metric_card("Oil Charge Volume", f"{res.V_oil_charge:.2f}", "cc")
        with vol_metric_cols[1]:
            metric_card("Total Gas @ Recomb", f"{res.total_V_gas_recomb_cc:.2f}", "cc")
        with vol_metric_cols[2]:
            metric_card("Cylinder Mix Ratio", f"{res.cylinder_mix_ratio:.4f}", "")
        with vol_metric_cols[3]:
            metric_card("GOR (check)", f"{res.GOR_check:.2f}", vol_gor_unit)

        vol_steps = [
            ("factor_recomb (Recombination Gas Factor)",
             "factor_recomb = (P_std/P_recomb) &times; (T_recomb_R/T_std_R) &times; Z_recomb<br>"
             f"= {res.factor_recomb:.6f} cc gas @ recomb / cc gas @ std"),
            ("Rp_total_cc (Total Producing GOR)",
             "Rp_cc = sum(R_stage_cc) + FF_cc<br>"
             f"= {res.Rp_total_cc:.6f} cc/cc"),
            ("cylinder_mix_ratio",
             "CMR = Rp_total_cc &times; factor_recomb / Bo_sep_eff<br>"
             f"= {res.cylinder_mix_ratio:.6f} cc gas @ recomb / cc oil"),
            ("V_oil_sep (Oil Volume at Recombination P)",
             "V_oil_sep = V_live / (1 + CMR)<br>"
             f"= {res.V_live:.2f} / (1 + {res.cylinder_mix_ratio:.6f}) = {res.V_oil_sep:.4f} cc"),
            ("V_oil_charge (Oil Volume at Charging P)",
             "V_oil_charge = V_oil_sep &times; exp(c_o &times; (P_recomb &minus; p_charge))<br>"
             f"= {res.V_oil_charge:.4f} cc"),
        ]
        calc_steps(vol_steps)

        report_download(
            volumetric_report_tables(res), MANUAL_SAMPLE, "recombination_volumetric_report.xlsx"
        )

# ---------------------------------------------------------------------------
# Molar (composition) tab
# ---------------------------------------------------------------------------
with tab_molar:
    st.caption(
        "Molar gas/oil recombination split, wellstream composition, and cylinder "
        "loading plan — ADRIC LiveOil v4.1 methodology."
    )
    figure_expander(
        "How your data flows",
        "docs/manual/figures/app-workflow.png",
        "Whichever mode you use — uploading a filled LiveOil workbook or typing values into "
        "the manual form — feeds the same molar-split calculation, and whichever one you "
        "last submitted successfully becomes the result shown below. Submitting a bad form, "
        "or a workbook the app can't read, clears any previous result rather than leaving a "
        "stale answer on screen.",
    )
    mtab_upload, mtab_manual = st.tabs(["Upload LiveOil Workbook", "Manual Entry"])

    with mtab_upload:
        st.caption("Upload a filled ADRIC LiveOil v4.1 template (.xlsx).")
        molar_uploaded = st.file_uploader(
            "Upload filled ADRIC LiveOil v4.1 template", type=["xlsx"],
            key="recomb.molar_uploaded_file",
        )
        if molar_uploaded is not None:
            # Gate the parse + state write on file identity: st.file_uploader
            # returns a non-None UploadedFile on EVERY script rerun while a
            # file remains attached, not just the run it was newly attached
            # on -- a naive "is not None" guard re-parses the workbook (and
            # re-pops "recomb.verify_result") on every unrelated widget
            # interaction elsewhere on the page, wiping the Actual-GOR QC
            # pill moments after the Verify form set it. Only (re-)process
            # when the attached file actually changes.
            file_id = upload_identity(molar_uploaded)
            if file_id != st.session_state.get("recomb.uploaded_file_id"):
                st.session_state["recomb.uploaded_file_id"] = file_id
                try:
                    molar_imp = read_uploaded_liveoil_bytes(molar_uploaded.getvalue())
                    molar_sto_mw = molar_imp.sto_stream.mw_from_mol()
                    molar_gas_mw = molar_imp.gas_stream.mw_from_mol()
                    molar_split_result = molar_split(
                        molar_imp.gor, molar_imp.gor_basis, molar_imp.shrinkage,
                        molar_imp.sto_density_60f, molar_sto_mw, molar_gas_mw,
                        z_std=molar_imp.z_std,
                    )
                except InputValidationError as exc:
                    st.session_state.pop("recomb.molar_active", None)
                    st.session_state.pop("recomb.verify_result", None)
                    st.session_state["recomb.upload_error"] = "; ".join(exc.errors)
                except ZeroDivisionError:
                    # A malformed-but-structurally-valid workbook (e.g. shrinkage
                    # or z_std of 0.0 in the Recombination sheet's B7/B12) reaches
                    # molar_split's divisions rather than the importer's own
                    # negative-composition guard -- degrade rather than crash.
                    st.session_state.pop("recomb.molar_active", None)
                    st.session_state.pop("recomb.verify_result", None)
                    st.session_state["recomb.upload_error"] = (
                        "Workbook values produce a division by zero (check shrinkage "
                        "factor and Z at standard conditions are non-zero)."
                    )
                else:
                    st.session_state.pop("recomb.upload_error", None)
                    st.session_state["recomb.molar_active"] = {
                        "split": molar_split_result,
                        "sto_stream": molar_imp.sto_stream,
                        "gas_stream": molar_imp.gas_stream,
                        "sto_density_60f": molar_imp.sto_density_60f,
                        "sto_mw": molar_sto_mw,
                        "z_std": molar_imp.z_std,
                        "loading": molar_imp.loading,
                        "sample": molar_imp.sample,
                    }
                    # A new split invalidates any prior Actual-GOR QC pill --
                    # it was graded against the OLD split's target GOR and
                    # would otherwise render (and export into the report)
                    # against this new one without ever having been
                    # re-verified.
                    st.session_state.pop("recomb.verify_result", None)
                    st.success(f"Loaded {molar_imp.sample.sample_id}.")

            # Re-render the cached error on EVERY run while this same (bad)
            # file stays attached -- review-round regression: the identity
            # gate above only runs the try/except (and thus only sets
            # st.error) on the run file_id actually changes, so an unrelated
            # rerun with the bad file still attached rendered nothing,
            # indistinguishable from no upload at all.
            upload_error = st.session_state.get("recomb.upload_error")
            if upload_error:
                st.error(upload_error)

    with mtab_manual:
        st.caption("Enter the recombination GOR/composition-summary and loading-cylinder inputs.")
        with st.form("recomb.molar_manual_form"):
            gcols = st.columns(3)
            with gcols[0]:
                m_gor = st.number_input(
                    "GOR (scf/STB)", min_value=0.0, value=339.0, key="recomb.molar_gor"
                )
            with gcols[1]:
                m_basis = st.radio(
                    "GOR basis", options=["separator", "stock_tank"],
                    format_func=lambda x: "Separator" if x == "separator" else "Stock Tank",
                    index=1, key="recomb.molar_basis",
                )
            with gcols[2]:
                m_shrinkage = st.number_input(
                    "Shrinkage Factor", min_value=0.01, max_value=1.0, value=1.0, step=0.01,
                    key="recomb.molar_shrinkage",
                )

            pcols = st.columns(3)
            with pcols[0]:
                m_sto_density = st.number_input(
                    "STO Density @60F (g/cc)", min_value=0.01, value=0.8196, format="%.4f",
                    key="recomb.molar_sto_density",
                )
            with pcols[1]:
                m_sto_mw = st.number_input(
                    "STO MW (g/mol)", min_value=0.01, value=187.05, key="recomb.molar_sto_mw"
                )
            with pcols[2]:
                m_gas_mw = st.number_input(
                    "Gas MW (g/mol)", min_value=0.01, value=26.10, key="recomb.molar_gas_mw"
                )

            m_z_std = st.number_input(
                "Z at Standard Conditions", min_value=0.01, max_value=2.0, value=0.99,
                step=0.001, format="%.3f", key="recomb.molar_z_std",
            )

            st.markdown("**Cylinder Loading**")
            lcols = st.columns(4)
            with lcols[0]:
                m_cyl_vol = st.number_input(
                    "Cylinder Volume (cc)", min_value=1.0, value=1000.0,
                    key="recomb.molar_cyl_vol",
                )
            with lcols[1]:
                m_target_oil = st.number_input(
                    "Target Oil Volume (cc)", min_value=0.01, value=150.0,
                    key="recomb.molar_target_oil",
                )
            with lcols[2]:
                m_oil_load_p = st.number_input(
                    "Oil Load Pressure (psig)", value=2000.0, key="recomb.molar_oil_load_p"
                )
            with lcols[3]:
                m_oil_load_t = st.number_input(
                    "Oil Load Temperature (F)", value=75.0, key="recomb.molar_oil_load_t"
                )

            lcols2 = st.columns(4)
            with lcols2[0]:
                m_gas_load_p = st.number_input(
                    "Gas Load Pressure (psig)", value=5000.0, key="recomb.molar_gas_load_p"
                )
            with lcols2[1]:
                m_gas_load_t = st.number_input(
                    "Gas Load Temperature (F)", value=75.0, key="recomb.molar_gas_load_t"
                )
            with lcols2[2]:
                m_z_gas_load = st.number_input(
                    "Z at Gas Load", min_value=0.01, max_value=2.0, value=0.85,
                    step=0.001, format="%.3f", key="recomb.molar_z_gas_load",
                )
            with lcols2[3]:
                m_sto_density_load = st.number_input(
                    "STO Density @ Load (g/cc)", min_value=0.01, value=0.885, format="%.4f",
                    key="recomb.molar_sto_density_load",
                )

            molar_submitted = st.form_submit_button("Calculate", key="recomb.molar_submit")

        if molar_submitted:
            m_gor_basis = GorBasis.SEPARATOR if m_basis == "separator" else GorBasis.STOCK_TANK
            st.session_state["recomb.molar_active"] = {
                "split": molar_split(
                    m_gor, m_gor_basis, m_shrinkage, m_sto_density, m_sto_mw, m_gas_mw,
                    z_std=m_z_std,
                ),
                "sto_stream": None,
                "gas_stream": None,
                "sto_density_60f": m_sto_density,
                "sto_mw": m_sto_mw,
                "z_std": m_z_std,
                "loading": LoadingInputs(
                    cylinder_volume_cc=m_cyl_vol, target_oil_cc=m_target_oil,
                    oil_load_p_psig=m_oil_load_p, oil_load_t_f=m_oil_load_t,
                    gas_load_p_psig=m_gas_load_p, gas_load_t_f=m_gas_load_t,
                    z_gas_load=m_z_gas_load, sto_density_at_load_g_cc=m_sto_density_load,
                ),
                "sample": MANUAL_SAMPLE,
            }
            # See the upload branch above: a new split invalidates any prior
            # Actual-GOR QC pill, which was graded against the OLD target GOR.
            st.session_state.pop("recomb.verify_result", None)

    # -----------------------------------------------------------------------
    # Shared molar results -- renders whichever mode last populated
    # "recomb.molar_active" (upload or manual, above).
    # -----------------------------------------------------------------------
    molar_active = st.session_state.get("recomb.molar_active")
    if molar_active is None:
        st.info("Upload a filled LiveOil v4.1 workbook, or fill in and submit the manual form.")
    else:
        split = molar_active["split"]
        sto_stream = molar_active["sto_stream"]
        gas_stream = molar_active["gas_stream"]

        molar_metric_cols = st.columns(4)
        with molar_metric_cols[0]:
            metric_card("Gas Mole Fraction", f"{split.f_gas:.4f}", "")
        with molar_metric_cols[1]:
            metric_card("Oil Mole Fraction", f"{split.f_oil:.4f}", "")
        with molar_metric_cols[2]:
            metric_card("Wellstream MW", f"{split.mw_wellstream:.2f}", "g/mol")
        with molar_metric_cols[3]:
            metric_card("GOR (effective)", f"{split.gor_scf_stb_effective:.2f}", "scf/STB")

        qc_results: list[QCResult] = []
        if sto_stream is not None and gas_stream is not None:
            try:
                qc_results = [
                    composition_normalization.check(sto_stream, "mol"),
                    composition_normalization.check(gas_stream, "mol"),
                ]
            except InputValidationError as exc:
                st.warning("Composition QC skipped: " + "; ".join(exc.errors))
            else:
                st.markdown("**Composition QC**")
                qc_panel(qc_results)
            # mw_consistency.check needs BOTH a mol% and a wt% basis; the
            # LiveOil v4.1 importer only reads the Mol% (INPUT) column (see
            # pvt.io.excel_import.liveoil_v41's module docstring, BLOCK C --
            # Wt% INPUT is not consumed), so these streams never carry a wt%
            # basis and mw_consistency.check would always raise
            # InputValidationError. Skipped entirely rather than
            # caught-and-hidden on every single run.

            st.markdown("**Wellstream Composition**")
            ws_mol = wellstream(split, sto_stream, gas_stream).normalized_mol()
            st.dataframe(wellstream_table(ws_mol))
        else:
            st.info("Upload a LiveOil workbook to see the wellstream composition table.")

        plan = None
        loading = molar_active["loading"]
        try:
            plan = plan_loading(
                loading, split, molar_active["sto_density_60f"], molar_active["sto_mw"],
                z_std=molar_active["z_std"],
            )
        except (InputValidationError, ZeroDivisionError) as exc:
            st.warning(f"Loading plan unavailable: {exc}")
        else:
            st.markdown("**Loading Plan**")
            plan_cols = st.columns(4)
            with plan_cols[0]:
                metric_card("Gas Charge Volume", f"{plan.v_gas_charge_cc:.2f}", "cc")
            with plan_cols[1]:
                metric_card("Total Charge Volume", f"{plan.total_charge_cc:.2f}", "cc")
            with plan_cols[2]:
                metric_card("Cylinder Utilization", f"{plan.utilization_pct:.1f}", "%")
            with plan_cols[3]:
                metric_card("Fits Cylinder", "Yes" if plan.fits else "No", "")

        st.markdown("**Actual-GOR Verification (QC)**")
        with st.form("recomb.verify_form"):
            vcols = st.columns(2)
            with vcols[0]:
                actual_oil_cc = st.number_input(
                    "Actual Oil Charged (cc)", min_value=0.0, value=0.0,
                    key="recomb.verify_oil_cc",
                )
            with vcols[1]:
                actual_gas_cc = st.number_input(
                    "Actual Gas Charged (cc)", min_value=0.0, value=0.0,
                    key="recomb.verify_gas_cc",
                )
            verify_submitted = st.form_submit_button("Verify Actual GOR", key="recomb.verify_submit")

        if verify_submitted:
            if actual_oil_cc <= 0 or actual_gas_cc <= 0:
                st.warning("Enter both actual oil and gas charge volumes (> 0) to verify.")
            else:
                try:
                    st.session_state["recomb.verify_result"] = verify_actual_gor(
                        actual_oil_cc, actual_gas_cc, loading, molar_active["sto_density_60f"],
                        target_gor_scf_stb=split.gor_scf_stb_effective,
                        z_std=molar_active["z_std"],
                    )
                except (InputValidationError, ZeroDivisionError) as exc:
                    st.warning(f"Verification unavailable: {exc}")

        verify_result = st.session_state.get("recomb.verify_result")
        if verify_result is not None:
            _, _, verify_qc = verify_result
            st.markdown("**Actual GOR QC**")
            qc_panel([verify_qc])
            qc_results = [*qc_results, verify_qc]

        if plan is not None:
            report_download(
                recombination_tables(split, plan, qc_results), molar_active["sample"],
                "recombination_molar_report.xlsx",
            )
        else:
            st.info("A cylinder loading plan is required to enable the report download.")
