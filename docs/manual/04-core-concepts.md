# Chapter 4: Core Concepts

This chapter documents the primitives every calculation module in `pvt/`
is built from: constants, units, the component library, composition
arithmetic, the sample/study provenance model, the QC engine, and the
engine's typed exceptions. Everything here lives under `pvt/core/` and
`pvt/qc/engine.py`.

## 4.1 The Dual Pressure Basis

`pvt/core/constants.py` is, in its own words, the "single source of truth
for all PVT calculations", and every module imports constants from here rather
than embedding a numeric literal. Its module header calls out one design
decision explicitly enough to quote in full, because getting it wrong
silently shifts results:

> Dual-basis design — this module deliberately carries TWO standard-condition
> pressures, and each constant is pinned to whichever one its source workbook
> uses:
>   - 14.73 psia — the volumetric standard (P_STD_PSIA). Used for gasometer /
>     GOR conversions and the ADRIC lab sheets (CC_PER_STB, CC_PER_SCF, etc.).
>   - 14.696 psia — the atmosphere & gas-constant basis (P_ATM_PSIA, 1 atm).
>     Used for psig→psia conversions, R values, and SCF_PER_LBMOL.
> Do not "simplify" by collapsing these to one value — mixing the two bases
> silently shifts results by ~0.2%.

Concretely:

$$P_{\text{STD}} = 14.73 \text{ psia} \qquad P_{\text{ATM}} = 14.696 \text{ psia} \quad (1\text{ atm})$$

`P_STD_PSIA` (14.73 psia) is the ADRIC lab's volumetric standard: it is the
basis for `CC_PER_SCF` (28,316.85), `CC_PER_STB` (158,987.29, "NIST:
158987.294928 cc; lab sheets canonize to 158987.29"), and
`SCF_STB_TO_CC_CC`. `P_ATM_PSIA` (14.696 psia, exactly one physical
atmosphere) is the basis `units.psig_to_psia`/`units.psia_to_psig` default
to, and it is what `SCF_PER_LBMOL` (379.482) is derived from. The module's
docstring for `SCF_PER_LBMOL` makes the risk of confusing the two concrete:
computing the molar volume as
$R \cdot T_{\text{STD,R}} / P_{\text{ATM}} = 10.7316 \times 519.67 / 14.696 \approx 379.484$
(rounded to the canonized 379.482) is correct; computing the same quantity
against `P_STD_PSIA` instead gives $\approx 378.61$ scf/lbmol: "a
different, also-valid number" for a different physical basis, not a
rounding error. `docs/excel-deviations.md` D-015 documents that the
pre-restructure app used the wrong pairing (`P_std=14.696` psia with
`CC_PER_STB=158987.1`), shifting recombination outputs by roughly 0.2%
against the canonical lab basis now in force.

The temperature standard is $T_{\text{STD}} = 60\,^\circ\text{F} = 519.67\,^\circ\text{R} = 288.7056\text{ K}$
(`T_STD_F`, `T_STD_R`, `T_STD_K`).

One correlation keeps its own, third, reference pressure entirely outside
this module: the Hoffman-Crump QC check (Section 4.6) uses 14.7 psia, "the
older, rounder reference pressure the original correlation was published
with", deliberately not `P_STD_PSIA` and not `P_ATM_PSIA`; it is kept
module-local in `pvt/qc/checks/hoffman_crump.py` rather than added to
`pvt.core.constants`, "because it belongs to this one correlation, not to
the engine's general unit system."

## 4.2 Units Module Conventions

`pvt/core/units.py` states its own scope in its header: "All conversions
are one-liners built strictly on `pvt.core.constants`. No numeric literals
except pure math (e.g., 5/9, 32, 141.5/131.5)." Every conversion function is
a single expression built from a named constant, never a re-derived or
hardcoded factor.

**Temperature.** Fahrenheit, Rankine, Celsius, and Kelvin are all
represented, with direct conversions where the module provides them:

$$^\circ R = \,^\circ F + 459.67 \qquad K = \,^\circ C + 273.15$$

`f_to_r`, `r_to_f`, `f_to_c`, `c_to_f`, `c_to_k`, `k_to_c`, and a direct
`f_to_k` (= `(temp_f + RANKINE_OFFSET) * 5 / 9`) are provided; there is no
direct `r_to_k`/`k_to_r` pair; a Rankine-Kelvin conversion currently has to
go through Fahrenheit or Celsius.

**Pressure.** `psig_to_psia`/`psia_to_psig` default their atmospheric
offset to `P_ATM_PSIA` (14.696 psia, Section 4.1) but accept an explicit
override; `bara_to_psia`/`psia_to_bara` use `PSIA_PER_BARA` (14.5038);
`mbar_to_psia` uses the lab's own mbar/psia pair,
`P_STD_PSIA / P_STD_MBAR` (14.73 / 1015.5981).

**Volume.** `scf_to_cc`/`cc_to_scf`, `stb_to_cc`/`cc_to_stb`, and the ratio
converters `scf_stb_to_cc_cc`/`cc_cc_to_scf_stb` all route through
`CC_PER_SCF`, `CC_PER_STB`, and `SCF_STB_TO_CC_CC` respectively, the
14.73 psia lab basis throughout, per Section 4.1.

**Density and API gravity.** This is the one place the module's docstring
calls out a deliberate, named house convention rather than a strict
physical conversion. `api_from_density_g_cc`:

```python
def api_from_density_g_cc(rho: float) -> float:
    """
    API gravity from density.

    House convention: treats g/cc at 60 °F as SG 60/60 (all ADRIC sheets do);
    `sg_from_density_g_cc` gives the strict conversion.
    """
    return (141.5 / rho) - 131.5
```

$$API = \frac{141.5}{\rho} - 131.5$$

Strictly, API gravity is defined from specific gravity (a dimensionless
ratio to water density), not from density in g/cc directly; the ADRIC
workbooks numerically substitute the g/cc value at 60 °F for that ratio
(since water is close to, but not exactly, 1.000 g/cc at 60 °F;
`WATER_DENSITY_60F_G_CC` is 0.9991). `density_g_cc_from_api` inverts the
same house formula
($\rho = 141.5 / (API + 131.5)$), and `sg_from_density_g_cc`
($\text{SG} = \rho / 0.9991$) is provided as the strict alternative when a
caller needs the distinction rather than the house shortcut.

## 4.3 The Katz-Firoozabadi Component Library

`pvt/core/components.py` defines a frozen `Component` dataclass (`code`,
`name`, `mw`, `liquid_density_g_cc`, `tb_r`, `pc_psia`, `tc_r`, plus a
derived `molar_volume_cc` property = `mw / liquid_density_g_cc`) and a
`ComponentLibrary` collection built from a fixed table of rows.

The canonical instance, `KATZ_FIROOZABADI`, holds exactly 52 components:
from `H2` and light gases (`H2S`, `CO2`, `N2`, `C1`...`nC4`) through the
aromatics/cyclics (`MCP`, `Benzene`, `CycloC6`, `MCH`, `Toluene`,
`EBenzene`, the xylenes, `TMB124`) to the single-carbon-number cuts `C7`
through `C35` and a lumped `C36+`. The module's comment block states its
provenance directly: "Data source:
`ADRIC_Flash_Separation_Calc_v6.1.xlsx`, `Component_Properties` sheet."

The SCN rows use "the workbook's rounded n-alkane MW variant (e.g. C7
100.204, C11 156.0) rather than Katz-Firoozabadi's generalized-fraction
MWs, the workbook is the source of record for this table per D-001." That
cross-reference is `docs/excel-deviations.md` D-001: two ADRIC workbooks
(`LiveOil v4.1` and `Flash v6.1`) carry slightly different
`Component_Properties` values for the same components (C7 100.205 vs
100.204; H2S 34.082 vs 34.0809; C36+ default 635 vs 636.4). The engine
canonizes on one table, the Flash v6.1 values, rather than carrying two
parallel libraries; per-study variation is handled the one way the lab
actually varies it, not by picking a different base table.

`ComponentLibrary.codes` returns component codes as an immutable tuple (a
copy, not the internal storage) specifically "so callers cannot mutate the
library's singleton state by mutating what they get back from this
property"; `KATZ_FIROOZABADI` is a shared module-level instance consumed
by every experiment, so this guard matters.

**The C36+ override.** `ComponentLibrary.with_c36_mw(mw)` is the library's
only mutation path, and it is not a mutation at all: it returns a *new*
`ComponentLibrary` with an isolated, `dataclasses.replace`d `C36+`
`Component`, while every other component dict entry is shared by reference
with the original. This is deliberately "the only editable property,
matching lab convention" (design spec Section 5): a study's plus-fraction
molecular weight varies sample to sample and is measured/reported per
sample, while the other 51 components' properties are fixed physical
constants. `pvt/io/excel_import/liveoil_v41.py` uses exactly this path,
reading a per-workbook C36+ MW cell and building
`KATZ_FIROOZABADI.with_c36_mw(c36_mw)` before constructing that sample's
composition streams.

## 4.4 CompositionStream

`pvt/core/composition.py` defines `CompositionStream`, described in its
module docstring as "the shared composition abstraction consumed by every
experiment module (flash separation, recombination, CCE/CVD reports,
...)." It is a frozen dataclass holding a `library: ComponentLibrary` and
one or both of `mol_pct` / `wt_pct` mappings (component code → percentage).

**Construction guards.** `__post_init__` requires at least one of
`mol_pct`/`wt_pct` to be present and non-empty, and requires every
component code that does appear to exist in `library.codes`; both failures
are collected into a single `InputValidationError` rather than raised on
the first problem found.

**Both bases may coexist**, but only one need be supplied at construction.
The docstring is explicit: "Exactly one of `mol_pct` / `wt_pct` may be
supplied and non-empty at construction time, but both may be present after
derivation (see `wt_from_mol`)." `wt_from_mol()` computes a wt% basis from
the normalized mol% basis (it does not mutate the frozen instance; callers
build a new stream or hold the derived dict alongside).

**Raw-sum guard semantics.** `raw_mol_sum()` and `raw_wt_sum()` both carry
an explicit caveat in their docstrings: each returns `0.0` both when its
basis is present but genuinely sums to zero, *and* when that basis was
never supplied at all; the method cannot tell the two apart. Callers that
need to distinguish "absent basis" from "a real zero-sum composition" (to
raise an accurate diagnostic) go through `_require_mol_basis()` /
`_require_wt_basis()` instead, which raise a precise
`InputValidationError` ("no mol% basis provided" / "no wt% basis
provided") when the basis mapping itself is missing or empty, rather than
falling through to a confusing "sums to zero" message.

**Normalization.** `normalized_mol()` / `normalized_wt()` rescale a basis
so it sums to exactly 100, raising `InputValidationError` ("composition
sums to zero") if the raw sum is zero.

**Molecular weight, by two independent routes.** Both are used together as
a cross-check (Section 4.6):

$$MW_{\text{mol}} = \frac{\sum_i z_i \cdot MW_i}{\sum_i z_i} \qquad MW_{\text{wt}} = \frac{100}{\sum_i (w_i / MW_i)}$$

(`mw_from_mol()` sums against the *raw*, not normalized, mol% and divides
by the raw sum, algebraically equivalent to normalizing first; `mw_from_wt()`
sums against the normalized wt% basis). `mw_consistency_pct()` reports the
two routes' relative deviation:

$$\Delta MW\% = \frac{MW_{\text{mol}} - MW_{\text{wt}}}{MW_{\text{wt}}} \times 100$$

**Physical properties derived from the normalized wt% basis:**

$$\rho_{\text{ideal}} = \frac{\sum_i w_i}{\sum_i (w_i / \rho_i)} \qquad \gamma_g = \frac{MW_{\text{mol}}}{MW_{\text{air}}}$$

`liquid_density_ideal_g_cc()` is ideal-mixing liquid density (no excess-
volume correction); `gas_gravity()` divides the mol-route mixture MW by
`AIR_MW` (28.964 g/mol).

A related module, `pvt/core/plus_fractions.py`, computes aggregate
properties (mol%, wt%, MW, density) for a plus-fraction cut (`C7+`, `C11+`,
`C20+`, `C36+`) of a `CompositionStream`. Cut boundaries are positional on
the library's fixed 52-slot order, not name-pattern matching: "a cut is
every component at or after its start code," which is what lets `C7+`
exclude the cyclics that sort before `C7` in the table (`MCP`, `Benzene`,
`CycloC6`) while including the ones that sort after it (`MCH`, `Toluene`),
matching the Flash workbook's `Plus_Properties_Report` convention.

## 4.5 Sample, Study, and CrossRef

`pvt/core/sample.py` defines three dataclasses. Its module docstring states
the intent directly: "`CrossRef` bridges upstream test results consumed
downstream with provenance, replacing manual retyping between workbooks.
Units are carried in source_field names."

`Sample` (a plain, mutable dataclass, not frozen) carries lab/well
identity: `sample_id`, `well`, `field_name`, `reservoir`,
`depth_ft_md: float | None`, `fluid_type`, `cylinder`, plus optional
`client` and `project`. This is the one dataclass from this module in
active use across the current codebase today: every Excel importer, the
CLI, `pvt/reporting/excel_export.py`, and the UI's shared components all
construct or consume a `Sample`.

`Study` bundles a `Sample` with reservoir conditions
(`reservoir_p_psig`, `reservoir_t_f`) and four optional `CrossRef` fields:
`psat`, `density_at_psat`, `rs_flash`, `bo_flash`. `CrossRef` itself is
`(value, source_test, source_field, note="")`: a number plus a record of
which upstream test and field it came from, and an optional free-text note.

As of Phase 2, `Study` and `CrossRef` exist as data-model primitives and
are covered by their own unit tests
(`tests/unit/test_sample.py`), but no experiment or importer currently
constructs or consumes one; the Flash v6.1 importer's own module docstring
notes this directly, describing reservoir P/T and saturation-pressure
cells on the workbook that are read visually by a technician but "have no
home until `Study`/`CrossRef` are wired in a later phase." Wiring
`Study`/`CrossRef` into real cross-test data flow (e.g. CCE's Psat feeding
DV/MSS without manual retyping, design spec Section 3 item 5) is future
work beyond the current Flash/Recombination slice.

## 4.6 The QC Engine

`pvt/qc/engine.py` is, per its own module docstring, the "shared vocabulary
for every check module under `pvt.qc.checks`": grade a numeric deviation
against a two-band threshold, carry the result in a typed `QCResult`, and
roll many results up to a worst-case severity for a study-level verdict.

**Severity** is a three-level `StrEnum`, ordered best to worst:
`PASS < REVIEW < FAIL`.

**Grading.** `grade(value, review_at, fail_at, *, absolute=True)` compares
the (optionally absolute-valued) input against the two band edges:

$$
\text{severity} =
\begin{cases}
\text{PASS} & |v| \le \text{review\_at} \\
\text{REVIEW} & \text{review\_at} < |v| \le \text{fail\_at} \\
\text{FAIL} & |v| > \text{fail\_at}
\end{cases}
$$

Band edges are inclusive downward: a value landing exactly on `fail_at`
grades `REVIEW`, not `FAIL`. `worst(results)` reduces any iterable of
`QCResult` to the single worst `Severity` present, defaulting to `PASS` on
an empty iterable.

**`QCResult`** is a frozen dataclass: `check_id`, `severity`,
`value: float | None`, `threshold` (a human-readable band description
string), `message`.

**`ThresholdRegistry`** holds one `(review_at, fail_at)` pair per
`check_id`, seeded from `DEFAULTS` and independently overridable per study
via `override(check_id, review_at, fail_at, note)`; every override is
appended to a `.audit` log carrying the caller's note, so a report can
explain why a given study's bands differ from the house defaults. The
class docstring is explicit that these defaults "come from the ADRIC house
conventions," with one named exception.

The current `DEFAULTS` table, reproduced from `pvt/qc/engine.py`:

| `check_id` | review\_at | fail\_at | Source | Consumed by (Phase 0-2) |
|---|---|---|---|---|
| `composition_sum` | 0.5 | 2.0 | ADRIC house convention (design spec Sections 5, 9: "±0.5 PASS / ±2 REVIEW") | `composition_normalization.py` |
| `mass_balance_pct` | 2.0 | 3.0 | ADRIC house convention (design spec Section 9: "mass balance 2/3%") | not yet consumed by an implemented check module |
| `molar_balance_pct` | 2.0 | 3.0 | ADRIC house convention (design spec Section 9: "molar balance 2/3%") | not yet consumed by an implemented check module |
| `z_deviation_pct` | 2.0 | 5.0 | ADRIC house convention (design spec Section 9: "Z deviation 2/5%") | not yet consumed by an implemented check module |
| `density_rsd_pct` | 0.5 | 1.0 | ADRIC house convention (design spec Section 9: "density %RSD 0.5/1") | not yet consumed by an implemented check module |
| `viscosity_vs_sim_pct` | 2.0 | 5.0 | ADRIC house convention (design spec Section 9: "viscosity vs sim 2/5%") | not yet consumed by an implemented check module |
| `mmp_mass_balance_pct` | 5.0 | 5.0 | ADRIC house convention (design spec Section 9: "MMP mass balance ±5%", a single band, represented here as equal review/fail edges) | not yet consumed by an implemented check module |
| `gor_actual_vs_target_pct` | 5.0 | 10.0 | Documented as a house threshold in its consuming module's own docstring; not individually itemized in design spec Section 9's list | `loading.py`'s `verify_actual_gor` |
| `mw_consistency_pct` | 5.0 | 10.0 | Documented as a house threshold in its consuming module's own docstring; not individually itemized in design spec Section 9's list | `mw_consistency.py` |
| `hoffman_r2` | 0.98 | 0.95 | **Not** an ADRIC house convention: the class docstring is explicit that this pair "is proposed by engineering judgment... pending Swej calibration," because the source PVT-check sheets show this crossplot visually with no numeric R² gate of their own | `hoffman_crump.py` |

All four `pvt/qc/checks/*.py` file names above (`composition_normalization.py`, `mw_consistency.py`, `hoffman_crump.py`) live under that one package; `loading.py` is the exception, living instead under `pvt/experiments/recombination/`.

Three implementation details worth calling out precisely:

- **`mmp_mass_balance_pct`'s `(5.0, 5.0)` pair is not a typo.** Because
  `review_at == fail_at`, `grade()` can never actually return `REVIEW` for
  this check: a value at or below 5.0% is `PASS`, anything above is
  immediately `FAIL`. This mirrors the spec's own single-number framing
  ("MMP mass balance ±5%") rather than the two-band framing every other
  default uses.
- **`hoffman_r2` is graded as an R²-*floor*, not a deviation band.** Its
  module (`pvt/qc/checks/hoffman_crump.py`) documents the semantics
  directly: `(0.98, 0.95)` reads "R² ≥ 0.98 is PASS, R² ≥ 0.95 is REVIEW,
  below that is FAIL", the opposite direction from every other threshold
  pair, where a *smaller* number is better. Because `grade()` itself only
  understands "smaller deviation is better," the check converts before
  calling it: it grades $1 - R^2$ against $(1 - 0.98,\ 1 - 0.95)$.
- **Six of the ten seeded defaults have no consuming check module yet.**
  `mass_balance_pct`, `molar_balance_pct`, `z_deviation_pct`,
  `density_rsd_pct`, `viscosity_vs_sim_pct`, and `mmp_mass_balance_pct` are
  all present in `ThresholdRegistry.DEFAULTS` today but are not read by any
  check module in `pvt/qc/checks/` as of Phase 2; they are reserved for
  check modules the design spec's target `qc/checks/` layout names
  (`material_balance.py`, `molar_balance.py`, a Z-factor/DAK-vs-Hall-
  Yarborough deviation check, etc.) that belong to later phases.

## 4.7 Typed Exceptions

`pvt/core/exceptions.py` defines the engine's exception hierarchy, all
deriving from one base:

- **`PvtError`**: base class for every engine error.
- **`InputValidationError(errors: list[str])`**: "Raised when calc inputs
  fail validation. Carries the message list." Stores the original list on
  `.errors` and joins it with `"; "` as the exception's string message, so
  a caller can either report every failure individually (iterating
  `.errors`, as `cli.py` does for both subcommands) or just print the
  exception.
- **`ConvergenceError(message, *, iterations: int, residual: float)`**:
  raised when an iterative solver (Newton iteration in the DAK Z-factor
  correlation, Hall-Yarborough's reduced-density solve) fails to converge.
  Both diagnostic values are stored as attributes and folded into the
  formatted message: `f"{message} (iterations={iterations},
  residual={residual:.3e})"`.

Every validation failure in the engine (a malformed composition, a
degenerate least-squares fit in the Hoffman-Crump check, a blank or
negative cell caught by an Excel importer) surfaces as one of these two
typed exceptions rather than a bare `ValueError`, `KeyError`, or
`ZeroDivisionError`, which is what lets `cli.py` and the Streamlit pages
catch `InputValidationError` specifically and render its `.errors` list as
user-facing messages instead of a traceback.
