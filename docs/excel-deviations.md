# Excel Deviations Ledger

Every place the Python engine deliberately differs from a source workbook.
Each entry needs: workbook + cell proof, what Excel does, what the engine does, status
(`proposed` until reviewed point-by-point with Swej, then `approved`/`parity-kept`).

| ID | Workbook / cell | Excel behavior | Engine behavior | Status |
|----|-----------------|----------------|-----------------|--------|
| D-001 | Library canonization: LiveOil v4.1 vs Flash v6.1 `Component_Properties` (C7 100.205 vs 100.204; H2S 34.082 vs 34.0809; C36+ default 635 vs 636.4) | Two variants in circulation | One canonical table (Flash v6.1 values); C36+ MW is a per-study override | proposed |
