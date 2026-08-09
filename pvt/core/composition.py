"""
pvt/core/composition.py — CompositionStream: mole/weight composition arithmetic
over a ComponentLibrary. The shared composition abstraction consumed by every
experiment module (flash separation, recombination, CCE/CVD reports, ...).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from pvt.core.components import ComponentLibrary
from pvt.core.constants import AIR_MW
from pvt.core.exceptions import InputValidationError


@dataclass(frozen=True)
class CompositionStream:
    """A single fluid stream's composition, on a mol% and/or wt% basis.

    Exactly one of `mol_pct` / `wt_pct` may be supplied and non-empty at
    construction time, but both may be present after derivation (see
    `wt_from_mol`). Component keys must exist in `library`.
    """

    library: ComponentLibrary
    mol_pct: Mapping[str, float] | None = None
    wt_pct: Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        errors: list[str] = []

        if not self.mol_pct and not self.wt_pct:
            errors.append("CompositionStream requires mol_pct and/or wt_pct.")

        for basis in (self.mol_pct, self.wt_pct):
            if not basis:
                continue
            for code in basis:
                if code not in self.library.codes:
                    errors.append(f"Unknown component code: {code!r}")

        if errors:
            raise InputValidationError(errors)

    # -----------------------------------------------------------------
    # Raw sums
    # -----------------------------------------------------------------

    def raw_mol_sum(self) -> float:
        """Sum of the raw (un-normalized) mol% values.

        Returns 0.0 both when a mol% basis is present but sums to zero, and
        when no mol% basis was provided at all (`mol_pct` is `None`/empty) —
        this method cannot distinguish the two. Callers that need to tell
        "absent basis" apart from "genuinely zero-sum basis" (e.g. to raise
        an accurate diagnostic) should check `self.mol_pct` directly instead
        of relying on this method; see `normalized_mol`/`mw_from_mol`.
        """
        return sum((self.mol_pct or {}).values())

    def raw_wt_sum(self) -> float:
        """Sum of the raw (un-normalized) wt% values.

        Returns 0.0 both when a wt% basis is present but sums to zero, and
        when no wt% basis was provided at all (`wt_pct` is `None`/empty) —
        this method cannot distinguish the two. Callers that need to tell
        "absent basis" apart from "genuinely zero-sum basis" (e.g. to raise
        an accurate diagnostic) should check `self.wt_pct` directly instead
        of relying on this method; see `normalized_wt`/`mw_from_wt`.
        """
        return sum((self.wt_pct or {}).values())

    # -----------------------------------------------------------------
    # Basis-presence guards
    # -----------------------------------------------------------------

    def _require_mol_basis(self) -> Mapping[str, float]:
        """Return `mol_pct`, raising a precise diagnostic if absent."""
        if not self.mol_pct:
            raise InputValidationError(["no mol% basis provided"])
        return self.mol_pct

    def _require_wt_basis(self) -> Mapping[str, float]:
        """Return `wt_pct`, raising a precise diagnostic if absent."""
        if not self.wt_pct:
            raise InputValidationError(["no wt% basis provided"])
        return self.wt_pct

    # -----------------------------------------------------------------
    # Normalized bases (sum to 100)
    # -----------------------------------------------------------------

    def normalized_mol(self) -> dict[str, float]:
        """Mol% basis rescaled to sum to 100."""
        mol_pct = self._require_mol_basis()
        total = self.raw_mol_sum()
        if total == 0:
            raise InputValidationError(["composition sums to zero"])
        return {code: value * 100.0 / total for code, value in mol_pct.items()}

    def normalized_wt(self) -> dict[str, float]:
        """Wt% basis rescaled to sum to 100."""
        wt_pct = self._require_wt_basis()
        total = self.raw_wt_sum()
        if total == 0:
            raise InputValidationError(["composition sums to zero"])
        return {code: value * 100.0 / total for code, value in wt_pct.items()}

    # -----------------------------------------------------------------
    # Molecular weight
    # -----------------------------------------------------------------

    def mw_from_mol(self) -> float:
        """Mixture MW from mol fractions: Σzᵢ·MWᵢ / Σzᵢ."""
        mol_pct = self._require_mol_basis()
        total = self.raw_mol_sum()
        if total == 0:
            raise InputValidationError(["composition sums to zero"])
        return sum(z * self.library.get(code).mw for code, z in mol_pct.items()) / total

    def mw_from_wt(self) -> float:
        """Mixture MW from wt fractions (normalized): 100 / Σ(wᵢ/MWᵢ)."""
        denom = sum(w / self.library.get(code).mw for code, w in self.normalized_wt().items())
        if denom == 0:
            raise InputValidationError(["composition sums to zero"])
        return 100.0 / denom

    def mw_consistency_pct(self) -> float:
        """Percent difference between mw_from_mol() and mw_from_wt()."""
        mw_mol = self.mw_from_mol()
        mw_wt = self.mw_from_wt()
        return (mw_mol - mw_wt) / mw_wt * 100.0

    # -----------------------------------------------------------------
    # Derived bases
    # -----------------------------------------------------------------

    def wt_from_mol(self) -> dict[str, float]:
        """Wt% basis (sums to 100) derived from the normalized mol% basis."""
        mol = self.normalized_mol()
        masses = {code: z * self.library.get(code).mw for code, z in mol.items()}
        total_mass = sum(masses.values())
        if total_mass == 0:
            raise InputValidationError(["composition sums to zero"])
        return {code: mass * 100.0 / total_mass for code, mass in masses.items()}

    # -----------------------------------------------------------------
    # Physical properties
    # -----------------------------------------------------------------

    def liquid_density_ideal_g_cc(self) -> float:
        """Ideal-mixing liquid density: Σw / Σ(w/ρᵢ), on the normalized wt% basis."""
        wt = self.normalized_wt()
        total_w = sum(wt.values())
        denom = sum(w / self.library.get(code).liquid_density_g_cc for code, w in wt.items())
        if denom == 0:
            raise InputValidationError(["composition sums to zero"])
        return total_w / denom

    def gas_gravity(self) -> float:
        """Gas specific gravity relative to air: mw_from_mol() / AIR_MW."""
        return self.mw_from_mol() / AIR_MW
