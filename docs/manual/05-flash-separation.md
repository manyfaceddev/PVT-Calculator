# Chapter 5 - Flash Separation (Atmospheric Flash, Water-Pump Method)

Module 2 of the platform. This chapter covers the single-stage atmospheric
flash test: what the lab does at the bench, the three ways to get that data
into the platform, the exact calculation chain the engine runs, the
mass-basis recombination that turns flashed oil + flashed gas back into a
whole-sample composition, the QC checks applied, and the report the test
produces. Every equation below is transcribed from
`pvt/experiments/flash/calc.py`, `pvt/experiments/flash/recombine.py`, and
`pvt/core/plus_fractions.py`. The worked numbers are the SA-372 sample,
taken from `tests/golden/test_flash_sa372.py`,
`tests/golden/test_flash_recombination_sa372.py`, and
`tests/fixtures/sa372_flash.py`, cached from
`ADRIC_Flash_Separation_Calc_v6.1.xlsx`.

## 5.1 The laboratory test

The engine's own module docstring names the method precisely:

> Atmospheric flash separation, water-pump method (ADRIC Flash v6.1
> methodology).

A single-stage flash takes a live reservoir-oil sample and expands it, in
one step, from cell/charge pressure down to atmospheric pressure and stock-
tank conditions. What comes out is a stock-tank oil and a liberated gas; the
volumes, masses, and compositions of both are what this test measures.

The ADRIC Flash v6.1 template's `Volumetrics_Master` sheet (the workbook the
importer reads - see 5.2) lays the bench procedure out as three instrument
blocks:

**The displacement pump.** The live-oil cylinder is metered through a
positive-displacement pump into the flash line. The pump's own reading is
taken before and after the transfer (`pump_initial_cc`, `pump_final_cc`,
cc), and the metered volume is corrected by two calibration factors read off
the pump itself: a **pump constant** (`pump_constant`) and a **volume
correction factor** (`vcf`). This gives the charge-pressure volume of live
oil that was pushed through the flash valve - equation (5.1) below.

**The stock-tank flask.** What is left after the oil flashes to atmospheric
conditions is caught in a stock-tank flask. Its volume is read directly off
the flask's graduation (`v_sto_cc`) - this is an *input*, not something the
engine derives. Its mass is the flask's gross weight minus its tare weight
(`oil_tare_g`, `oil_gross_g`), giving the flashed-oil mass by difference -
equation (5.2).

**The gasometer.** Gas liberated at the flash valve is routed to a
gasometer - a water-displacement gas meter. Its reading is likewise taken
before and after (`gasometer_initial_cc`, `gasometer_final_cc`) and
corrected by a **gasometer factor** (`gasometer_factor`) - equation (5.3).
Because the gasometer reads at whatever temperature and pressure prevail in
the room and the drum at the time (`gas_temp_c`, `gas_abs_pressure_mbar`),
that raw volume is then corrected to lab standard conditions (14.73 psia /
60°F) with the combined gas law - equation (5.4). Gas gravity (air = 1) is
measured separately (`gas_gravity`) and is not derived by this chain - it
feeds the gas-density equation (5.5) directly.

Both liberated streams - the stock-tank oil and the flash gas - are also
sent for GC compositional analysis against the 52-component
Katz-Firoozabadi table (mol% and wt% bases for each). That composition data
is what section 5.4's mass recombination and section 5.5's composition QC
run on.

## 5.2 Data entry

The platform accepts flash data through three routes, all producing the
same `FlashVolumetrics` dataclass (13 fields) that `pvt.experiments.flash.calc.calculate`
consumes.

### Route 1 - App upload

Upload a filled `ADRIC_Flash_Separation_Calc_v6.1.xlsx` template on the
Flash Separation page's **Upload Workbook** tab. The importer
(`pvt.io.excel_import.flash_v61.read`) reads the `Volumetrics_Master` sheet
only - the other sheets (`Component_Properties`, `Recombination`,
`Plus_Properties_Report`) are downstream/computed in the workbook and are
not read. It pulls:

- **Sample metadata** (rows 5–8): Client, Well/Field, Sampling Depth,
  Sample ID, Chamber/Cylinder, Project No., Fluid Type.
- **Volumetric inputs** (rows 11–21, the yellow input cells only - B13,
  B16, B19 and the whole of rows 25–37 are computed in the sheet and are
  deliberately not read).
- **GC compositions** (rows 41–92): component code plus Gas Mol%, Gas Wt%,
  Oil Mol%, Oil Wt% for all 52 Katz-Firoozabadi rows.

Two cells - `E17` (barometric pressure) and `E20` (back pressure) - are read
by the workbook into an unused `P_base` composite (`B25`) that the workbook
itself never consumes downstream. The engine does not read them either; see
5.5's note and the deviations ledger entry D-017.

If the workbook is missing the `Volumetrics_Master` sheet, or its header
text has shifted from the expected v6.1 layout, or any composition cell
reads negative, the import is rejected with a listed `InputValidationError`
rather than silently reading garbage.

### Route 2 - Manual form

The **Manual Entry** tab mirrors `FlashVolumetrics`'s 13 fields directly:

| Field | Label | Unit | Default | Constraint (validate.py) |
|---|---|---|---|---|
| `pump_initial_cc` | Initial pump reading | cc | 0.0 | ≥ 0 |
| `pump_final_cc` | Final pump reading | cc | 0.0 | > `pump_initial_cc` |
| `v_sto_cc` | Stock tank oil volume (V_sto) | cc | 1.0 | > 0 |
| `oil_tare_g` | Oil tare weight | g | 0.0 | ≥ 0 |
| `oil_gross_g` | Final oil + tare weight | g | 0.0 | > `oil_tare_g` |
| `gasometer_initial_cc` | Initial gasometer reading | cc | 0.0 | ≥ 0 |
| `gasometer_final_cc` | Final gasometer reading | cc | 0.0 | ≥ `gasometer_initial_cc` |
| `gas_temp_c` | Gas temperature | °C | 20.0 | −10 < t < 60 (exclusive) |
| `gas_abs_pressure_mbar` | Measured gas abs. pressure | mbar | 1013.25 | 500 < p < 1500 (exclusive) |
| `gas_gravity` | Gas gravity (Air = 1) | - | 1.0 | 0.5 < g < 3.0 (exclusive) |
| `pump_constant` | Pump constant | - | 1.0 | > 0 |
| `vcf` | Volume correction factor (VCF) | - | 1.0 | > 0 |
| `gasometer_factor` | Gasometer factor | - | 1.0 | > 0 |

These are the 8 rules `pvt.experiments.flash.validate.validate` enforces
(each producing its own error message; every violation is reported, not
just the first). The manual form's number-input widgets additionally clamp
the three explicitly-bounded fields (temperature, pressure, gravity) 0.01
inside their exclusive bounds, so the widget itself cannot submit the
excluded boundary value.

Below the volumetrics fields, an **optional** GC composition editor is
seeded with all 52 Katz-Firoozabadi codes and four blank columns (Gas Mol%,
Gas Wt%, Oil Mol%, Oil Wt%). Composition is genuinely optional in manual
mode - a stream is only built when at least one of its two columns has a
non-zero entry. Leaving it blank still gives you the 12 flash results (5.3);
it skips the mass recombination, plus-fraction, and composition-QC sections
(5.4–5.5), which need both streams.

### Route 3 - CLI

```
python cli.py flash --workbook path/to/ADRIC_Flash_Separation_Calc_v6.1.xlsx
```

The CLI's `flash` subcommand only supports the workbook-upload route - there
is no field-by-field flag interface for flash (unlike `cli.py recombine`,
Chapter 6). It runs the same importer, the same calculation chain, the same
mass recombination, and the same four QC checks (composition normalization
×4, MW consistency ×2 - Hoffman-Crump is not run from the CLI), and prints
the report tables (5.6) as fixed-width text to stdout.

## 5.3 Calculation chain

`pvt.experiments.flash.calc.calculate` runs the following chain on a
validated `FlashVolumetrics`. All twelve `FlashResults` fields are produced
here, in this order.

**Charge-pressure volume** - the live-oil volume metered through the pump:

$$V_{press} = (V_{pump,final} - V_{pump,initial}) \times k_{pump} \times VCF \tag{5.1}$$

**Flashed-oil mass** - by difference, gross minus tare:

$$m_{oil} = m_{oil,gross} - m_{oil,tare} \tag{5.2}$$

**Measured gas volume** - raw gasometer displacement, calibration-corrected:

$$V_{gas,meas} = (V_{gasometer,final} - V_{gasometer,initial}) \times k_{gasometer} \tag{5.3}$$

**Gas volume at standard conditions** - ideal-gas ($Z=1$) correction from
the measured absolute pressure and temperature to the lab standard (14.73
psia / 1015.5981 mbar, 60°F / 288.7056 K):

$$V_{gas,std} = V_{gas,meas} \times \frac{P_{gas}}{P_{std}} \times \frac{T_{std}}{T_{gas}} \tag{5.4}$$

where $P_{gas}$ is `gas_abs_pressure_mbar` and $T_{gas} = t_{gas,°C} + 273.15$ K.

**Gas density at standard conditions** - from the independently-measured gas
gravity and standard-conditions air density (0.0012255 g/cc):

$$\rho_{gas,std} = \gamma_{gas} \times \rho_{air,std} \tag{5.5}$$

**Flashed-gas mass**:

$$m_{gas} = V_{gas,std} \times \rho_{gas,std} \tag{5.6}$$

**Gas-oil ratio**, cc gas (std) per cc stock-tank oil:

$$GOR_{cc/cc} = \frac{V_{gas,std}}{V_{sto}} \tag{5.7}$$

and in field units (scf/bbl), using the 5.61458 ft³/bbl conversion:

$$GOR_{scf/bbl} = GOR_{cc/cc} \times 5.61458 \tag{5.8}$$

**Flash formation volume factor**, live-oil volume at charge pressure per
unit stock-tank oil volume:

$$B_{o,flash} = \frac{V_{press}}{V_{sto}} \tag{5.9}$$

**Shrinkage**, the reciprocal relationship:

$$Shrinkage = \frac{V_{sto}}{V_{press}} \tag{5.10}$$

**Stock-tank oil density at 60°F**:

$$\rho_{oil,60°F} = \frac{m_{oil}}{V_{sto}} \tag{5.11}$$

**API gravity** - the house convention treats g/cc at 60°F as SG 60/60
directly:

$$API = \frac{141.5}{\rho_{oil,60°F}} - 131.5 \tag{5.12}$$

If validation fails, `calculate` raises `InputValidationError` listing every
rule violated (Section 5.2) rather than computing on bad data; call it with
`validate_inputs=False` only if you have already validated upstream.

### Worked example - SA-372

Inputs (`tests/unit/experiments/test_flash_validate.py`, `SA372`):

| Input | Value | Unit |
|---|---|---|
| `pump_initial_cc` | 50.0 | cc |
| `pump_final_cc` | 70.8945 | cc |
| `v_sto_cc` | 15.7576 | cc |
| `oil_tare_g` | 100.0 | g |
| `oil_gross_g` | 113.71 | g |
| `gasometer_initial_cc` | 500.0 | cc |
| `gasometer_final_cc` | 1458.2037 | cc |
| `gas_temp_c` | 20.0 | °C |
| `gas_abs_pressure_mbar` | 1012.25 | mbar |
| `gas_gravity` | 1.146 | (air = 1) |
| `pump_constant`, `vcf`, `gasometer_factor` | 1.0 | (each) |

All twelve outputs (`tests/golden/test_flash_sa372.py::test_sa372_flash_chain`,
workbook cell refs noted):

| Eq. | Quantity | Value | Unit | Workbook cell |
|---|---|---|---|---|
| (5.1) | $V_{press}$ | 20.8945 | cc | B13 |
| (5.2) | $m_{oil}$ | 13.71 | g | B16 |
| (5.3) | $V_{gas,meas}$ | 958.2037 | cc | B19 |
| (5.4) | $V_{gas,std}$ | 940.5655 | cc | B27 |
| (5.5) | $\rho_{gas,std}$ | 0.001404423 | g/cc | B28 |
| (5.6) | $m_{gas}$ | 1.32095 | g | B29 |
| (5.7) | $GOR_{cc/cc}$ | 59.6896 | cc/cc | B31 |
| (5.8) | $GOR_{scf/bbl}$ | 335.13 | scf/bbl | B32 |
| (5.9) | $B_{o,flash}$ | 1.32600 | vol/vol | B33 |
| (5.10) | $Shrinkage$ | 0.754151 | - | B34 |
| (5.11) | $\rho_{oil,60°F}$ | 0.870056 | g/cc | B36 |
| (5.12) | $API$ | 31.133 | °API | B37 |

## 5.4 Mass recombination & plus fractions

Once both the flashed-oil and flashed-gas GC compositions are available
(uploaded or entered), `pvt.experiments.flash.recombine.recombine_mass`
blends them back into a single whole-sample ("wellstream") composition on a
**mass** basis - the live-fluid technique.

**Gas and oil mass fractions**, from the two measured masses (5.2, 5.6):

$$w_{f,gas} = \frac{m_{gas}}{m_{gas} + m_{oil}} \qquad w_{f,oil} = \frac{m_{oil}}{m_{gas} + m_{oil}} \tag{5.13, 5.14}$$

**Wellstream wt% blend** - each stream's own normalized (sum-to-100) wt%
basis, mass-fraction-weighted:

$$w_{whole,i} = w_{f,gas} \cdot w_{gas,i} + w_{f,oil} \cdot w_{oil,i} \tag{5.15}$$

**Mol% back-calculation** - the wt% blend is the primary result; mol% is
derived from it and renormalized, so the two MW routes agree by
construction:

$$n_{raw,i} = \frac{w_{whole,i}}{MW_i} \qquad z_{whole,i} = \frac{n_{raw,i} \times 100}{\sum_i n_{raw,i}} \tag{5.16, 5.17}$$

**Whole-sample molecular weight** (mw_from_wt on the resulting wellstream):

$$MW_{whole} = \frac{100}{\sum_i (w_{whole,i}/MW_i)} \tag{5.18}$$

Worked SA-372 numbers (`tests/golden/test_flash_recombination_sa372.py::test_golden_wf_and_mw`,
Recombination sheet cells B18/B21):

$$w_{f,gas} = 0.0878821 \qquad MW_{whole} = 135.0426 \text{ g/mol}$$

### Plus fractions - the positional cut convention

`pvt.core.plus_fractions.plus_fraction` computes C7+, C11+, C20+, and C36+
cut properties. The cut boundary is **positional on the component
library's fixed 52-slot order, not name-pattern matching**: a cut is every
component at or after its start code's slot. Per the module docstring, this
is what makes "C7+" **exclude** the cyclics that sort *before* C7 in the
Katz-Firoozabadi table - MCP, Benzene, CycloC6 - while **including** the
cyclics that sort *after* it - MCH, Toluene - matching the flash workbook's
`Plus_Properties_Report` convention. (Library order around the boundary:
… C6, MCP, Benzene, CycloC6, **C7**, MCH, Toluene, C8, … - only `C7`
onward is in the cut.)

For a cut with mol% $z_i$ and wt% $w_i$ (both on the stream's normalized
basis) and component codes restricted to the cut:

$$mol\%_{cut} = \sum_{i \in cut} z_i \qquad wt\%_{cut} = \sum_{i \in cut} w_i \tag{5.19, 5.20}$$

$$MW_{cut} = \frac{\sum_{i \in cut} z_i \cdot MW_i}{mol\%_{cut}} \tag{5.21}$$

$$\rho_{cut} = \frac{wt\%_{cut}}{\sum_{i \in cut} (w_i / \rho_i)} \tag{5.22}$$

(5.22 is ideal-mixing density: same denominator form as (5.11)'s reciprocal
build, applied per-cut.)

**Worked C7+ numbers, SA-372:**

*Flashed oil alone* (before recombination; `tests/golden/test_flash_recombination_sa372.py::test_cut_boundaries`)
demonstrates the boundary directly - the flashed-liquid composition already
excludes MCP/Benzene/CycloC6 from its C7+ figure:

$$mol\%_{C7+,oil} = 79.873\%$$

*Recombined wellstream* (`test_golden_c7_plus_of_recombined`, Plus_Properties_Report "Recombined" column):

| Property | Value | Unit |
|---|---|---|
| mol% | 51.119 | % |
| wt% | 84.236 | % |
| MW | 222.53 | g/mol |
| Density | 0.84661 | g/cc |

## 5.5 QC applied

QC only runs on the composition streams - it needs both an oil and a gas
`CompositionStream` (5.2, Route 1 or an optional Route 2 entry). Each check
runs independently: one check raising `InputValidationError` (for example, a
manual-entry stream with mol% only and no wt% basis, which `mw_consistency`
cannot grade) does not block the others - the page renders a caption
explaining the skip and continues.

| Check | Runs on | Threshold (review / fail) | What it grades |
|---|---|---|---|
| `composition_sum` | Gas mol%, Gas wt%, Oil mol%, Oil wt% (4 checks) | 0.5 / 2.0 (points off 100) | Raw composition sum vs. 100 - eq. (5.23) |
| `mw_consistency_pct` | Gas, Oil (2 checks) | 5.0% / 10.0% | mol%-derived MW vs. wt%-derived MW - eq. (5.24) |
| `hoffman_r2` | Gas/liquid pair (1 check) | R² ≥ 0.98 / ≥ 0.95 (floor) | Hoffman-Crump K-value consistency crossplot - eqs. (5.25)–(5.26) |

$$deviation_{sum} = raw\_sum - 100.0 \tag{5.23}$$

$$mw\_consistency\% = \frac{MW_{mol} - MW_{wt}}{MW_{wt}} \times 100 \tag{5.24}$$

The Hoffman-Crump crossplot (`pvt.qc.checks.hoffman_crump`) forms one point
per component present, with positive mole fraction, in **both** the gas and
liquid streams:

$$K_i = \frac{y_i}{x_i} \qquad b_i = \frac{\log_{10}(P_{c,i}/14.7)}{1/T_{b,i} - 1/T_{c,i}} \qquad F_i = b_i\left(\frac{1}{T_{b,i}} - \frac{1}{T_R}\right) \qquad y\text{-axis} = \log_{10}(K_i \cdot P) \tag{5.25}$$

($P$ = flash pressure, $T_R$ = flash temperature in Rankine; 14.7 psia is
the Hoffman-Crump correlation's own fixed reference pressure, not one of the
engine's standard-condition constants.) A least-squares line is fit
($\log_{10}(KP)$ vs. $F$) and graded on its R²; since `grade()` only
understands "smaller deviation is better," the R²-floor pair is converted:

$$deviation_{R^2} = 1 - R^2, \text{ graded against } (1-0.98,\ 1-0.95) \tag{5.26}$$

Fewer than 2 qualifying components, or a degenerate fit (all points sharing
one F-factor or one $\log_{10}(KP)$), raises `InputValidationError` - the
page shows a warning and skips the plot rather than crashing.

**QC pills.** Each `QCResult` renders as a coloured dot + check id + message
(`ui.common.components.qc_pill`): green for PASS, amber for REVIEW, red for
FAIL - the same three colours the report workbook fills the value cell with
(`38A169` / `DD9A0A` / `E53E3E`). Grading is inclusive downward: a value
exactly at the fail threshold still grades REVIEW, not FAIL.

**Worked SA-372 QC** - every check passes cleanly on this sample:

| Check | Value | Severity |
|---|---|---|
| Gas mol% sum | 100.0000 (Δ 0.0000) | PASS |
| Gas wt% sum | 100.0000 (Δ 0.0000) | PASS |
| Oil mol% sum | 100.0000 (Δ 0.0000) | PASS |
| Oil wt% sum | 100.0000 (Δ 0.0000) | PASS |
| MW consistency (gas) | +0.0031% | PASS |
| MW consistency (oil) | +0.1465% | PASS |
| Hoffman-Crump | R² = 0.9819, 22 points | PASS |

Note (deviations ledger D-017): the workbook's `Volumetrics_Master!B25`
computes a `P_base` composite from barometric pressure (E17) and back
pressure (E20) but never uses it downstream; the engine likewise takes only
the measured absolute pressure input (`gas_abs_pressure_mbar`) for eq.
(5.4), and does not read E17/E20 at all.

## 5.6 Report contents

`pvt.reporting.tables.flash_tables` builds three sections from a
`FlashResults`, a `MassRecombination`, and whatever QC results were run:

1. **Flash Results** - all twelve values from Section 5.3, formatted to the
   same precision as the golden tests (e.g. GOR to 4 decimal places cc/cc
   and 2 decimal places scf/bbl, API to 1 decimal).
2. **Whole Sample** - Gas Mass Fraction and Oil Mass Fraction (wt%, from
   5.13/5.14) and Whole Sample MW (from 5.18).
3. **QC Summary** - one row per `QCResult` passed in: check id, severity,
   and the full message. Every QC result the caller runs appears here,
   whichever of Section 5.5's checks actually ran.

`pvt.reporting.excel_export.write_report` writes these, plus a Sample
Information block (sample ID, well, field, reservoir, depth, fluid type,
cylinder, client, project), to a single-sheet, navy-banner-styled `.xlsx`
workbook. QC Summary value cells are fill-coloured to match the pill colours
above. The download filename is prefixed with the sample ID
(`report_download`, `ui.common.components`) so reports for different
samples never collide in a downloads folder.

The mass-recombination report (and therefore the Whole Sample / QC Summary
tables) is only available once both composition streams are present; with
volumetrics only, the page shows the 12-result metric cards and calculation
steps but prompts for composition before the report download appears.

The CLI's `flash` subcommand prints the same three tables as fixed-width
text (no Excel file) alongside the Sample Information header.
