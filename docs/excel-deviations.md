# Excel Deviations Ledger

Every place the Python engine deliberately differs from a source workbook.
Each entry needs: workbook + cell proof, what Excel does, what the engine does, status
(`proposed` until reviewed point-by-point with Swej, then `approved`/`parity-kept`).

| ID | Workbook / cell | Excel behavior | Engine behavior | Status |
|----|-----------------|----------------|-----------------|--------|
| D-001 | Library canonization: LiveOil v4.1 vs Flash v6.1 `Component_Properties` (C7 100.205 vs 100.204; H2S 34.082 vs 34.0809; C36+ default 635 vs 636.4) | Two variants in circulation | One canonical table (Flash v6.1 values); C36+ MW is a per-study override | proposed |
| D-002 | Engine-wide | Sheets never call their validators; silent div/0 possible (e.g. recomb calc.py P_recomb=0) | calc entry points raise `InputValidationError` (Phase 2 pattern; recombination retrofit tracked there) | proposed |
| D-015 | Engine-wide vs pre-Phase-0 app | Old recombination app used P_std=14.696 psia and CC_PER_STB=158987.1 | Canonical lab basis P_STD_PSIA=14.73 + CC_PER_STB=158987.29 per spec §6; recombination outputs shift ~0.2% vs the old app | proposed |
| D-003 | `Z factor calculation.xls` Properties!J4 | CO2 coefficient alpha2 = -0.09034 (digit transposition) | Piper-McCain-Corredor gravity form uses the published alpha2 = -0.90348 (SPE 26668, 1993); Tpc shifts ~2.5% vs the transposed value at 20% CO2 | proposed |
| D-004 | `Z factor calculation.xls` Piper-McCain-Corredor compositional form, C7+ MW cell | C7+ molecular weight is an unweighted sum/average across C7+ species | Engine mole-fraction-weights the C7+ MW: Sigma(y_i*MW_i) / Sigma(y_i), per SPE 26668 | proposed |
| D-005 | `Z factor calculation.xls` Dranchuk-Abou-Kassem Z-factor Newton iteration | Incorrect Newton derivative formula in the implicit residual with respect to Z | Engine uses mathematically correct derivative of the compressibility residual; converged Z roots remain identical (divergence only in iteration path) | proposed |
