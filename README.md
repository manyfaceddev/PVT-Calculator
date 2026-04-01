# PVT Calculator Suite
## Module 1 — Separator Fluid Recombination

A professional-grade Streamlit web app for petroleum reservoir engineers to calculate exact separator oil and gas volumes for recombination cell charging.

---

### Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## Deploy to Streamlit Community Cloud (free)

1. Push this repo to GitHub (public or private)
2. Go to https://share.streamlit.io
3. Click **New app**
4. Select your repo, branch: `main`, main file: `app.py`
5. Click **Deploy** — your app will be live in ~2 minutes

No extra configuration needed — `requirements.txt`, `.python-version`, and `.streamlit/config.toml` are picked up automatically.

### Local network access (same WiFi)

```bash
./launch.sh
# Prints the phone URL, e.g. http://192.168.x.x:8501
```

---

### What it does

Given separator GOR, pressure, temperature, and gas Z-factor, the calculator tells you:

| Output | Description |
|--------|-------------|
| **V_oil_sep** | Volume of separator liquid to charge into the cell (cc) |
| **V_gas_std** | Volume of separator gas at standard conditions (cc and scf/sm³) |
| **V_gas_sep** | Volume of separator gas at separator conditions (cc) — reference for gas pump |
| **GOR check** | Back-calculated GOR to verify the charged volumes reproduce the original separator GOR |

---

### Core Physics

#### GOR conversion (field units)
```
R_cc [cc/cc] = R_sep [scf/STB] × (28316.85 cc/scf) / (158987.1 cc/STB)
             = R_sep × 0.178107
```

#### Oil volumes
```
V_oil_sep = oil_fraction × V_cell
V_oil_STO = V_oil_sep / Bo_sep
```

#### Gas at standard conditions
```
V_gas_std [cc] = R_cc [cc/cc] × V_oil_STO [cc]
```

#### Gas at separator conditions (real-gas law)
```
V_gas_sep = V_gas_std × (P_std / P_sep) × (T_sep_R / T_std_R) × Z_sep
```

Where:
- P_std = 14.696 psia
- T_std = 519.67 R (60°F)
- T in Rankine = T(°F) + 459.67

---

### Inputs

| Parameter | Field Units | SI Units | Default |
|-----------|-------------|----------|---------|
| Cell volume | cc | cc | 300 cc |
| GOR | scf/STB | sm³/sm³ | 850 / 151 |
| Separator pressure | psia | bara | 815 / 56 |
| Separator temperature | °F | °C | 145 / 62.8 |
| Z-factor | — | — | 0.855 |
| Bo at separator | res bbl/STB | — | 1.000 |
| Oil fraction | 0–1 | 0–1 | 0.70 |

---

### Project Structure

```
PVT-Calculator/
├── app.py          — Streamlit UI (single-page app)
├── pvt_calc.py     — Core physics calculations (pure Python, no UI)
├── requirements.txt
└── README.md
```

`pvt_calc.py` is fully decoupled from Streamlit — import it in scripts, notebooks, or future modules without any UI dependency.

---

### Planned Modules

- **Module 2** — Differential Liberation (CCE/DL) analysis
- **Module 3** — Fluid property correlations (Standing, Vazquez-Beggs, etc.)
- **Module 4** — EOS tuning assistant

---

*Standard conditions: 14.696 psia / 60°F (field) &nbsp;|&nbsp; 1.01325 bara / 15°C (SI)*
