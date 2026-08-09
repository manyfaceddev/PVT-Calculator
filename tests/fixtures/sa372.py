"""Sample SA-372 lab data (ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx cached values)."""

STO_MOL_PCT: dict[str, float] = {
    "C2": 0.18, "C3": 1.65, "iC4": 1.20, "nC4": 3.98, "iC5": 2.99, "nC5": 4.33,
    "C6": 7.09, "MCP": 1.24, "Benzene": 0.34, "CycloC6": 0.75, "C7": 6.12,
    "MCH": 1.34, "Toluene": 0.99, "C8": 6.19, "EBenzene": 0.65, "MP-Xylene": 1.20,
    "O-Xylene": 0.59, "C9": 5.17, "C10": 6.00, "C11": 5.60, "C12": 4.57,
    "C13": 4.03, "C14": 3.51, "C15": 3.13, "C16": 2.62, "C17": 2.20, "C18": 1.99,
    "C19": 1.89, "C20": 1.64, "C21": 1.47, "C22": 1.28, "C23": 1.13, "C24": 1.02,
    "C25": 0.90, "C26": 0.82, "C27": 0.73, "C28": 0.69, "C29": 0.63, "C30": 0.58,
    "C31": 0.52, "C32": 0.47, "C33": 0.43, "C34": 0.41, "C35": 0.36, "C36+": 4.69,
}
GAS_MOL_PCT: dict[str, float] = {
    "CO2": 4.71, "N2": 0.87, "C1": 62.51, "C2": 14.17, "C3": 9.98, "iC4": 1.77,
    "nC4": 3.25, "NeoC5": 0.01, "iC5": 0.86, "nC5": 0.88, "C6": 0.55, "MCP": 0.06,
    "Benzene": 0.02, "CycloC6": 0.06, "C7": 0.13, "MCH": 0.02, "Toluene": 0.03,
    "C8": 0.05, "EBenzene": 0.01, "MP-Xylene": 0.01, "C9": 0.03, "C10": 0.01, "C11": 0.01,
}
STO_MW_FROM_MOL = 187.05     # workbook B7 (uses C36+ MW = 635)
STO_C36_MW = 635.0
GAS_MW_FROM_MOL = 26.10      # workbook B6
STO_DENSITY_60F = 0.8196     # g/cc, input B5
