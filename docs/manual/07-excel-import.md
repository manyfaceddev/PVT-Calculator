# Chapter 7: Excel Import

## 7.1 The Template-Import Philosophy

The PVT Lab Platform does not re-implement the ADRIC lab workbooks in Excel form and it does not trust any formula result already sitting in a cell. When a lab technician uploads a filled template, the importer opens the workbook with `openpyxl.load_workbook(path, data_only=True, read_only=True)` and reads back **only the yellow input cells**, the raw numbers and text a person typed in. Every computed quantity, from the flash gas volume at standard conditions to the wellstream molecular weight, is recalculated from scratch by the Python engine (`pvt.experiments.*`).

This gives the workbook a single job: it is the data carrier, the audited paper trail of what was measured in the lab. It is deliberately not treated as a calculator. Three consequences follow directly from the importer source:

- Cells that hold formulas or workbook-computed intermediates (block C of the Flash v6.1 `Volumetrics_Master` sheet, for example) are never read, even though `data_only=True` would hand back their cached values.
- If a workbook's formula logic has a known defect (see `docs/excel-deviations.md`), that defect cannot leak into a report, because the defective cell is never consulted.
- The importer fails loudly (`InputValidationError`) rather than silently, whenever the sheet it opens does not look like the template it expects, or a required cell is blank.

Both importers live under `pvt/io/excel_import/` and each exposes one function, `read(path)`, returning a frozen dataclass (`FlashImport`, `LiveOilImport`) ready to hand straight to the matching `pvt.experiments` calculation chain.

## 7.2 Supported Templates

| Template | File | Importer module | Sheets read |
|---|---|---|---|
| ADRIC Flash Separation Calc v6.1 | `ADRIC_Flash_Separation_Calc_v6.1.xlsx` | `pvt.io.excel_import.flash_v61` | `Volumetrics_Master` only |
| ADRIC LiveOil Preparation Calc v4.1 | `ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx` | `pvt.io.excel_import.liveoil_v41` | `Sample_Info`, `STO_Composition`, `Gas_Composition`, `Recombination`, `Loading_Volumes` |

The Flash v6.1 workbook carries all of its yellow inputs on one sheet; `Component_Properties`, `Recombination`, and `Plus_Properties_Report` on that workbook are downstream/computed and are not opened by the importer at all. The LiveOil v4.1 workbook spreads its inputs across five sheets, all of which are opened and validated.

## 7.3 ADRIC Flash v6.1 Cell Map

Source: `pvt/io/excel_import/flash_v61.py`. All cells below are on the `Volumetrics_Master` sheet.

### Block A: Project & Sample Information (rows 5-8)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B5 | `Sample.client` | Client | text |
| B6 | `Sample.well`, `Sample.field_name` | Well / Field, split on `" / "` | text |
| B7 | `Sample.depth_ft_md` | Sampling depth (MD) | ft |
| H5 | `Sample.sample_id` | Sample ID | text |
| H6 | `Sample.cylinder` | Chamber / cylinder | text |
| H8 | `Sample.project` | Project number | text |
| E8 | `Sample.fluid_type` | Fluid type | text |

`Sample.reservoir` has no source cell in this template (only reservoir *temperature*/*pressure* exist, which are conditions, not a reservoir name) and is set to `""`.

### Block B: Volumetric Measurements (rows 11-21)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B11 | `FlashVolumetrics.pump_constant` | Pump constant | dimensionless |
| E11 | `FlashVolumetrics.vcf` | Volume correction factor (VCF) | dimensionless |
| B12 | `FlashVolumetrics.pump_initial_cc` | Initial pump reading | cc |
| E12 | `FlashVolumetrics.pump_final_cc` | Final pump reading | cc |
| B14 | `FlashVolumetrics.v_sto_cc` | Stock tank oil volume, V_sto | cc |
| B15 | `FlashVolumetrics.oil_tare_g` | Oil tare weight | g |
| E15 | `FlashVolumetrics.oil_gross_g` | Final oil + tare weight | g |
| B17 | `FlashVolumetrics.gasometer_factor` | Gasometer factor | dimensionless |
| B18 | `FlashVolumetrics.gasometer_initial_cc` | Initial gasometer reading | cc |
| E18 | `FlashVolumetrics.gasometer_final_cc` | Final gasometer reading | cc |
| B20 | `FlashVolumetrics.gas_temp_c` | Gas temperature | degC |
| B21 | `FlashVolumetrics.gas_abs_pressure_mbar` | Measured gas absolute pressure | mbar |
| E21 | `FlashVolumetrics.gas_gravity` | Gas gravity (Air = 1) | dimensionless |
| E17 | not read | Barometric pressure | mbar |
| E20 | not read | Back pressure | mbar |

E17 and E20 are read visually by the lab technician but never consumed by the engine; see section 7.9.

### Block D: GC Compositions (row 40 header, rows 41-92, 52 components)

| Cell (per row 41-92) | Field | Meaning | Units |
|---|---|---|---|
| B{row} | component code | Component code (aliased if needed, see 7.5) | text |
| E{row} | `gas_stream.mol_pct[code]` | Gas Mol% (INPUT) | mol% |
| F{row} | `gas_stream.wt_pct[code]` | Gas Wt% (INPUT) | wt% |
| G{row} | `oil_stream.mol_pct[code]` | Oil Mol% (INPUT) | mol% |
| H{row} | `oil_stream.wt_pct[code]` | Oil Wt% (INPUT) | wt% |

Row order matches `pvt.core.components.KATZ_FIROOZABADI.codes` exactly except for the three aliased codes.

## 7.4 ADRIC LiveOil v4.1 Cell Map

Source: `pvt/io/excel_import/liveoil_v41.py`. All five required sheets are opened: `Sample_Info`, `STO_Composition`, `Gas_Composition`, `Recombination`, `Loading_Volumes`.

### Block A: Recombination Inputs (`Recombination!B5:B12`)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B5 | `gor` | GOR | scf/STB |
| B6 | `gor_basis` | GOR type ("Separator" / "Stock Tank" dropdown text, mapped verbatim to `GorBasis`) | enum |
| B7 | `shrinkage` | Shrinkage factor, B_st | dimensionless |
| B12 | `z_std` | Z-factor at standard conditions | dimensionless |

### Block B: STO Properties (`STO_Composition!B5`, `D65`)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B5 | `sto_density_60f` | STO density at 60 degF, reported | g/cc |
| D65 | `c36_mw` | C36+ molecular weight (editable, row 65) | g/mol |

### Block C: Compositions (`STO_Composition!`, `Gas_Composition!`, row 14 header, rows 15-65, 51 components)

| Cell (per row 15-65) | Field | Meaning | Units |
|---|---|---|---|
| B{row} | component code | Component code (aliased if needed, see 7.5) | text |
| I{row} | `sto_stream.mol_pct[code]` / `gas_stream.mol_pct[code]` | Mol% (INPUT), the only composition column read | mol% |
| J{row} | not read | Wt% (INPUT); not consumed by any calc.py in this phase | wt% |

### Block D: Loading (`Loading_Volumes!B5:B12`)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B5 | `LoadingInputs.cylinder_volume_cc` | Cylinder volume | cc |
| B6 | `LoadingInputs.target_oil_cc` | Target oil volume | cc |
| B7 | `LoadingInputs.oil_load_p_psig` | Oil-cylinder gauge pressure at loading | psig |
| B8 | `LoadingInputs.oil_load_t_f` | Oil-cylinder temperature at loading | degF |
| B9 | `LoadingInputs.gas_load_p_psig` | Gas-cylinder gauge pressure at loading | psig |
| B10 | `LoadingInputs.gas_load_t_f` | Gas-cylinder temperature at loading | degF |
| B11 | `LoadingInputs.z_gas_load` | Gas Z-factor at gas-load conditions | dimensionless |
| B12 | `LoadingInputs.sto_density_at_load_g_cc` | STO density at oil-load conditions | g/cc |
| B13 | not read | BSW / water content of loaded oil | % |

### Block E: Sample Metadata (`Sample_Info!B5:B9`, `E5:E9`)

| Cell | Field | Meaning | Units |
|---|---|---|---|
| B5 | `Sample.client` | Company / client | text |
| B6 | `Sample.well` | Well | text |
| B7 | `Sample.sample_id` | Sample ID | text |
| B8 | `Sample.depth_ft_md` | Sampling depth (MD) | ft |
| B9 | `Sample.fluid_type` | Fluid type | text |
| E5 | `Sample.field_name` | Field | text |
| E6 | `Sample.reservoir` | Reservoir | text |
| E7 | `Sample.cylinder` | Chamber / cylinder number | text |
| E8 | not read | Sampling date | date |
| E9 | `Sample.project` | Project number | text |

Unlike the Flash v6.1 importer, this template carries a `Reservoir` field (E6) directly, so `Sample.reservoir` is populated here rather than left as `""`.

## 7.5 Component Name Alias Handling

Both templates' GC composition rows use a `Code` column that mostly, but not exactly, matches `pvt.core.components.KATZ_FIROOZABADI.codes`. Each importer carries a small local `_ALIAS` dict, applied as `code = _ALIAS.get(raw_code, raw_code)` before the row is stored:

**Flash v6.1** (`flash_v61._ALIAS`, 3 entries):

| Workbook code | Library code | Workbook Component column text |
|---|---|---|
| `Cyclohex` | `CycloC6` | Cyclohexane |
| `MPXylenes` | `MP-Xylene` | M/P-Xylenes |
| `OXylene` | `O-Xylene` | O-Xylene |

**LiveOil v4.1** (`liveoil_v41._ALIAS`, 4 entries):

| Workbook code | Library code | Workbook Component column text |
|---|---|---|
| `Neo-C5` | `NeoC5` | Neo-Pentane |
| `Cyclohex` | `CycloC6` | Cyclohexane |
| `E-Benzene` | `EBenzene` | E-Benzene |
| `M/P-Xylene` | `MP-Xylene` | M/P-Xylene |

`O-Xylene` needs no alias in the LiveOil template; it is already spelled exactly like the library code there, unlike Flash's `OXylene`.

The LiveOil v4.1 composition block is also one component short: it carries 51 rows against the library's 52 codes, omitting `TMB124` (1,2,4-Trimethylbenzene) entirely. That component is not aliased to anything, it is simply absent from every row read, matching what the lab actually reported. `CompositionStream` does not require every library code to be present, so the resulting stream is silently missing that one component.

## 7.6 The C36+ Molecular Weight Override

`KATZ_FIROOZABADI`'s built-in C36+ default molecular weight is 636.4 g/mol (see `docs/excel-deviations.md` D-001). The LiveOil v4.1 importer overrides this per sample: it reads `STO_Composition!D65` as `c36_mw`, then builds

```python
library = KATZ_FIROOZABADI.with_c36_mw(c36_mw)
```

before either composition stream (`STO_Composition`, `Gas_Composition`) is constructed. Both streams share that one per-sample library instance. This override is required for accuracy: building the streams against the unmodified canonical library reproduces the reference `f_gas` golden only to about 1e-4 (borderline); overriding C36+ MW first tightens that to about 1e-6.

The Flash v6.1 importer has no equivalent override; it always uses the canonical `KATZ_FIROOZABADI` library as-is.

## 7.7 Wrong-File Detection

Each importer checks that the workbook it was handed is actually an instance of the template it expects, before reading any input cell.

**Flash v6.1** (`flash_v61._check_layout`): the sheet must be named `Volumetrics_Master`; a missing sheet raises `InputValidationError` immediately:

```
{path}: missing required sheet 'Volumetrics_Master' — not an ADRIC Flash Separation Calc v6.1 workbook
```

Five anchor cells are then compared against expected text (`A1`, `B40`, `E40`, `F40`, `G40`, `H40`); any mismatch raises one error per mismatched cell, e.g.:

```
Volumetrics_Master!A1: expected 'ATMOSPHERIC FLASH SEPARATION - WATER PUMP METHOD (v6.1)', found <actual value>
```

**LiveOil v4.1** (`liveoil_v41._check_layout`): all five required sheets (`Sample_Info`, `STO_Composition`, `Gas_Composition`, `Recombination`, `Loading_Volumes`) must be present; any missing sheet raises `InputValidationError` naming the missing set. Nine anchor cells across those sheets are then compared against expected title/header text. The Flash v6.1 workbook is rejected by the missing-sheet check alone (it has no `Sample_Info`/`STO_Composition`/`Gas_Composition`/`Loading_Volumes` sheet), but it does carry a sheet literally named `Recombination` with an entirely different layout, which is why the title-anchor check on that sheet is kept too, rather than relying on sheet-name presence alone.

A third, LiveOil-specific check validates `Recombination!B6`'s GOR-basis dropdown text against the two recognized values ("Separator", "Stock Tank"); an unrecognized value raises its own typed error naming the cell:

```
Recombination!B6: unrecognized GOR basis '<value>'
```

## 7.8 Blank-Cell and Negative-Composition Error Behavior

Both importers apply the same two guards, using the same helper pattern (`_num`), and both name the offending cell in the raised error.

**Required scalar cells** (every cell read via `_num`: volumetrics inputs, sampling depth, STO density, C36+ MW, loading inputs, recombination inputs) are read with:

```python
def _num(ws, addr, errors):
    value = ws[addr].value
    if not isinstance(value, int | float):
        errors.append(f"{ws.title}!{addr} is blank or non-numeric")
        return 0.0
    return float(value)
```

A blank or non-numeric required cell is collected into `errors` rather than crashing `float(None)`/`float("...")` with a raw `TypeError`/`ValueError`. All such cells for a given block are checked before `InputValidationError(errors)` is raised, so a single import attempt reports every bad cell in that block at once, e.g.:

```
Volumetrics_Master!B14 is blank or non-numeric
```

**Composition cells** (Flash v6.1 columns E-H, rows 41-92; LiveOil v4.1 column I, rows 15-65) get a different treatment for blanks versus negatives:

- A blank or non-numeric composition cell is treated as absent, the same as an explicit zero, rather than crashing the sign check (`None < 0` raises `TypeError`).
- A composition cell that reads as a genuine negative number raises `InputValidationError`, naming the row, component code, and value, e.g.:

```
Volumetrics_Master!row 47 (C1): negative Gas Mol% value -0.5
Recombination!row 22 (nC5): negative Mol% value -1.2
```

(LiveOil errors are reported against whichever sheet, `STO_Composition` or `Gas_Composition`, the negative cell was found on; the example above uses the sheet's `.title`.)

`CompositionStream` itself does not validate value sign, so the Excel-import boundary is the deliberate place to reject a malformed lab entry sheet.

## 7.9 What Is Deliberately Not Read

Every importer reads a strict subset of its template's cells. The rest fall into two categories:

**Computed/downstream cells**, left alone because the engine recomputes them independently:

- Flash v6.1 `Volumetrics_Master`: B13, B16, B19 (computed sub-results inline in Block B), and all of Block C (`B25`-`B37`), are never read.
- Flash v6.1: `Component_Properties`, `Recombination`, and `Plus_Properties_Report` sheets are never opened at all.
- LiveOil v4.1: `STO_Composition!J{row}` and `Gas_Composition!J{row}` (Wt% INPUT column) are never read; only the Mol% column (`I`) is consumed.
- LiveOil v4.1: `Loading_Volumes!B13` (BSW / water content) and `Sample_Info!E8` (sampling date) have no corresponding dataclass field and are not read.

**Dead cells with a known workbook defect**, documented in `docs/excel-deviations.md` D-017: Flash v6.1 `Volumetrics_Master!E17` (barometric pressure) and `E20` (back pressure) feed the workbook's own `B25` `P_base` composite formula (barometric + back-pressure), but that composite is never actually used downstream in the workbook, `V_gas_std` there is computed from the measured absolute pressure cell (`B21`) instead. The engine mirrors this: `calculate()` takes only the measured absolute pressure input (`gas_abs_pressure_mbar`, from `B21`) and never consumes a barometric or back-pressure value. E17 and E20 are read by eye by the lab technician for QA purposes but have no path into any calculation, in the workbook or in the engine.
