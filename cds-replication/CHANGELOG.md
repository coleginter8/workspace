## cds-20260522-1354 — 2026-05-22
- **Request**: Replicate HKM (2017) CDS portfolio returns using Palhares (2012) methodology
- **Verdict**: PASS WITH NOTE (42/42 tests)
- **Deliverables**: `ftsfr_cds_portfolio_returns.parquet` (3,820 rows, 20 portfolios), `ftsfr_cds_contract_returns.parquet` (614,342 rows, 6,950 contracts)
- **Key achievement**: 3Y_Q1 portfolio correlation with oracle = 0.976; correct Palhares formula, entry-month ds labeling, quintile sort, and carry-only portfolio aggregation
- **Documented gap**: Oracle uses ~184 tickers/month; WRDS full universe ~808 → irreducible inter-quintile correlation gap for 5Y/7Y/10Y portfolios
- **Builder versions**: V1–V5 (5 iterations to resolve carry vs total return, ds labeling, quintile shift, spread cap)
