# Request: cds-20260522-1354

## Scope

Replicate the HKM (2017) CDS portfolio returns pipeline using the Palhares (2012) mark-to-market return methodology.

## Task Description

Build a Python pipeline that:
1. Pulls CDS data from WRDS (Markit CDS database)
2. Computes individual CDS contract monthly mark-to-market returns using Palhares (2012) methodology
3. Constructs 20 portfolios (4 tenors × 5 quintiles) sorted by CDS spread level
4. Outputs two parquet files matching exact schema

## Deliverables

- `ftsfr_cds_portfolio_returns.parquet` — columns: ds (month-end date), unique_id ({tenor}_Q{quintile}), y (return) — 20 portfolios, monthly
- `ftsfr_cds_contract_returns.parquet` — columns: ds, unique_id ({ticker}_{tenor}), y — individual contract returns, monthly

## Source Papers

- papers/hkm_2017.pdf — Haddad, Kozak, Manela (2017)
- papers/AQR CashFlow Maturity and Risk Premia in CDS Markets.pdf — Palhares (2012)

## Validation Oracles

- validation/validation_portfolio.parquet — 20 portfolio series (builder must NOT read)
- validation/validation_contract.parquet — individual contract series (builder must NOT read)

## Data Source

- WRDS PostgreSQL: wrds-pgdata.wharton.upenn.edu:9737
- Username: coleginter
- Credentials: ~/.pgpass

## Target Repository

- coleginter8/cds-replication
- Checkout: /Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/CDS Replication/.repos/cds-replication

## Workspace Repository

- coleginter8/workspace
- Checkout: /Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/CDS Replication/.repos/workspace

## Acceptance Criteria

1. Portfolio parquet: 20 unique_id values ({tenor}_Q{quintile} for tenor ∈ {1Y,3Y,5Y,10Y}, quintile ∈ {1,2,3,4,5})
2. Contract parquet: unique_id format {ticker}_{tenor}
3. Returns within tolerance of validation oracles
4. Monthly frequency, ds = month-end dates
5. No NaN values in y (or clearly documented NaN policy)
6. No duplicate (ds, unique_id) pairs

## Special Instructions

- If methodology requires a discount curve or short-rate input, raise HOLD rather than assuming
- Maintain evaluation.md with stage timings and token costs
- Builder must not read validation oracle files
- Tester may read both oracle files
