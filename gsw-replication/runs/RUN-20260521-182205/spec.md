# Spec — RUN-20260521-182205

## Task Summary

Implement a Python pipeline that downloads the Federal Reserve's FEDS200628 CSV (which contains pre-computed Nelson-Siegel-Svensson zero-coupon yields SVENY01–SVENY30), reshapes it from wide to long format, drops NaN rows, and writes a parquet file with columns `ds`, `unique_id`, `y`.

Builder MUST NOT access or read `validation/validation_oracle.parquet` at any point.

---

## Target Repository Layout

```
src/gsw_replication/
    __init__.py          (package init — may be empty or expose public API)
    download.py          (fetch FEDS200628 CSV from Fed website)
    transform.py         (wide → long reshape, NaN drop, schema enforcement)
    build.py             (orchestrate: download + transform → write parquet)
data/
    gsw_yield_curve.parquet   (primary deliverable — created at runtime, NOT committed to git)
tests/
    (tester will create test files here — builder does not touch)
evaluation.md            (create in target repo root with timing placeholders)
pyproject.toml           (update: add script entry point)
```

---

## Module Specifications

### `src/gsw_replication/__init__.py`

Content: empty file (or minimal `__version__` string). Must exist to make `gsw_replication` a proper package.

---

### `src/gsw_replication/download.py`

#### Function: `fetch_feds200628() -> pd.DataFrame`

**Purpose**: Download the FEDS200628 CSV from the Federal Reserve website and return a wide-format DataFrame.

**URL**:
```
https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv
```

**CSV structure** (confirmed by direct inspection):
- Rows 0–7 (0-indexed): metadata/legend text — MUST be skipped
- Row 8: actual column header line — `Date,BETA0,BETA1,...,SVENY01,...,SVENY30,...,TAU1,TAU2`
- Row 9 onward: daily data, one row per trading date

**Parsing instructions**:
```python
df = pd.read_csv(
    url,
    skiprows=8,          # skip the 8 metadata rows; row 8 becomes the header
    na_values=["NA"],    # the CSV uses "NA" (string) for missing values
    parse_dates=["Date"],
    infer_datetime_format=True,
)
```

**Return value**: Wide DataFrame with at minimum columns `Date`, `SVENY01`, `SVENY02`, ..., `SVENY30` (plus other columns that will be ignored in transform). The `Date` column must be `datetime64[ns]` dtype.

**Error handling**:
- If HTTP request fails (non-200 status code), raise `RuntimeError` with message: `"Failed to download FEDS200628 CSV: HTTP {status_code}"`.
- No retry logic needed.
- Use `requests` to stream the content; pass to `pd.read_csv` via `io.StringIO` OR pass the URL directly to `pd.read_csv` (both are acceptable).

**Preferred implementation** (using requests for explicit error handling):
```python
import io
import requests
import pandas as pd

FEDS_URL = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"

def fetch_feds200628() -> pd.DataFrame:
    response = requests.get(FEDS_URL, timeout=60)
    if response.status_code != 200:
        raise RuntimeError(f"Failed to download FEDS200628 CSV: HTTP {response.status_code}")
    df = pd.read_csv(
        io.StringIO(response.text),
        skiprows=8,
        na_values=["NA"],
        parse_dates=["Date"],
        infer_datetime_format=True,
    )
    return df
```

**Must NOT**: read, write, or reference `validation/validation_oracle.parquet`.

---

### `src/gsw_replication/transform.py`

#### Function: `to_long_format(df_wide: pd.DataFrame) -> pd.DataFrame`

**Purpose**: Transform the wide FEDS200628 DataFrame into the target long format with columns `ds`, `unique_id`, `y`. Drop all rows with missing yields.

**Input**: Wide DataFrame as returned by `fetch_feds200628()` — has column `Date` (datetime64) and columns `SVENY01` through `SVENY30` among others.

**Processing steps** (in order):

1. **Select relevant columns**:
   ```python
   sveny_cols = [f"SVENY{i:02d}" for i in range(1, 31)]   # ['SVENY01', ..., 'SVENY30']
   df = df_wide[["Date"] + sveny_cols].copy()
   ```

2. **Melt to long format**:
   ```python
   df_long = df.melt(
       id_vars="Date",
       value_vars=sveny_cols,
       var_name="unique_id",
       value_name="y",
   )
   ```

3. **Rename date column**:
   ```python
   df_long = df_long.rename(columns={"Date": "ds"})
   ```

4. **Drop NaN rows**:
   ```python
   df_long = df_long.dropna(subset=["y"])
   ```
   This removes all (ds, unique_id) pairs where the yield is missing — expected for early dates where long-maturity yields were not estimated.

5. **Sort**:
   ```python
   df_long = df_long.sort_values(["unique_id", "ds"]).reset_index(drop=True)
   ```

6. **Enforce dtypes**:
   ```python
   df_long["ds"] = pd.to_datetime(df_long["ds"])       # ensure datetime64[ns]
   df_long["unique_id"] = df_long["unique_id"].astype(str)   # ensure object/string
   df_long["y"] = df_long["y"].astype(float)           # ensure float64
   ```

**Return value**: DataFrame with exactly three columns: `ds` (datetime64[ns]), `unique_id` (object/str), `y` (float64 in percent — e.g., 2.9825 for ~3% yield). No NaN values in any column.

**Column order in return value**: `ds`, `unique_id`, `y` (in that order).

**Must NOT**: read, write, or reference `validation/validation_oracle.parquet`.

---

### `src/gsw_replication/build.py`

#### Function: `build_dataset(output_path: str = "data/gsw_yield_curve.parquet") -> None`

**Purpose**: Orchestrate the full pipeline: download → transform → write parquet.

**Processing steps** (in order):

1. Call `fetch_feds200628()` from `download.py`.
2. Call `to_long_format(df_wide)` from `transform.py`.
3. Create the output directory if it does not exist:
   ```python
   import pathlib
   pathlib.Path(output_path).parent.mkdir(parents=True, exist_ok=True)
   ```
4. Write parquet:
   ```python
   df_long.to_parquet(output_path, index=False)
   ```
5. Print a success message:
   ```python
   print(f"Written {len(df_long):,} rows to {output_path}")
   print(f"Date range: {df_long['ds'].min().date()} to {df_long['ds'].max().date()}")
   print(f"Tenors: {sorted(df_long['unique_id'].unique())}")
   ```

**CLI entry point** (also in `build.py`):
```python
if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "data/gsw_yield_curve.parquet"
    build_dataset(output)
```

**Import structure within build.py**:
```python
from gsw_replication.download import fetch_feds200628
from gsw_replication.transform import to_long_format
```

**Must NOT**: read, write, or reference `validation/validation_oracle.parquet`.

---

## `pyproject.toml` Updates

The existing `pyproject.toml` already has `pandas`, `pyarrow`, and `requests` as dependencies. No dependency additions are needed (`scipy` is not required since we are not re-fitting the model).

**Add the following `[project.scripts]` section** (not currently present):
```toml
[project.scripts]
gsw-build = "gsw_replication.build:build_dataset"
```

The final `pyproject.toml` should look like:
```toml
[project]
name = "gsw-replication"
version = "0.0.1"
description = "GSW (2007) U.S. Treasury zero-coupon yield curve dataset"
requires-python = ">=3.10"
dependencies = ["pandas", "pyarrow", "requests"]

[project.optional-dependencies]
dev = ["pytest>=7.4", "mypy>=1.5", "ruff>=0.1"]

[project.scripts]
gsw-build = "gsw_replication.build:build_dataset"
```

---

## `evaluation.md` (create in target repo root)

Builder must create `evaluation.md` in the target repo root (`/path/to/gsw-replication/evaluation.md`) with the following content. Builder fills in the wall-clock start times for planning and building stages; tester fills in results:

```markdown
# Evaluation Log: GSW (2007) Treasury Yield Curve Dataset

Comparison: Vanilla Claude Code plan mode vs StatsClaw framework

## Clarification Questions

| # | Question | Resolution | Stage |
|---|---|---|---|

## Assumptions Made

| # | Assumption | Rationale |
|---|---|---|
| 1 | Use Fed FEDS200628 directly — no NSS fitting | Fed publishes fitted yields already; SVENY01-SVENY30 match schema exactly |
| 2 | Drop rows with NaN y — no forward-fill | Oracle will determine; conservative default |
| 3 | Coverage = full FEDS200628 range (Jun 1961–present) | User said "maximum available from source" |

## Stage Timings

| Stage | Wall-clock start | Wall-clock end | Duration |
|---|---|---|---|
| Planning | — | — | — |
| Planner (PDF read + spec) | — | — | — |
| Builder (download + transform) | — | — | — |
| Tester (oracle validation) | — | — | — |

## Approximate Token Cost

| Stage | Input tokens | Output tokens |
|---|---|---|
| Planning | — | — |
| Total | — | — |

## Validation Results

| Test | Result | Notes |
|---|---|---|
| Schema | — | — |
| Date range | — | — |
| Row count | — | — |
| Spot checks (sample of oracle rows) | — | — |
| No duplicates | — | — |
| NaN policy | — | — |
```

---

## Key Implementation Notes for Builder

1. **`skiprows=8` is exact**: The FEDS200628 CSV has exactly 8 metadata rows (confirmed by direct download inspection). The 9th line (index 8) is the column header. Using `skiprows=8` gives pandas the header on what would have been row 8.

2. **NA values are the string "NA"**: The CSV uses the literal string `NA` (not blank, not `nan`). `pd.read_csv` with default settings or explicit `na_values=["NA"]` will handle this correctly by converting to `NaN` in float columns.

3. **Date format is YYYY-MM-DD**: No custom date parser needed; `parse_dates=["Date"]` with pandas defaults works.

4. **Units are in percent**: SVENY values like `2.9825` mean 2.9825%, not 0.029825. Do not divide by 100.

5. **Column selection is exact**: Only select `SVENY01` through `SVENY30` (30 columns). Do not include SVENPY, SVENF, SVEN1F, BETA, TAU columns.

6. **`data/` directory must be created**: The directory may not exist in the repo. Use `mkdir(parents=True, exist_ok=True)`.

7. **`data/gsw_yield_curve.parquet` must be git-ignored**: Add `data/` to `.gitignore` if not already present (large binary file, generated artifact).

8. **Do NOT add `data/gsw_yield_curve.parquet` to git**: This is a generated runtime artifact. Ensure the `.gitignore` in the target repo excludes `data/` or `*.parquet`.

---

## `.gitignore` Update

Check if `data/` or `*.parquet` is in `.gitignore`. If not, add:
```
data/
```

---

## `src/gsw_replication/__init__.py` Content

Minimal:
```python
"""GSW (2007) U.S. Treasury zero-coupon yield curve replication."""
__version__ = "0.0.1"
```

---

## Implementation Validation (builder self-check, NOT using oracle)

After writing the parquet, builder may self-check by loading it and printing:
```python
import pandas as pd
df = pd.read_parquet("data/gsw_yield_curve.parquet")
print(df.dtypes)
print(df.shape)
print(df.head())
print(df['unique_id'].unique())
print(df['y'].describe())
```

Expected: ~379,352 rows (or more if Fed has added new data), 3 columns, y values in range 0–20 roughly, 30 unique unique_id values.

Builder MUST NOT compare against `validation/validation_oracle.parquet`.

---

## Pipeline Isolation Note

This spec.md is the ONLY artifact builder receives. Builder does NOT receive test-spec.md or any oracle path. All oracle comparison is tester's responsibility.
