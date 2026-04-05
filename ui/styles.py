"""
ui/styles.py — CSS stylesheet for the PVT Calculator Streamlit app.

Call inject() once at the top of any page that needs these styles.
"""

import streamlit as st

_CSS = """
<style>
/* ── global ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #f0f4f8;
    font-family: 'Segoe UI', Arial, sans-serif;
}

/* ── page header ── */
.pvt-header {
    background: linear-gradient(135deg, #0a1628 0%, #1a3a6b 100%);
    color: #fff;
    padding: 1.2rem 1.4rem 1rem 1.4rem;
    border-radius: 12px;
    margin-bottom: 1.2rem;
}
.pvt-header h1 { margin: 0; font-size: 1.35rem; letter-spacing: 0.3px; line-height: 1.3; }
.pvt-header p  { margin: 0.3rem 0 0 0; color: #90b8e8; font-size: 0.82rem; }

/* ── hero charge card ── */
.pvt-hero {
    background: linear-gradient(135deg, #0a3d62, #1a6dad);
    color: #fff;
    border-radius: 14px;
    padding: 1.4rem 1.4rem 1.2rem 1.4rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.18);
}
.pvt-hero .hero-title  { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.2px; color: #90c8f0; margin-bottom: 0.8rem; }
.pvt-hero .charge-row  { display: flex; align-items: baseline; gap: 0.5rem; margin: 0.55rem 0; }
.pvt-hero .charge-val  { font-size: 2rem; font-weight: 800; color: #fff; line-height: 1; }
.pvt-hero .charge-unit { font-size: 1rem; color: #b0d8f8; font-weight: 400; }
.pvt-hero .charge-label{ font-size: 0.82rem; color: #90b8e0; margin-top: -0.1rem; }
.pvt-hero .hero-divider{ border: none; border-top: 1px solid rgba(255,255,255,0.15); margin: 0.9rem 0; }
.pvt-hero .hero-sub    { font-size: 0.8rem; color: #90b8e0; }

/* ── metric cards ── */
.pvt-card-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    margin-bottom: 1rem;
}
.pvt-metric-card        { background: #fff; border-radius: 10px; padding: 0.9rem 1rem; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
.pvt-metric-card .m-val { font-size: 1.55rem; font-weight: 700; color: #0a3d62; line-height: 1.1; }
.pvt-metric-card .m-unit{ font-size: 0.78rem; color: #1a6dad; font-weight: 600; }
.pvt-metric-card .m-lbl { font-size: 0.72rem; color: #6a7f96; text-transform: uppercase; letter-spacing: 0.4px; margin-top: 0.2rem; }
.pvt-metric-card.accent { background: #e8f2fd; border: 2px solid #1a6dad; }

/* ── bubble point card ── */
.pb-card           { background: #fffbea; border: 1px solid #f0c040; border-left: 5px solid #e8900a; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1rem; }
.pb-card .pb-title { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.8px; color: #7a5000; margin-bottom: 0.5rem; }
.pb-card .pb-val   { font-size: 2rem; font-weight: 800; color: #7a3800; line-height: 1.1; }
.pb-card .pb-unit  { font-size: 1rem; font-weight: 400; color: #9a6010; }
.pb-card .pb-range { font-size: 0.82rem; color: #9a7010; margin-top: 0.3rem; }
.pb-card .pb-note  { font-size: 0.75rem; color: #aa8020; margin-top: 0.6rem; font-style: italic; line-height: 1.45; }

/* ── section heading ── */
.pvt-section { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #4a6080; margin: 1.2rem 0 0.5rem 0; font-weight: 700; }

/* ── stage breakdown card ── */
.stage-card           { background: #fff; border-radius: 10px; padding: 1rem 1.1rem; margin-bottom: 0.7rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border-left: 4px solid #1a6dad; }
.stage-card .sc-title { font-size: 0.88rem; font-weight: 700; color: #0a3d62; margin-bottom: 0.5rem; }
.stage-card .sc-row   { display: flex; justify-content: space-between; font-size: 0.85rem; padding: 0.15rem 0; }
.stage-card .sc-lbl   { color: #6a7f96; }
.stage-card .sc-val   { font-weight: 600; color: #1a2b45; }

/* ── calculation step blocks ── */
.pvt-step            { background: #f4f8fc; border: 1px solid #d0dcea; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.55rem; font-family: 'Courier New', monospace; font-size: 0.82rem; color: #2c3e50; line-height: 1.5; }
.pvt-step .step-label{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 0.75rem; font-weight: 700; color: #1a6dad; margin-bottom: 0.25rem; }

/* ── lab report table ── */
.pvt-table              { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
.pvt-table th           { background: #0a3d62; color: #fff; padding: 0.5rem 0.8rem; text-align: left; }
.pvt-table td           { padding: 0.4rem 0.8rem; border-bottom: 1px solid #e0e8f0; }
.pvt-table tr:nth-child(even) td { background: #f4f8fc; }
.pvt-table .tbl-section td { background: #1a3a6b; color: #90c8f0; font-weight: 700; font-size: 0.72rem; letter-spacing: 0.8px; padding: 0.35rem 0.8rem; }

/* ── ASCII diagram ── */
.pvt-ascii { background: #0a1628; color: #60b0e0; font-family: 'Courier New', monospace; font-size: 0.72rem; padding: 0.9rem 1rem; border-radius: 8px; white-space: pre; line-height: 1.5; overflow-x: auto; }

/* ── GOR verification colours ── */
.gor-ok   { color: #147a3a; font-weight: 700; }
.gor-warn { color: #b03010; font-weight: 700; }

/* ── sidebar ── */
[data-testid="stSidebar"]                                       { background: #0a1628; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label                                 { color: #c0d8f0 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3                                    { color: #60b0e0 !important; }
[data-testid="stSidebar"] hr                                    { border-color: #1a3a6b; }

/* radio buttons — make text and indicators visible on dark bg */
[data-testid="stSidebar"] [data-testid="stRadio"] label         { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] p             { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [role="radiogroup"] label             { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [data-baseweb="radio"] div            { border-color: #60b0e0 !important; }
[data-testid="stSidebar"] [data-baseweb="radio"][aria-checked="true"] div
                                                                { background: #1a6dad !important; border-color: #60b0e0 !important; }

/* number inputs — ensure readable text on dark bg */
[data-testid="stSidebar"] input[type="number"]                  { color: #0a1628 !important; background: #e8f2fd !important; border: 1px solid #4a7aad !important; border-radius: 6px; }
[data-testid="stSidebar"] div[data-testid="stNumberInput"] input{ color: #0a1628 !important; background: #e8f2fd !important; }

/* select/dropdown on sidebar */
[data-testid="stSidebar"] [data-testid="stSelectbox"] div       { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] span      { color: #c0d8f0 !important; }

/* toggle / checkbox */
[data-testid="stSidebar"] [data-testid="stCheckbox"] label      { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [data-testid="stToggle"] label        { color: #c0d8f0 !important; }
[data-testid="stSidebar"] [data-testid="stToggle"] p            { color: #c0d8f0 !important; }

/* ── mobile touch targets ── */
input[type="number"]                                            { font-size: 1rem !important; min-height: 44px; }
div[data-testid="stNumberInput"] input                          { font-size: 1rem !important; }
</style>
"""


def inject() -> None:
    """Inject the PVT Calculator stylesheet into the current Streamlit page."""
    st.markdown(_CSS, unsafe_allow_html=True)
