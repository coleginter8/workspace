# Impact Analysis: cds-20260522-1354

## Target Repository State

Target repo `coleginter8/cds-replication` currently contains:
- `pyproject.toml` (Python project config, dependencies: pandas, numpy, scipy, pyarrow, sqlalchemy, psycopg2-binary, requests)
- `tests/__init__.py` (empty)
- `.gitignore`

No source code exists yet. This is a greenfield implementation.

## Oracle Analysis (Leader Planning Only)

From validation oracles (NOT to be shared with builder):
- **Tenors**: 3Y, 5Y, 7Y, 10Y (NOT 1Y — user's prompt description said "4 tenors × 5 quintiles" which is correct, but actual tenors differ from prompt example)
- **Date range**: 2001-01-01 to 2023-12-01 (monthly, ~275-276 observations per portfolio)
- **Portfolio returns**: All positive, mean increases with quintile and tenor (Q1=lowest spread, lowest return; Q5=highest spread, highest return)
- **Return magnitude**: Very small (mean ≈ 0.001–0.007), suggesting these are monthly excess returns in decimal form
- **Contract-level**: 201,830 rows, {TICKER}_{TENOR} format, returns can be large negative (down to -1.8)

## Write Surface (Target Repo)

Files to be created by builder:
```
src/cds_replication/
    __init__.py
    data.py            # WRDS Markit data pull
    returns.py         # Palhares (2012) mark-to-market return calculation
    portfolios.py      # Quintile sort + equal-weight aggregation
    pipeline.py        # Main orchestration script
ftsfr_cds_portfolio_returns.parquet   # final output
ftsfr_cds_contract_returns.parquet    # final output
```

Files to be created by tester:
```
tests/test_pipeline.py   # Oracle comparison tests
```

## Risk Areas

1. **HIGH: WRDS Markit schema** — Must identify correct table and columns. Likely `markit.wrds_cds_monthly` but schema must be verified. Key fields needed: ticker, date, tenor, spread (par spread), DV01/duration, coupon.
2. **HIGH: Discount curve requirement** — Palhares formula may require a risk-free discount curve to compute PV of coupon leg. If so, must HOLD and ask user for source.
3. **HIGH: Recovery rate assumption** — Standard 40% assumed per ISDA convention; planner must confirm from Palhares paper.
4. **MEDIUM: Quintile sorting** — Must determine: within-tenor quintiles sorted on prior-month spread level? Or concurrent? Sort on first observation of month?
5. **MEDIUM: Equal-weight vs value-weight** — HKM uses equal-weight portfolios; planner must confirm from paper.
6. **MEDIUM: Date alignment** — CDS data may not be exactly month-end; must align to month-end dates.
7. **LOW: DV01 convention** — Per Palhares, DV01 = duration × notional. Need to confirm duration calculation (annuity formula vs WRDS direct field).

## Required Teammates

| Teammate | Role | Priority |
|---|---|---|
| planner | Read both papers, produce spec.md + test-spec.md, raise HOLD if discount curve needed | IMMEDIATE |
| builder | Implement pipeline from spec.md | After SPEC_READY |
| tester | Validate outputs against oracles | After builder |
| scriber | Document architecture + process | After tester |
| reviewer | Quality gate | After scriber |

## Profile

python-package

## Brain Mode

isolated (skip distiller)

## Key Design Decision for Planner

The Palhares (2012) formula for CDS mark-to-market monthly return needs:
- Beginning-of-period par spread (S_0)
- End-of-period par spread (S_1)
- CDS duration/DV01 at both dates
- Running coupon (standardized: 100 or 500 bps per ISDA Big Bang)

The formula is approximately:
  r_t = (S_{t-1} - S_t) × Duration_t + coupon × (1/12)

Planner must confirm exact formula and whether a discount curve enters.
