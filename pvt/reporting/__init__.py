"""pvt.reporting — Report table builders and Excel export (Phase 2 Task 9).

`tables` turns the typed result dataclasses produced by `pvt.experiments`
(and the `QCResult` list from `pvt.qc`) into plain `ReportTable`/`ReportRow`
structures; `excel_export` writes those tables out as a single-sheet
ADRIC-styled Excel workbook via openpyxl.
"""
