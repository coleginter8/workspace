# Impact — RUN-20260521-182205

## Affected Surfaces in Target Repo (coleginter8/gsw-replication)

| File/Path | Status | Reason |
|---|---|---|
| `src/gsw_replication/__init__.py` | NEW | Package root |
| `src/gsw_replication/download.py` | NEW | Fetch FEDS200628 data from Fed website |
| `src/gsw_replication/transform.py` | NEW | Reshape wide → long, produce ds/unique_id/y parquet |
| `src/gsw_replication/build.py` | NEW | Entry point: download + transform → parquet |
| `data/gsw_yield_curve.parquet` | NEW | Primary deliverable |
| `evaluation.md` | NEW | Per-run evaluation log (required by user) |
| `pyproject.toml` | MODIFY | Add scipy/requests deps if needed; add build script entry point |
| `ARCHITECTURE.md` | NEW | Scriber will write |

## Data Source

The Fed publishes FEDS 2006-28 fitted yields daily at:
- CSV: `https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv`
- The published file contains columns SVENY01–SVENY30 (zero-coupon yields in percent) already computed
- Date range in oracle: 1961-06-14 to 2026-05-15 (16,194 trading days × 30 = 481,820 rows — however oracle has 379,352, suggesting NaN rows are dropped)

## Key Risk Areas

| Risk | Severity | Notes |
|---|---|---|
| NaN handling | Medium | Some tenors are missing for early dates; oracle drops NaN rows (379,352 < 16,194 × 30 = 485,820) |
| Column name parsing | Low | FEDS CSV header may have metadata rows to skip |
| Date parsing | Low | Fed CSV date format; must produce datetime64 |
| Schema compliance | High | ds must be datetime64, unique_id string, y float64 (percent not decimal) |
| Oracle not accessible to builder | High | Builder must NOT read validation/validation_oracle.parquet |

## Profile

Python package (pyproject.toml present, Python ≥ 3.10)

## Required Teammates

| Teammate | Role | Notes |
|---|---|---|
| planner | Comprehend paper, produce spec.md + test-spec.md | Must read full PDF |
| builder | Implement download + transform pipeline | Must NOT access oracle |
| tester | Validate against oracle | Reads oracle; produces audit.md |
| scriber | Document, write ARCHITECTURE.md, log entry | Mandatory |
| reviewer | Quality gate | Reads all artifacts |
| shipper | Push + workspace sync | Run after review |

## Workflow

Workflow 1 (Code Change) → Workflow 2 (Code + Ship implied by "construct dataset")

## Simplified Workflow Assessment

This task involves:
- New Python modules across multiple files
- External data download with URL handling
- Data transformation with NaN policy decisions
- Oracle validation

This does NOT qualify for simplified workflow (>3 files, non-trivial algorithm). Full workflow required.
