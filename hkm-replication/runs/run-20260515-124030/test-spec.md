# Test Specification: HKM (2017) JFE Tables 2 & 3 Replication

**Run**: run-20260515-124030
**For**: tester (test pipeline only)
**Source paper**: He, Kelly & Manela (2017), *Journal of Financial Economics* 126, pp. 1–35
**Revision**: SECOND DISPATCH — corrected targets (JFE Table 2 = size comparison; JFE Table 3 = pairwise correlations)

---

## 0. Scope

This document specifies validation for the HKM replication Python package. Tests verify:
1. Unit correctness of individual data modules (η construction logic, ratio computation, correlation logic)
2. Numerical accuracy of JFE Table 2 cells (size comparison ratios) within specified tolerances
3. Numerical accuracy of JFE Table 3 cells (pairwise correlations) within specified tolerances
4. Code quality: mypy type checking, ruff linting

No implementation details (algorithm steps, function internals) are referenced. Tester verifies observable behaviors only.

---

## 1. Validation Commands

Run from the repo root (target repo path: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication`):

```bash
# Install package in editable mode with dev dependencies
pip install -e ".[dev]"

# Linting
ruff check hkm/ tests/

# Type checking
mypy hkm/ --ignore-missing-imports --strict

# Unit and integration tests
pytest tests/ -v --tb=short

# BLOCK criteria: any of the above exits with non-zero return code
```

---

## 2. Behavioral Contracts

The implementation MUST satisfy all of the following observable behaviors:

**B1**: `hkm.data.wrds_connect.get_engine()` returns a live SQLAlchemy engine when `~/.pgpass` is configured, or raises `ConnectionError` with a descriptive message when credentials are missing.

**B2**: `hkm.data.dealers.get_active_dealers(date, us_only=True)` returns a non-empty list for any date between 1970-01-01 and 2012-12-31.

**B3**: `hkm.data.dealers.get_active_dealers(date, us_only=True)` returns entries where all have `is_us_based = True`.

**B4**: `hkm.data.intermediary.build_capital_ratio()` returns a DataFrame with 172 non-null rows for the 1970Q1–2012Q4 period (one per quarter), assuming WRDS access.

**B5**: Every value in the `eta` column of `build_capital_ratio()` output is strictly between 0 and 1 (exclusive).

**B6**: `hkm.data.intermediary.build_capital_factor(eta_series)` returns a Series of the same length as the input, with the first element NaN and all remaining elements finite.

**B7**: `hkm.tables.table2.compute_table2()` returns a DataFrame with shape (3, 12).

**B8**: Every cell value in `compute_table2()` output is strictly between 0.0 and 1.0 (exclusive) — ratios must be valid proportions.

**B9**: `hkm.tables.table3.compute_table3()` returns a tuple of two DataFrames.

**B10**: Panel A of `compute_table3()` has the diagonal values (η vs. η, book_η vs. book_η, AEM vs. AEM) equal to 1.0 (within ±0.001).

**B11**: Panel B of `compute_table3()` has the diagonal values (η^Δ vs. η^Δ, book capital factor vs. book capital factor, AEM LevFac vs. AEM LevFac) equal to 1.0 (within ±0.001).

**B12**: `hkm.utils.log_change(series)` returns a Series with the first element NaN and subsequent elements equal to log(x_t / x_{t-1}).

**B13**: `hkm.utils.to_quarterly(series, method="last")` returns a Series with quarterly frequency (DatetimeIndex with period 'Q' or equivalent quarter-end dates).

**B14**: `hkm.data.compustat.get_balance_sheet()` returns a DataFrame where `book_debt` = `atq − ceqq` for every row (within floating-point precision).

**B15**: `hkm.data.crsp.get_market_equity()` returns a DataFrame where all values in the `market_equity_k` column are strictly positive.

---

## 3. Unit Tests (no WRDS required)

These tests use synthetic data and do not require WRDS access. They must pass in any environment.

### 3.1 Capital Ratio Construction — Synthetic Data

**Test UT-1: Correct η formula**

Setup:
```python
import pandas as pd
import numpy as np

# Three synthetic primary dealers, one quarter
dates = pd.date_range("1985-03-31", periods=1, freq="QE")
me = np.array([100.0, 200.0, 300.0])   # market equity (arbitrary units)
bd = np.array([900.0, 800.0, 700.0])   # book debt (arbitrary units)
```

Expected:
```
η = (100 + 200 + 300) / (100 + 200 + 300 + 900 + 800 + 700)
  = 600 / 3000
  = 0.2000
```

Assert: The η construction logic, when given these inputs, produces exactly 0.20 (within ±1e-10).

**Test UT-2: AR(1) factor extraction**

Setup:
```python
np.random.seed(42)
n = 50
# Simulate AR(1) with ρ = 0.94
eta = np.zeros(n)
eta[0] = 0.06
for t in range(1, n):
    eta[t] = 0.005 + 0.94 * eta[t-1] + np.random.normal(0, 0.005)
eta_series = pd.Series(eta, index=pd.date_range("1970-03-31", periods=n, freq="QE"))
```

Expected behavior of `build_capital_factor(eta_series)`:
- Returns a Series of length 50
- First element is NaN
- Remaining 49 elements are finite (no NaN, no Inf)
- The estimated AR(1) coefficient should be within ±0.15 of 0.94 (large CI for small sample)

Assert all three conditions.

**Test UT-3: Ratio bounds**

Setup: Create a synthetic monthly DataFrame with PD aggregates and comparison group aggregates where PD aggregate is always less than comparison group aggregate (as must be true for Table 2).

Expected: All 12 resulting ratio cells are in (0.0, 1.0).

Assert: `(result > 0.0).all()` and `(result < 1.0).all()`.

**Test UT-4: log_change correctness**

Setup:
```python
series = pd.Series([100.0, 110.0, 99.0], index=pd.date_range("1970", periods=3, freq="QE"))
```

Expected:
```
result[0] = NaN
result[1] = log(110/100) ≈ 0.09531
result[2] = log(99/110) ≈ -0.10536
```

Assert: All three values within ±1e-8 of expected.

**Test UT-5: quarter_end correctness**

Setup: Input dates mid-quarter: `pd.Timestamp("1985-02-15")`, `pd.Timestamp("1985-05-01")`, `pd.Timestamp("1985-11-30")`.

Expected quarter ends: `1985-03-31`, `1985-06-30`, `1985-12-31`.

Assert exact date equality.

**Test UT-6: Book debt formula**

Setup: Synthetic Compustat row with `atq = 1000.0`, `ceqq = 150.0`.

Expected: `book_debt = 850.0`, `book_equity = 150.0`, `total_assets = 1000.0`.

Assert exact equality (floating point: within ±1e-10).

**Test UT-7: Pairwise correlation correctness**

Setup:
```python
np.random.seed(123)
x = pd.Series(np.random.normal(0, 1, 100))
y = 0.7 * x + np.sqrt(1 - 0.49) * np.random.normal(0, 1, 100)
```

Expected: Pearson correlation between x and y ≈ 0.70 (within ±0.10 for N=100 with seed 123).

Assert: The correlation computation in the table3 module matches `pd.Series.corr(other, method="pearson")`.

**Test UT-8: Dealer list completeness**

Assert: `get_active_dealers(pd.Timestamp("1995-03-31"), us_only=True)` returns at least 15 entries (the paper lists around 20+ active dealers in the mid-1990s period).

Assert: `get_active_dealers(pd.Timestamp("2008-09-30"), us_only=True)` does NOT include Lehman Brothers (Lehman's end date in Table A.1 is 9/22/2008 — before quarter end 9/30/2008).

Assert: `get_active_dealers(pd.Timestamp("2012-12-31"), us_only=True)` includes Goldman Sachs and JPMorgan Chase.

---

## 4. Integration Tests (WRDS required — skip if WRDS unavailable)

These tests require live WRDS access and are marked with `@pytest.mark.skipif(not WRDS_AVAILABLE, ...)`. Set `WRDS_AVAILABLE = True/False` via the `HKM_WRDS_AVAILABLE` environment variable.

### 4.1 CRSP Pull

**Test IT-1: Market equity pull for Goldman Sachs**

Pull market equity for Goldman Sachs Group (permno to be looked up from CRSP) for 2005Q4 (month ending December 2005).

Expected: Market equity (ME) for Goldman Sachs in Q4 2005 should be approximately $50–$80 billion (shares × price). This is a broad sanity check.

Assert: ME is in range [40e6, 120e6] (thousands of dollars = 40 billion to 120 billion dollars).

**Test IT-2: Compustat pull returns expected fields**

Pull balance sheet for Goldman Sachs gvkey for 2005.

Expected: DataFrame contains columns `[gvkey, datadate, atq, ceqq, book_debt, book_equity, total_assets]` with non-null values. `book_debt = atq − ceqq` within ±0.01.

Assert column existence and formula accuracy.

**Test IT-3: CRSP-Compustat link returns at least 100 records**

Assert: `get_crsp_compustat_link()` returns DataFrame with ≥ 100 rows and no null `permno` or `gvkey` values.

### 4.2 Capital Ratio

**Test IT-4: η series coverage**

Call `build_capital_ratio("1970-01-01", "2012-12-31")`.

Assert:
- Returns DataFrame with ≥ 170 rows (allowing for occasional missing quarters)
- All `eta` values in (0.02, 0.25) — consistent with Fig. 1 of the paper which shows η mostly between 4% and 15% (percentages: 0.04 to 0.15), with some spikes to 0.20
- `n_dealers` is at least 5 for all quarters

**Test IT-5: η^Δ factor — AR(1) coefficient**

Build η series from IT-4, then call `build_capital_factor()`.

Assert:
- Returns Series of same length as input
- The OLS-estimated AR(1) coefficient ρ is in [0.85, 1.00] (reference: paper states ρ ≈ 0.94)
- No NaN values except the first observation

### 4.3 Comparison Group Aggregates

**Test IT-6: BD sector aggregate is always >= PD aggregate**

For each quarter from 1970Q1 to 2012Q4, total assets of all broker-dealers (SIC 6211 or 6221) must be >= total assets of primary dealers alone.

Assert: The ratio (PD total assets) / (BD total assets) is in (0, 1] for every month.

**Test IT-7: Compustat aggregate — all firms > banks > broker-dealers**

For any given month, total assets of all Compustat firms >= total assets of all banks >= total assets of all broker-dealers.

Assert: ratio_PD/Cmpust < ratio_PD/Banks < ratio_PD/BD for total assets (i.e., the denominators are ordered as expected).

---

## 5. Table 2 Numerical Accuracy Tests

### Reference Values from JFE Table 2 (p. 7)

```python
TABLE2_REFERENCE = {
    "1960-2012": {
        ("total_assets", "BD"):     0.959,
        ("total_assets", "Banks"):  0.596,
        ("total_assets", "Cmpust."): 0.240,
        ("book_debt", "BD"):        0.960,
        ("book_debt", "Banks"):     0.602,
        ("book_debt", "Cmpust."):   0.280,
        ("book_equity", "BD"):      0.939,
        ("book_equity", "Banks"):   0.514,
        ("book_equity", "Cmpust."): 0.079,
        ("market_equity", "BD"):    0.911,
        ("market_equity", "Banks"): 0.435,
        ("market_equity", "Cmpust."): 0.026,
    },
    "1960-1990": {
        ("total_assets", "BD"):     0.927,
        ("total_assets", "Banks"):  0.635,
        ("total_assets", "Cmpust."): 0.286,
        ("book_debt", "BD"):        0.998,
        ("book_debt", "Banks"):     0.639,
        ("book_debt", "Cmpust."):   0.305,
        ("book_equity", "BD"):      0.908,
        ("book_equity", "Banks"):   0.568,
        ("book_equity", "Cmpust."): 0.095,
        ("market_equity", "BD"):    0.961,
        ("market_equity", "Banks"): 0.447,
        ("market_equity", "Cmpust."): 0.015,
    },
    "1990-2012": {
        ("total_assets", "BD"):     0.914,
        ("total_assets", "Banks"):  0.543,
        ("total_assets", "Cmpust."): 0.202,
        ("book_debt", "BD"):        0.916,
        ("book_debt", "Banks"):     0.550,
        ("book_debt", "Cmpust."):   0.240,
        ("book_equity", "BD"):      0.883,
        ("book_equity", "Banks"):   0.444,
        ("book_equity", "Cmpust."): 0.058,
        ("market_equity", "BD"):    0.848,
        ("market_equity", "Banks"): 0.419,
        ("market_equity", "Cmpust."): 0.039,
    },
}
```

### Test T2-1: Shape and Structure (WRDS required)

Call `compute_table2()`.

Assert:
- Shape is (3, 12)
- Index contains exactly `["1960-2012", "1960-1990", "1990-2012"]`
- Column MultiIndex has 4 level-0 values: `total_assets`, `book_debt`, `book_equity`, `market_equity`
- Each level-0 value has 3 level-1 sub-columns: `BD`, `Banks`, `Cmpust.`

### Test T2-2: All-period ratios within tolerance (WRDS required)

**Tolerance**: ±0.05 (5 percentage points) for all cells. This accounts for:
- Possible differences in the exact dealer-to-permno/gvkey mapping (manual lookup vs. exact paper mapping)
- Differences in Compustat data vintages
- Approximations in which quarters are included per sub-period

For each `(period, item, group)` combination, assert:
```
|computed_value − reference_value| ≤ 0.05
```

**Priority cells** (the primary acceptance test — tighter ±0.03 tolerance):
- `("1960-2012", "total_assets", "BD")` ≈ 0.959
- `("1960-2012", "book_debt", "BD")` ≈ 0.960
- `("1960-2012", "market_equity", "BD")` ≈ 0.911
- `("1990-2012", "total_assets", "BD")` ≈ 0.914

### Test T2-3: Sub-period ordering consistency

For each (item, group) combination, the ratios should not be wildly inconsistent across sub-periods. The 1960–2012 average should be approximately a weighted average of the two sub-periods.

Assert: For each (item, group):
- `|ratio_1960-2012 − (ratio_1960-1990 + ratio_1990-2012) / 2| ≤ 0.10`

---

## 6. Table 3 Numerical Accuracy Tests

### Reference Values from JFE Table 3 (p. 9)

**Panel A (levels)**:
```python
TABLE3_PANEL_A_REFERENCE = {
    # (row_variable, column_variable): correlation
    ("Market capital", "Market capital"):     1.00,
    ("Market capital", "Book capital"):       0.50,
    ("Market capital", "AEM leverage"):      -0.42,
    ("Book capital", "Market capital"):       0.50,
    ("Book capital", "Book capital"):         1.00,
    ("Book capital", "AEM leverage"):        -0.07,
    ("AEM leverage", "Market capital"):      -0.42,
    ("AEM leverage", "Book capital"):        -0.07,
    ("AEM leverage", "AEM leverage"):         1.00,
    ("E/P", "Market capital"):               -0.83,
    ("E/P", "Book capital"):                 -0.38,
    ("E/P", "AEM leverage"):                 -0.64,
    ("Unemployment", "Market capital"):      -0.63,
    ("Unemployment", "Book capital"):        -0.10,
    ("Unemployment", "AEM leverage"):        -0.33,
    ("GDP", "Market capital"):                0.18,
    ("GDP", "Book capital"):                  0.32,
    ("GDP", "AEM leverage"):                 -0.23,
    ("Financial conditions", "Market capital"): -0.48,
    ("Financial conditions", "Book capital"):   -0.53,
    ("Financial conditions", "AEM leverage"):   -0.19,
    ("Market volatility", "Market capital"):   -0.06,
    ("Market volatility", "Book capital"):     -0.31,
    ("Market volatility", "AEM leverage"):      0.33,
}

TABLE3_PANEL_B_REFERENCE = {
    # (row_variable, column_variable): correlation
    ("Market capital factor", "Market capital factor"):   1.00,
    ("Market capital factor", "Book capital factor"):     0.30,
    ("Market capital factor", "AEM leverage factor"):     0.14,
    ("Book capital factor", "Market capital factor"):     0.30,
    ("Book capital factor", "Book capital factor"):       1.00,
    ("Book capital factor", "AEM leverage factor"):      -0.06,
    ("AEM leverage factor", "Market capital factor"):     0.14,
    ("AEM leverage factor", "Book capital factor"):      -0.06,
    ("AEM leverage factor", "AEM leverage factor"):       1.00,
    ("Market excess return", "Market capital factor"):    0.78,
    ("Market excess return", "Book capital factor"):      0.10,
    ("Market excess return", "AEM leverage factor"):      0.15,
    ("E/P growth", "Market capital factor"):             -0.75,
    ("E/P growth", "Book capital factor"):               -0.10,
    ("E/P growth", "AEM leverage factor"):               -0.18,
    ("Unemployment growth", "Market capital factor"):    -0.05,
    ("Unemployment growth", "Book capital factor"):       0.12,
    ("Unemployment growth", "AEM leverage factor"):      -0.08,
    ("GDP growth", "Market capital factor"):              0.20,
    ("GDP growth", "Book capital factor"):                0.09,
    ("GDP growth", "AEM leverage factor"):                0.04,
    ("Financial conditions growth", "Market capital factor"): -0.38,
    ("Financial conditions growth", "Book capital factor"):   -0.29,
    ("Financial conditions growth", "AEM leverage factor"):   -0.06,
    ("Market volatility growth", "Market capital factor"):   -0.49,
    ("Market volatility growth", "Book capital factor"):     -0.18,
    ("Market volatility growth", "AEM leverage factor"):     -0.08,
}
```

### Test T3-1: Panel A structure (WRDS required)

Call `compute_table3()` and inspect `panel_a`.

Assert:
- panel_a has at least 8 rows and 3 columns
- Diagonal entries (η vs. η, book_η vs. book_η, AEM vs. AEM) equal 1.00 within ±0.001
- All values are in [−1.0, 1.0]

### Test T3-2: Panel B structure (WRDS required)

Assert:
- panel_b has at least 9 rows and 3 columns
- Diagonal entries equal 1.00 within ±0.001
- All values are in [−1.0, 1.0]

### Test T3-3: Panel A correlations within tolerance (WRDS required)

**Tolerance**: ±0.05 for all Panel A cells.

For each reference entry in `TABLE3_PANEL_A_REFERENCE`:
```
|computed − reference| ≤ 0.05
```

**Priority cells** (tighter ±0.03 tolerance — these are large and stable correlations):
- corr(η, E/P) ≈ −0.83
- corr(η, book_η) ≈ 0.50
- corr(η, AEM leverage) ≈ −0.42
- corr(η, Unemployment) ≈ −0.63

### Test T3-4: Panel B correlations within tolerance (WRDS required)

**Tolerance**: ±0.05 for all Panel B cells.

**Priority cells** (tighter ±0.03 tolerance):
- corr(η^Δ, market excess return) ≈ 0.78
- corr(η^Δ, E/P growth) ≈ −0.75
- corr(η^Δ, market vol growth) ≈ −0.49
- corr(η^Δ, book capital factor) ≈ 0.30

### Test T3-5: Sign consistency

For all Panel A and Panel B cells, the sign of the computed correlation must match the sign of the reference value. This is a weaker test than numerical accuracy and must hold even if magnitude tolerance is missed.

Exception: cells where |reference| ≤ 0.10 are excluded from this test (near-zero correlations may flip sign with small sample differences).

---

## 7. Code Quality Tests

### Test CQ-1: Ruff linting passes

```bash
ruff check hkm/ tests/
```

Assert: exits with return code 0 (no linting errors).

### Test CQ-2: Mypy type checking passes

```bash
mypy hkm/ --ignore-missing-imports --strict
```

Assert: exits with return code 0 (no type errors).

**Allowable exceptions**: The `--ignore-missing-imports` flag handles WRDS/psycopg2 stubs. No other mypy errors are permitted.

### Test CQ-3: Package importable

```python
import hkm
import hkm.data.wrds_connect
import hkm.data.crsp
import hkm.data.compustat
import hkm.data.intermediary
import hkm.data.macro
import hkm.data.dealers
import hkm.tables.table2
import hkm.tables.table3
import hkm.utils
```

Assert: All imports succeed without errors or warnings.

### Test CQ-4: No print statements in library code

Assert: No call to `print()` in any file under `hkm/` (library code must use `logging`, not `print`). This can be checked with a simple grep/AST scan.

---

## 8. BLOCK Criteria

Tester MUST issue BLOCK if any of the following conditions hold:

**BLOCK-1**: `ruff check` exits with non-zero return code (linting failures in library or test code).

**BLOCK-2**: `mypy` exits with non-zero return code (type errors).

**BLOCK-3**: Any unit test (UT-1 through UT-8) fails. These do not require WRDS and must always pass.

**BLOCK-4**: Package cannot be imported (Test CQ-3 fails).

**BLOCK-5** (if WRDS available): Any priority-cell numerical test (T2-2 priority cells, T3-3 priority cells, T3-4 priority cells) fails beyond tolerance.

**BLOCK-6** (if WRDS available): Any Table 2 ratio is outside [0, 1] — a ratio > 1 means PDs exceed the total sector, which is a logical impossibility.

**BLOCK-7** (if WRDS available): The η series from `build_capital_ratio()` contains any value outside (0, 0.5), or has fewer than 100 non-null observations over 1970–2012.

**BLOCK-8**: Test CQ-4 fails (library code uses print statements).

---

## 9. Data Availability Notes

| Test group | WRDS required? | Note |
|---|---|---|
| UT-1 through UT-8 | No | Synthetic data only |
| IT-1 through IT-7 | Yes | Live WRDS access to crsp and comp schemas |
| T2-1, T2-2, T2-3 | Yes | Full CRSP + Compustat pull required |
| T3-1 through T3-5 | Yes | Requires CRSP, Compustat, and macro data (FRED) |
| CQ-1 through CQ-4 | No | Code quality checks only |

If WRDS is unavailable, tester should:
1. Run all non-WRDS tests and confirm they pass.
2. Report: "WRDS integration tests skipped — unit tests passed."
3. Do NOT issue BLOCK solely due to WRDS unavailability.
4. Issue BLOCK if unit tests fail.

The `HKM_WRDS_AVAILABLE` environment variable controls skipping:
```python
import os
import pytest
WRDS_AVAILABLE = os.environ.get("HKM_WRDS_AVAILABLE", "false").lower() == "true"
```

---

## 10. Regression Scenario

If a future builder revision breaks existing functionality, the following regression test must catch it:

**RT-1**: After any change to `intermediary.py`, re-run UT-1 (η formula) and UT-2 (AR(1) factor). Both must pass.

**RT-2**: After any change to `dealers.py`, re-run UT-8 (dealer list completeness for 1995-03-31 and 2008-09-30 and 2012-12-31). All three assertions must pass.

**RT-3**: After any change to `utils.py`, re-run UT-4 (log_change) and UT-5 (quarter_end). Both must pass.
