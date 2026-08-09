"""Importers for filled ADRIC Excel lab templates.

Each module owns one template version (e.g. `flash_v61` for
`ADRIC_Flash_Separation_Calc_v6.1.xlsx`) and exposes a single `read(path)`
entry point returning a frozen dataclass ready to hand to the matching
`pvt.experiments` calculation chain.
"""
