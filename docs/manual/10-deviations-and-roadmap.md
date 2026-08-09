# 10. Deviations Ledger and Roadmap

## 10.1 The deviations-ledger discipline

The engine's authority over calculation logic is unconditional: where a
source ADRIC workbook is provably wrong, or takes a stance the engine does
not, the engine implements what the underlying petroleum-engineering
reference says is correct, and the difference is recorded — not silently
ported, not silently corrected. The record lives in one file,
[`docs/excel-deviations.md`](../excel-deviations.md), and every entry is
added before the deviating behavior's test lands. Any golden-parity test
failure that is *not* backed by a ledger entry is treated as a bug in the
port, not a deliberate deviation; this is the mechanism that keeps
"the engine fixed it" from becoming an unaudited claim.

### Lifecycle

Every entry starts life as `proposed`. It stays `proposed` until it has
been walked through point-by-point with the PVT domain owner (Swej), at
which point it resolves to one of:

- **`approved`** — the engine's behavior is confirmed correct and the
  workbook's differing behavior is confirmed a defect.
- **`parity-kept`** — the workbook's behavior is confirmed the intended lab
  convention, and the engine is expected to match it (the ledger entry
  documents the convention rather than a bug).

As of this writing every entry in the ledger is still `proposed`; none has
been walked through the phase-wrap review yet. D-018 additionally carries
`NEEDS SWEJ RULING` — it is not just unreviewed, it is a live open question
(see §10.3).

### What a ledger row contains

Each row in the `docs/excel-deviations.md` table has five fields:

| Field | Contents |
|-------|----------|
| **ID** | `D-NNN`, assigned in the order the deviation was found |
| **Workbook / cell** | The source file and the specific sheet/cell(s) or formula the behavior was read from — the proof that the claim is verifiable, not asserted |
| **Excel behavior** | What the workbook actually computes, in enough detail to reproduce it |
| **Engine behavior** | What `pvt/` computes instead, with a citation to the published correlation/reference where one exists, and the numeric size of the divergence where it has been measured |
| **Status** | `proposed`, `approved`, or `parity-kept` |

## 10.2 Current ledger: D-001 through D-018

Fifteen entries exist today. The IDs are not contiguous: D-012, D-013, and
D-014 do not appear in `docs/excel-deviations.md` — there is a gap in the
numbering, not fifteen consecutive rows. Every row below is still
`proposed`.

| ID | Summary |
|----|---------|
| D-001 | Two component-library MW variants circulated (LiveOil v4.1 vs Flash v6.1); the engine canonizes one table (Flash v6.1 values) with C36+ MW as the only per-study override. |
| D-002 | Workbook sheets never call their own validators, risking silent divide-by-zero; engine `calc` entry points raise `InputValidationError` instead (Phase 2 pattern, recombination retrofit tracked separately). |
| D-003 | Piper-McCain-Corredor CO2 coefficient is transposed in the reference workbook (`alpha2 = -0.09034`); engine uses the published `-0.90348` (SPE 26668, 1993), shifting Tpc ~2.5% at 20% CO2. |
| D-004 | Reference workbook computes C7+ MW as an unweighted sum/average; engine mole-fraction-weights it, `Sigma(y_i*MW_i) / Sigma(y_i)`, per SPE 26668. |
| D-005 | Reference workbook's Dranchuk-Abou-Kassem Newton iteration uses an incorrect derivative of the residual; engine uses the mathematically correct derivative (converged Z roots are identical; only the iteration path differs). |
| D-006 | CVD workbook's `Additional_QC` Hall-Yarborough variant uses Tr instead of the reciprocal `t`, omits `t` from the A-term, and reports the reduced density itself as "Z"; engine implements canonical Hall & Yarborough (1973), matching the separate, correct Gas_Gradient VBA kernel. |
| D-007 | Standing bubble-point sheet leaves the correlation exponent `a` as a raw user-entered cell rather than computing it; engine computes `a` from T/API internally, with a `bubble_point_with_exponent()` parity hook that reproduces the sheet's raw-`a` form exactly. |
| D-008 | Vasquez-Beggs sheet computes the exponent term by multiplying by `(T+460)` instead of dividing, overflowing to `#NUM!`; engine divides, per the published Pb-form (Vasquez & Beggs 1980), cross-checked against the original Rs-form inversion (~0.5% agreement). |
| D-009 | Glaso sheet multiplies Pb* by a stray 14.5 and never applies the final `10^log10(Pb)` step, and rounds the correlation constants; engine applies the published constants (1.7669/1.7447) and the correct final exponentiation, anchored to the workbook's own cached Pb* cell to prove the stray factor is understood, not guessed. |
| D-010 | Viscosity workbook hardcodes the lbm/ft3-to-g/cc conversion as the rounded `0.0014935`; engine derives the coefficient exactly from canonical constants (`0.0014926...`), ~0.06% lower. |
| D-011 | Reference VBA hardcodes the gas constant as `10.73`; engine uses the canonical `R_PSIA_FT3_LBMOL_R = 10.7316`, per the task brief; all other Jossi-Stiel-Thodos coefficients are transcribed from the VBA exactly. |
| D-015 | The old pre-Phase-0 app used `P_std = 14.696` psia and `CC_PER_STB = 158987.1`; engine uses the canonical lab basis `P_STD_PSIA = 14.73` / `CC_PER_STB = 158987.29` per the design spec, shifting recombination outputs ~0.2% versus the old app. |
| D-016 | Gas_Gradient VBA's `EstimatePseudoCriticals` takes density in g/cc and converts internally; engine's `erbar.c7_plus_criticals` takes SG directly (the VBA's post-conversion value) — callers with raw density must convert first. |
| D-017 | Flash v6.1 computes a `P_base` (barometric + back-pressure) that is never used downstream; V_gas_std actually uses the separately measured absolute pressure. Engine takes the measured absolute pressure input only and does not compute the unused quantity. |
| D-018 | LiveOil v4.1's GOR-basis toggle divides the **Stock Tank** GOR by shrinkage when convention divides the **Separator** GOR; masked in the workbook today because its shrinkage factor is 1.0. Engine implements the conventional direction. **Open — needs a ruling; see §10.3.** |

## 10.3 Open rulings

Four items remain genuinely undecided — not unreviewed line items, but
questions where the workbook, the engine, and lab convention do not all
point the same way. These are carried over verbatim from
[`docs/workbook-defect-review.md`](../workbook-defect-review.md) §3:

1. **D-018 — GOR-basis direction.** LiveOil v4.1's `Recombination!B8`
   divides the Stock Tank GOR by shrinkage; the engine currently implements
   the conventional direction (Separator GOR / SF -> STO basis). The
   workbook's own goldens do not distinguish the two because its shrinkage
   factor is 1.0, so this has not yet been forced to a decision by test
   data. Needs a ruling before D-018 can move past `proposed`.
2. **`hoffman_r2` bands.** The Hoffman-Crump QC check currently grades
   R^2 >= 0.98 as PASS and R^2 >= 0.95 as REVIEW. These are engineering-judgment
   defaults, not yet confirmed against house practice.
3. **Z = 1 conventions.** Both the Flash v6.1 workbook (`Volumetrics_Master!B27`)
   and the MSS workbook (`MSS_Input!O24:O27`, gas Z collected but never
   used) assume Z = 1 in standard-volume gas conversions — a ~0.2-0.3%
   systematic bias that is standard lab-sheet practice but currently
   undocumented as a deliberate convention. Whether to keep it as-is or
   wire in an actual Z correlation (sheet-side or platform-side) is open.
4. **DV pressure basis and MMP recovery basis.** The DV workbook
   (`3_ADRIC_DV_Calc_v6.2.xlsx`) enters Psat in psig with no `+14.7`
   conversion anywhere downstream, while the engine uses absolute pressure
   consistently — the house convention for stage pressures needs to be
   fixed explicitly. Separately, the MMP recovery-basis defect (dead
   volume double-counted or omitted between the QC tool and the raw-logger
   file) needs a defined house basis; the engine currently exposes this as
   an explicit flag rather than picking silently.

Two related housekeeping items from the same review are worth noting here
without being open engineering questions: flipping the fifteen ledger
entries from `proposed` to `approved`/`parity-kept` is itself pending the
walkthrough described in §10.1, and the stashed `stash@{0}` (a July 15
cosmetic ASCII-diagram tweak to the pre-Phase-2 `ui/recombination.py`) is
still sitting untouched, per the design spec's git-workflow section,
until the UI rebuild absorbs or formally obsoletes it.

## 10.4 Phase roadmap

The phased scope below is defined in
[`docs/superpowers/specs/2026-08-09-pvt-lab-platform-design.md`](../superpowers/specs/2026-08-09-pvt-lab-platform-design.md)
§2. Phases 0-2 are built (see the earlier chapters of this manual);
Phases 3-5 are planned. Each phase's paragraph below draws on what the
full formula-level dissection of the ADRIC workbook set —
`docs/workbook-defect-review.md` — already tells us about the modules that
phase will need to implement.

### Phase 3 — CCE, DV, MSS, Density HPHT, Viscosity HPHT

Phase 3 covers Constant Composition Expansion (with Y-function and
compressibility QC), Differential Vaporization (with the Amyx/Carlson
flash-basis adjustment), Multi-Stage Separator tests, and the two HPHT
physical-property tests (density and viscosity). The dissected workbooks
already surface most of what this phase has to get right on day one. The
CCE workbook (`2_CCE_Calculation_Sheet_v5...xlsx`) has a mean-compressibility
sign flip that propagates a negative value into its own report tab, "PVTsim
comparison" columns that are vacuous self-references rather than real
comparison data, and a spurious compressibility spike at the bubble-point
row from a central-difference stencil that straddles the two-phase
transition; its Y-function is QC-only by design across every version from
v1 to v5, never used to auto-pick Psat, which the platform should keep as
deliberate rather than "fix." Two QC checks that existed in the v1/v2
CCE sheets — compressibility monotonicity and rho*V constancy — were
dropped in v5's layout compaction and need to be resurrected in the
platform's QC set. The DV workbook has a bubble-point Rs formula that
wrongly folds in stage-2's delta-Rs, an empty-link Fluid Type field, Psat
entered in psig with no conversion to the absolute-pressure basis the rest
of the sheet needs, dead override cells for STO density/MW, only eight gas
composition slots (data beyond that silently drops from the mass balance),
and a back-pressure term that is never added to the measured gasometer
pressure. The MSS workbook repeats the Fluid Type link bug, collects a gas
Z column it never uses, has a K-value trend block that divides by an
always-empty reservoir-composition column so its charts are permanently
blank, and has no cross-test check comparing its own measured cumulative
GOR against the flash Rs_fb value it should be validated against — exactly
the kind of check the Phase 5 QC Center is meant to formalize. The two HPHT
sheets share a machine-written `_xludf.STDEV.S` artifact that silently
evaluates to blank, meaning Std Dev, %RSD, and the QC pass/fail verdict
have never actually computed in either sheet; the density sheet's working
pressure and temperature inputs are wired to nothing (water density enters
only via two manually typed values, a candidate for computing rho_w(P,T)
from IAPWS instead) and its average includes out-of-range runs; the
viscosity sheet's table lookups require an exact pressure match and a
hardcoded row index for the stock-tank row, both of which the engine
should interpolate/derive rather than replicate.

### Phase 4 — CVD, MMP

Phase 4 covers Constant Volume Depletion (Whitson-style material balance)
and MMP slim-tube analysis, including a real two-line-intersection solver
Excel never had. The CVD workbook
(`CVD_Calc_WaterPump_v3_WhitsonStyle_AdditionalQC.xlsx`, which ships empty)
has two defects serious enough to flag as critical before any lab use of
the sheet itself: cells labeled "R" and "scf_per_lbmol" are missing a
sheet qualifier and actually resolve to that sheet's own stage-pressure
cells, poisoning every downstream mole-count calculation, and a stage
table referenced at the wrong row offset drops four stages from every
chart and breaks the report's dewpoint/temperature figures. Its
`Additional_QC` block has the same broken Hall-Yarborough variant already
handled by D-006, plus a Hoffmann K-value estimate that overflows to
`#NUM!` from an unguarded `10^x`, and several physical constants stored as
text rather than numbers. Because the CVD workbook ships empty, Phase 4's
golden fixtures for it will necessarily be synthetic — a published dataset
(e.g. Whitson & Brulé) frozen into `tests/fixtures/`, not a lab-cached
value — until real lab data is available. The MMP tooling's most
consequential finding is structural rather than a formula bug: MMP itself
is never computed anywhere in the existing tools — the engineer eyeballs
the intersection of two plotted lines and types in the answer — so Phase
4's slim-tube module needs an actual solver, not a port. Beyond that, the
recovery-percent calculation double-counts or omits dead volume depending
on which of two inconsistent formulas is used (the platform should expose
this as an explicit, named basis rather than silently picking one), empty
runs produce a garbage "100% error / REVIEW" result instead of being
excluded, the gas and oil series in the raw-logger template use
forward and backward differences respectively (a one-sample GOR lead the
engine must not reproduce), and the reporting lookup uses a stair-step
`VLOOKUP(...,TRUE)` where real interpolation is needed.

### Phase 5 — Cross-test QC Center, consolidated reporting

Phase 5 implements the full PVT-check QC catalog as a first-class
cross-test QC Center, plus consolidated study-level reporting. The case
for this phase is made by nearly every workbook reviewed: CCE's dropped
monotonicity and rho*V-constancy checks, MSS's missing GOR cross-check
against the flash-derived Rs_fb, and the DV/MSS Fluid Type link bugs are
all instances of the same underlying gap — checks that exist in principle
(or existed in an earlier sheet version) but are not wired to run
automatically today, and nothing in the current tooling compares a result
computed in one test against the same physical quantity computed in
another. The reference-tool review (`docs/workbook-defect-review.md` §2)
adds the specific check catalog this phase should implement: Hoffmann
(log10(K*P) vs F linearity), Buckley (ln K vs Tc^2 linearity), Y-function
regression fit and per-point error, K-value trend consistency, material-
and molar-balance closure, GOR back-calculation from a material-balance
diagram slope, and a compressibility-sign screen (Co/Cg >= 0). The design
spec's `Study`/`CrossRef` data model (already in place since Phase 0) is
what makes this possible without manual retyping: results computed
upstream (CCE's Psat, for instance) are consumed downstream with
provenance, so the QC Center can flag staleness the moment an upstream
value changes rather than relying on an engineer to notice a stale
hand-typed cell, which is exactly the failure mode several of the defects
above describe.
