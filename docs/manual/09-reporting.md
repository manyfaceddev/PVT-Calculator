# Chapter 9: Reporting

## 9.1 The ReportRow / ReportTable Model

Module: `pvt/reporting/tables.py`. Two small frozen dataclasses carry every report, regardless of which experiment produced it or which format (Excel, in-app pill list, CLI text) ultimately renders it:

```python
@dataclass(frozen=True)
class ReportRow:
    label: str
    value: str
    unit: str = ""

@dataclass(frozen=True)
class ReportTable:
    title: str
    rows: list[ReportRow]
```

A `ReportRow` is a single labelled value, already formatted as a string (the builder functions below choose the decimal precision per field, e.g. `f"{results.v_press_cc:.4f}"`), plus an optional unit string. A `ReportTable` is a titled block of rows, one report section. A report is simply `list[ReportTable]`.

Every `ReportTable` list built by this module ends with a `"QC Summary"` section, built by the shared helper:

```python
def _qc_rows(qc: list[QCResult]) -> list[ReportRow]:
    return [ReportRow(result.check_id, result.severity.value, result.message) for result in qc]
```

One row per `QCResult`: label is the `check_id`, value is the severity string (`"PASS"`/`"REVIEW"`/`"FAIL"`), unit holds the full check message. Every `QCResult` a caller passes in is guaranteed to appear as its own row, nothing is filtered or deduplicated at this layer.

## 9.2 flash_tables

```python
def flash_tables(results: FlashResults, recomb: MassRecombination, qc: list[QCResult]) -> list[ReportTable]
```

Builds three sections from a flash-separation run (`pvt.experiments.flash.calc.calculate`) and its mass-basis recombination (`pvt.experiments.flash.recombine.recombine_mass`):

**"Flash Results"** (12 rows, from `FlashResults`):

| Label | Source field | Format | Unit |
|---|---|---|---|
| Charge Pressure Volume | `v_press_cc` | `.4f` | cc |
| Flashed Oil Mass | `m_oil_g` | `.2f` | g |
| Gas Volume (Measured) | `v_gas_meas_cc` | `.2f` | cc |
| Gas Volume (Standard) | `v_gas_std_cc` | `.2f` | cc |
| Gas Density (Standard) | `gas_density_std_g_cc` | `.6f` | g/cc |
| Flashed Gas Mass | `m_gas_g` | `.5f` | g |
| GOR | `gor_cc_cc` | `.4f` | cc/cc |
| GOR | `gor_scf_bbl` | `.2f` | scf/bbl |
| Bo | `bo_flash` | `.4f` | vol/vol |
| Shrinkage | `shrinkage` | `.4f` | (none) |
| Oil Density (60F) | `oil_density_60f_g_cc` | `.4f` | g/cc |
| API Gravity | `api` | `.1f` | API |

**"Whole Sample"** (3 rows, from `MassRecombination`):

| Label | Source field | Format | Unit |
|---|---|---|---|
| Gas Mass Fraction | `wf_gas * 100.0` | `.2f` | wt% |
| Oil Mass Fraction | `wf_oil * 100.0` | `.2f` | wt% |
| Whole Sample MW | `mw_whole_sample` | `.2f` | g/mol |

**"QC Summary"**: `_qc_rows(qc)`, one row per `QCResult` passed in.

## 9.3 recombination_tables

```python
def recombination_tables(split: MolarSplit, plan: LoadingPlan, qc: list[QCResult]) -> list[ReportTable]
```

Builds three sections from a molar gas/oil split (`pvt.experiments.recombination.molar.molar_split`) and a cylinder loading plan (`pvt.experiments.recombination.loading.plan_loading`):

**"Molar Split"** (9 rows, from `MolarSplit`):

| Label | Source field | Format | Unit |
|---|---|---|---|
| GOR (Effective) | `gor_scf_stb_effective` | `.2f` | scf/STB |
| GOR | `gor_cc_cc` | `.4f` | cc/cc |
| Gas Moles per cc STO | `n_gas_per_cc_sto` | `.6f` | mol/cc |
| Oil Moles per cc STO | `n_oil_per_cc_sto` | `.6f` | mol/cc |
| Gas Mole Fraction | `f_gas * 100.0` | `.2f` | mol% |
| Oil Mole Fraction | `f_oil * 100.0` | `.2f` | mol% |
| Gas Mass Fraction | `w_gas * 100.0` | `.2f` | wt% |
| Oil Mass Fraction | `w_oil * 100.0` | `.2f` | wt% |
| Wellstream MW | `mw_wellstream` | `.2f` | g/mol |

**"Loading Plan"** (10 rows, from `LoadingPlan`):

| Label | Source field | Format | Unit |
|---|---|---|---|
| Oil Charge Volume | `v_oil_charge_cc` | `.2f` | cc |
| STO Equivalent Volume | `v_sto_equivalent_cc` | `.2f` | cc |
| Oil Moles Charged | `n_oil_mol` | `.6f` | mol |
| Gas Moles Required | `n_gas_mol` | `.6f` | mol |
| Gas Volume (Standard) | `v_gas_std_cc` | `.2f` | cc |
| Std cc per cc (Load) | `std_cc_per_cc_at_load` | `.4f` | (none) |
| Gas Charge Volume | `v_gas_charge_cc` | `.2f` | cc |
| Total Charge Volume | `total_charge_cc` | `.2f` | cc |
| Fits Cylinder | `"Yes" if plan.fits else "No"` | | (none) |
| Cylinder Utilization | `utilization_pct` | `.2f` | % |

**"QC Summary"**: `_qc_rows(qc)`, one row per `QCResult` passed in.

## 9.4 Excel Export Styling

Module: `pvt/reporting/excel_export.py`. `write_report(path, tables, *, title, sample)` writes a single-sheet, ADRIC-styled workbook via `openpyxl`. `path` accepts a filesystem path or any writable binary file-like object (e.g. an in-memory `BytesIO`), because `Workbook.save` accepts either transparently.

### Colors

```python
_NAVY = "00205B"
_WHITE = "FFFFFF"

_SEVERITY_FILL = {
    "PASS": "38A169",
    "REVIEW": "DD9A0A",
    "FAIL": "E53E3E",
}
```

- **ADRIC navy header**: the title banner cell (row 1) uses `_HEADER_FONT = Font(color=_WHITE, bold=True, size=14)` on `_HEADER_FILL = PatternFill("solid", fgColor=_NAVY)`, i.e. hex `00205B`, merged across all three columns.
- **Severity fills**: any data row whose *value* cell (column B) reads exactly `"PASS"`, `"REVIEW"`, or `"FAIL"` gets that cell filled solid with the matching hex color: green `38A169` for PASS, amber `DD9A0A` for REVIEW, red `E53E3E` for FAIL. This is a plain string match in `_write_row`, so it fires for QC Summary rows and any other row whose formatted value happens to equal one of those three strings.

### Column layout

Every row is written as three columns: label (A), value (B), unit (C). Section titles and the title banner are single cells merged across all three columns (`_LAST_COLUMN = 3`).

Top to bottom, a written report is:

1. Navy title banner (row 1), merged A:C.
2. Spacer row.
3. **"Sample Information"** section (bold, merged title row), then 9 rows built from the `Sample` passed in: Sample ID, Well, Field, Reservoir, Depth (MD) in ft (formatted `.1f`, or `"N/A"` if `None`), Fluid Type, Cylinder, Client, Project.
4. Spacer row.
5. Each `ReportTable` in the `tables` argument, in order: a bold section-title row, then each of its rows as label/value/unit, then a spacer row.

Column widths are fixed: `A` = 30, `B` = 20, `C` = 50. Column C was widened from an earlier value of 16 specifically because QC Summary rows put the full check message in this column (e.g. `"Hoffman-Crump crossplot R²=0.9657 over 3 points (REVIEW)"`), and at 16 characters wide Excel's on-screen display clipped the message (the stored cell value itself was never truncated, only its rendering).

## 9.5 Downloads in the App

`ui/common/components.py`'s `report_download(tables, sample, filename, *, title=None)` is what every page's "Download Excel Report" button calls. The workbook is built **entirely in memory**, never touching disk:

```python
buffer = BytesIO()
write_report(buffer, tables, title=report_title, sample=sample)
buffer.seek(0)
st.download_button(
    "Download Excel Report",
    data=buffer,
    file_name=_prefixed_filename(filename, sample.sample_id),
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
```

The report title defaults to the base filename, Title-Cased with underscores turned to spaces (`_derive_title`, e.g. `"flash_separation_report.xlsx"` becomes `"Flash Separation Report"`), unless the caller supplies an explicit `title`.

The download filename is prefixed with the sample ID before it reaches the browser:

```python
def _prefixed_filename(filename: str, sample_id: str) -> str:
    prefix = "_".join(sample_id.split()) or "sample"
    return f"{prefix}_{filename}"
```

Whitespace in `sample_id` is collapsed to underscores. This exists so that reports downloaded for different samples do not share a download name and silently clobber each other in a browser's downloads folder.

## 9.6 CLI Text Reports

`cli.py` has two subcommands; only one of them uses the `ReportTable`/`ReportRow` model above.

### `flash` subcommand

```
python cli.py flash --workbook path/to/ADRIC_Flash_Separation_Calc_v6.1.xlsx
```

`_run_flash` imports the workbook via `pvt.io.excel_import.flash_v61.read`, runs `calculate()` and `recombine_mass()`, builds exactly four composition-normalization checks and two `mw_consistency` checks (gas mol%, gas wt%, oil mol%, oil wt% normalization; gas and oil MW consistency, no Hoffman-Crump crossplot and no GOR verification in this path), calls `flash_tables(results, recomb, qc)`, and prints the result as fixed-width text via `_format_report_tables`:

```python
_COL = 26   # label column width
_W   = 52   # total line width (inside borders)

def _rule(char="="):
    return char * (_W + 4)

def _row(label, value):
    return f"  {label:<{_COL}}: {value}"

def _section(title):
    pad = (_W - len(title)) // 2
    return f"\n{'─' * (pad + 2)} {title} {'─' * (_W - pad - len(title) + 2)}"
```

`_format_report_tables(tables, sample, title)` renders: a top `=` rule and the title, a `SAMPLE` section (Sample ID, Well, Field, Client, read straight off the `Sample`), then each `ReportTable` as an upper-cased, dash-bracketed section header followed by its rows rendered `"{value} {unit}".strip()`, then a closing `=` rule. On import failure, `InputValidationError`'s `.errors` are printed one per line to stderr (`error: <message>`) and the command exits 1; an `OSError` (e.g. file not found) is reported the same way.

### `recombine` subcommand

```
python cli.py recombine --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 \
    --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820
```

This is the original single-purpose CLI (multi-stage separator recombination, Carlsen & Whitson SF/FF flow), predating the `ReportTable` model. It builds its fixed-width report by hand, appending directly to a `lines: list[str]`, using the same `_rule`/`_row`/`_section` helpers, rather than constructing `ReportTable`/`ReportRow` objects. Its sections are: SETUP, RECOMBINATION CONDITIONS, one STAGE block per separator stage, CHARGE VOLUMES, VERIFICATION (back-calculated GOR match, with a checkmark or a `⚠  deviation X%` flag if the round-trip error exceeds 0.1%), and, when both `--api` and `--sg_gas` are supplied, a BUBBLE POINT ESTIMATE section from Standing's (1947) correlation. The report closes with a fixed footer line: `Standard conditions: 14.73 psia (lab basis) / 60 °F`.
