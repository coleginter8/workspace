# Handoff — gsw-replication

**Last run**: RUN-20260521-182205 (2026-05-21)  
**Status**: DONE

## What was built

GSW (2007) daily zero-coupon Treasury yield curve dataset.  
Source: Federal Reserve FEDS200628 (https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv)  
Output schema: ds (datetime64), unique_id (SVENY01–SVENY30), y (float64, percent)  
Row count: 379,352 rows, date range 1961-06-14 to 2026-05-15

## How to refresh

```bash
cd .repos/gsw-replication
pip install -e .
python -m gsw_replication.build
```

## Validation

```bash
cd .repos/gsw-replication
pytest tests/test_gsw_dataset.py -v
```

The oracle at `validation/validation_oracle.parquet` (StatsClaw repo) is the ground truth.  
All 9 tests must pass with oracle alignment max diff < 0.01 (actual: 0.000000).

## Notes

- The parquet file is git-ignored (`data/`) — regenerate locally after cloning
- HTTP error path in download.py is not unit-tested (acceptable risk)
- Oracle path in test file is resolved dynamically relative to the repo root (two levels up from target repo root to StatsClaw root). If the repo is moved or cloned standalone outside the StatsClaw directory structure, the oracle path will break — update `ORACLE_PATH` in `tests/test_gsw_dataset.py` accordingly
- Early sample sparsity is correct: before August 1971, only SVENY01–SVENY07 are available
- NaN policy is intentional — do not add imputation or forward-fill
- As the Fed adds new trading days, row count will grow; tests use `>= 350,000` lower bound to accommodate future additions
- Oracle covers through 2026-05-15; after that date, validate new rows against the Fed's published SVENY values directly
