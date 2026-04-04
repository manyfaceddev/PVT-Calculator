"""
ui/styles.py — CSS stylesheet for the PVT Calculator Streamlit app.

Call inject() once at the top of any page that needs these styles.

Colour palette
──────────────
  Deep navy (sidebar / primary)  : #0d1829 · #1a2e4a · #2a4a70 · #d4e4f4
  Petroleum teal (accents)       : #0d4a3a · #1a7a60 · #2aaa88 · #d4f0e8
  Gas blue                       : #1a3d6e · #2060b0 · #4a90d4 · #d4e8fa
  Amber / oil                    : #6b3d00 · #b06010 · #e08020 · #fff3e0
  Neutral warm                   : #1a1a18 · #3a3a36 · #7a7a72 · #f7f5f2
  Card white                     : #ffffff · shadow rgba(0,0,0,0.07)
"""

import streamlit as st

_CSS = """
<style>

/* ══════════════════════════════════════════════════════
   GLOBAL
══════════════════════════════════════════════════════ */
html, body, [data-testid="stAppViewContainer"] {
    background: #eef0f4;
    font-family: 'Segoe UI', system-ui, Arial, sans-serif;
    color: #1a1a20;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR (input zone — deep navy petroleum)
══════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #0d1829;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stSelectbox label {
    color: #b0c8e8 !important;
    font-size: 0.82rem;
}
[data-testid="stSidebar"] h2 { color: #60b4f0 !important; font-size: 1rem !important; }
[data-testid="stSidebar"] h3 { color: #4a9ada !important; font-size: 0.88rem !important; }
[data-testid="stSidebar"] hr { border-color: #1a2e4a; }
[data-testid="stSidebar"] .stInfo { background: #0d1e38; border-color: #1a4070; color: #70a8d8; font-size: 0.78rem; }

/* ══════════════════════════════════════════════════════
   PAGE HEADER
══════════════════════════════════════════════════════ */
.pvt-header {
    background: linear-gradient(135deg, #08111e 0%, #0d2040 55%, #1a3560 100%);
    color: #fff;
    padding: 1.3rem 1.5rem 1.1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 1rem;
    border-left: 5px solid #2a70c0;
}
.pvt-header h1 {
    margin: 0; font-size: 1.4rem; letter-spacing: 0.3px; line-height: 1.25;
    font-weight: 700;
}
.pvt-header p {
    margin: 0.3rem 0 0 0; color: #80b8e8; font-size: 0.81rem;
}

/* ══════════════════════════════════════════════════════
   INPUT / OUTPUT SECTION BANNERS
══════════════════════════════════════════════════════ */
.pvt-section-input-banner {
    background: linear-gradient(90deg, #0d2040 0%, #1a3560 100%);
    color: #b0cce8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 10px;
    border-left: 4px solid #2a70c0;
}
.pvt-section-output-banner {
    background: linear-gradient(90deg, #0a3020 0%, #1a5038 100%);
    color: #90d8b8;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 10px;
    border-left: 4px solid #2aaa80;
}

/* ══════════════════════════════════════════════════════
   PROCESS FLOW DIAGRAM
══════════════════════════════════════════════════════ */
.pvt-flow-wrap {
    background: #ffffff;
    border: 1px solid #d8d4cc;
    border-radius: 10px;
    padding: 14px 16px 12px 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}
.pvt-flow-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 0.71rem;
    font-weight: 700;
    letter-spacing: 0.4px;
    margin-bottom: 10px;
}
.pvt-flow-badge.case1 { background: #d4f0e4; color: #0d3d2a; border: 1px solid #2a9966; }
.pvt-flow-badge.case2 { background: #fff3e0; color: #6b3d00; border: 1px solid #e08020; }

/* Flow nodes */
.pfd-node {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 2px solid;
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 0.72rem;
    font-weight: 600;
    min-width: 82px;
    text-align: center;
    line-height: 1.3;
}
.pfd-node .pfd-icon { font-size: 1.1rem; line-height: 1; margin-bottom: 2px; }
.pfd-node .pfd-title { font-size: 0.73rem; font-weight: 700; }
.pfd-node .pfd-sub { font-size: 0.64rem; font-weight: 400; margin-top: 2px; line-height: 1.3; }

.pfd-node.well    { background:#e8f4ee; border-color:#1a6644; color:#0d3d2a; }
.pfd-node.sep     { background:#e6f0fb; border-color:#2060b0; color:#1a3d6e; }
.pfd-node.gascyl  { background:#e8f0fb; border-color:#4a90d4; color:#1a4a80; }
.pfd-node.stank   { background:#fff3e0; border-color:#e08020; color:#6b3d00; }
.pfd-node.cell    { background:#d4f0e4; border-color:#1a6644; color:#0d3d2a; font-weight:800; }

/* Flow arrows and labels */
.pfd-arrow { font-size:1.1rem; color:#888; padding:0 3px; }
.pfd-stream-lbl { font-size:0.62rem; color:#666; text-align:center; line-height:1.3; padding:0 3px; }
.pfd-connector { border-top:2px dashed #bbb; flex:1; min-width:20px; margin:0 2px; align-self:center; }
.pfd-row { display:flex; align-items:center; flex-wrap:wrap; gap:2px; margin-bottom:4px; }
.pfd-gas-row { display:flex; align-items:center; flex-wrap:wrap; gap:2px; margin-bottom:2px; }
.pfd-oil-row { display:flex; align-items:center; flex-wrap:wrap; gap:2px; }
.pfd-note {
    font-size:0.72rem; color:#5a5a52; line-height:1.5;
    border-top:1px solid #ebe8e2; padding-top:7px; margin-top:8px;
}

/* ══════════════════════════════════════════════════════
   INPUT SUMMARY CARD (echo of sidebar inputs)
══════════════════════════════════════════════════════ */
.pvt-input-summary {
    background: #f0f4fa;
    border: 1px solid #c8d8ee;
    border-left: 4px solid #2a70c0;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 12px;
    font-size: 0.78rem;
    color: #2a3040;
}
.pvt-input-summary .is-title {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.8px;
    color: #1a4a80; font-weight: 700; margin-bottom: 6px;
}
.pvt-input-summary .is-grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 3px 20px;
}
.pvt-input-summary .is-row { display:flex; justify-content:space-between; }
.pvt-input-summary .is-lbl { color:#6a7090; }
.pvt-input-summary .is-val { font-weight:600; color:#1a1a20; }

/* ══════════════════════════════════════════════════════
   RESULTS ZONE HEADER
══════════════════════════════════════════════════════ */
.pvt-results-header {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1.2px;
    color: #1a4a80; font-weight: 800; margin: 14px 0 8px 0;
    padding-bottom: 5px; border-bottom: 2px solid #2a70c0;
    display: flex; align-items: center; gap: 6px;
}

/* ══════════════════════════════════════════════════════
   HERO CHARGE CARD (primary results)
══════════════════════════════════════════════════════ */
.pvt-hero {
    background: linear-gradient(135deg, #08111e 0%, #0d2040 45%, #1a3060 100%);
    color: #fff;
    border-radius: 12px;
    padding: 1.3rem 1.4rem 1.1rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 18px rgba(0,0,0,0.22);
    border-left: 5px solid #2a70c0;
}
.pvt-hero .hero-title {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1.2px;
    color: #80b8e8; margin-bottom: 0.9rem;
}
.pvt-hero .hero-step-num {
    display:inline-flex; align-items:center; justify-content:center;
    width:20px; height:20px; border-radius:50%; background:#2a70c0;
    font-size:0.68rem; font-weight:800; color:#fff; flex-shrink:0;
    margin-right:6px;
}
.pvt-hero .charge-row  {
    display: flex; align-items: baseline; gap: 0.5rem; margin: 0.5rem 0;
}
.pvt-hero .charge-val  { font-size: 2rem; font-weight: 800; color: #fff; line-height: 1; }
.pvt-hero .charge-val.highlight { color: #f0d060; }
.pvt-hero .charge-unit { font-size: 1rem; color: #90c8f0; font-weight: 400; }
.pvt-hero .charge-label{ font-size: 0.8rem; color: #70a8d8; margin-top: -0.1rem; }
.pvt-hero .charge-label.highlight { color: #f0d060; font-weight: 600; }
.pvt-hero .hero-divider{ border:none; border-top:1px solid rgba(255,255,255,0.12); margin:0.85rem 0; }
.pvt-hero .hero-sub    { font-size: 0.78rem; color: #7ab0d4; }

/* Shrinkage info banner inside hero */
.pvt-hero .shrink-banner {
    background: rgba(255,200,40,0.12);
    border: 1px solid rgba(255,200,40,0.3);
    border-radius: 5px;
    padding: 5px 10px;
    font-size: 0.75rem;
    color: #f0d060;
    margin: 4px 0 8px 0;
}

/* ══════════════════════════════════════════════════════
   METRIC CARDS
══════════════════════════════════════════════════════ */
.pvt-card-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.65rem;
    margin-bottom: 1rem;
}
.pvt-metric-card {
    background: #fff;
    border-radius: 10px;
    padding: 0.85rem 0.9rem;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border-top: 3px solid #c8d4e8;
}
.pvt-metric-card .m-val  { font-size: 1.45rem; font-weight: 700; color: #0d2550; line-height: 1.1; }
.pvt-metric-card .m-unit { font-size: 0.76rem; color: #1a4a80; font-weight: 600; }
.pvt-metric-card .m-lbl  { font-size: 0.68rem; color: #6a7090; text-transform: uppercase; letter-spacing: 0.4px; margin-top: 0.2rem; }
.pvt-metric-card.accent-green { background: #e8f8f2; border-top-color: #1a7060; }
.pvt-metric-card.accent-green .m-val { color: #0d4030; }
.pvt-metric-card.accent-blue  { background: #e6f0fb; border-top-color: #2060b0; }
.pvt-metric-card.accent-blue  .m-val { color: #1a3d6e; }
.pvt-metric-card.accent-amber { background: #fff3e0; border-top-color: #e08020; }
.pvt-metric-card.accent-amber .m-val { color: #6b3d00; }

/* ══════════════════════════════════════════════════════
   BUBBLE POINT CARD
══════════════════════════════════════════════════════ */
.pb-card {
    background: #fffbea;
    border: 1px solid #e8c840;
    border-left: 5px solid #c88000;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
}
.pb-card .pb-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.8px; color: #7a5000; margin-bottom: 0.45rem; font-weight: 700; }
.pb-card .pb-val   { font-size: 2rem; font-weight: 800; color: #7a3800; line-height: 1.1; }
.pb-card .pb-unit  { font-size: 1rem; font-weight: 400; color: #9a6010; }
.pb-card .pb-range { font-size: 0.8rem; color: #9a7010; margin-top: 0.3rem; }
.pb-card .pb-note  { font-size: 0.73rem; color: #aa8020; margin-top: 0.6rem; font-style: italic; line-height: 1.45; }

/* ══════════════════════════════════════════════════════
   SECTION HEADING
══════════════════════════════════════════════════════ */
.pvt-section {
    font-size: 0.68rem; text-transform: uppercase; letter-spacing: 1px;
    color: #2a5080; margin: 1.1rem 0 0.5rem 0; font-weight: 700;
    border-bottom: 1px solid #c8d4e4; padding-bottom: 3px;
}

/* ══════════════════════════════════════════════════════
   STAGE BREAKDOWN CARDS
══════════════════════════════════════════════════════ */
.stage-card {
    background: #fff;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    margin-bottom: 0.65rem;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    border-left: 4px solid #2060b0;
}
.stage-card.sto-stage { border-left-color: #e08020; }
.stage-card .sc-title { font-size: 0.86rem; font-weight: 700; color: #0d3d2a; margin-bottom: 0.45rem; }
.stage-card .sc-row   { display: flex; justify-content: space-between; font-size: 0.83rem; padding: 0.13rem 0; border-bottom: 1px solid #f0ece6; }
.stage-card .sc-row:last-child { border-bottom: none; }
.stage-card .sc-lbl   { color: #7a7a72; }
.stage-card .sc-val   { font-weight: 600; color: #1a1a18; }
.stage-card .sc-val.gas-recomb { color: #1a4a80; font-size: 1rem; font-weight: 700; }
.stage-card .sc-val.sto-recomb { color: #b06010; font-size: 1rem; font-weight: 700; }

/* ══════════════════════════════════════════════════════
   CALCULATION STEP BLOCKS
══════════════════════════════════════════════════════ */
.pvt-step {
    background: #f6f8fc;
    border: 1px solid #c8d4e8;
    border-left: 3px solid #2a70c0;
    border-radius: 6px;
    padding: 0.75rem 1rem 0.7rem 1rem;
    margin-bottom: 0.5rem;
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 0.8rem;
    color: #1a2030;
    line-height: 1.55;
}
.pvt-step .step-label {
    font-family: 'Segoe UI', system-ui, Arial, sans-serif;
    font-size: 0.73rem;
    font-weight: 700;
    color: #1a4a80;
    margin-bottom: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
.pvt-step .conv-factor {
    color: #888;
    font-size: 0.72rem;
}
.pvt-step .result-val { color: #0d3060; font-weight: 700; }
.pvt-step .warn-val   { color: #c04000; font-weight: 700; }

/* Unit conversion reference box inside steps */
.pvt-step .conv-box {
    background: #e8f0fc;
    border: 1px solid #b0c8e8;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 0.72rem;
    color: #1a4880;
    margin-top: 4px;
    display: inline-block;
}

/* Unit conversion table inside steps */
.pvt-step .conv-table {
    background: #e8f0fc;
    border: 1px solid #b0c8e8;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 0.72rem;
    color: #1a4080;
    margin-top: 6px;
    display: block;
    line-height: 1.7;
}

/* ══════════════════════════════════════════════════════
   LAB REPORT TABLE
══════════════════════════════════════════════════════ */
.pvt-table { width:100%; border-collapse:collapse; font-size:0.81rem; }
.pvt-table th { background:#0d2040; color:#fff; padding:0.5rem 0.8rem; text-align:left; font-size:0.75rem; letter-spacing:0.3px; }
.pvt-table td { padding:0.38rem 0.8rem; border-bottom:1px solid #e0e8f4; }
.pvt-table tr:nth-child(even) td { background:#f4f6fc; }
.pvt-table .tbl-section td { background:#1a3060; color:#90c8f8; font-weight:700; font-size:0.7rem; letter-spacing:0.8px; padding:0.32rem 0.8rem; }
.pvt-table .tbl-highlight td { background:#fffbea !important; font-weight:700; }
.pvt-table .tbl-highlight td:first-child { border-left: 3px solid #e08020; }

/* ══════════════════════════════════════════════════════
   GOR VERIFICATION COLOURS
══════════════════════════════════════════════════════ */
.gor-ok   { color: #0d7a3a; font-weight: 700; }
.gor-warn { color: #b03010; font-weight: 700; }

/* ══════════════════════════════════════════════════════
   MOBILE TOUCH TARGETS
══════════════════════════════════════════════════════ */
input[type="number"]                   { font-size: 1rem !important; min-height: 44px; }
div[data-testid="stNumberInput"] input { font-size: 1rem !important; }

</style>
"""


def inject() -> None:
    """Inject the PVT Calculator stylesheet into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)
