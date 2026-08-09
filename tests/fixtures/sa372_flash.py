"""SA-372 flash GC compositions (ADRIC_Flash_Separation_Calc_v6.1.xlsx cached values).

Generated from `tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx`,
sheet `Volumetrics_Master`, rows 41-92 (the 52-slot GC composition block):
col B = component code, E = Gas Mol% (INPUT), F = Gas Wt% (INPUT),
G = Oil Mol% (INPUT), H = Oil Wt% (INPUT). Zero/None entries are omitted.
See the generator script embedded as a comment footer below for provenance
and the alias map applied to 3 workbook codes that don't match the
`pvt.core.components.KATZ_FIROOZABADI` library verbatim.
"""

GAS_MOL_PCT: dict[str, float] = {
    "H2S": 0.075, "CO2": 3.925, "N2": 0.588, "C1": 47.656, "C2": 14.083,
    "C3": 14.82, "iC4": 3.6, "nC4": 7.465, "NeoC5": 0.033, "iC5": 2.482,
    "nC5": 2.587, "C6": 1.613, "MCP": 0.165, "Benzene": 0.043, "CycloC6": 0.169,
    "C7": 0.341, "MCH": 0.064, "Toluene": 0.041, "C8": 0.134, "EBenzene": 0.009,
    "MP-Xylene": 0.01, "O-Xylene": 0.006, "C9": 0.058, "C10": 0.02, "C11": 0.008,
    "C12": 0.005,
}
GAS_WT_PCT: dict[str, float] = {
    "H2S": 0.078, "CO2": 5.251, "N2": 0.501, "C1": 23.242, "C2": 12.874,
    "C3": 19.867, "iC4": 6.361, "nC4": 13.19, "NeoC5": 0.072, "iC5": 5.443,
    "nC5": 5.675, "C6": 4.226, "MCP": 0.422, "Benzene": 0.103, "CycloC6": 0.432,
    "C7": 1.038, "MCH": 0.19, "Toluene": 0.114, "C8": 0.466, "EBenzene": 0.03,
    "MP-Xylene": 0.033, "O-Xylene": 0.018, "C9": 0.227, "C10": 0.088,
    "C11": 0.036, "C12": 0.023,
}
OIL_MOL_PCT: dict[str, float] = {
    "C1": 0.012, "C2": 0.126, "C3": 0.939, "iC4": 0.765, "nC4": 2.745,
    "iC5": 2.496, "nC5": 3.775, "C6": 6.941, "MCP": 1.214, "Benzene": 0.34,
    "CycloC6": 0.774, "C7": 6.273, "MCH": 1.399, "Toluene": 1.033, "C8": 6.419,
    "EBenzene": 0.683, "MP-Xylene": 1.276, "O-Xylene": 0.619, "C9": 5.368,
    "TMB124": 0.757, "C10": 6.216, "C11": 5.881, "C12": 4.81, "C13": 4.245,
    "C14": 3.669, "C15": 3.322, "C16": 2.762, "C17": 2.32, "C18": 2.09,
    "C19": 2.001, "C20": 1.73, "C21": 1.554, "C22": 1.335, "C23": 1.188,
    "C24": 1.081, "C25": 0.96, "C26": 0.86, "C27": 0.779, "C28": 0.729,
    "C29": 0.669, "C30": 0.611, "C31": 0.554, "C32": 0.492, "C33": 0.451,
    "C34": 0.429, "C35": 0.396, "C36+": 4.912,
}
OIL_WT_PCT: dict[str, float] = {
    "C1": 0.001, "C2": 0.02, "C3": 0.218, "iC4": 0.234, "nC4": 0.84,
    "iC5": 0.948, "nC5": 1.434, "C6": 3.15, "MCP": 0.538, "Benzene": 0.14,
    "CycloC6": 0.343, "C7": 3.309, "MCH": 0.723, "Toluene": 0.501, "C8": 3.86,
    "EBenzene": 0.382, "MP-Xylene": 0.713, "O-Xylene": 0.346, "C9": 3.625,
    "TMB124": 0.479, "C10": 4.656, "C11": 4.551, "C12": 4.077, "C13": 3.911,
    "C14": 3.67, "C15": 3.603, "C16": 3.228, "C17": 2.895, "C18": 2.762,
    "C19": 2.77, "C20": 2.504, "C21": 2.381, "C22": 2.143, "C23": 1.989,
    "C24": 1.883, "C25": 1.744, "C26": 1.626, "C27": 1.534, "C28": 1.489,
    "C29": 1.415, "C30": 1.338, "C31": 1.255, "C32": 1.15, "C33": 1.087,
    "C34": 1.066, "C35": 1.013, "C36+": 16.456,
}

# ---------------------------------------------------------------------------
# Provenance: throwaway generator script used to produce the four dicts above
# (run once from the repo root with the venv active; not part of the test
# suite). Cross-checked against the task-3 brief's digest spot values before
# being pasted in here — see the `assert` block below.
# ---------------------------------------------------------------------------
#
# """Throwaway generator for tests/fixtures/sa372_flash.py.
#
# Reads Volumetrics_Master rows 41-92 (the 52-slot GC composition block) from
# the ADRIC Flash Separation Calc v6.1 workbook and emits the four dicts used
# by the Task-3 golden tests: GAS_MOL_PCT, GAS_WT_PCT, OIL_MOL_PCT, OIL_WT_PCT.
#
# Column layout confirmed by direct inspection of Volumetrics_Master!A40:I40:
#   B = component code, E = Gas Mol% (INPUT), F = Gas Wt% (INPUT),
#   G = Oil Mol% (INPUT), H = Oil Wt% (INPUT).
#
# Workbook component codes were checked one-by-one against
# pvt.core.components.KATZ_FIROOZABADI.codes; 49/52 codes match the library
# verbatim. The remaining 3 needed an explicit alias (workbook code -> library
# code), confirmed by inspecting the workbook's Component column (C) text and
# the KF library's `name`/`code` fields side by side:
#   - "Cyclohex"   -> "CycloC6"    (workbook Component col says "Cyclohexane")
#   - "MPXylenes"  -> "MP-Xylene"  (workbook Component col says "M/P-Xylenes")
#   - "OXylene"    -> "O-Xylene"   (workbook Component col says "O-Xylene")
# Row order (after aliasing) was verified to equal KF.codes exactly
# (list(KF.codes) == aliased_workbook_order -> True), which is what makes the
# plus_fraction() positional-boundary convention well-defined.
# """
#
# import openpyxl
#
# from pvt.core.components import KATZ_FIROOZABADI as KF
#
# ALIAS = {
#     "Cyclohex": "CycloC6",
#     "MPXylenes": "MP-Xylene",
#     "OXylene": "O-Xylene",
# }
#
# wb = openpyxl.load_workbook(
#     "tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx", data_only=True
# )
# ws = wb["Volumetrics_Master"]
#
# gas_mol: dict[str, float] = {}
# gas_wt: dict[str, float] = {}
# oil_mol: dict[str, float] = {}
# oil_wt: dict[str, float] = {}
#
# order: list[str] = []
# for row in range(41, 93):
#     raw_code = ws.cell(row=row, column=2).value
#     code = ALIAS.get(raw_code, raw_code)
#     assert code in KF.codes, f"row {row}: {raw_code!r} (aliased {code!r}) not in KF library"
#     order.append(code)
#
#     gm = ws.cell(row=row, column=5).value
#     gw = ws.cell(row=row, column=6).value
#     om = ws.cell(row=row, column=7).value
#     ow = ws.cell(row=row, column=8).value
#
#     if gm:
#         gas_mol[code] = gm
#     if gw:
#         gas_wt[code] = gw
#     if om:
#         oil_mol[code] = om
#     if ow:
#         oil_wt[code] = ow
#
# assert order == list(KF.codes), "workbook row order does not match KF.codes positional order"
#
# # Cross-check digest spot values before emitting the fixture file.
# checks = [
#     ("gas C1 mol", gas_mol["C1"], 47.656),
#     ("gas C1 wt", gas_wt["C1"], 23.242),
#     ("gas C3 mol", gas_mol["C3"], 14.82),
#     ("gas C3 wt", gas_wt["C3"], 19.867),
#     ("oil C7 mol", oil_mol["C7"], 6.273),
#     ("oil C7 wt", oil_wt["C7"], 3.309),
#     ("oil C36+ mol", oil_mol["C36+"], 4.912),
#     ("oil C36+ wt", oil_wt["C36+"], 16.456),
#     ("oil C1 mol", oil_mol["C1"], 0.012),
#     ("oil C1 wt", oil_wt["C1"], 0.001),
#     ("gas H2S mol", gas_mol["H2S"], 0.075),
#     ("gas H2S wt", gas_wt["H2S"], 0.078),
# ]
# for label, got, want in checks:
#     assert abs(got - want) < 1e-9, f"MISMATCH {label}: got {got}, want {want}"
