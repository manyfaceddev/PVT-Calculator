"""Katz-Firoozabadi component library for PVT calculations."""

import dataclasses
from dataclasses import dataclass


@dataclass(frozen=True)
class Component:
    """A thermodynamic component with physical properties.

    Attributes:
        code: Component code (e.g., 'C1', 'Toluene').
        name: Full component name.
        mw: Molecular weight (g/mol).
        liquid_density_g_cc: Liquid density (g/cm³).
        tb_r: Boiling point (°R).
        pc_psia: Critical pressure (psia).
        tc_r: Critical temperature (°R).
    """

    code: str
    name: str
    mw: float
    liquid_density_g_cc: float
    tb_r: float
    pc_psia: float
    tc_r: float

    @property
    def molar_volume_cc(self) -> float:
        """Molar volume in cm³/mol = MW / liquid_density."""
        return self.mw / self.liquid_density_g_cc


# Data source: ADRIC_Flash_Separation_Calc_v6.1.xlsx, Component_Properties sheet
# 52 entries: code, name, mw, density (g/cc), Tb (°R), Pc (psia), Tc (°R)
# SCN rows (C7...C36+) use the workbook's rounded n-alkane MW variant (e.g.
# C7 100.204, C11 156.0) rather than Katz-Firoozabadi's generalized-fraction
# MWs — the workbook is the source of record for this table per D-001.
_KF_ROWS: list[tuple[str, str, float, float, float, float, float]] = [
    ("H2", "Hydrogen", 2.016, 0.0711, 36.7, 188.0, 59.4),
    ("H2S", "Hydrogen sulfide", 34.0809, 0.8006, 383.1, 1300.0, 672.4),
    ("CO2", "Carbon dioxide", 44.0095, 0.818, 350.0, 1071.0, 547.6),
    ("N2", "Nitrogen", 28.0134, 0.8094, 139.3, 493.0, 227.2),
    ("C1", "Methane", 16.043, 0.3, 200.7, 666.4, 343.0),
    ("C2", "Ethane", 30.07, 0.3562, 332.2, 706.5, 549.6),
    ("C3", "Propane", 44.097, 0.507, 415.9, 616.0, 665.7),
    ("iC4", "i-Butane", 58.123, 0.5629, 470.6, 527.9, 734.1),
    ("nC4", "n-Butane", 58.123, 0.584, 490.7, 550.6, 765.3),
    ("NeoC5", "Neopentane", 72.151, 0.5967, 482.6, 464.0, 734.6),
    ("iC5", "i-Pentane", 72.151, 0.6244, 541.7, 490.4, 828.7),
    ("nC5", "n-Pentane", 72.151, 0.6311, 556.6, 488.6, 845.5),
    ("C6", "Hexanes", 86.177, 0.664, 615.4, 436.9, 913.3),
    ("MCP", "Methylcyclopentane", 84.16, 0.7536, 621.0, 548.9, 959.2),
    ("Benzene", "Benzene", 78.11, 0.8844, 636.3, 710.4, 1012.0),
    ("CycloC6", "Cyclohexane", 84.16, 0.7834, 637.2, 590.8, 996.5),
    ("C7", "Heptanes", 100.204, 0.722, 668.8, 396.8, 972.4),
    ("MCH", "Methylcyclohexane", 98.19, 0.7702, 675.0, 503.5, 1029.8),
    ("Toluene", "Toluene", 92.14, 0.8718, 690.5, 595.9, 1065.6),
    ("C8", "Octanes", 114.231, 0.745, 717.9, 360.7, 1023.9),
    ("EBenzene", "Ethylbenzene", 106.17, 0.872, 735.5, 523.5, 1111.1),
    ("MP-Xylene", "m/p-Xylene", 106.17, 0.8687, 738.4, 513.6, 1112.8),
    ("O-Xylene", "o-Xylene", 106.17, 0.8848, 751.9, 541.4, 1135.4),
    ("C9", "Nonanes", 128.258, 0.764, 763.1, 331.8, 1070.4),
    ("TMB124", "1,2,4-Trimethylbenzene", 120.195, 0.876, 807.5, 495.0, 1129.0),
    ("C10", "Decanes", 142.285, 0.778, 805.2, 305.7, 1111.8),
    ("C11", "Undecanes", 156.0, 0.789, 847.0, 285.0, 1150.0),
    ("C12", "Dodecanes", 170.0, 0.8, 885.0, 264.0, 1185.0),
    ("C13", "Tridecanes", 184.0, 0.811, 923.0, 246.0, 1220.0),
    ("C14", "Tetradecanes", 198.0, 0.822, 958.0, 230.0, 1250.0),
    ("C15", "Pentadecanes", 212.0, 0.832, 991.0, 217.0, 1280.0),
    ("C16", "Hexadecanes", 226.0, 0.839, 1020.0, 205.0, 1305.0),
    ("C17", "Heptadecanes", 240.0, 0.847, 1049.0, 193.0, 1332.0),
    ("C18", "Octadecanes", 254.0, 0.852, 1075.0, 186.0, 1354.0),
    ("C19", "Nonadecanes", 268.0, 0.857, 1101.0, 175.0, 1381.0),
    ("C20", "Eicosanes", 282.0, 0.862, 1124.0, 167.0, 1402.0),
    ("C21", "C21", 296.0, 0.867, 1146.0, 159.0, 1424.0),
    ("C22", "C22", 310.0, 0.872, 1167.0, 152.0, 1442.0),
    ("C23", "C23", 324.0, 0.877, 1187.0, 146.0, 1460.0),
    ("C24", "C24", 338.0, 0.881, 1207.0, 140.0, 1478.0),
    ("C25", "C25", 352.0, 0.885, 1226.0, 134.0, 1494.0),
    ("C26", "C26", 366.0, 0.889, 1244.0, 129.0, 1509.0),
    ("C27", "C27", 380.0, 0.893, 1262.0, 125.0, 1523.0),
    ("C28", "C28", 394.0, 0.896, 1277.0, 120.0, 1537.0),
    ("C29", "C29", 408.0, 0.899, 1294.0, 116.0, 1550.0),
    ("C30", "C30", 422.0, 0.902, 1310.0, 112.0, 1563.0),
    ("C31", "C31", 436.0, 0.906, 1323.0, 108.0, 1574.0),
    ("C32", "C32", 450.0, 0.909, 1335.0, 104.0, 1584.0),
    ("C33", "C33", 464.0, 0.912, 1349.0, 101.0, 1594.0),
    ("C34", "C34", 478.0, 0.915, 1360.0, 98.0, 1603.0),
    ("C35", "C35", 492.0, 0.917, 1373.0, 95.0, 1612.0),
    ("C36+", "C36 plus", 636.4, 0.94, 1490.0, 80.0, 1700.0),
]


class ComponentLibrary:
    """Collection of components with lookup and override capabilities."""

    def __init__(self, components: dict[str, Component]) -> None:
        """Initialize library from a component dictionary.

        Args:
            components: Dict mapping code to Component.
        """
        self._components = components
        self._codes = tuple(components.keys())

    @classmethod
    def from_rows(cls, rows: list[tuple[str, str, float, float, float, float, float]]) -> "ComponentLibrary":
        """Create library from tabular data rows.

        Args:
            rows: List of (code, name, mw, density, tb, pc, tc) tuples.

        Returns:
            ComponentLibrary instance with components built from rows.
        """
        components = {
            row[0]: Component(
                code=row[0],
                name=row[1],
                mw=row[2],
                liquid_density_g_cc=row[3],
                tb_r=row[4],
                pc_psia=row[5],
                tc_r=row[6],
            )
            for row in rows
        }
        return cls(components)

    def get(self, code: str) -> Component:
        """Retrieve a component by code.

        Args:
            code: Component code.

        Returns:
            Component object.

        Raises:
            KeyError: If code is not found.
        """
        return self._components[code]

    @property
    def codes(self) -> tuple[str, ...]:
        """Component codes in order, as an immutable tuple.

        Returned as a tuple (not the internal list) so callers cannot
        mutate the library's singleton state by mutating what they get
        back from this property.
        """
        return self._codes

    def with_c36_mw(self, mw: float) -> "ComponentLibrary":
        """Create a new library with C36+ MW overridden.

        Args:
            mw: New molecular weight for C36+.

        Returns:
            New ComponentLibrary with isolated C36+ Component (others shared).
        """
        c36_old = self._components["C36+"]
        c36_new = dataclasses.replace(c36_old, mw=mw)
        new_components = self._components.copy()
        new_components["C36+"] = c36_new
        return ComponentLibrary(new_components)


# Module constant: canonical Katz-Firoozabadi library (52 components from Flash v6.1)
KATZ_FIROOZABADI = ComponentLibrary.from_rows(_KF_ROWS)
