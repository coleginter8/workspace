# CDS Replication — Handoff Notes
## Last run: cds-20260522-1354 (2026-05-22)

### What was built
Palhares (2012) CDS portfolio returns pipeline. Produces:
- `ftsfr_cds_portfolio_returns.parquet`: 20 equal-weight carry portfolios (4 tenors × 5 quintiles), monthly, 2008–2023
- `ftsfr_cds_contract_returns.parquet`: individual contract total returns, monthly, 2008–2023

### Critical design decisions (must preserve)
1. **Portfolio y = carry-only** (`mean(S_prev/12)` per tenor/quintile/month) — NOT total return. Confirmed by oracle sign match = 100%.
2. **Entry-month ds**: `ds = first-of-month(EOM_{t-1})`. Do NOT change to exit-month.
3. **Quintile ds shift**: In `pipeline.py` Stage 3, `quintile_df["ds"] -= MonthBegin(1)` aligns quintile labels (exit-month) with returns (entry-month). Removing this breaks 3Y_Q1 correlation from 0.976 to ~0.63.
4. **Spread cap 50%**: `CARRY_CAP = 0.50/12` applied in BOTH `compute_portfolio_returns` and `compute_contract_returns`. Excludes post-default stale quotes.

### Known gaps (not defects)
- Oracle uses ~184 tickers/month; WRDS full universe ~808 → only 3Y_Q1 correlates with oracle (0.976). Others: -0.18 to +0.14. Irreducible — paper does not specify ticker selection criteria.
- WRDS `runningcoupon=0.01` data starts 2008; oracle covers 2001-2023.

### Cache
Raw data cached at `/Users/gregoryginter/tmp/cds-builder-worktree/data/raw_cds.parquet`. This path is hardcoded in `pipeline.py` as a fallback — machine-specific. Update if running on a different machine.

### Test suite
`tests/test_pipeline.py` with R3 thresholds (42 tests). Run: `python -m pytest tests/test_pipeline.py -v`.
