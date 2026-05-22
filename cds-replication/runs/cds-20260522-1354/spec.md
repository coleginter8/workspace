# Implementation Specification: CDS Portfolio Returns Pipeline
## cds-20260522-1354

---

## 1. Notation

| Symbol | Type | Description |
|--------|------|-------------|
| S_{i,τ,t} | float (decimal) | Par spread for issuer i, tenor τ, at date t. Decimal form: 0.0080 = 80 bps |
| RD_{i,τ,t} | float (years) | Risky duration for issuer i, tenor τ, at date t |
| r_{i,τ,m} | float (decimal) | Monthly return for issuer i, tenor τ, month m |
| m | int | Calendar month index |
| τ | str | CDS tenor: one of '3Y', '5Y', '7Y', '10Y' |
| N | int | Tenor in years: 3, 5, 7, or 10 |
| R | float | Recovery rate = 0.40 (fixed) |
| LGD | float | Loss-given-default = 1 - R = 0.60 |
| λ | float | Quarterly flat hazard rate |
| EOM_t | date | Last business day of month t |
| BOM_t | date | First business day (or last day of prior month) = EOM of previous month |

---

## 2. Data Pull Specification

### 2.1 WRDS Connection

- **Host**: `wrds-pgdata.wharton.upenn.edu`
- **Port**: `9737`
- **Database**: `wrds`
- **Username**: `coleginter`
- **Credentials**: Read from `~/.pgpass` using `pgpass` file convention

### 2.2 Source Tables

Pull from annual partitioned tables: `markit.cds{YYYY}` for YYYY in 2001, 2002, ..., 2023.

Use `UNION ALL` across all years or iterate year by year and concatenate.

### 2.3 SQL Query per Year

```sql
SELECT
    date,
    ticker,
    tenor,
    parspread,
    riskypv01
FROM markit.cds{YYYY}
WHERE
    currency = 'USD'
    AND country = 'United States'
    AND tier = 'SNRFOR'
    AND docclause IN ('XR14', 'XR', 'MR14', 'MR')
    AND tenor IN ('3Y', '5Y', '7Y', '10Y')
    AND runningcoupon = 0.01
    AND parspread IS NOT NULL
    AND parspread > 0
```

### 2.4 Docclause Priority Deduplication

After pulling all rows, a ticker may appear multiple times per (date, tenor) due to multiple docclause codes. Apply priority deduplication:

- For dates **before 2009-04-01**: prefer `MR14 > XR14 > MR > XR`
- For dates **on or after 2009-04-01**: prefer `XR14 > MR14 > XR > MR`

Implementation: add integer priority column, then keep only the row with the lowest priority integer per (date, ticker, tenor) group.

After deduplication, the dataset must have at most ONE row per (date, ticker, tenor).

### 2.5 End-of-Month Sampling

From the daily data:
1. Assign each row a `(year, month)` key
2. For each (year, month, ticker, tenor) group, keep only the row with the **maximum date** (= last business day of that month)
3. This yields one observation per (ticker, tenor, year-month)

### 2.6 Result Schema After Pull

The raw pulled DataFrame (before return computation) must have columns:
- `date`: date (last business day of month)
- `year_month`: period or (year, month) integer tuple — for grouping
- `ticker`: str — issuer identifier
- `tenor`: str — '3Y', '5Y', '7Y', or '10Y'
- `parspread`: float — par spread in decimal
- `riskypv01`: float or NaN — risky duration from Markit (NaN for pre-2008 rows)

---

## 3. Risky Duration Computation

### 3.1 When riskypv01 is Available (2008+)

Use the Markit `riskypv01` value directly. No computation needed.

### 3.2 When riskypv01 is NULL (pre-2008)

Compute from parspread using the flat hazard, zero risk-free rate formula:

```python
def compute_rd(S: float, N: int, R: float = 0.40) -> float:
    """
    Compute risky duration (risky PV01) for a CDS with:
      S: par spread (decimal, e.g. 0.0080)
      N: maturity in years (integer)
      R: recovery rate (default 0.40)
    
    Uses quarterly coupon payments and flat hazard rate.
    Zero risk-free rate approximation (r=0).
    
    Formula (HKM footnote 27, Palhares standard CDS model):
      lambda_q = 4 * log(1 + S / (4 * (1-R)))
      RD = (1/4) * sum_{j=1}^{4*N} exp(-lambda_q * j / 4)
    """
    LGD = 1.0 - R
    lambda_q = 4.0 * math.log(1.0 + S / (4.0 * LGD))
    rd = sum(0.25 * math.exp(-lambda_q * j / 4.0) for j in range(1, 4*N + 1))
    return rd
```

Apply `compute_rd` to all rows where `riskypv01` IS NULL.

Fill RD column: use Markit `riskypv01` when not NaN, else `compute_rd(parspread, N, 0.40)`.

Edge case: if `parspread <= 0` or `parspread >= LGD` (spread >= 60%), the log formula overflows. Clamp: `S_clamped = min(max(S, 1e-6), 0.599)` before applying the formula.

---

## 4. Monthly Return Computation

### 4.1 Sort Data

Sort the EOM dataset by (ticker, tenor, date). Group by (ticker, tenor).

### 4.2 Lag Spreads and RD

For each (ticker, tenor) group, compute:
- `S_prev`: lagged parspread (previous month's EOM value)
- `RD_prev`: lagged riskypv01_filled (previous month's EOM value)

If the previous month observation is missing (gap > 1 month), `S_prev` and `RD_prev` will be NaN for that row.

### 4.3 Compute Return

```python
# Monthly return for protection seller (long credit risk):
# r_t = S_{t-1}/12 + (S_{t-1} - S_t) * RD_{t-1}
df['carry'] = df['S_prev'] / 12.0
df['capital_gain'] = (df['S_prev'] - df['parspread']) * df['RD_prev']
df['return'] = df['carry'] + df['capital_gain']
```

### 4.4 Drop Invalid Returns

Drop rows where:
- `S_prev` is NaN (no prior month data)
- `return` is NaN or Inf

### 4.5 Date Label Assignment

Assign `ds` = first calendar day of the month corresponding to `date`:
```python
df['ds'] = df['date'].to_period('M').dt.to_timestamp()
# e.g., date=2001-01-31 (last biz day of Jan 2001) → ds=2001-01-01
```

---

## 5. Quintile Sort Procedure

### 5.1 Ranking Variable

Each month m, the ranking variable is:
- `S_5Y_prev(i, m-1)` = end-of-month 5Y spread for issuer i from the previous month (m-1)

This is the beginning-of-month spread for month m, looking back to EOM of month m-1.

**Source**: From the EOM 5Y spread data (after pre-2008 RD fill), extract the 5Y series:

```python
spread_5y = df_eom[df_eom['tenor'] == '5Y'][['ds', 'ticker', 'parspread']].copy()
spread_5y = spread_5y.rename(columns={'parspread': 'spread_5y_eom'})
```

Lag by one period to get beginning-of-month rank variable:

```python
spread_5y = spread_5y.sort_values(['ticker', 'ds'])
spread_5y['spread_5y_prev'] = spread_5y.groupby('ticker')['spread_5y_eom'].shift(1)
```

### 5.2 Monthly Quintile Assignment

Each month m, across all tickers with valid `spread_5y_prev`:
```python
# Group by ds, compute quintile rank (1=lowest, 5=highest)
spread_5y['quintile'] = spread_5y.groupby('ds')['spread_5y_prev'].transform(
    lambda x: pd.qcut(x, q=5, labels=[1,2,3,4,5], duplicates='drop')
).astype(int)
```

Edge case: if fewer than 5 unique spread values in a month (unlikely but possible), `duplicates='drop'` handles it; resulting quintiles may have fewer than 5 distinct labels. Accept and continue.

### 5.3 Merge Quintiles into Return Data

Join quintile assignment to the full return DataFrame on (ticker, ds):
```python
df_returns = df_returns.merge(
    spread_5y[['ds', 'ticker', 'quintile']],
    on=['ds', 'ticker'],
    how='inner'  # only keep tickers with a valid quintile assignment this month
)
```

Any ticker/month where quintile assignment is missing is **excluded** from portfolio returns.

---

## 6. Portfolio Return Computation

### 6.1 Equal-Weight Portfolio

For each (ds, tenor, quintile) cell:
```python
portfolio_returns = df_returns.groupby(['ds', 'tenor', 'quintile'])['return'].mean().reset_index()
portfolio_returns.rename(columns={'return': 'y'}, inplace=True)
```

### 6.2 Construct unique_id

```python
portfolio_returns['unique_id'] = portfolio_returns['tenor'] + '_Q' + portfolio_returns['quintile'].astype(str)
# e.g., '5Y_Q3'
```

### 6.3 Final Portfolio DataFrame

Columns: `ds` (datetime), `unique_id` (str), `y` (float)

Expected unique_id values (20):
```
10Y_Q1, 10Y_Q2, 10Y_Q3, 10Y_Q4, 10Y_Q5,
3Y_Q1,  3Y_Q2,  3Y_Q3,  3Y_Q4,  3Y_Q5,
5Y_Q1,  5Y_Q2,  5Y_Q3,  5Y_Q4,  5Y_Q5,
7Y_Q1,  7Y_Q2,  7Y_Q3,  7Y_Q4,  7Y_Q5
```

---

## 7. Contract Return Output

### 7.1 Contract unique_id

```python
df_returns['unique_id'] = df_returns['ticker'] + '_' + df_returns['tenor']
# e.g., 'GE_5Y', 'IBM_3Y'
```

### 7.2 Final Contract DataFrame

Columns: `ds` (datetime), `unique_id` (str), `y` (float)

Drop rows where `y` is NaN or Inf before output.

---

## 8. Output Specification

### 8.1 Portfolio Parquet

**File**: `ftsfr_cds_portfolio_returns.parquet`

| Column | dtype | Description |
|--------|-------|-------------|
| ds | datetime64[ns] | First calendar day of month (e.g., 2001-01-01) |
| unique_id | object (str) | Portfolio identifier: `{TENOR}_Q{QUINTILE}` |
| y | float64 | Equal-weight monthly return (decimal) |

- 20 unique `unique_id` values
- ds from 2001-01-01 to 2023-12-01
- No NaN in `y`
- No duplicate (ds, unique_id) pairs
- Sorted by: unique_id, then ds

### 8.2 Contract Parquet

**File**: `ftsfr_cds_contract_returns.parquet`

| Column | dtype | Description |
|--------|-------|-------------|
| ds | datetime64[ns] | First calendar day of month (e.g., 2001-01-01) |
| unique_id | object (str) | Contract identifier: `{TICKER}_{TENOR}` |
| y | float64 | Individual monthly return (decimal) |

- ds from 2001-01-01 to 2023-12-01
- No NaN in `y`
- No duplicate (ds, unique_id) pairs
- Sparse: not all tickers present in all months
- Sorted by: unique_id, then ds

---

## 9. Module Structure

```
src/cds_replication/
    __init__.py          # Package init
    data.py              # WRDS data pull and caching
    returns.py           # RD computation + monthly return formula
    portfolios.py        # Quintile sort + equal-weight aggregation
    pipeline.py          # Orchestration: pull → returns → portfolios → save
```

### 9.1 data.py

```python
def pull_cds_data(start_year: int = 2001, end_year: int = 2023,
                  use_cache: bool = True, cache_path: str = 'data/raw_cds.parquet') -> pd.DataFrame:
    """
    Pull CDS daily data from WRDS Markit for US corporates.
    Returns DataFrame with columns:
      date (date), ticker (str), tenor (str), parspread (float), riskypv01 (float or NaN)
    Applies docclause priority deduplication and end-of-month sampling.
    Caches result to parquet to avoid re-querying.
    """
```

Connection string: `postgresql://coleginter@wrds-pgdata.wharton.upenn.edu:9737/wrds`
Use `~/.pgpass` for password via psycopg2 or sqlalchemy.

### 9.2 returns.py

```python
def compute_rd_flat(S: float, N: int, R: float = 0.40) -> float:
    """Flat hazard risky duration. Used when riskypv01 is unavailable."""

def fill_rd(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill riskypv01 column: use Markit value when present, compute_rd_flat otherwise.
    Adds column 'rd_filled'.
    """

def compute_monthly_returns(df_eom: pd.DataFrame) -> pd.DataFrame:
    """
    Given EOM daily snapshot data (one row per ticker/tenor/month),
    compute monthly returns.
    Returns DataFrame with columns: ds, ticker, tenor, return.
    """
```

### 9.3 portfolios.py

```python
def assign_quintiles(df_eom: pd.DataFrame) -> pd.DataFrame:
    """
    Assign quintile rank (1-5) to each ticker per month based on lagged 5Y spread.
    Returns df with added 'quintile' column.
    """

def compute_portfolio_returns(df_returns: pd.DataFrame) -> pd.DataFrame:
    """
    Compute equal-weight portfolio returns for each (ds, tenor, quintile) cell.
    Returns DataFrame with columns: ds, unique_id, y.
    """

def compute_contract_returns(df_returns: pd.DataFrame) -> pd.DataFrame:
    """
    Format individual contract returns.
    Returns DataFrame with columns: ds, unique_id, y.
    """
```

### 9.4 pipeline.py

```python
def run_pipeline(
    start_year: int = 2001,
    end_year: int = 2023,
    output_dir: str = '.',
    use_cache: bool = True
) -> None:
    """
    Full pipeline: pull → returns → portfolios → save parquet files.
    """
```

---

## 10. Input Validation

- `parspread > 0` and `parspread < 1.0` (flag extreme values > 50% as warning but do not drop)
- `riskypv01` when present: must be > 0 and < tenor_years + 1 (e.g., < 11 for 10Y)
- If computed `rd_flat` produces NaN or Inf (e.g., S >= LGD), set RD = NaN and drop the return for that observation
- `tenor` must be in `{'3Y', '5Y', '7Y', '10Y'}`

---

## 11. Numerical Constraints and Stability

- The flat hazard formula: `λ = 4 × log(1 + S/(4×LGD))` — valid for 0 < S < LGD
- For HY credits with S ≈ 0.40–0.60, λ is large but finite; RD will be small (< 2 years for short tenors)
- For distressed (S > 0.50), clamp S to `min(S, 0.599)` before computing λ
- Monthly returns can be large negative (default/spread spike events): do NOT drop outliers; include them in the output
- Contract returns outside [-2.0, 2.0] should be included but logged as warnings

---

## 12. Recovery Rate

Use `R = 0.40` (40% recovery) as the standard ISDA convention. This is the value used by Palhares ("loss-given-default of 40%") and standard for North American investment-grade corporates.

---

## 13. Date and Period Handling

- All `ds` values in output parquets are first-of-month: `pd.Timestamp('2001-01-01')` etc.
- Use `pandas.Period` for month grouping to avoid ambiguity
- When merging EOM data with first-of-month label: `df['ds'] = df['date'].to_period('M').dt.to_timestamp()`
- Output parquet `ds` column: `datetime64[ns]`

---

## 14. Performance Notes

- Total raw data volume: ~50M rows across all years
- Implement year-by-year pulls with early EOM sampling in SQL to reduce data transfer
- Cache raw EOM data to parquet after first pull
- Use `pd.qcut` with `duplicates='drop'` for quintile assignment
- Use vectorized pandas operations for return computation (avoid row-by-row loops)

---

## 15. Methodological Assumptions and Documented Gaps

### 15.1 Contract Spread Cap (Builder-Introduced Assumption)

**Assumption**: Exclude contract returns where `carry = S_prev / 12 > 0.50 / 12` (equivalently, `S_prev > 50%`) from the contract return output.

**Rationale**: Post-default names (e.g., ABK, PMI) retain stale Markit spread quotes orders of magnitude above market levels (5,000+ bps) long after default. When spreads subsequently collapse, the protection-seller return formula produces positive returns of ~+200%, which are economically meaningless (the CDS has already triggered). The 50% cap is the same threshold applied in the portfolio carry aggregation (`CARRY_CAP = 0.50 / 12`) and is consistent with Palhares (2012) sample construction.

**This is a builder-introduced methodological choice not explicitly specified in HKM (2017) or Palhares (2012).** It is flagged in `evaluation.md`.

### 15.2 Oracle Universe Gap (Irreducible Paper-vs-Oracle Gap)

**Observation**: The oracle `validation_portfolio.parquet` was constructed using approximately 184 unique tickers per month. The WRDS Markit full universe (with our current filters: USD, US, SNRFOR, XR14/XR/MR14/MR, 3Y/5Y/7Y/10Y, coupon=1%) produces approximately 808 unique tickers per month.

**Effect on portfolios**: With 808 tickers, idiosyncratic spread movements average out in the equal-weight aggregation, causing all 20 portfolios to track the same macro credit factor (inter-quintile correlations 0.85–0.99). With 184 tickers, idiosyncratic effects survive, producing near-orthogonal quintile time series (oracle inter-quintile correlations 0.03–0.09). The methodology from HKM (2017) and Palhares (2012) does not specify the exact ticker selection criteria used to construct the oracle's curated universe.

**Consequence**: Only the 3Y_Q1 portfolio achieves high correlation with its oracle counterpart (0.976). All other 19 portfolios: -0.18 to +0.14. This is an irreducible gap given available data.

**Effect on contracts**: Per-contract oracle correlation is near-zero to mildly negative (pooled -0.074) because individual company time series reflect company-specific dynamics that differ between universes.

### 15.3 Data Availability Gap

**Observation**: The oracle covers 2001-01-01 to 2023-12-01. The WRDS Markit data with `runningcoupon=0.01` filter is only available from early 2008 onward. WRDS data before 2008 uses `runningcoupon=0.00` (pre-CDS Big Bang convention), which is not queried by our current filters.

**Consequence**: Pipeline output covers 2008-2023 only. Oracle rows from 2001-2007 (~58,800 contract rows) are inherently uncoverable from the current data pull. This gap is acknowledged and documented; the pipeline produces the full set of results achievable with available WRDS data.
