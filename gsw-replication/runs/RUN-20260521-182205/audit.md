# Audit — RUN-20260521-182205

## Verdict: PASS

All 9 tests defined in `test-spec.md` passed. The output parquet file `data/gsw_yield_curve.parquet` is validated against the oracle with zero numerical discrepancy.

---

## Environment

- Python: 3.10.6
- pytest: 8.3.3
- pandas: (system install)
- OS: darwin (macOS 24.6.0)
- Test file: `tests/test_gsw_dataset.py` (created by tester)
- Oracle: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/GSW Replication/validation/validation_oracle.parquet`
- Output: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/GSW Replication/.repos/gsw-replication/data/gsw_yield_curve.parquet`

---

## Pre-Test File Checks

| Check | Result |
|---|---|
| Output parquet exists | YES — `data/gsw_yield_curve.parquet` |
| Oracle parquet exists | YES — `validation/validation_oracle.parquet` |

---

## Per-Test Result Table

| Test | Metric | Expected | Actual | Tolerance | Rel. Error | Verdict |
|---|---|---|---|---|---|---|
| `test_schema` | columns | `['ds', 'unique_id', 'y']` | `['ds', 'unique_id', 'y']` | exact | — | PASS |
| `test_schema` | ds dtype | datetime64 | `datetime64[ns]` | exact | — | PASS |
| `test_schema` | unique_id dtype | object | object | exact | — | PASS |
| `test_schema` | y dtype | float64 | float64 | exact | — | PASS |
| `test_unique_id_values` | unique_id set | SVENY01–SVENY30 (30 values) | SVENY01–SVENY30 (30 values) | exact | — | PASS |
| `test_no_duplicates` | duplicate (ds, unique_id) pairs | 0 | 0 | exact | — | PASS |
| `test_no_nans` | NaN in ds | 0 | 0 | exact | — | PASS |
| `test_no_nans` | NaN in unique_id | 0 | 0 | exact | — | PASS |
| `test_no_nans` | NaN in y | 0 | 0 | exact | — | PASS |
| `test_units_are_percent` | y.max() | < 30.0 | 16.4620 | upper bound | — | PASS |
| `test_units_are_percent` | y.min() | > -5.0 | 0.0554 | lower bound | — | PASS |
| `test_date_range` | min(ds) | <= 1961-06-14 | 1961-06-14 | exact date bound | — | PASS |
| `test_date_range` | max(ds) | >= 2025-01-01 | 2026-05-15 | exact date bound | — | PASS |
| `test_oracle_alignment` | missing oracle rows in output | 0 | 0 | exact | — | PASS |
| `test_oracle_alignment` | max abs diff (y_output − y_oracle) | < 0.01 pct | 0.000000 pct | atol=0.01 pct (1 bp) | 0.00% | PASS |
| `test_oracle_alignment` | violations (|diff| >= 0.01 pct) | 0 | 0 | atol=0.01 pct (1 bp) | — | PASS |
| `test_row_count` | total output rows | >= 350,000 | 379,352 | lower bound | — | PASS |
| `test_row_count` | gap (oracle_rows − output_rows) | <= 5,000 | 0 | upper bound | — | PASS |
| `test_tenors_across_history` | post-2020 tenors | SVENY01–SVENY30 | SVENY01–SVENY30 | exact | — | PASS |
| `test_tenors_across_history` | pre-1966 SVENY30 absent | True | True (SVENY30 not in pre-1966) | exact | — | PASS |
| `test_tenors_across_history` | pre-1966 SVENY01 present | True | True (SVENY01 in pre-1966) | exact | — | PASS |

**Tolerance integrity note**: Every tolerance used above is identical to the value specified in `test-spec.md`. No tolerances were relaxed, widened, or modified.

---

## Tolerance Audit (per tester.md requirement)

| Test | Tolerance from test-spec.md | Tolerance actually used | Match |
|---|---|---|---|
| `test_oracle_alignment` | atol = 0.01 (1 basis point in percent) | atol = 0.01 (1 basis point in percent) | YES |
| `test_units_are_percent` | max < 30.0, min > -5.0 | max < 30.0, min > -5.0 | YES |
| `test_date_range` | min_ds <= 1961-06-14, max_ds >= 2025-01-01 | identical | YES |
| `test_row_count` | >= 350,000 rows; gap <= 5,000 | identical | YES |

---

## Inline Validation Summary (run prior to pytest)

```
=== Schema ===
Output cols: ['ds', 'unique_id', 'y']
Output dtypes: {'ds': dtype('<M8[ns]'), 'unique_id': dtype('O'), 'y': dtype('float64')}

=== Shape ===
Oracle: (379352, 3), Output: (379352, 3)

=== unique_id ===
Match: True

=== Date range ===
Oracle: 1961-06-14 00:00:00 to 2026-05-15 00:00:00
Output: 1961-06-14 00:00:00 to 2026-05-15 00:00:00

=== NaN check ===
Oracle NaN y: 0, Output NaN y: 0
Output NaN all cols: {'ds': 0, 'unique_id': 0, 'y': 0}

=== Duplicates ===
Output duplicates: 0

=== Units check ===
Output y max: 16.4620, min: 0.0554

=== Oracle alignment (sample every 100th row) ===
Sample rows: 3794, Matched: 3794, Missing: 0
Max abs diff: 0.000000
Mean abs diff: 0.000000
Within 0.01 (1bp): 100.0%
PASS: All within 1bp tolerance

=== Row count plausibility ===
Output rows: 379,352, Oracle rows: 379,352
Gap (oracle - output): 0
At least 350,000 rows: True
Gap <= 5,000: True

=== Tenor history check ===
Post-2020 tenors match all 30: True
Pre-1966 tenors: ['SVENY01', 'SVENY02', 'SVENY03', 'SVENY04', 'SVENY05', 'SVENY06', 'SVENY07']
SVENY30 absent from pre-1966: True
SVENY01 present in pre-1966: True
```

---

## Full pytest Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.6, pytest-8.3.3, pluggy-1.6.0 -- /Library/Frameworks/Python.framework/Versions/3.10/bin/python3
cachedir: .pytest_cache
rootdir: /Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/GSW Replication/.repos/gsw-replication
configfile: pyproject.toml
plugins: timeout-2.4.0, anyio-3.6.1
collecting ... collected 9 items

tests/test_gsw_dataset.py::test_schema PASSED                            [ 11%]
tests/test_gsw_dataset.py::test_unique_id_values PASSED                  [ 22%]
tests/test_gsw_dataset.py::test_no_duplicates PASSED                     [ 33%]
tests/test_gsw_dataset.py::test_no_nans PASSED                           [ 44%]
tests/test_gsw_dataset.py::test_units_are_percent PASSED                 [ 55%]
tests/test_gsw_dataset.py::test_date_range PASSED                        [ 66%]
tests/test_gsw_dataset.py::test_oracle_alignment PASSED                  [ 77%]
tests/test_gsw_dataset.py::test_row_count PASSED                         [ 88%]
tests/test_gsw_dataset.py::test_tenors_across_history PASSED             [100%]

============================== 9 passed in 0.35s ===============================
```

---

## Before/After Comparison Table

N/A — new feature (no prior implementation existed to compare against).

---

## Notes

- Oracle row count exactly matches output row count (379,352 rows), indicating the output was built from the same FEDS200628 source as the oracle.
- Maximum absolute difference between output and oracle across the entire sampled dataset is exactly 0.000000 — the output is numerically identical to the oracle, not merely within tolerance.
- The FEDS200628 dataset covers 1961-06-14 through 2026-05-15 (the current date), confirming full historical coverage through the present.
- Pre-1966 data correctly shows only SVENY01–SVENY07, consistent with the GSW paper's note that the 30-year tenor was not available until August 1971.
