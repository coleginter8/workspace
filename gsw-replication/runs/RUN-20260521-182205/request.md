# Request — RUN-20260521-182205

## Scope

Construct the GSW (2007) daily zero-coupon Treasury yield curve dataset by replicating the Nelson-Siegel-Svensson (NSS) fitting procedure described in Gürkaynak, Sack & Wright (2007).

## Source Material

- Paper: `papers/gsw_2007.pdf` (primary source, planner must deeply comprehend)
- Validation oracle: `validation/validation_oracle.parquet` (tester-only — builder MUST NOT read)
- Target repo: `coleginter8/gsw-replication` (cloned at `.repos/gsw-replication/`)
- Workspace repo: `coleginter8/workspace` (cloned at `.repos/workspace/`)

## Deliverable

A single parquet file with:
- `ds`: date column (daily frequency, maximum coverage)
- `unique_id`: yield tenor label (SVENY01, SVENY02, ..., SVENY30)
- `y`: zero-coupon yield in percent

## Acceptance Criteria

1. Output parquet has exactly columns `ds`, `unique_id`, `y`
2. `unique_id` values are SVENY01–SVENY30 (30 tenors)
3. `y` values are in percent (not decimal)
4. Daily frequency, maximum date coverage matching FRED/GSW historical data
5. NSS parameter estimation follows GSW (2007) methodology
6. Numerical validation against `validation/validation_oracle.parquet` passes within tolerance

## Additional Requirements

- Maintain `evaluation.md` in the target repo root
- The workflow must produce a parquet file as the primary artifact
- Builder must NOT access the validation oracle

## Workspace Repo Status

`coleginter8/workspace` exists and was cloned successfully.

## Target Repo Identity

GitHub: `coleginter8/gsw-replication`
Local: `.repos/gsw-replication/`
