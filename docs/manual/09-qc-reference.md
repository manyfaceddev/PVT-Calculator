# Chapter 9: QC Reference

## 9.1 The QC Engine Model

Every QC check in the platform speaks the same small vocabulary, defined once in `pvt/qc/engine.py` and reused by every check module under `pvt/qc/checks/` and by the two QC checks that live inline in `pvt.experiments` (`gor_actual_vs_target`, see 8.5).

### Severity

```python
class Severity(enum.StrEnum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    FAIL = "FAIL"
```

Ordered best to worst: `PASS < REVIEW < FAIL`.

### QCResult

```python
@dataclass(frozen=True)
class QCResult:
    check_id: str
    severity: Severity
    value: float | None
    threshold: str
    message: str
```

One `QCResult` is the outcome of one check on one stream/pair. `check_id` identifies which threshold band was used (it is also the key into `ThresholdRegistry`), `value` carries the graded numeric deviation, `threshold` is a human-readable rendering of the band that was applied, and `message` is the sentence a report or UI pill shows verbatim.

### Grading a value against a two-band threshold

`grade()` is the shared banding function every check calls:

```python
def grade(value, review_at, fail_at, *, absolute=True):
    graded = abs(value) if absolute else value
    if graded <= review_at:
        return Severity.PASS
    if graded <= fail_at:
        return Severity.REVIEW
    return Severity.FAIL
```

$$
severity(v) = \begin{cases}
\text{PASS} & |v| \le review\_at \\
\text{REVIEW} & review\_at < |v| \le fail\_at \\
\text{FAIL} & |v| > fail\_at
\end{cases}
$$

Band edges are inclusive downward: a value exactly at `fail_at` grades `REVIEW`, not `FAIL`.

### Rolling many results up to one verdict

```python
def worst(results: Iterable[QCResult]) -> Severity
```

Returns the highest-severity result across a collection, or `PASS` if the collection is empty. This is how a study-level verdict is derived from a list of individual `QCResult`s.

### ThresholdRegistry, overrides, and the audit trail

`ThresholdRegistry` holds one `(review_at, fail_at)` pair per `check_id`. It is constructed with the ADRIC house-convention defaults (`ThresholdRegistry.DEFAULTS`, reproduced in full in 8.6) already loaded, and any check may be overridden per study:

```python
def override(self, check_id, review_at, fail_at, note) -> None:
    self._thresholds[check_id] = (review_at, fail_at)
    self.audit.append(
        f"{check_id}: threshold overridden to ({review_at}, {fail_at}) — {note}"
    )
```

Every override is appended to `registry.audit` with the caller-supplied `note`, so a QC report can explain why a particular study's bands differ from the house defaults, rather than silently applying a different number. `registry.get(check_id)` returns the current `(review_at, fail_at)` pair, whether default or overridden.

## 9.2 composition_normalization

Module: `pvt/qc/checks/composition_normalization.py`. Check ID: `composition_sum`.

Lab compositions (mol% or wt%) are expected to sum to 100 before use; small deviations come from analytical rounding, larger ones flag a transcription or unit error. The check grades the raw-sum deviation:

```python
def check(stream, basis, registry=None) -> QCResult:
    raw_sum = stream.raw_mol_sum() if basis == "mol" else stream.raw_wt_sum()
    deviation = raw_sum - 100.0
    severity = grade(deviation, review_at, fail_at)
```

`basis` selects `stream.raw_mol_sum()` or `stream.raw_wt_sum()` (both defined on `CompositionStream` in `pvt/core/composition.py`). The signed deviation is preserved in `value`/`message` (so a report can tell over- from under-normalized), but `grade()` bands on its magnitude.

Default threshold band: **review at 0.5, fail at 2.0** (percentage points away from 100).

## 9.3 mw_consistency

Module: `pvt/qc/checks/mw_consistency.py`. Check ID: `mw_consistency_pct`.

A composition stream carrying both a mol% and a wt% basis implies two independent routes to the mixture molecular weight. This check grades how well they agree:

$$
mw\_consistency\_pct = \frac{MW_{mol} - MW_{wt}}{MW_{wt}} \times 100
$$

where `MW_mol` = `stream.mw_from_mol()` ($\sum z_i \cdot MW_i / \sum z_i$) and `MW_wt` = `stream.mw_from_wt()` ($100 / \sum (w_i / MW_i)$, on the normalized wt% basis), both from `pvt/core/composition.py`.

```python
def check(stream, registry=None) -> QCResult:
    pct = stream.mw_consistency_pct()
    severity = grade(pct, review_at, fail_at)
```

If a stream carries only one basis (mol% or wt%, not both), `mw_from_mol()`/`mw_from_wt()` raises `InputValidationError` and this check cannot run at all; see 8.7 for how the UI handles that.

Default threshold band: **review at 5.0%, fail at 10.0%**.

## 9.4 hoffman_crump

Module: `pvt/qc/checks/hoffman_crump.py`. Check ID: `hoffman_r2`.

For every component present, with a positive mole fraction, in **both** the gas and liquid streams of a flash, the classic Hoffman (1953) / Crump K-value consistency plot forms one point. A thermodynamically consistent K-value set falls on (nearly) a single straight line across all components; this check fits that line by ordinary least squares and grades its $R^2$.

### The b-factor and F-factor equations

For each qualifying component $i$, with vapor mole fraction $y_i$ and liquid mole fraction $x_i$:

$$
K_i = \frac{y_i}{x_i}
$$

$$
b_i = \frac{\log_{10}(P_{c,i} / 14.7)}{1/T_{b,i} - 1/T_{c,i}}
$$

$$
F_i = b_i \left( \frac{1}{T_{b,i}} - \frac{1}{T_R} \right)
$$

$$
y\text{-axis value} = \log_{10}(K_i \cdot P)
$$

where $T_{b,i}$, $P_{c,i}$, $T_{c,i}$ are the component's boiling point, critical pressure, and critical temperature (from the `Component` records in the active `ComponentLibrary`), and $T_R$ is the flash temperature in Rankine (`u.f_to_r(t_f)`). $F_i$ (the code's `f_factor`) is the crossplot x-axis; $\log_{10}(K_i P)$ (the code's `log10_kp`) is the y-axis. The engine implementation:

```python
b = math.log10(component.pc_psia / _HOFFMAN_P_ATM) / (
    1.0 / component.tb_r - 1.0 / component.tc_r
)
f_factor = b * (1.0 / component.tb_r - 1.0 / t_r)
log10_kp = math.log10(k * p_psia)
```

### The 14.7 Hoffman convention constant

```python
_HOFFMAN_P_ATM = 14.7
```

This is the reference pressure baked into the classic b-factor correlation. It is deliberately **not** `pvt.core.constants.P_STD_PSIA` (14.73, the ADRIC lab volumetric standard) and **not** `P_ATM_PSIA` (14.696, the gas-constant / psig-to-psia basis); it is the older, rounder reference pressure the original correlation was published with. Using either engine constant in its place would shift every b-factor by a fraction of a percent, so `_HOFFMAN_P_ATM` is kept module-local rather than added to `pvt.core.constants`, it belongs to this one correlation, not to the engine's general unit system.

### R-squared grading, and the pending-calibration note

`ThresholdRegistry.get("hoffman_r2")` returns an **R-squared floor** pair `(review_r2, fail_r2)`, the default `(0.98, 0.95)` reads "R-squared $\ge$ 0.98 is PASS, R-squared $\ge$ 0.95 is REVIEW, below that is FAIL", because that is how an engineer specifies acceptance on this plot. `grade()` itself only understands "smaller deviation is better" bands, so `check()` converts:

```python
deviation = 1.0 - r_squared
severity = grade(deviation, review_at=1.0 - review_r2, fail_at=1.0 - fail_r2)
```

The default thresholds (0.98, 0.95) are, unlike every other entry in `ThresholdRegistry.DEFAULTS`, **not** transcribed from an ADRIC house convention. The source PVT-check sheets show this crossplot visually with no numeric $R^2$ gate of their own, so this default is proposed by engineering judgment, configurable via `registry.override`, pending Swej calibration.

### The fewer-than-2-component typed error

Fitting a line needs at least 2 points. `_fit_least_squares` raises `InputValidationError` (not a raw `ZeroDivisionError`) in three degenerate cases:

- Fewer than 2 qualifying components (present, with a positive mole fraction, in both streams):
  ```
  Hoffmann-Crump QC needs at least 2 components present in both streams (found <n>)
  ```
- All qualifying components share the same F-factor (`ss_xx == 0`, the slope's denominator):
  ```
  Hoffmann-Crump QC: all qualifying components share the same F-factor (degenerate fit, cannot compute a slope)
  ```
- All qualifying components share the same $\log_{10}(K \cdot P)$ (`ss_tot == 0`, the $R^2$ denominator):
  ```
  Hoffmann-Crump QC: all qualifying components share the same log10(K*P) (degenerate fit, cannot compute R²)
  ```

`check()` returns a `HoffmanResult` (points, slope, intercept, r_squared, qc) rather than a bare `QCResult`, so callers can also plot the fitted line.

## 9.5 gor_actual_vs_target

This check is **not** a module under `pvt/qc/checks/`; it is implemented inline inside `pvt.experiments.recombination.loading.verify_actual_gor` (`pvt/experiments/recombination/loading.py`), using the same `QCResult`/`grade`/`ThresholdRegistry` contract as every other check. Check ID: `gor_actual_vs_target_pct`.

`verify_actual_gor` runs the cylinder-loading bookkeeping (`plan_loading`) in reverse: given the oil and gas volumes actually metered into the transfer cylinder, it recovers the as-loaded GOR and grades its deviation from the target GOR.

$$
n_{actual} = \frac{V_{gas,actual} \cdot P_{load}}{Z_{load} \cdot R \cdot T_{load}}
\qquad
V_{std} = n_{actual} \cdot Z_{std} \cdot R \cdot \frac{T_{std}}{P_{std}}
$$

$$
STO_{actual} = V_{oil,actual} \cdot \frac{\rho_{load}}{\rho_{60F}}
\qquad
GOR = \frac{V_{std}}{STO_{actual}} \cdot \frac{CC_{STB}}{CC_{SCF}}
$$

$$
dev\_pct = \frac{GOR - GOR_{target}}{GOR_{target}} \times 100
$$

```python
check_id = "gor_actual_vs_target_pct"
review_at, fail_at = registry.get(check_id)
severity = grade(dev_pct, review_at, fail_at)
```

Pressure basis note: `P_load_psia = psig + 14.73` (`constants.P_STD_PSIA`), not `psig + 14.696` (`constants.P_ATM_PSIA`), because the Loading_Volumes sheet's gauge-to-absolute formulas add the lab volumetric standard, not the atmosphere/gas-constant standard used elsewhere for psig-to-psia conversions.

Default threshold band: **review at 5.0%, fail at 10.0%**.

## 9.6 ThresholdRegistry Defaults

Full table, `pvt/qc/engine.py`, `ThresholdRegistry.DEFAULTS`:

| check_id | review_at | fail_at | Provenance | Implemented? |
|---|---|---|---|---|
| `composition_sum` | 0.5 | 2.0 | ADRIC house convention | Yes, `composition_normalization` |
| `mass_balance_pct` | 2.0 | 3.0 | ADRIC house convention | No check module yet |
| `molar_balance_pct` | 2.0 | 3.0 | ADRIC house convention | No check module yet |
| `z_deviation_pct` | 2.0 | 5.0 | ADRIC house convention | No check module yet |
| `density_rsd_pct` | 0.5 | 1.0 | ADRIC house convention | No check module yet |
| `viscosity_vs_sim_pct` | 2.0 | 5.0 | ADRIC house convention | No check module yet |
| `mmp_mass_balance_pct` | 5.0 | 5.0 | ADRIC house convention | No check module yet |
| `gor_actual_vs_target_pct` | 5.0 | 10.0 | ADRIC house convention | Yes, `pvt.experiments.recombination.loading.verify_actual_gor` |
| `mw_consistency_pct` | 5.0 | 10.0 | ADRIC house convention | Yes, `mw_consistency` |
| `hoffman_r2` | 0.98 | 0.95 | Engineering judgment, pending Swej calibration (R²-floor semantics, not a deviation band) | Yes, `hoffman_crump` |

Every threshold not marked "pending Swej calibration" is transcribed from ADRIC house conventions; `hoffman_r2` is the sole documented exception, because the source PVT-check sheets show the Hoffman-Crump crossplot visually with no numeric acceptance gate of their own.

## 9.7 How Pages Surface QC

### The pill

`ui/common/components.py` renders one `QCResult` as a colored-dot pill:

```python
_QC_COLORS = {
    "PASS": TOKENS["qc_green"],    # #38a169
    "REVIEW": TOKENS["qc_amber"],  # #dd9a0a
    "FAIL": TOKENS["qc_red"],      # #e53e3e
}

def qc_pill(result: QCResult) -> None:
    color = _QC_COLORS[result.severity.value]
    # colored dot + check_id (bold) + message (muted, smaller)
```

`qc_panel(results)` renders a stack of pills, one per `QCResult`. Both the Flash Separation page (`ui/pages/flash_page.py`) and the Recombination page (`ui/pages/recombination_page.py`) call `qc_panel` under a bold `**Composition QC**` / `**Actual GOR QC**` markdown label.

### Captions and warnings for skipped checks

The two pages differ in how granularly they surface a skipped check, and both differences trace directly to which `InputValidationError` is being caught.

**Flash page** (`ui/pages/flash_page.py`): the six composition checks (gas/oil mol%/wt% normalization, gas/oil `mw_consistency`) are run **independently**, each in its own `try`/`except InputValidationError`, rather than as one list comprehension. This matters because a mol-only manual-entry composition (no wt% at all) makes `mw_consistency` raise `InputValidationError` (it needs both bases); catching that per-check, rather than around the whole batch, means the other five checks (including the Hoffmann-Crump crossplot, which only needs mol%) still run and render. A skipped individual check renders a small caption instead of vanishing silently:

```python
except InputValidationError as exc:
    st.caption(f"{label}: skipped — {'; '.join(exc.errors)}")
```

The Hoffmann-Crump section (labelled `**Hoffmann-Crump K-value Consistency**` in the UI, note the UI spells it with a double n where the module `hoffman_crump.py` and its `check_id`/`HoffmanResult` spell it with one) has its own precheck: if fewer than 2 components overlap between the gas and oil streams, `st.warning("Hoffmann-Crump QC skipped: fewer than 2 components present in both streams.")` is shown up front. Beyond that precheck, any other `InputValidationError` from `hoffman_crump.check` (including the degenerate-fit cases) is caught and shown the same way:

```python
except InputValidationError as exc:
    st.warning("Hoffmann-Crump QC skipped: " + "; ".join(exc.errors))
```

When it succeeds, the pill for `hoffman.qc` renders, followed by an `st.scatter_chart` of the observed vs. fitted crossplot points.

**Recombination page** (`ui/pages/recombination_page.py`): the two composition-normalization checks (STO mol%, gas mol%) are wrapped in **one** `try`/`except`, so a failure skips the whole `**Composition QC**` block with a single warning:

```python
except InputValidationError as exc:
    st.warning("Composition QC skipped: " + "; ".join(exc.errors))
```

`mw_consistency` is not run on this page at all, not even inside a try/except, because the LiveOil v4.1 importer only reads the Mol% (INPUT) column (block C, section 8.4); the resulting streams never carry a wt% basis, so the check would always raise. The code comment on this page notes it is "skipped entirely rather than caught-and-hidden on every single run."

The loading plan and actual-GOR verification are similarly guarded, but with `except (InputValidationError, ZeroDivisionError)`, since `plan_loading`/`verify_actual_gor` can also divide by a caller-supplied zero (e.g. a target GOR of 0):

```python
except (InputValidationError, ZeroDivisionError) as exc:
    st.warning(f"Loading plan unavailable: {exc}")
```

The verify-GOR `QCResult`, once computed, renders through `qc_panel([verify_qc])` under `**Actual GOR QC**`, and is appended to the same `qc_results` list that feeds the report download (Chapter 10).
