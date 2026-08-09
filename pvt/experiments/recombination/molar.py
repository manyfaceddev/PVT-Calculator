"""Molar-basis recombination of stock-tank oil (STO) + recombination gas into a
wellstream, per the LiveOil v4.1 Recombination sheet (PV=ZnRT molar split).

Given a lab GOR (scf gas per barrel of oil, on either a separator or
stock-tank basis) plus STO density/MW and gas MW, `molar_split` computes the
molar gas/oil split — moles of gas and moles of oil per cc of stock-tank oil,
at standard conditions — that reproduces that GOR (ideal-gas PV=ZnRT at
standard conditions for the gas moles; ρ/MW for the oil moles). `wellstream`
then blends the STO and gas compositions on that molar split into a single
recombined-fluid composition. `k_values` derives y/x equilibrium ratios from
any gas/liquid stream pair.
"""

import enum
from dataclasses import dataclass

from pvt.core import constants as c
from pvt.core.composition import CompositionStream


class GorBasis(enum.StrEnum):
    """Basis of the input GOR value passed to `molar_split`."""

    SEPARATOR = "separator"
    """scf gas per separator barrel of oil — divided by shrinkage to convert
    to a stock-tank-oil (scf/STB) basis before use."""

    STOCK_TANK = "stock_tank"
    """Already scf gas per STB stock-tank oil — used as-is."""


@dataclass(frozen=True)
class MolarSplit:
    """Molar gas/oil split for a recombination GOR, per cc of stock-tank oil."""

    gor_scf_stb_effective: float
    """GOR on a stock-tank (scf/STB) basis, after the `GorBasis` conversion."""

    gor_cc_cc: float
    """`gor_scf_stb_effective` converted to cc gas per cc stock-tank oil."""

    n_gas_per_cc_sto: float
    """Moles of gas per cc of stock-tank oil (ideal gas at standard conditions)."""

    n_oil_per_cc_sto: float
    """Moles of stock-tank oil per cc of stock-tank oil (= density / MW)."""

    f_gas: float
    """Gas mole fraction of the wellstream: n_gas / (n_gas + n_oil)."""

    f_oil: float
    """Oil mole fraction of the wellstream: n_oil / (n_gas + n_oil)."""

    w_gas: float
    """Gas mass fraction of the wellstream."""

    w_oil: float
    """Oil mass fraction of the wellstream."""

    mw_wellstream: float
    """Molecular weight of the recombined wellstream: f_gas·MW_gas + f_oil·MW_sto."""


def molar_split(
    gor: float,
    basis: GorBasis,
    shrinkage: float,
    sto_density_g_cc: float,
    sto_mw: float,
    gas_mw: float,
    z_std: float = 0.99,
) -> MolarSplit:
    """Compute the molar gas/oil split for a recombination GOR.

    Args:
        gor: Lab GOR (scf gas per barrel of oil), on the basis given by `basis`.
        basis: Whether `gor` is separator-basis (scf/sep-bbl) or already
            stock-tank basis (scf/STB).
        shrinkage: Separator-oil shrinkage factor SF = V_STO / V_sep_oil.
            Only used to convert a SEPARATOR-basis GOR to stock-tank basis
            (see `GorBasis.SEPARATOR`); has no effect for STOCK_TANK basis.
        sto_density_g_cc: Stock-tank oil density at standard conditions (g/cc).
        sto_mw: Stock-tank oil molecular weight (g/mol).
        gas_mw: Recombination gas molecular weight (g/mol).
        z_std: Gas Z-factor at standard conditions (default 0.99, per the
            LiveOil Recombination sheet).

    Returns:
        MolarSplit with the effective GOR, its cc/cc equivalent, moles of gas
        and oil per cc of stock-tank oil, gas/oil mole and mass fractions, and
        the resulting wellstream molecular weight.
    """
    # D-018: conventional direction — separator-basis GOR (scf/sep-bbl) is
    # divided by shrinkage to convert to a stock-tank (scf/STB) basis;
    # stock-tank-basis GOR is already on that basis and used as-is. LiveOil
    # v4.1 Recombination!B8 implements the reverse (divides on the
    # STOCK_TANK branch instead); see docs/excel-deviations.md D-018.
    if basis == GorBasis.SEPARATOR:
        gor_eff = gor / shrinkage
    else:
        gor_eff = gor

    gor_cc = gor_eff * c.SCF_STB_TO_CC_CC
    n_gas = c.P_STD_PSIA * gor_cc / (z_std * c.R_PSIA_CC_MOL_K * c.T_STD_K)
    n_oil = sto_density_g_cc / sto_mw

    n_total = n_gas + n_oil
    f_gas = n_gas / n_total
    f_oil = n_oil / n_total

    mass_gas = f_gas * gas_mw
    mass_oil = f_oil * sto_mw
    mw_wellstream = mass_gas + mass_oil
    w_gas = mass_gas / mw_wellstream
    w_oil = mass_oil / mw_wellstream

    return MolarSplit(
        gor_scf_stb_effective=gor_eff,
        gor_cc_cc=gor_cc,
        n_gas_per_cc_sto=n_gas,
        n_oil_per_cc_sto=n_oil,
        f_gas=f_gas,
        f_oil=f_oil,
        w_gas=w_gas,
        w_oil=w_oil,
        mw_wellstream=mw_wellstream,
    )


def wellstream(
    split: MolarSplit, sto: CompositionStream, gas: CompositionStream
) -> CompositionStream:
    """Blend a stock-tank-oil and gas composition into a recombined wellstream.

    zᵢ = f_gas·yᵢ + f_oil·xᵢ, on each input stream's normalized (sum-to-100)
    mol% basis.

    Args:
        split: Molar gas/oil split from `molar_split`.
        sto: Stock-tank oil composition (mol% basis).
        gas: Recombination gas composition (mol% basis).

    Returns:
        CompositionStream for the recombined wellstream (mol% basis). Sums to
        100 because f_gas + f_oil = 1 and each input basis is normalized to
        100 before blending.
    """
    x = sto.normalized_mol()
    y = gas.normalized_mol()
    codes = set(x) | set(y)
    z = {code: split.f_gas * y.get(code, 0.0) + split.f_oil * x.get(code, 0.0) for code in codes}
    return CompositionStream(library=sto.library, mol_pct=z)


def k_values(gas: CompositionStream, liquid: CompositionStream) -> dict[str, float]:
    """Equilibrium K-values (K = y/x) from a gas/liquid stream pair.

    Computed on each stream's normalized (sum-to-100) mol% basis. Only
    components with a positive liquid mol fraction are included — x=0 would
    make K undefined (or infinite); a component present only in the gas
    stream is simply omitted rather than reported as K=inf.

    Args:
        gas: Gas-phase composition (mol% basis).
        liquid: Liquid-phase composition (mol% basis).

    Returns:
        Mapping of component code -> K = y/x, for every code with x > 0 in
        `liquid`'s normalized mol% basis. A code present in `liquid` but
        absent from `gas` contributes y=0, giving K=0.0 (still included).
    """
    y = gas.normalized_mol()
    x = liquid.normalized_mol()
    codes = set(x) | set(y)
    return {code: y.get(code, 0.0) / x[code] for code in codes if x.get(code, 0.0) > 0}
