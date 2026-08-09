# Chapter 5: Correlations Reference

This chapter documents every empirical correlation implemented under
`pvt/correlations/`: pseudocritical properties, gas compressibility factor
(Z), bubble-point pressure, and gas viscosity. Each section follows the same
structure: Purpose, Equation(s), Inputs & units, Validity & guards, Source,
Function signature, and Anchoring (how the implementation is pinned against
a published value, a source spreadsheet cell, or a hand/VBA trace).

Every equation below was transcribed directly from the corresponding module
in `pvt/correlations/` and checked term-by-term against the source code
(not retyped from memory of the textbook form), so engineers can diff it
against their own references with confidence. Where the engine deliberately
diverges from a source workbook or VBA macro, the deviation is called out
and cross-referenced to its ledger entry in `docs/excel-deviations.md`
(the "D-0xx" identifiers).

---

## 5.1 Pseudocritical Properties (`pvt/correlations/pseudocritical/`)

### 5.1.1 Sutton (1985)

**Purpose.** Estimate sweet-gas pseudocritical temperature and pressure
from gas specific gravity alone (no composition required).

**Equation(s).**

$$
p_{pc} = 756.8 - 131.0\,\gamma_g - 3.6\,\gamma_g^2
$$

$$
T_{pc} = 169.2 + 349.5\,\gamma_g - 74.0\,\gamma_g^2
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $\gamma_g$ | Gas specific gravity (air = 1) | dimensionless |

Returns $(T_{pc}, p_{pc})$ in (deg R, psia).

**Validity & guards.** Raises `InputValidationError` unless
$0.55 \le \gamma_g \le 2.0$. This is a sweet-gas correlation (no H2S/CO2
term); the module docstring directs callers to apply
`wichert_aziz.correct` to its output for sour gas.

**Source.** Sutton, R.P., SPE 14265 (1985). Coefficients as used in the
ADRIC CVD workbook (`Additional_QC!E9/F9`) and DV v5 `Additional_QC`.

**Function signature.**

```python
def pseudo_criticals(gas_gravity: float) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia])."""
```

**Anchoring.** `tests/unit/correlations/test_sutton.py::test_known_value_gamma_07`
recomputes both formulas independently at $\gamma_g = 0.7$ and asserts
exact agreement (`rel=1e-12`); this is a formula self-check, not an
external published or workbook value. `test_physical_trend` checks the
expected monotonic direction (heavier gas raises $T_{pc}$, lowers $p_{pc}$),
and `test_out_of_range_rejected` parametrizes over $\gamma_g \in
\{0.0, 0.4, 2.5, -1.0\}$ to confirm the range guard.

---

### 5.1.2 Stewart-Burkhardt-Voo (1959)

**Purpose.** Compute mixture pseudocriticals from a full mole composition
using the SBV J/K mixing rules.

**Equation(s).** With $y_i$ the normalized mole fraction of component $i$:

$$
J = \frac{1}{3}\sum_i y_i \frac{T_{c,i}}{p_{c,i}} + \frac{2}{3}\left(\sum_i y_i \sqrt{\frac{T_{c,i}}{p_{c,i}}}\right)^{2}
$$

$$
K = \sum_i y_i \frac{T_{c,i}}{\sqrt{p_{c,i}}}
$$

$$
T_{pc} = \frac{K^2}{J}, \qquad p_{pc} = \frac{T_{pc}}{J}
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| `stream` | `CompositionStream` (mol% composition + component library) | mol% |
| $T_{c,i}, p_{c,i}$ | Component critical temperature / pressure (from `stream.library`) | deg R, psia |

Returns $(T_{pc}, p_{pc})$ in (deg R, psia).

**Validity & guards.** No explicit range check in `sbv.py` itself; the
composition is normalized via `stream.normalized_mol()`, and unknown
component codes are rejected at `CompositionStream` construction time
(`InputValidationError`), not inside this module. This is a sweet-gas
correlation; apply `wichert_aziz.correct` to the output for sour gas.

**Source.** Stewart-Burkhardt-Voo (1959) pseudo-critical mixing rules, per
the module docstring.

**Function signature.**

```python
def pseudo_criticals(stream: CompositionStream) -> tuple[float, float]:
    """Return (Tpc [R], Ppc [psia]) from mole composition via SBV J/K."""
```

**Anchoring.**
`tests/unit/correlations/test_sbv.py::test_golden_equimolar_c1c2c3` is a
workbook golden: `"Z factor calculation.xls"` cells `I5`/`I6` for an
equimolar C1/C2/C3 mix, checked at `rel=2e-3` (the tolerance absorbs a
small Katz-Firoozabadi-vs-workbook Tc/Pc table difference, D-001, rather
than masking formula regressions).
`test_single_component_recovers_own_criticals` is an exact identity check
(`rel=1e-12`): for a pure C1 stream, $J=K=1$ and $(T_{pc}, p_{pc})$ must
recover the component's own $(T_c, p_c)$ from the library exactly.

---

### 5.1.3 Piper, McCain & Corredor (1993), SPE 26668

**Purpose.** Estimate mixture pseudocriticals from either (a) gas gravity
plus sour-species mole fractions, or (b) a full mole composition, using
correlations that are sour-aware from the start (unlike Sutton/SBV).

Both forms solve the same $J/K$ shape: $T_{pc} = K^2/J$, $p_{pc} = T_{pc}/J$.

**Equation(s), gravity form** (`from_gravity`).

$$
J = \alpha_0 + \alpha_1\, y_{H_2S}\frac{T_{c,H_2S}}{p_{c,H_2S}} + \alpha_2\, y_{CO_2}\frac{T_{c,CO_2}}{p_{c,CO_2}} + \alpha_3\, y_{N_2}\frac{T_{c,N_2}}{p_{c,N_2}} + \alpha_4\,\gamma_g + \alpha_5\,\gamma_g^2
$$

$$
K = \beta_0 + \beta_1\, y_{H_2S}\frac{T_{c,H_2S}}{\sqrt{p_{c,H_2S}}} + \beta_2\, y_{CO_2}\frac{T_{c,CO_2}}{\sqrt{p_{c,CO_2}}} + \beta_3\, y_{N_2}\frac{T_{c,N_2}}{\sqrt{p_{c,N_2}}} + \beta_4\,\gamma_g + \beta_5\,\gamma_g^2
$$

Gravity-form coefficient table ($\alpha_0 \ldots \alpha_5$ / $\beta_0
\ldots \beta_5$):

| Coefficient | Value | Coefficient | Value |
|---|---|---|---|
| $\alpha_0$ | 0.11582 | $\beta_0$ | 3.8216 |
| $\alpha_1$ | -0.4582 | $\beta_1$ | -0.06534 |
| $\alpha_2$ | -0.90348 | $\beta_2$ | -0.42113 |
| $\alpha_3$ | -0.66026 | $\beta_3$ | -0.91249 |
| $\alpha_4$ | 0.70729 | $\beta_4$ | 17.438 |
| $\alpha_5$ | -0.099397 | $\beta_5$ | -3.2191 |

The H2S/CO2/N2 critical properties used in these terms are pinned to the
Katz-Firoozabadi (KF) library rows (`H2S`, `CO2`, `N2`), not a separate
table copied from the paper, so that `from_gravity` and `from_composition`
stay numerically consistent when fed a KF-library stream.

**Equation(s), compositional form** (`from_composition`). Let $S_J =
\sum_{i \in C1..C6} y_i\, T_{c,i}/p_{c,i}$, $S_K = \sum_{i \in C1..C6} y_i\,
T_{c,i}/\sqrt{p_{c,i}}$, and $F = y_{C7+}\cdot MW_{C7+}$ (the C7+ bucket's
mole fraction times its molecular weight):

$$
J = \alpha_0 + \alpha_1\, y_{H_2S}\frac{T_{c,H_2S}}{p_{c,H_2S}} + \alpha_2\, y_{CO_2}\frac{T_{c,CO_2}}{p_{c,CO_2}} + \alpha_3\, y_{N_2}\frac{T_{c,N_2}}{p_{c,N_2}} + \alpha_4 S_J + \alpha_5 S_J^2 + \alpha_6 F + \alpha_7 F^2
$$

$$
K = \beta_0 + \beta_1\, y_{H_2S}\frac{T_{c,H_2S}}{\sqrt{p_{c,H_2S}}} + \beta_2\, y_{CO_2}\frac{T_{c,CO_2}}{\sqrt{p_{c,CO_2}}} + \beta_3\, y_{N_2}\frac{T_{c,N_2}}{\sqrt{p_{c,N_2}}} + \beta_4 S_K + \beta_5 S_K^2 + \beta_6 F + \beta_7 F^2
$$

where a sour term (e.g. $y_{H_2S}\,T_{c,H_2S}/p_{c,H_2S}$) evaluates to
$0$ if that species is absent from the composition, and

$$
MW_{C7+} = \frac{\sum_{i\in C7+} y_i\, MW_i}{\sum_{i\in C7+} y_i}
$$

unless the caller overrides it via the `c7p_mw` argument. The C7+ bucket
is every component that is neither a sour species (H2S/CO2/N2) nor in the
C1-C6 list, including naphthenes/aromatics (e.g. MCP, Benzene) by design.

Compositional-form coefficient table ($\alpha_0 \ldots \alpha_7$ /
$\beta_0 \ldots \beta_7$):

| Coefficient | Value | Coefficient | Value |
|---|---|---|---|
| $\alpha_0$ | 0.052073 | $\beta_0$ | -0.39741 |
| $\alpha_1$ | 1.0160 | $\beta_1$ | 1.0503 |
| $\alpha_2$ | 0.86961 | $\beta_2$ | 0.96592 |
| $\alpha_3$ | 0.72646 | $\beta_3$ | 0.78569 |
| $\alpha_4$ | 0.85101 | $\beta_4$ | 0.98211 |
| $\alpha_5$ | 0.0 | $\beta_5$ | 0.0 |
| $\alpha_6$ | 0.020818 | $\beta_6$ | 0.45536 |
| $\alpha_7$ | -0.0001506 | $\beta_7$ | -0.0037684 |

Index 5 is published as $0.0$ (no squared-HC-sum term in this form);
it is kept only for positional alignment with the gravity form's
$\alpha_4/\alpha_5$ ($\gamma_g, \gamma_g^2$) slots.

**Inputs & units.**

Gravity form: $\gamma_g$ (dimensionless), $y_{H_2S}, y_{CO_2}, y_{N_2}$ as
mole **fractions** in $[0,1]$ (not mole percent). Compositional form:
`stream` (`CompositionStream`, mol% basis) and optional `c7p_mw` override
(g/mol). Both return $(T_{pc}, p_{pc})$ in (deg R, psia).

**Validity & guards.** `from_gravity` raises `InputValidationError`
(collecting all violations) if $\gamma_g \le 0$, any of
$y_{H_2S}, y_{CO_2}, y_{N_2} \notin [0,1]$, or their sum exceeds 1 -
explicitly guarding the mole-percent trap (e.g. passing `y_co2=20` meaning
20%). `from_composition` has no dedicated validation function; it inherits
`CompositionStream`'s construction-time checks.

**Sour-route warning (do not chain into Wichert-Aziz).** Both entry points
are already impurity-adjusted through their own $\alpha_2/\alpha_1/\alpha_3$
(J) and $\beta_2/\beta_1/\beta_3$ (K) sour terms. Passing their output
through `wichert_aziz.correct` double-applies the sour correction; at 5%
CO2/3% H2S this shifts $T_{pc}$ by roughly 3.5% relative to the correct
single-application result.

**Source.** Piper, L.D., McCain, W.D., and Corredor, J.H. (1993), SPE
26668. Coefficients above are the *published* SPE 26668 values, not the
source workbook's.

**Function signature.**

```python
def from_gravity(
    gas_gravity: float, y_h2s: float = 0.0, y_co2: float = 0.0, y_n2: float = 0.0
) -> tuple[float, float]: ...

def from_composition(
    stream: CompositionStream, c7p_mw: float | None = None
) -> tuple[float, float]: ...
```

**Anchoring.**
`test_golden_gravity_form_sweet` is a workbook golden ("Z factor
calculation.xls" unknown-composition sheet `F4`/`F5`, $\gamma_g=0.737$, no
impurities), `rel=1e-9`.
`test_golden_compositional_form` is a workbook golden against the sour
known-composition sheet `I5`/`I6`, `rel=2e-3` (library Tc/Pc differ from
the workbook's in the 3rd-4th significant figure).
`test_deviation_d003_co2_coefficient` is an exact hand-computed pin
(independently derived from the published J/K formula, the published
$\alpha_2=-0.90348$, and the KF library's CO2 $T_c/p_c = 547.6\text{ R} /
1071.0\text{ psia}$), `rel=1e-9`; it exists specifically to catch the D-003
digit-transposition regression (workbook's $\alpha_2 = -0.09034$).
`test_compositional_form_h2s_present` is a self-derived formula-spec pin
exercising the H2S branch, `rel=1e-9`.
`test_c7_plus_bucket_includes_naphthenes_mole_weighted_mw` verifies D-004
(mole-fraction-weighted C7+ MW, including non-C1-C6/non-sour species like
MCP) by cross-checking the auto-computed result against an explicit
`c7p_mw` override, and confirms the workbook's unweighted-average bug
would give a materially different (wrong) answer.

---

### 5.1.4 Wichert-Aziz (1972) Sour Gas Correction

**Purpose.** Correct pseudocritical temperature and pressure for the
presence of CO2 and H2S, given a sweet-gas $(T_{pc}, p_{pc})$ pair (e.g.
from Sutton or SBV).

**Equation(s).**

$$
A = y_{CO_2} + y_{H_2S}, \qquad B = y_{H_2S}
$$

$$
\varepsilon = 120\left(A^{0.9} - A^{1.6}\right) + 15\left(B^{0.5} - B^4\right) \quad [^\circ R]
$$

$$
T_{pc}' = T_{pc} - \varepsilon
$$

$$
p_{pc}' = p_{pc}\,\frac{T_{pc}'}{T_{pc} + B(1-B)\varepsilon}
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $T_{pc}$, $p_{pc}$ | Uncorrected pseudocriticals | deg R, psia |
| $y_{CO_2}$, $y_{H_2S}$ | Mole fractions | dimensionless, $[0,1]$ |

Returns $(T_{pc}', p_{pc}')$ in (deg R, psia).

**Validity & guards.** Raises `InputValidationError` (collecting all
violations) if $y_{CO_2} \notin [0,1]$, $y_{H_2S} \notin [0,1]$, or
$y_{CO_2}+y_{H_2S} > 1$; the guard messages explicitly call out that these
are mole fractions, not mole percent.

**Source.** Wichert, G.C., and Aziz, K. (1972). "Calculate Z's for Sour
Gases." *Hydrocarbon Processing*, 51(5), 119-122. As implemented in the
Amoco GasProp VBA (`CalculateCriticals`).

**Function signature.**

```python
def correct(tpc_r: float, ppc_psia: float, y_co2: float, y_h2s: float) -> tuple[float, float]:
```

**Anchoring.** `test_no_impurities_is_identity` confirms $A=B=0$ returns
the input unchanged. `test_hand_computed_case` independently recomputes
$\varepsilon$ from the closed-form expression at $A=0.15$, $B=0.05$ and
checks both $T_{pc}'$ and $p_{pc}'$ against it at `rel=1e-12` (a formula
self-check, not an external golden). `test_correction_lowers_both`
confirms the expected physical direction.

---

### 5.1.5 Erbar C7+ Pseudocriticals (Chao-Seader lineage; Hall 1971 Vc)

**Purpose.** Estimate $(T_c, p_c, V_c)$ for a C7+ pseudo-component from its
molecular weight and specific gravity, for use as an input to mixture
pseudocritical mixing rules (e.g. `critical_volumes.vc_mix`).

**Equation(s).** `c7_plus_criticals` is a line-for-line transcription of
the private VBA subroutine `EstimatePseudoCriticals`
(`docs/reference/gasprop_functions.bas`). Inputs are first floored:
$MW < 99 \to 110$, $sg < 0.7 \to 0.74$ (each emits a `UserWarning`
containing "clamped"). With $M = MW$ (post-clamp):

Boiling point (deg F), a quartic in $M$ plus an SG-slope quartic in $M$:

$$
bp_{base}(M) = -264.65726 + M\Big(6.2374923 + M\big(-0.021451518 + M(4.3992405\times10^{-5} - 3.43845\times10^{-8}M)\big)\Big)
$$

$$
s_x(M) = 364.9632 + M\Big(-4.759161 + M\big(0.04974927 + M(-1.5157213\times10^{-4} + 1.431011\times10^{-7}M)\big)\Big)
$$

$$
bp = bp_{base}(M) + s_x(M)\,(sg - 0.6)
$$

If $sg > 0.86$, with $c_1 = sg - 0.86$:

$$
sz = \Big[\big(16.823557 + M(-0.071486 + 0.000998994\,M)\big) + \big(65.42352 + M(0.9092107 - 0.00801609\,M)\big)c_1\Big]\,c_1
$$

$$
bp \leftarrow bp + e^{sz}
$$

With $bp$ finalized, $b_2 = bp^2$, $b_3 = bp^3$:

$$
sgr_p = 0.57248636 + 0.0006948103\,bp - 7.5728178\times10^{-7}\,b_2 + 3.207736\times10^{-10}\,b_3
$$

$$
sgr_b = 0.91610329 - 0.00025041792\,bp + 3.5706705\times10^{-7}\,b_2 - 1.663182\times10^{-10}\,b_3
$$

$$
sgr_n = 1.9082378 - 0.0034097612\,bp + 4.3083811\times10^{-6}\,b_2 - 1.85173\times10^{-9}\,b_3
$$

$$
x_{mp} = 45.19165 + 0.26993166\,bp - 8.805269\times10^{-5}\,b_2 + 3.58456\times10^{-7}\,b_3
$$

$$
x_{mb} = 14.93085 + 0.407469\,bp - 4.228928\times10^{-4}\,b_2 + 5.85848\times10^{-7}\,b_3
$$

$$
x_{mn} = 4.825517 + 0.13158172\,bp + 4.2669638\times10^{-4}\,b_2 - 1.49796\times10^{-7}\,b_3
$$

Paraffin/naphthene/aromatic (PNA) volume-fraction split: if $sg \le sgr_b$,

$$
vf_p = \frac{sg - sgr_b}{sgr_p - sgr_b}, \quad vf_b = 1 - vf_p, \quad vf_n = 0
$$

else

$$
vf_b = \frac{sg - sgr_n}{sgr_b - sgr_n}, \quad vf_n = 1 - vf_b, \quad vf_p = 0
$$

Converted to mole fractions via two weighting passes:

$$
q = vf_p\,sgr_p + vf_b\,sgr_b + vf_n\,sgr_n
$$

$$
wf_p = \frac{vf_p\,sgr_p}{q}, \quad wf_b = \frac{vf_b\,sgr_b}{q}, \quad wf_n = \frac{vf_n\,sgr_n}{q}
$$

$$
q' = \frac{wf_p}{x_{mp}} + \frac{wf_b}{x_{mb}} + \frac{wf_n}{x_{mn}}
$$

$$
x_{fp} = \frac{wf_p}{x_{mp}\,q'}, \quad x_{fb} = \frac{wf_b}{x_{mb}\,q'}, \quad x_{fn} = \frac{wf_n}{x_{mn}\,q'}
$$

Critical temperature (deg R), a PNA-weighted blend of three cubics in $bp$:

$$
xz_u = 727.47745 + 1.2626579\,bp - 4.5330572\times10^{-4}\,b_2 + 1.23217\times10^{-7}\,b_3
$$

$$
xz_i = 839.54553 + 1.0776683\,bp - 4.7253008\times10^{-4}\,b_2 + 2.8135443\times10^{-7}\,b_3
$$

$$
xz_o = 1521.9287 - 1.5416102\,bp + 0.0033237804\,b_2 - 1.65984\times10^{-6}\,b_3
$$

$$
T_c = \max\big(0,\ x_{fp}\,xz_u + x_{fb}\,xz_i + x_{fn}\,xz_o\big)
$$

Critical pressure (psia), same blend structure, different cubics:

$$
xz_u = 593.11935 - 1.1655109\,bp + 0.001210827\,b_2 - 6.92878\times10^{-7}\,b_3
$$

$$
xz_i = 1128.158 - 2.8264468\,bp + 0.0028014571\,b_2 - 9.72225\times10^{-7}\,b_3
$$

$$
xz_o = 2748.4398 - 9.519013\,bp + 0.012696074\,b_2 - 5.97439\times10^{-6}\,b_3
$$

$$
p_c = \max\big(0,\ x_{fp}\,xz_u + x_{fb}\,xz_i + x_{fn}\,xz_o\big)
$$

Critical volume, Hall's (1971) correlation (note: uses specific gravity,
not density, per the D-016 contract below):

$$
V_c = 0.025\left(\frac{M}{sg^{0.69}}\right)^{1.15}
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $MW$ | C7+ molecular weight | lb/lbmol |
| $sg$ | C7+ specific gravity, relative to water | dimensionless |

Returns $(T_c, p_c, V_c)$ in (deg R, psia, ft3/lbmol).

**Validity & guards.** Inputs are floored (not rejected):
$MW < 99 \to 110$, $sg < 0.7 \to 0.74$, each emitting a `UserWarning`
containing "clamped". $T_c$ and $p_c$ are separately floored at $0.0$ as a
defensive clamp only reachable for non-physical $(MW, sg)$ combinations far
outside the correlation's intended range.

**D-016: the SG-not-density contract.** The VBA source
(`EstimatePseudoCriticals`, line ~497) takes a C7+ *density* argument
(g/cc) and converts it internally via `ssg = PseudoDensGmCC / 0.999015`
before using it anywhere downstream. This module's public signature takes
`sg` (specific gravity) directly, and uses it everywhere the VBA uses
`ssg` - i.e. the `/0.999015` conversion is **not** applied a second time.
Callers holding a raw density must convert to specific gravity themselves
before calling. This is forced by the pinned characterization test
(`vc == 0.025*(mw/sg**0.69)**1.15` at `rel=1e-12`, `mw=217`, `sg=0.845`):
applying the extra `/0.999015` division would shift $V_c$ by about 0.07%,
well outside that tolerance. See `docs/excel-deviations.md` D-016.

**Source.** Erbar (Chao-Seader program) C7+ correlation, transcribed
verbatim from the Amoco GasProp VBA (`docs/reference/gasprop_functions.bas`);
critical volume via Hall, R.R. (1971).

**Function signature.**

```python
def c7_plus_criticals(mw: float, sg: float) -> tuple[float, float, float]:
    """Return (tc_r, pc_psia, vc)."""
```

**Anchoring.** This correlation is proprietary Amoco/Chao-Seader lineage
with no public worked example, so its primary anchor is a **VBA-trace**
(transcription self-consistency), not an external published or workbook
value. `test_vba_trace_mw217_sg0845` hand-traces
`EstimatePseudoCriticals(PseudoMolWt=217.0, PseudoDensGmCC=0.845)`
line-by-line from the `.bas` file independently of `erbar.py` (intermediate
values `bp=560.6575339349728`, `sgrp=0.7805270473601936`,
`sgrb=0.8586327919042741`, `sgrn=1.024472269520219`), then asserts the
Python output matches that trace to `rel=1e-12`
($T_c=1340.2602949758316$, $p_c=244.54023185923086$,
$V_c=13.896579108178768$). Supporting tests: `test_typical_c7plus_is_physical`
(bounds sanity + exact $V_c$ formula check), `test_monotone_in_mw`,
`test_clamps_warn` (both floors fire and warn), and
`test_extreme_inputs_floor_tc_and_pc_at_zero` (drives $MW=1000$, $sg=0.72$
to exercise the $T_c<0$/$p_c<0$ defensive floors).

---

## 5.2 Gas Compressibility Factor (Z) (`pvt/correlations/zfactor/`)

### 5.2.1 Dranchuk & Abou-Kassem (1975)

**Purpose.** Solve the DAK equation of state for Z by Newton iteration on
the implicit residual, given pressure, temperature, and pseudocriticals.

**Equation(s).** With $T_{pr}=T/T_{pc}$, $p_{pr}=p/p_{pc}$:

$$
C_1 = A_1 + \frac{A_2}{T_{pr}} + \frac{A_3}{T_{pr}^3} + \frac{A_4}{T_{pr}^4} + \frac{A_5}{T_{pr}^5}
$$

$$
C_2 = A_6 + \frac{A_7}{T_{pr}} + \frac{A_8}{T_{pr}^2}
$$

$$
C_3 = A_9\left(\frac{A_7}{T_{pr}} + \frac{A_8}{T_{pr}^2}\right)
$$

$$
\rho_r = \frac{0.27\,p_{pr}}{Z\,T_{pr}}
$$

$$
C_4 = A_{10}\left(1 + A_{11}\rho_r^2\right)\frac{\rho_r^2}{T_{pr}^3}\,e^{-A_{11}\rho_r^2}
$$

$$
F(Z) = Z - \left(1 + C_1\rho_r + C_2\rho_r^2 - C_3\rho_r^5 + C_4\right) = 0
$$

solved by Newton's method, $Z_{n+1} = Z_n - F(Z_n)/F'(Z_n)$, with (using
$d\rho_r/dZ = -\rho_r/Z$):

$$
F'(Z) = 1 + \frac{C_1\rho_r}{Z} + \frac{2C_2\rho_r^2}{Z} - \frac{5C_3\rho_r^5}{Z} + \frac{2A_{10}\rho_r^2}{T_{pr}^3\,Z}\,e^{-A_{11}\rho_r^2}\Big(1 + A_{11}\rho_r^2 - (A_{11}\rho_r^2)^2\Big)
$$

This derivative was independently re-derived from $F(Z)$ above (via
$u=\rho_r^2$ and $d(\rho_r^n)/dZ=-n\rho_r^n/Z$) and confirmed to match the
code's `dc4`/`df` terms exactly, including sign. The module docstring notes
the reference workbook ("Z factor calculation.xls") uses a different,
incorrect derivative that happens to still converge (D-005); this module
uses the mathematically correct one, so it and the workbook can diverge in
iteration path while (per D-005) landing on the same converged root.

The 11 coefficients ($A_1 \ldots A_{11}$):

| $A_1$ | $A_2$ | $A_3$ | $A_4$ | $A_5$ | $A_6$ | $A_7$ | $A_8$ | $A_9$ | $A_{10}$ | $A_{11}$ |
|---|---|---|---|---|---|---|---|---|---|---|
| 0.3265 | -1.07 | -0.5339 | 0.01569 | -0.05165 | 0.5475 | -0.7361 | 0.1844 | 0.1056 | 0.6134 | 0.721 |

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $p$ | Pressure | psia |
| $T$ | Temperature | deg R |
| $T_{pc}$, $p_{pc}$ | Pseudocriticals | deg R, psia |
| `tol` | Newton convergence tolerance on $\lvert F(Z)\rvert$ | default $10^{-10}$ |
| `max_iter` | Newton iteration cap | default 100 |
| `z0` | Optional warm-start Z | dimensionless |

Returns $Z$ (dimensionless).

**Validity & guards.** Raises `InputValidationError` if $p<0$; if $T$,
$T_{pc}$, or $p_{pc} \le 0$; if `z0` is supplied and $\le 0$. Separately
raises `InputValidationError` unless $1.0 < T_{pr} \le 3.0$ **and**
$p_{pr} < 30.0$; there is no enforced lower bound on $p_{pr}$ (values near
zero are accepted and converge toward the ideal-gas limit $Z\to1$, per the
module docstring's "accepting Ppr < 0.2 as the ideal-gas limit" note - this
is intentional, not an unenforced guard). Each Newton step that would drive
$Z \le 0$ is reset to $10^{-3}$ (a defensive safety valve). Raises
`ConvergenceError` (with iteration count and final residual) if `max_iter`
is exhausted without meeting `tol`.

**Source.** Dranchuk, P.M. and Abou-Kassem, J.H. (1975). Coefficients per
the original paper, as stated in the module docstring.

**Function signature.**

```python
def z_factor(p_psia: float, t_r: float, tpc_r: float, ppc_psia: float, *,
             tol: float = 1e-10, max_iter: int = 100, z0: float | None = None) -> float:
```

**Anchoring.** `test_golden_fixture1` is a **workbook golden**: four
pressures against `"Z factor calculation.xls"`-cached Z values at
$T_{pc}=527.028947342463$ R, $p_{pc}=676.464314208584$ psia (SBV on the
workbook's own critical-property table), $T=703.8$ R (the workbook's
$T_F+460$ Rankine convention, not the engine's usual $+459.67$, needed for
parity with the cached values); tolerance `abs=2e-6` (per the test's
comment, this reproduces to $\le 8.2\times10^{-7}$ at this exact T basis).
`test_golden_fixture3_gravity_based` is the same style of golden using
gravity-form pseudocriticals. Supporting tests: `test_low_pressure_limit`
($Z\to1$ as $p\to0$), `test_warm_start_agrees_with_cold` (z0 doesn't change
the converged root), and a full set of `InputValidationError` /
`ConvergenceError` guard tests, including `test_z_positive_safety_valve`
which drives a Newton step negative to exercise the $Z\le0\to10^{-3}$ clamp.

---

### 5.2.2 Hall & Yarborough (1973)

**Purpose.** Solve the Hall & Yarborough equation of state for Z by Newton
iteration on the reduced gas density $y$, using the **reciprocal** reduced
temperature convention.

**Equation(s).** With $t = T_{pc}/T$ (note: reciprocal of the usual
$T_{pr}=T/T_{pc}$) and $p_{pr}=p/p_{pc}$:

$$
A = 0.06125\, t\, p_{pr}\, e^{-1.2(1-t)^2}
$$

$$
B = t\left(14.76 - 9.76t + 4.58t^2\right)
$$

$$
C = t\left(90.7 - 242.2t + 42.4t^2\right)
$$

$$
D = 2.18 + 2.82t
$$

Newton-solved for reduced density $y$:

$$
F(y) = -A + \frac{y+y^2+y^3-y^4}{(1-y)^3} - By^2 + Cy^D = 0
$$

$$
F'(y) = \frac{1+4y+4y^2-4y^3+y^4}{(1-y)^4} - 2By + CD\,y^{D-1}
$$

$$
Z = \frac{A}{y}
$$

$F'$ is the closed-form derivative of $F$, symbolically verified per the
module docstring, and is algebraically equivalent to the Gas_Gradient VBA
`CalculateZFactor` kernel's derivative of the residual $F(y)/y$.

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $p$ | Pressure | psia |
| $T$ | Temperature | deg R |
| $T_{pc}$, $p_{pc}$ | Pseudocriticals | deg R, psia |
| `tol` | Newton convergence tolerance on $\lvert F(y)\rvert$ | default $10^{-10}$ |
| `max_iter` | Newton iteration cap | default 60 |

Returns $Z$ (dimensionless).

**Validity & guards.** Raises `InputValidationError` if $p<0$ or if $T$,
$T_{pc}$, $p_{pc} \le 0$. Unlike `dak.z_factor`, this module does **not**
enforce a $(p_{pr}, T_{pr})$ validity window - deliberate, per the module
docstring; extreme inputs are handled by the Newton iteration's own
defensive clamps: $y$ is reset to $0.999$ if a step would push it $\ge 1$,
and to $10^{-6}$ if a step would push it $\le 0$. Raises `ConvergenceError`
if `max_iter` is exhausted without meeting `tol`.

**D-006 (adjacent).** A separate workbook (ADRIC CVD `Additional_QC`
sheet) implements a broken variant of this equation: it uses the ordinary
$T_{pr}$ instead of the reciprocal $t$, omits the $\cdot t$ factor in the
$A$ term, and returns the reduced density $y$ itself as "Z". This module
implements the canonical 1973 form per the Gas_Gradient VBA reference, not
that broken variant.

**Source.** Hall, K.R. and Yarborough, L. (1973), per the module docstring.

**Function signature.**

```python
def z_factor(p_psia: float, t_r: float, tpc_r: float, ppc_psia: float, *,
             tol: float = 1e-10, max_iter: int = 60) -> float:
```

**Anchoring.** This module's tests do not cite an external workbook
golden; its primary anchor is a **cross-correlation check**:
`test_agrees_with_dak_within_2pct` compares `hy_z(...)` against
`dak.z_factor(...)` at six pressures for the same sweet 0.737-gravity gas
pseudocriticals used in the DAK golden fixture, `rel=0.02`.
`test_low_pressure_limit` checks $Z\to1$ as $p\to0$.
`test_z_is_a_over_y_not_y` is a D-006 guard: at high pressure it asserts
$Z>0.7$ while the underlying reduced density $y$ is small ($\sim0.1$),
which would fail if the function returned $y$ instead of $A/y$.
`test_upper_clamp_safety_valve` drives $p_{pr}\approx150{,}000$
(non-physical) specifically to exercise the $y\ge1\to0.999$ clamp and
confirms iteration still converges. Full `InputValidationError` /
`ConvergenceError` guard coverage is also present.

---

## 5.3 Bubble-Point Pressure (`pvt/correlations/bubble_point/`)

The package intentionally exposes no ambiguous bare `bubble_point` name at
the package level (four independent correlations each define their own);
call `<module>.bubble_point(...)` explicitly.

### 5.3.1 Standing (1947)

**Purpose.** Estimate bubble-point pressure from solution GOR, gas
gravity, API gravity, and temperature, using Standing's original
California-crude correlation.

**Equation(s).**

$$
a = 0.00091\,T_F - 0.0125\,API
$$

$$
p_b = 18.2\left[\left(\frac{R_s}{\gamma_g}\right)^{0.83} 10^{a} - 1.4\right]
$$

`bubble_point_with_exponent(rs, gas_gravity, a)` exposes the same formula
with $a$ supplied directly (a parity hook matching the source workbook,
which leaves $a$ as a raw user-entered cell, D-007); `bubble_point(...)`
is the normal entry point and computes $a$ from $T_F$/$API$ internally.

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $R_s$ | Total solution GOR | scf/STB |
| $\gamma_g$ | Gas specific gravity (air = 1) | dimensionless |
| $API$ | Stock-tank oil API gravity | deg API |
| $T_F$ | Reservoir temperature | deg F |

Returns $p_b$ in psia (floored at 0 for non-physical inputs).

**Validity & guards.** `bubble_point_with_exponent` returns $0.0$ (no
exception) if $\gamma_g \le 0$ or $R_s \le 0$; otherwise returns
$\max(p_b, 0)$. `bubble_point` emits a `UserWarning` (message contains
"outside Standing") for any input outside Standing's original data range:
$R_s \in [20, 1425]$ scf/STB, $\gamma_g \in [0.59, 0.95]$,
$API \in [16.5, 63.8]$, $T_F \in [100, 258]$ deg F. Neither function raises
`InputValidationError`; out-of-range inputs only warn.

**Source.** Standing, M.B. (1947). *A Pressure-Volume-Temperature
Correlation for Mixtures of California Oils and Gases.* Drill. & Prod.
Prac., API.

**Function signature.**

```python
def bubble_point_with_exponent(rs_scf_stb: float, gas_gravity: float, a: float) -> float: ...
def bubble_point(rs_scf_stb: float, gas_gravity: float, api: float, t_f: float) -> float: ...
def standing_bubble_point(R_scf_stb: float, gamma_g: float, T_F: float, API: float) -> float:
    """Deprecated alias; ORIGINAL argument order (R, gamma_g, T_F, API)."""
```

**Anchoring.** `test_golden_sheet_literal_form` is a **workbook golden**:
`bubble_point_with_exponent(1000.0, 0.65, 0.0)` against `"Bubble point
pressure correlations.xls"` cell `F38` (which leaves $a=0$ as a raw
input, D-007), `rel=1e-10`. `test_computed_exponent_form` and the
`TestBubblePointFormula` class are formula self-checks against an
independently written reference implementation (`_standing_pb`) across
several parametrized inputs, `rel=1e-9`. `test_range_warning` confirms the
out-of-range `UserWarning`. Edge-case and physical-trend tests
(`TestBubblePointEdgeCases`, `TestBubblePointPhysicalTrends`) and a
dedicated `TestStandingBubblePointDeprecatedAlias` class (confirming the
`DeprecationWarning` and reordered-argument equivalence) round out coverage.

---

### 5.3.2 Vasquez & Beggs (1980)

**Purpose.** Estimate bubble-point pressure from solution GOR, gas
gravity, API gravity, and temperature, with a separator-gravity correction
and an API-gravity-dependent coefficient switch.

**Equation(s).** Separator gas gravity correction to a 100 psia reference:

$$
\gamma_{gs} = \gamma_g\left[1 + 5.912\times10^{-5}\,API\,T_{sep}\,\log_{10}\!\left(\frac{p_{sep}}{114.7}\right)\right]
$$

Bubble-point pressure (Ahmed's tabulated Pb-form, the form this module
implements):

$$
p_b = \left[C_1\left(\frac{R_s}{\gamma_g}\right)10^{-C_3\,API/(T_F+460)}\right]^{C_2}
$$

with $(C_1, C_2, C_3) = (27.62,\ 0.914,\ 11.172)$ for $API \le 30$, and
$(56.18,\ 0.842,\ 10.393)$ for $API > 30$.

An algebraically equivalent original 1980 Rs-form exists in the
literature (inverted to give the Pb-form above), solved for $R_s$
directly:

$$
R_s = C_1'\,\gamma_g\, p_b^{C_2'}\, \exp\!\left(\frac{C_3'\,API}{T_F+460}\right)
$$

with $(C_1', C_2', C_3') = (0.0362,\ 1.0937,\ 25.7240)$ for $API \le 30$,
and $(0.0178,\ 1.1870,\ 23.9310)$ for $API > 30$. The two forms agree to
within about 0.5% (not bit-identical) because each published coefficient
table is independently rounded; this module implements only the Pb-form.

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $R_s$ | Solution GOR at bubble point | scf/STB |
| $\gamma_g$ | Gas specific gravity (air = 1) | dimensionless |
| $API$ | Stock-tank oil API gravity | deg API |
| $T_F$ | Reservoir temperature | deg F |
| $T_{sep}$, $p_{sep}$ | Separator temperature, pressure | deg F, psia |

Returns $p_b$ in psia; `corrected_gas_gravity` returns $\gamma_{gs}$
(dimensionless).

**Validity & guards.** `bubble_point` raises `InputValidationError` if
$R_s \le 0$, $\gamma_g \le 0$, or $API \le 0$. `corrected_gas_gravity`
raises `InputValidationError` if $\gamma_g \le 0$, $API \le 0$, or
$p_{sep} \le 0$. `bubble_point` additionally emits a `UserWarning`
(message contains "outside Vasquez-Beggs") for inputs outside the original
data range: $R_s \in [20, 2070]$ scf/STB, $\gamma_g \in [0.511, 1.351]$,
$API \in [15.3, 59.3]$, $T_F \in [75, 294]$ deg F.

**D-008.** The source workbook computes the exponent term as
$a = -C_3\,API\,(T_F+460)$ (multiplying by $(T_F+460)$ instead of
dividing), which overflows to `#NUM!`. This module divides by
$(T_F+460)$, per both published forms above.

**Source.** Vasquez, M. and Beggs, H.D. (1980). *Correlations for Fluid
Physical Property Prediction.* JPT, June 1980. Tabulated coefficients per
Ahmed, T., *Reservoir Engineering Handbook*.

**Function signature.**

```python
def corrected_gas_gravity(gas_gravity: float, api: float, t_sep_f: float, p_sep_psia: float) -> float: ...
def bubble_point(rs_scf_stb: float, gas_gravity: float, api: float, t_f: float) -> float: ...
```

**Anchoring.** `test_golden_gamma_gs` is a **workbook golden**:
`corrected_gas_gravity(1.0, 30.0, 100.0, 150.0)` against `"Bubble point
pressure correlations.xls"` cell `F64`, `rel=1e-10`.
`test_corrected_bubble_point_magnitude` checks $p_b \approx 5855$ psia at
`rel=0.02` (a controller-adjudicated anchor, cross-verified via both the
Pb-form and the original Rs-form to 0.003% agreement).
`test_round_trip_against_original_rs_form` is a genuine external
cross-check: it feeds `bubble_point()`'s Pb-form output back into the
independent, differently-parameterized 1980 Rs-form (different
coefficients, $\exp()$ instead of $10^{()}$) and recovers the input $R_s$
to within the tabulated coefficients' own rounding precision (`rel=5e-3`
for $API\le30$, `rel=6e-3` for $API>30$, both branches checked).
`test_coefficient_switch_at_api_30` confirms the branch actually switches
at $API=30$. Full `InputValidationError` and range-`UserWarning` guard
coverage is also present (`test_range_warning_all_four_checks` fires all
four range warnings in one call).

---

### 5.3.3 Glaso (1980), SPE 8016

**Purpose.** Estimate bubble-point pressure via Glaso's generalized
correlating number and a quadratic-in-log10 fit.

**Equation(s).**

$$
p_b^{*} = \left(\frac{R_s}{\gamma_g}\right)^{0.816} \frac{T_F^{0.172}}{API^{0.989}}
$$

$$
\log_{10}(p_b) = 1.7669 + 1.7447\,\log_{10}(p_b^{*}) - 0.30218\,\big(\log_{10}(p_b^{*})\big)^2
$$

$$
p_b = 10^{\log_{10}(p_b)}
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $R_s$ | Solution GOR at bubble point | scf/STB |
| $\gamma_g$ | Gas specific gravity (air = 1) | dimensionless |
| $API$ | Stock-tank oil API gravity | deg API |
| $T_F$ | Reservoir temperature | deg F |

Returns $p_b^{*}$ (dimensionless, from `pb_star`) or $p_b$ in psia (from
`bubble_point`).

**Validity & guards.** Both `pb_star` and `bubble_point` raise
`InputValidationError` (collecting all violations) if $R_s \le 0$,
$\gamma_g \le 0$, $API \le 0$, or $T_F \le 0$. No warning-only range check
is implemented for this correlation.

**D-009.** The source workbook multiplies $p_b^{*}$ by a stray factor of
14.5 and never applies the final $10^{(\cdot)}$ step (returning
$\log_{10}(p_b)$ itself, mislabeled as $p_b$); it also rounds the
correlation constants to 1.767/1.745. This module applies neither
deviation: `pb_star()` has no stray factor, `bubble_point()` exponentiates
back out of log space, and the published 1.7669/1.7447 constants are used.

**Source.** Glaso, O. (1980). *Generalized Pressure-Volume-Temperature
Correlations.* JPT, May 1980, pp. 785-795 (SPE 8016).

**Function signature.**

```python
def pb_star(rs_scf_stb: float, gas_gravity: float, api: float, t_f: float) -> float: ...
def bubble_point(rs_scf_stb: float, gas_gravity: float, api: float, t_f: float) -> float: ...
```

**Anchoring.** `test_pb_star_matches_workbook_cell` is a **workbook
golden**: `pb_star(1000.0, 0.65, 30.0, 200.0)` against the reference
sheet's cached cell `F81 = 497.662528246482`, divided by the sheet's own
stray 14.5 factor (D-009), `rel=1e-6` - an exact anchor for the published
Pb* form derived by dividing out a known bug. `test_corrected_magnitude`
checks $p_b \approx 5413.4$ psia at `rel=0.02` (hand-derivation:
$p_b^{*}=34.32$, $\log_{10}(p_b)=3.7336$). `test_trends` confirms the
expected GOR/API/gravity directions. Full `InputValidationError` guard
coverage is present for both `pb_star` and `bubble_point`.

---

### 5.3.4 Al-Marhoun (1988)

**Purpose.** Estimate bubble-point pressure for Middle East crude oils
from solution GOR, gas gravity, stock-tank oil specific gravity, and
temperature.

**Equation(s).**

$$
T_R = T_F + 459.67
$$

$$
p_b = 5.38088\times10^{-3}\; R_s^{0.715082}\; \gamma_g^{-1.87784}\; \gamma_o^{3.1437}\; T_R^{1.32657}
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $R_s$ | Solution GOR at bubble point | scf/STB |
| $\gamma_g$ | Gas specific gravity (air = 1) | dimensionless |
| $\gamma_o$ | Stock-tank oil specific gravity | dimensionless |
| $T_F$ | Reservoir temperature | deg F |

Returns $p_b$ in psia.

**Validity & guards.** Raises `InputValidationError` (collecting all
violations) if $R_s \le 0$, $\gamma_g \le 0$, $\gamma_o \notin (0, 2)$, or
$T_F \le -459.67$ (absolute zero). No warning-only range check is
implemented for this correlation.

**Source.** Al-Marhoun, M.A. (1988). *PVT Correlations for Middle East
Crude Oils.* Journal of Petroleum Technology, 40(5), 650-666.

**Function signature.**

```python
def bubble_point(rs_scf_stb: float, gas_gravity: float, oil_sg: float, t_f: float) -> float:
```

**Anchoring.** `test_full_precision_value` is a formula self-check: it
recomputes the equation term-by-term independently and asserts exact
agreement (`rel=1e-12`). `test_close_to_sheet_rounded_form` is a **loose
workbook golden**: $p_b \approx 5585.23$ psia at `rel=0.006`, matching the
reference sheet's rounded-coefficient result with $T_F+460$ (the
full-precision published form used here lands within 0.6% of the sheet's
rounded one). `test_trends` confirms higher GOR gives higher $p_b$. Full
`InputValidationError` guard coverage is present, including the oil-SG
bounds and the absolute-zero temperature floor.

---

## 5.4 Gas Viscosity (`pvt/correlations/viscosity/`)

### 5.4.1 Lee, Gonzalez & Eakin (1966), SPE 1340

**Purpose.** Estimate natural gas viscosity from temperature, apparent
molecular weight, and gas density (itself computed from the real-gas law).

**Equation(s).**

$$
K = \frac{(9.4 + 0.02\,M)\,T^{1.5}}{209 + 19M + T} \qquad (T \text{ in deg R})
$$

$$
X = 3.5 + \frac{986}{T} + 0.01\,M
$$

$$
Y = 2.4 - 0.2X
$$

$$
\mu_g = 10^{-4}\,K\,e^{X\,\rho_g^{Y}} \qquad (\rho_g \text{ in g/cc},\ \mu_g \text{ in cP})
$$

Gas density input, via the real-gas law:

$$
\rho_g = \frac{p\,M}{Z\,T_R}\cdot \text{DENSITY\_COEF}, \qquad T_R = T_F + 459.67
$$

where `DENSITY_COEF` is the exact lbm/ft3 to g/cc conversion divided by
the gas constant:

$$
\text{DENSITY\_COEF} = \frac{G_{PER\_LB}}{30.48^3} \Big/ R_{PSIA\_FT3\_LBMOL\_R} = \frac{453.59237}{28316.846592} \Big/ 10.7316 \approx 0.0014926
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $p$ | Pressure | psia |
| $M$ | Gas apparent molecular weight | g/mol (lbm/lbmol) |
| $Z$ | Gas compressibility factor | dimensionless |
| $T_F$ | Temperature | deg F |
| $\rho_g$ | Gas density (from `gas_density_g_cc`) | g/cc |

Returns $\rho_g$ (g/cc) or $\mu_g$ (cP).

**Validity & guards.** `gas_density_g_cc` raises `InputValidationError`
(collecting all violations) if $p < 0$, $M \le 0$, or $Z \le 0$.
`gas_viscosity_cp` raises `InputValidationError` if $M \le 0$ or
$\rho_g < 0$.

**D-010.** The source workbook (`5_Viscosity_HPHT_Calc_v2.xlsx`) hardcodes
the lbm/ft3 to g/cc conversion as the rounded literal 0.0014935. This
module derives `DENSITY_COEF` exactly from canonical constants instead
(30.48 cm/ft is the formula-grade, exact-by-definition inch/foot
conversion); the two agree to about 0.06%.

**Source.** Lee, A.L., Gonzalez, M.H., and Eakin, B.E. (1966). *The
Viscosity of Natural Gases.* JPT, August 1966, pp. 997-1000 (SPE 1340).

**Function signature.**

```python
def gas_density_g_cc(p_psia: float, mw: float, z: float, t_f: float) -> float: ...
def gas_viscosity_cp(t_f: float, mw: float, rho_g_cc: float) -> float: ...
```

**Anchoring.** `test_golden_viscosity_workbook_point` is a **workbook
golden**: at 965 psia, $Z=0.945$, $M=19.5$, $T_F=256$, the reference
workbook caches $\rho=0.04155$ g/cc and $\mu_g=0.015395$ cP; the test
checks $\rho$ at `rel=2e-3` and $\mu_g$ at `rel=5e-3` (D-010's exact
coefficient is about 0.06% lower than the workbook's rounded one, so the
tolerance absorbs that known, intentional difference rather than masking a
regression). `test_viscosity_increases_with_density` and
`test_dilute_limit_positive` check physical trends/bounds. Full
`InputValidationError` guard coverage is present for both functions.

---

### 5.4.2 Jossi, Stiel & Thodos (1962)

**Purpose.** Estimate dense-gas viscosity from reduced density and a
dilute-gas ("zero-density") viscosity term, transcribed from the Amoco
GasProp VBA `ThodosGasVisc`.

**Equation(s).**

$$
\chi = \frac{(T_{pc}/1.8)^{1/6}}{\sqrt{M}\,(p_{pc}/14.696)^{2/3}} \qquad (T_{pc} \text{ in deg R},\ p_{pc} \text{ in psia})
$$

Dilute-gas term, split at $T_r = T/T_{pc} = 1.5$:

$$
T_r \le 1.5:\quad \mu^{*} = \frac{0.00034\,T_r^{0.888}}{\chi}
$$

$$
T_r > 1.5:\quad \mu^{*} = \frac{0.001668\,(0.1338\,T_r - 0.0932)^{5/9}}{\chi}
$$

Dense-gas viscosity:

$$
\mu = \frac{\left(0.1023 + 0.023364\,\rho_r + 0.058533\,\rho_r^2 - 0.040758\,\rho_r^3 + 0.0093324\,\rho_r^4\right)^4 - 10^{-4}}{\chi} + \mu^{*}
$$

Reduced density input:

$$
\rho_r = \frac{V_{c,mix}\,p}{Z\,R\,T} \qquad (R = 10.7316 \text{ psia}\cdot\text{ft}^3/(\text{lbmol}\cdot{}^\circ\text{R}))
$$

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| $T$ | Temperature | deg R |
| $M$ | Gas apparent molecular weight | g/mol |
| $T_{pc}$, $p_{pc}$ | Mixture pseudocriticals | deg R, psia |
| $\rho_r$ | Reduced density (from `reduced_density`) | dimensionless |
| $p$, $Z$, $V_{c,mix}$ | Pressure, Z-factor, mixture critical volume | psia, dimensionless, ft3/lbmol |

Returns $\rho_r$ (dimensionless, from `reduced_density`) or $\mu$
(cP, from `gas_viscosity_cp`).

**Validity & guards.** `reduced_density` raises `InputValidationError`
(collecting all violations) if $Z \le 0$ or $V_{c,mix} \le 0$.
`gas_viscosity_cp` raises `InputValidationError` if $M \le 0$,
$T_{pc} \le 0$, $p_{pc} \le 0$, or $\rho_r < 0$.

**Amoco-variant caveat.** The $T_r \le 1.5$ / $T_r > 1.5$ dilute-term split
and its coefficients ($0.00034/0.888$; $0.001668/0.1338/0.0932/(5/9)$) are
the Amoco GasProp VBA's variant of the Stiel-Thodos (1961) dilute-gas
viscosity correlation, not a transcription of the originally published
Stiel-Thodos coefficients; this VBA variant deviates from published forms
by roughly $-2\%$ to $+3\%$ depending on $T_r$. The two branches do **not**
meet exactly at $T_r=1.5$ (confirmed to differ by up to 5%,
faithful to the VBA source, not a transcription error).

**D-011.** The VBA source hardcodes the gas constant in `reduced_density`
as the rounded literal 10.73. This module uses the canonical
`R_PSIA_FT3_LBMOL_R` (10.7316) instead; the two agree to about 0.015%.

**Source.** Jossi, J.A., Stiel, L.I., and Thodos, G. (1962). *The
Viscosity of Pure Substances in the Dense Gaseous and Liquid Phases.*
AIChE Journal, 8(1), 59-63. Transcribed from the preserved VBA
`ThodosGasVisc` (`docs/reference/gasprop_functions.bas`).

**Function signature.**

```python
def reduced_density(p_psia: float, z: float, t_r: float, vc_mix: float) -> float: ...
def gas_viscosity_cp(t_r: float, mw: float, tpc_r: float, ppc_psia: float, rho_r: float) -> float: ...
```

**Anchoring.** No external workbook golden is used for this module; its
tests are **formula self-checks**. `test_zero_density_recovers_dilute_term`
recomputes $\chi$ and $\mu^{*}$ (the $T_r>1.5$ branch) independently and
checks the $\rho_r=0$ result at `rel=1e-9`. `test_reduced_density_formula`
recomputes the $\rho_r$ formula directly, `rel=1e-12`.
`test_branch_boundary_continuity_documented` evaluates just below and just
above $T_r=1.5$ and asserts they agree only to `rel=0.05`, explicitly
documenting (not hiding) the branch discontinuity. `test_monotone_in_reduced_density`
checks the expected trend. Full `InputValidationError` guard coverage is
present for both functions.

---

### 5.4.3 Critical Volume Table (`critical_volumes.py`)

**Purpose.** Supply the mole-fraction-weighted mixture critical volume
$V_{c,mix}$ that `jossi_stiel_thodos.reduced_density` consumes, using a
fixed 11-component table plus a per-call C7+ value.

**Equation(s).**

$$
V_{c,mix} = \sum_i y_i\, V_{c,i}
$$

where $V_{c,i}$ is looked up in `VC_TABLE` for the 11 tabulated
components, or supplied as the `c7_plus_vc` argument for the `"C7+"` key
(typically `erbar.c7_plus_criticals(mw, sg)[2]`, Hall's 1971 $V_c$).

`VC_TABLE` (ft3/lbmol), ported verbatim, in the VBA's fixed positional
order:

| N2 | C1 | CO2 | C2 | H2S | C3 | iC4 | nC4 | iC5 | nC5 | C6 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.44 | 1.59 | 1.51 | 2.37 | 1.565 | 3.21 | 4.21 | 4.08 | 4.9 | 4.87 | 5.93 |

C7+ is deliberately excluded from the table; it is not a fixed constant
because the VBA (and this module) computes it per-call.

**Inputs & units.**

| Symbol | Meaning | Units |
|---|---|---|
| `mol_fractions` | Mole fraction (0-1) by component code | dimensionless |
| `c7_plus_vc` | C7+ pseudo-component critical volume (used only if `"C7+"` is a key) | ft3/lbmol |

Returns $V_{c,mix}$ in ft3/lbmol.

**Validity & guards.** Raises `InputValidationError` listing any unknown
component code(s) in `mol_fractions` (i.e. not in `VC_TABLE` and not
`"C7+"`).

**Source.** Gas_Gradient VBA `CalculateCriticals`
(`docs/reference/gasprop_functions.bas`, lines ~437-444), ported verbatim;
not itself a separately dated literature correlation (the values are
Amoco-internal component-property constants, distinct from the Hall
(1971) correlation used to compute the C7+ entry).

**Function signature.**

```python
def vc_mix(mol_fractions: dict[str, float], c7_plus_vc: float = 0.0) -> float:
```

**Anchoring.** `test_table_matches_vba_spot_values` is an **exact VBA spot
check**: every `VC_TABLE` entry against the `.bas` file's `crit_vc` array
values, confirmed positionally against the parallel `mol_wt` array at the
same lines. `test_table_has_exactly_eleven_entries_no_c7_plus` confirms
the table's shape contract. `test_pure_component_identity` and
`test_pure_c7_plus_identity` check single-component mixes recover the
table value (or the supplied `c7_plus_vc`) exactly, `rel=1e-12`.
`test_mole_fraction_weighted_mix` recomputes a four-component mix
independently. `test_unknown_key_raises` /
`test_unknown_key_raises_alongside_known_keys` cover the guard.

---

## 5.5 Summary Table

| Module | Correlation | Source year | Anchor type |
|---|---|---|---|
| `pseudocritical/sutton.py` | Sutton | 1985 | Formula self-check (exact) |
| `pseudocritical/sbv.py` | Stewart-Burkhardt-Voo | 1959 | Workbook golden + exact identity |
| `pseudocritical/piper_mccain.py` | Piper, McCain & Corredor (SPE 26668) | 1993 | Workbook golden + hand-derived exact pins |
| `pseudocritical/wichert_aziz.py` | Wichert-Aziz | 1972 | Formula self-check (hand-derived) |
| `pseudocritical/erbar.py` | Erbar (Chao-Seader) / Hall Vc | n/a (VBA) / 1971 (Vc) | VBA line-trace (transcription self-consistency) |
| `zfactor/dak.py` | Dranchuk & Abou-Kassem | 1975 | Workbook golden |
| `zfactor/hall_yarborough.py` | Hall & Yarborough | 1973 | Cross-correlation check (vs DAK) |
| `bubble_point/standing.py` | Standing | 1947 | Workbook golden + formula self-check |
| `bubble_point/vasquez_beggs.py` | Vasquez & Beggs | 1980 | Workbook golden + cross-form round-trip |
| `bubble_point/glaso.py` | Glaso (SPE 8016) | 1980 | Workbook golden (exact) + hand-derived magnitude |
| `bubble_point/almarhoun.py` | Al-Marhoun | 1988 | Formula self-check + loose workbook golden |
| `viscosity/lee_gonzalez_eakin.py` | Lee, Gonzalez & Eakin (SPE 1340) | 1966 | Workbook golden |
| `viscosity/jossi_stiel_thodos.py` | Jossi, Stiel & Thodos (Amoco VBA variant) | 1962 | Formula self-check |
| `viscosity/critical_volumes.py` | Vc table (Gas_Gradient VBA) | n/a (VBA transcription) | VBA spot-check (exact) |
