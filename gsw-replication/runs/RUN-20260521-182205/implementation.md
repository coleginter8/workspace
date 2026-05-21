# Implementation — RUN-20260521-182205

## Status: COMPLETE

---

## Files Created

| File | Lines | Description |
|---|---|---|
| `src/gsw_replication/__init__.py` | 2 | Package init; exposes `__version__ = "0.0.1"` |
| `src/gsw_replication/download.py` | 41 | `fetch_feds200628()`: downloads FEDS CSV via requests, skips 8 metadata rows, parses dates, handles NA values and HTTP errors |
| `src/gsw_replication/transform.py` | 62 | `to_long_format(df_wide)`: selects SVENY01–SVENY30, melts wide→long, renames Date→ds, drops NaN y, enforces dtypes, sorts by (unique_id, ds) |
| `src/gsw_replication/build.py` | 54 | `build_dataset(output_path)`: orchestrates download+transform, creates output dir, writes parquet, prints summary |

## Files Modified

| File | Change |
|---|---|
| `pyproject.toml` | Added `[project.scripts]` with `gsw-build` entry point; added `[build-system]` block with `setuptools.build_meta` backend (fixed from spec's `setuptools.backends.legacy:build` which is not available on this environment's setuptools version) |
| `.gitignore` | Added `data/` entry to exclude generated parquet artifact |

## Files Created in Repo Root

| File | Description |
|---|---|
| `evaluation.md` | Evaluation log with timing/assumption/result placeholders per spec |

---

## Output Parquet: `data/gsw_yield_curve.parquet`

| Metric | Value |
|---|---|
| Row count | 379,352 |
| Columns | ds (datetime64[ns]), unique_id (object), y (float64) |
| Date range | 1961-06-14 to 2026-05-15 |
| Tenor count | 30 (SVENY01–SVENY30) |
| NaN values | 0 (all rows with NA yield dropped) |
| Duplicate rows | 0 |
| y range | 0.0554 – 16.462 (in percent) |

---

## Deviations from Spec

1. **`infer_datetime_format=True` removed**: The spec included this argument in `pd.read_csv()`, but it is deprecated in pandas ≥ 2.0 and generates a FutureWarning. Removed it — pandas default date parsing handles `YYYY-MM-DD` correctly without it.

2. **`build-backend = "setuptools.build_meta"` instead of `"setuptools.backends.legacy:build"`**: The spec's `setuptools.backends.legacy:build` requires setuptools ≥ 71.1, which is not available in this environment. Changed to the standard `setuptools.build_meta` backend which is available in setuptools ≥ 42. Functionally equivalent for this simple project.

3. **`data/gsw_yield_curve.parquet` not committed to git**: Per spec note 7, the parquet is a generated runtime artifact. Added `data/` to `.gitignore`. The file was generated locally and validated.

---

## Design Choices

- Used `requests` library with explicit HTTP status check rather than passing URL directly to `pd.read_csv` — this gives a clean `RuntimeError` on HTTP failure as specified.
- Used `pathlib.Path.mkdir(parents=True, exist_ok=True)` in `build.py` for idiomatic Python directory creation.
- `SVENY_COLS` constant defined at module level in `transform.py` to avoid repeated list comprehension in function calls.
- Import structure in `build.py` uses top-level imports (not deferred inside function) for clarity, consistent with Python conventions.

---

## Oracle Access Confirmation

Builder did NOT read, access, or reference `validation/validation_oracle.parquet` at any point. All self-checks used the generated parquet only.

---

## Self-Check Results (without oracle)

```
Shape: (379352, 3)
Dtypes:
  ds           datetime64[ns]
  unique_id            object
  y                   float64
unique_id: ['SVENY01', ..., 'SVENY30']  (30 values)
NaN count: {'ds': 0, 'unique_id': 0, 'y': 0}
Duplicate rows: 0
y range: 0.0554 – 16.462
```

Row count of 379,352 matches the expected value documented in `comprehension.md`.

---

## Commit

```
675c190  feat: implement GSW (2007) daily zero-coupon yield curve dataset
```

Branch: `main` of `coleginter8/gsw-replication` (local commit, not yet pushed).
