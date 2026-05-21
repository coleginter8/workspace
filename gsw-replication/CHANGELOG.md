# Changelog — gsw-replication

## 2026-05-21 — RUN-20260521-182205: Initial GSW Yield Curve Dataset Build

**Commits pushed**: 675c190, b64f54f, 550dfb7  
**Verdict**: PASS (all 9 tests, oracle alignment max diff = 0.000000)

Implemented GSW (2007) daily zero-coupon Treasury yield curve dataset:
- `src/gsw_replication/download.py`: fetch FEDS200628 CSV from Federal Reserve
- `src/gsw_replication/transform.py`: wide→long reshape, NaN drop, schema enforcement
- `src/gsw_replication/build.py`: orchestrate pipeline, write parquet
- `tests/test_gsw_dataset.py`: 9-test pytest suite validating schema, oracle alignment, NaN policy, date range, tenor history
- Output: 379,352 rows, SVENY01–SVENY30, 1961-06-14 to 2026-05-15, percent units
- `ARCHITECTURE.md`: full system architecture with Mermaid diagrams

See [run log](runs/2026-05-21-gsw-yield-curve-initial-build.md) for full process record.
