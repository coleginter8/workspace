# Request: run-20260515-124030

## Scope

Replicate **Tables 2 and 3 only** from He, Kelly & Manela (2017), "Intermediary Asset Pricing: New Theory and Evidence," *Journal of Finance* 72(6), pp. 2799–2837.

- **Table 2**: Summary statistics for the intermediary capital ratio (η) factor and the cross-sectional test portfolios
- **Table 3**: Cross-sectional asset pricing tests (Fama-MacBeth and related)

## Source Paper

- File: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication/hkm-paper.pdf`

## Target Repository

- Repo: `coleginter8/hkm-replication`
- Local checkout: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication`

## Workspace Repository

- Repo: `coleginter8/workspace`
- Status: Exists on GitHub (empty), cloned to `.repos/workspace/`

## Data Sources

- WRDS PostgreSQL: `wrds-pgdata.wharton.upenn.edu:9737`
- WRDS user: `coleginter` (credentials in `~/.pgpass`)
- Required WRDS datasets: CRSP (monthly returns, market cap), Compustat (broker-dealer balance sheet data), potentially FRED for macro series

## Acceptance Criteria

1. Table 2 values match HKM (2017) within rounding (typically ±0.01 for statistics like mean, std, SR)
2. Table 3 factor loadings, t-stats, and R² values match within rounding tolerance
3. Code is reproducible from raw WRDS pull through final table output
4. Python implementation with clear data pipeline

## Language / Profile

- Python (pandas, statsmodels, psycopg2/sqlalchemy for WRDS)
- Profile: python-package

## Workflow

Workflow 1 (Code Change) — implement replication code for Tables 2 and 3.

## Brain Mode

Isolated (not connected to shared brain).
