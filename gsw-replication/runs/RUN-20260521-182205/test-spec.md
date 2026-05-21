# Test Spec — RUN-20260521-182205

## Task Summary

Validate the output parquet file `data/gsw_yield_curve.parquet` against the oracle `validation/validation_oracle.parquet`. All nine test cases below must pass. If any test fails, issue BLOCK with the specific failing test name, observed value, and expected value.

Tester MUST NOT modify any source files in `src/` or any other target repo file. Tester reads only; builder fixes on BLOCK.

---

## File Paths

```python
import pandas as pd

ORACLE_PATH = "validation/validation_oracle.parquet"   # read-only reference
OUTPUT_PATH = "data/gsw_yield_curve.parquet"           # the artifact under test

ORACLE = pd.read_parquet(ORACLE_PATH)
OUTPUT = pd.read_parquet(OUTPUT_PATH)
```

Absolute paths for reference:
- Oracle: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/GSW Replication/validation/validation_oracle.parquet`
- Output: `<target_repo_root>/data/gsw_yield_curve.parquet`

---

## Test File

**Location**: `tests/test_gsw_dataset.py` in the target repo.

Tester creates this file. The test file must use `pytest` conventions and import from the paths above. Tester runs the tests from the target repo root.

**Run command**:
```bash
cd <target_repo_root>
pip install -e ".[dev]" --quiet
pytest tests/test_gsw_dataset.py -v
```

---

## Test Cases

### Test 1: Schema — Column Names and Dtypes

```python
def test_schema():
    assert list(OUTPUT.columns) == ["ds", "unique_id", "y"], \
        f"Expected columns ['ds', 'unique_id', 'y'], got {list(OUTPUT.columns)}"
    assert pd.api.types.is_datetime64_any_dtype(OUTPUT["ds"]), \
        f"Expected ds to be datetime64, got {OUTPUT['ds'].dtype}"
    assert OUTPUT["unique_id"].dtype == object, \
        f"Expected unique_id to be object/string, got {OUTPUT['unique_id'].dtype}"
    assert pd.api.types.is_float_dtype(OUTPUT["y"]), \
        f"Expected y to be float64, got {OUTPUT['y'].dtype}"
```

**Pass condition**: OUTPUT has exactly 3 columns in order `ds`, `unique_id`, `y`; ds is datetime64; unique_id is object; y is float64.

---

### Test 2: unique_id Values — Exactly SVENY01 Through SVENY30

```python
def test_unique_id_values():
    expected_ids = [f"SVENY{i:02d}" for i in range(1, 31)]
    actual_ids = sorted(OUTPUT["unique_id"].unique())
    assert actual_ids == expected_ids, \
        f"unique_id mismatch. Expected {expected_ids}, got {actual_ids}"
```

**Pass condition**: Exactly 30 unique_id values, sorted as SVENY01, SVENY02, ..., SVENY30. No extras, no missing.

---

### Test 3: No Duplicate (ds, unique_id) Pairs

```python
def test_no_duplicates():
    dup_count = OUTPUT.duplicated(subset=["ds", "unique_id"]).sum()
    assert dup_count == 0, \
        f"Found {dup_count} duplicate (ds, unique_id) rows in OUTPUT"
```

**Pass condition**: Zero duplicate pairs.

---

### Test 4: No NaN Values in Any Column

```python
def test_no_nans():
    nan_counts = OUTPUT.isna().sum()
    assert nan_counts.sum() == 0, \
        f"Found NaN values: {nan_counts[nan_counts > 0].to_dict()}"
```

**Pass condition**: No NaN in ds, unique_id, or y.

---

### Test 5: Units Check — Values in Percent

```python
def test_units_are_percent():
    assert OUTPUT["y"].max() < 30.0, \
        f"y.max() = {OUTPUT['y'].max():.4f} — expected < 30.0 (values should be in percent, not decimal)"
    assert OUTPUT["y"].min() > -5.0, \
        f"y.min() = {OUTPUT['y'].min():.4f} — expected > -5.0 (values should be in percent)"
```

**Pass condition**: All y values are in the range (-5, 30) percent. If values were in decimal form (e.g., 0.035 instead of 3.5), the max would be ~0.20 which would fail the max < 30 check — but more importantly, the oracle alignment test (Test 7) would catch that immediately. This test also guards against sign errors and scaling errors.

---

### Test 6: Date Range Coverage

```python
def test_date_range():
    min_ds = OUTPUT["ds"].min()
    max_ds = OUTPUT["ds"].max()
    assert min_ds <= pd.Timestamp("1961-06-14"), \
        f"OUTPUT starts at {min_ds.date()} — expected <= 1961-06-14 (first FEDS200628 date)"
    assert max_ds >= pd.Timestamp("2025-01-01"), \
        f"OUTPUT ends at {max_ds.date()} — expected >= 2025-01-01 (must cover at least through 2025)"
```

**Pass condition**: Dataset starts on or before 1961-06-14 (the first FEDS200628 date) and extends through at least January 1, 2025.

---

### Test 7: Oracle Alignment — Sample-Based Spot Check (KEY TEST)

This is the primary correctness test. For a sample of oracle rows, verify that OUTPUT has a matching (ds, unique_id) pair with a yield value within 1 basis point (0.01 percent).

```python
def test_oracle_alignment():
    # Sample every 100th oracle row to cover the full date/tenor space
    sample = ORACLE.iloc[::100].copy()
    
    # Merge sample against OUTPUT on (ds, unique_id)
    merged = sample.merge(
        OUTPUT,
        on=["ds", "unique_id"],
        how="left",
        suffixes=("_oracle", "_output"),
    )
    
    # Check that all sample rows have a match in OUTPUT
    missing = merged["y_output"].isna().sum()
    assert missing == 0, \
        f"{missing} oracle sample rows have no matching row in OUTPUT. " \
        f"Missing examples: {merged[merged['y_output'].isna()][['ds', 'unique_id', 'y_oracle']].head(5).to_string()}"
    
    # Check that matched values are within 1 basis point (0.01 percent)
    abs_diff = (merged["y_output"] - merged["y_oracle"]).abs()
    max_diff = abs_diff.max()
    violations = (abs_diff >= 0.01).sum()
    assert violations == 0, \
        f"{violations} oracle sample rows have |y_output - y_oracle| >= 0.01 percent. " \
        f"Max absolute difference: {max_diff:.6f}. " \
        f"Worst offenders: {merged.loc[abs_diff >= 0.01, ['ds', 'unique_id', 'y_oracle', 'y_output']].head(5).to_string()}"
```

**Pass condition**: For all sampled oracle rows, OUTPUT has a matching (ds, unique_id) pair, and the absolute difference in y is less than 0.01 (1 basis point in percent terms).

**Note on sample**: `ORACLE.iloc[::100]` samples approximately every 100th row, yielding ~3,794 sample rows covering the full history and tenor range. This is sufficient to detect systematic errors while being fast to run.

---

### Test 8: Row Count Plausibility

```python
def test_row_count():
    oracle_rows = len(ORACLE)
    output_rows = len(OUTPUT)
    assert output_rows >= 350_000, \
        f"OUTPUT has {output_rows:,} rows — expected at least 350,000"
    # OUTPUT should be >= oracle rows because it may include more recent dates
    # (oracle was generated at a fixed point in time; OUTPUT is from live download)
    # We allow OUTPUT to be smaller than oracle if the Fed's data lags briefly,
    # but not by more than 5,000 rows (roughly ~167 days × 30 tenors)
    gap = oracle_rows - output_rows
    assert gap <= 5_000, \
        f"OUTPUT ({output_rows:,} rows) is {gap:,} rows fewer than oracle ({oracle_rows:,} rows). " \
        f"This suggests a data truncation problem."
```

**Pass condition**: OUTPUT has at least 350,000 rows, and is not more than 5,000 rows fewer than the oracle (to allow for minor timing differences in live data).

---

### Test 9: All 30 Tenors Present Across Multiple Date Ranges

```python
def test_tenors_across_history():
    """Verify that recent dates have all 30 tenors, and early dates have fewer."""
    recent_date = pd.Timestamp("2020-01-02")
    recent_data = OUTPUT[OUTPUT["ds"] >= recent_date]
    recent_tenors = sorted(recent_data["unique_id"].unique())
    expected_all = [f"SVENY{i:02d}" for i in range(1, 31)]
    assert recent_tenors == expected_all, \
        f"For dates >= 2020-01-02, expected all 30 tenors. Got: {recent_tenors}"
    
    early_date_end = pd.Timestamp("1965-12-31")
    early_data = OUTPUT[OUTPUT["ds"] <= early_date_end]
    early_tenors = sorted(early_data["unique_id"].unique())
    # Before Aug 1971, only up to 7 years → SVENY01-SVENY07 only
    assert "SVENY30" not in early_tenors, \
        f"SVENY30 should not be present for dates <= 1965-12-31, but found in early data"
    assert "SVENY01" in early_tenors, \
        f"SVENY01 should be present for dates <= 1965-12-31"
```

**Pass condition**: Recent dates (post-2020) have all 30 tenors; early dates (pre-1966) do NOT have SVENY30 but DO have SVENY01.

---

## Complete Test File

Tester should write `tests/test_gsw_dataset.py` with the following structure:

```python
"""
Test suite for GSW yield curve dataset.
Validates data/gsw_yield_curve.parquet against validation/validation_oracle.parquet.
"""
import pytest
import pandas as pd

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
ORACLE_PATH = "validation/validation_oracle.parquet"
OUTPUT_PATH = "data/gsw_yield_curve.parquet"


@pytest.fixture(scope="module")
def oracle():
    return pd.read_parquet(ORACLE_PATH)


@pytest.fixture(scope="module")
def output():
    return pd.read_parquet(OUTPUT_PATH)


# ---------------------------------------------------------------------------
# Test 1: Schema
# ---------------------------------------------------------------------------
def test_schema(output):
    assert list(output.columns) == ["ds", "unique_id", "y"], \
        f"Expected columns ['ds', 'unique_id', 'y'], got {list(output.columns)}"
    assert pd.api.types.is_datetime64_any_dtype(output["ds"]), \
        f"Expected ds to be datetime64, got {output['ds'].dtype}"
    assert output["unique_id"].dtype == object, \
        f"Expected unique_id to be object/string, got {output['unique_id'].dtype}"
    assert pd.api.types.is_float_dtype(output["y"]), \
        f"Expected y to be float64, got {output['y'].dtype}"


# ---------------------------------------------------------------------------
# Test 2: unique_id values
# ---------------------------------------------------------------------------
def test_unique_id_values(output):
    expected_ids = [f"SVENY{i:02d}" for i in range(1, 31)]
    actual_ids = sorted(output["unique_id"].unique())
    assert actual_ids == expected_ids, \
        f"unique_id mismatch. Expected {expected_ids}, got {actual_ids}"


# ---------------------------------------------------------------------------
# Test 3: No duplicates
# ---------------------------------------------------------------------------
def test_no_duplicates(output):
    dup_count = output.duplicated(subset=["ds", "unique_id"]).sum()
    assert dup_count == 0, \
        f"Found {dup_count} duplicate (ds, unique_id) rows in OUTPUT"


# ---------------------------------------------------------------------------
# Test 4: No NaN values
# ---------------------------------------------------------------------------
def test_no_nans(output):
    nan_counts = output.isna().sum()
    assert nan_counts.sum() == 0, \
        f"Found NaN values: {nan_counts[nan_counts > 0].to_dict()}"


# ---------------------------------------------------------------------------
# Test 5: Units are in percent
# ---------------------------------------------------------------------------
def test_units_are_percent(output):
    assert output["y"].max() < 30.0, \
        f"y.max() = {output['y'].max():.4f} — expected < 30.0 (values should be in percent)"
    assert output["y"].min() > -5.0, \
        f"y.min() = {output['y'].min():.4f} — expected > -5.0"


# ---------------------------------------------------------------------------
# Test 6: Date range coverage
# ---------------------------------------------------------------------------
def test_date_range(output):
    min_ds = output["ds"].min()
    max_ds = output["ds"].max()
    assert min_ds <= pd.Timestamp("1961-06-14"), \
        f"OUTPUT starts at {min_ds.date()} — expected <= 1961-06-14"
    assert max_ds >= pd.Timestamp("2025-01-01"), \
        f"OUTPUT ends at {max_ds.date()} — expected >= 2025-01-01"


# ---------------------------------------------------------------------------
# Test 7: Oracle alignment (sample-based spot check — KEY TEST)
# ---------------------------------------------------------------------------
def test_oracle_alignment(oracle, output):
    sample = oracle.iloc[::100].copy()

    merged = sample.merge(
        output,
        on=["ds", "unique_id"],
        how="left",
        suffixes=("_oracle", "_output"),
    )

    missing = merged["y_output"].isna().sum()
    assert missing == 0, (
        f"{missing} oracle sample rows have no matching row in OUTPUT. "
        f"Missing examples:\n{merged[merged['y_output'].isna()][['ds', 'unique_id', 'y_oracle']].head(5).to_string()}"
    )

    abs_diff = (merged["y_output"] - merged["y_oracle"]).abs()
    max_diff = abs_diff.max()
    violations = (abs_diff >= 0.01).sum()
    assert violations == 0, (
        f"{violations} oracle sample rows have |y_output - y_oracle| >= 0.01 percent. "
        f"Max absolute difference: {max_diff:.6f}. "
        f"Worst offenders:\n{merged.loc[abs_diff >= 0.01, ['ds', 'unique_id', 'y_oracle', 'y_output']].head(5).to_string()}"
    )


# ---------------------------------------------------------------------------
# Test 8: Row count plausibility
# ---------------------------------------------------------------------------
def test_row_count(oracle, output):
    oracle_rows = len(oracle)
    output_rows = len(output)
    assert output_rows >= 350_000, \
        f"OUTPUT has {output_rows:,} rows — expected at least 350,000"
    gap = oracle_rows - output_rows
    assert gap <= 5_000, (
        f"OUTPUT ({output_rows:,} rows) is {gap:,} rows fewer than oracle ({oracle_rows:,} rows). "
        f"This suggests a data truncation problem."
    )


# ---------------------------------------------------------------------------
# Test 9: Tenors across history
# ---------------------------------------------------------------------------
def test_tenors_across_history(output):
    recent_date = pd.Timestamp("2020-01-02")
    recent_data = output[output["ds"] >= recent_date]
    recent_tenors = sorted(recent_data["unique_id"].unique())
    expected_all = [f"SVENY{i:02d}" for i in range(1, 31)]
    assert recent_tenors == expected_all, \
        f"For dates >= 2020-01-02, expected all 30 tenors. Got: {recent_tenors}"

    early_date_end = pd.Timestamp("1965-12-31")
    early_data = output[output["ds"] <= early_date_end]
    early_tenors = sorted(early_data["unique_id"].unique())
    assert "SVENY30" not in early_tenors, \
        f"SVENY30 should not be present for dates <= 1965-12-31"
    assert "SVENY01" in early_tenors, \
        f"SVENY01 should be present for dates <= 1965-12-31"
```

---

## BLOCK Conditions

Tester MUST issue BLOCK (in `audit.md`) if ANY of the following occur:

| Condition | Test | Action |
|---|---|---|
| Output file does not exist | Pre-test | BLOCK immediately — builder did not produce the artifact |
| Oracle file does not exist | Pre-test | BLOCK immediately — setup error, report to leader |
| Wrong column names or order | Test 1 | BLOCK — builder schema error |
| Wrong dtypes | Test 1 | BLOCK — builder dtype enforcement failed |
| Missing or extra unique_id values | Test 2 | BLOCK — builder column selection error |
| Duplicate rows | Test 3 | BLOCK — builder sort/dedup error |
| NaN values remain | Test 4 | BLOCK — builder dropna failed |
| y values not in percent | Test 5 | BLOCK — builder unit/scaling error |
| Date range too short | Test 6 | BLOCK — builder truncated the data |
| Oracle alignment fails | Test 7 | BLOCK — values mismatch; most critical failure |
| Row count too low | Test 8 | BLOCK — data truncation |
| Historical tenor pattern wrong | Test 9 | BLOCK — NaN policy or reshape error |

Tester MUST NOT modify any source files to fix failures. Tester MUST report the specific test that failed with the observed vs expected values in `audit.md` so that builder can diagnose and fix.

---

## `audit.md` Format

```markdown
# Audit — RUN-20260521-182205

## Verdict: [PASS | BLOCK]

## Test Results

| Test | Status | Observed | Expected |
|---|---|---|---|
| test_schema | PASS/FAIL | ... | ... |
| test_unique_id_values | PASS/FAIL | ... | ... |
| test_no_duplicates | PASS/FAIL | ... | ... |
| test_no_nans | PASS/FAIL | ... | ... |
| test_units_are_percent | PASS/FAIL | ... | ... |
| test_date_range | PASS/FAIL | ... | ... |
| test_oracle_alignment | PASS/FAIL | ... | ... |
| test_row_count | PASS/FAIL | ... | ... |
| test_tenors_across_history | PASS/FAIL | ... | ... |

## Full pytest Output

[paste full pytest -v output here]

## BLOCK Reason (if BLOCK)

[specific test name, observed value, expected value, recommendation for builder]
```

---

## Pipeline Isolation Note

This test-spec.md is the ONLY artifact tester receives from planner. Tester does NOT receive spec.md or implementation.md. Tester validates the final merged artifact (the parquet file), not the source code. Tester reads the oracle freely; builder never does.
