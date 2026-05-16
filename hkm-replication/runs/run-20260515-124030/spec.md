# Implementation Specification: HKM (2017) JFE Tables 2 & 3 Replication

**Run**: run-20260515-124030
**For**: builder (code pipeline only)
**Source paper**: He, Kelly & Manela (2017), *Journal of Financial Economics* 126, pp. 1–35
**Revision**: SECOND DISPATCH — corrected targets (JFE Table 2 = size comparison; JFE Table 3 = pairwise correlations)

---

## 1. Package Structure

```
hkm/
├── __init__.py                    # version = "0.1.0"
├── data/
│   ├── __init__.py
│   ├── wrds_connect.py            # WRDS PostgreSQL connection
│   ├── crsp.py                    # CRSP market equity pulls
│   ├── compustat.py               # Compustat balance sheet pulls + comparison groups
│   ├── intermediary.py            # η construction + η^Δ factor + book capital + AEM
│   ├── macro.py                   # Macro series: E/P, Unemployment, GDP, NFCI, realized vol
│   └── dealers.py                 # Primary dealer list + holding company mapping
├── tables/
│   ├── __init__.py
│   ├── table2.py                  # JFE Table 2: size comparison ratios
│   └── table3.py                  # JFE Table 3: pairwise correlations
└── utils.py                       # Shared helpers: date alignment, winsorization, logging
tests/
├── __init__.py
├── test_data.py                   # Unit tests for data modules
└── test_tables.py                 # Numerical tests for Table 2 & 3 values
pyproject.toml                     # Package metadata and dependencies
README.md                          # Usage, data requirements, WRDS setup
```

---

## 2. Dependencies

```toml
[project]
name = "hkm"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "pandas>=2.0",
    "numpy>=1.24",
    "scipy>=1.10",
    "sqlalchemy>=2.0",
    "psycopg2-binary>=2.9",
    "pandas-datareader>=0.10",   # FRED access via pandas-datareader
    "requests>=2.28",            # HTTP downloads (Shiller data, public HKM data)
    "statsmodels>=0.14",         # OLS AR(1) estimation
]

[project.optional-dependencies]
dev = ["pytest>=7.4", "mypy>=1.5", "ruff>=0.1"]
```

---

## 3. WRDS Connection (`hkm/data/wrds_connect.py`)

### Function: `get_engine() -> sqlalchemy.Engine`

Reads credentials from `~/.pgpass` (host: `wrds-pgdata.wharton.upenn.edu`, port: `9737`, database: `wrds`, user: `coleginter`). Returns a SQLAlchemy engine with connection pool settings appropriate for WRDS (pool_pre_ping=True, connect_args={"connect_timeout": 30}).

**~/.pgpass format** (must have permissions 600):
```
wrds-pgdata.wharton.upenn.edu:9737:wrds:coleginter:<password>
```

### Function: `query(sql: str, engine: sqlalchemy.Engine | None = None) -> pd.DataFrame`

Executes a SQL query against WRDS and returns a DataFrame. If `engine` is None, calls `get_engine()`. Raises `ConnectionError` with diagnostic message if connection fails.

### Constants
```python
WRDS_HOST = "wrds-pgdata.wharton.upenn.edu"
WRDS_PORT = 9737
WRDS_DB = "wrds"
WRDS_USER = "coleginter"
```

---

## 4. Primary Dealer Mapping (`hkm/data/dealers.py`)

### Data: `DEALER_MAPPING`

A Python list of dicts, one entry per historical primary dealer. Built from Table 1 and Table A.1 of the paper.

```python
DEALER_MAPPING: list[dict] = [
    {
        "dealer_name": str,          # Name as it appears on NY Fed list
        "holding_company": str,      # Holding company name (from Table 1)
        "gvkey": str | None,         # Compustat gvkey (6-digit zero-padded string), None if not in Compustat
        "permno": int | None,        # CRSP permno, None if not in CRSP
        "start_date": str,           # "YYYY-MM-DD" — date dealer designation began
        "end_date": str | None,      # "YYYY-MM-DD" or None if currently active as of 2014
        "is_us_based": bool,         # True if US-incorporated holding company (in CRSP/Compustat)
        "source": str,               # "Table1" or "TableA1"
    },
    ...
]
```

Minimum required entries for US-based firms (is_us_based=True):
Goldman Sachs Group (gvkey needed), Morgan Stanley, Merrill Lynch (multiple entries per Table A.1), Bear Stearns (end 10/1/2008), Lehman Brothers Holdings (end 9/22/2008), Citigroup, JPMorgan Chase & Co., Bank of America Corporation, Drexel Burnham Lambert (end 3/28/1990), Kidder Peabody (end 12/30/1994), Paine Webber (end 12/4/2000), Jefferies LLC, Cantor Fitzgerald. Builder must look up and encode the gvkey and permno for each using the Compustat company table and CRSP stocknames table.

### Function: `get_active_dealers(date: pd.Timestamp, us_only: bool = True) -> list[dict]`

Returns list of DEALER_MAPPING entries where `start_date <= date <= end_date` (or end_date is None). Filters to `is_us_based == True` when `us_only=True`.

### Function: `get_us_gvkeys() -> list[str]`

Returns sorted list of all unique gvkeys from DEALER_MAPPING where `is_us_based=True` and `gvkey is not None`.

### Function: `get_us_permnos() -> list[int]`

Returns sorted list of all unique permnos from DEALER_MAPPING where `is_us_based=True` and `permno is not None`.

---

## 5. CRSP Module (`hkm/data/crsp.py`)

### Function: `get_market_equity(permnos: list[int], start_date: str, end_date: str, engine=None) -> pd.DataFrame`

**Purpose**: Pull monthly market equity (shares × price) for specified permnos.

**WRDS table**: `crsp.msf` (monthly stock file)

**SQL fields needed**: `permno`, `date`, `shrout` (shares outstanding in thousands), `prc` (price — may be negative if closing price unavailable, take absolute value)

**Returns**: DataFrame with columns `[permno, date, market_equity_k]` where:
- `date` is month-end (last trading day of each month — already the convention in `crsp.msf`)
- `market_equity_k` = `shrout × abs(prc)` in thousands of dollars
- Rows: one per (permno, month) for months with non-null, non-zero `shrout` and `prc`

**Filters**:
- Drop rows where `shrout` is null or <= 0
- Drop rows where `prc` is null or == 0
- Keep only SHRFLAG = 'A' or no SHRFLAG filter (use all share classes available in msf, which already consolidates)

**Date range**: `start_date` to `end_date` inclusive (both as "YYYY-MM-DD" strings).

### Function: `get_comparison_market_equity(sic_codes: list[str] | None, start_date: str, end_date: str, engine=None) -> pd.DataFrame`

**Purpose**: Pull monthly market equity for all CRSP-Compustat linked firms, optionally filtered by SIC code prefix(es).

**WRDS tables**: `crsp.msf` joined to `comp.company` via `crsp.ccmxpf_lnkhist`

**Returns**: DataFrame with columns `[permno, gvkey, sic, date, market_equity_k]`

**SIC filter logic**:
- If `sic_codes` is None: return all firms
- If `sic_codes = ["6211", "6221"]`: return BD comparison group
- If `sic_codes = ["602", "603"]` (prefixes): return bank firms (SIC starting with 602x, 603x, etc.)
- Implement as: `WHERE LEFT(sic, N) IN (...)` where N varies by entry length

**Note**: SIC codes in Compustat are in `comp.company.sich` (historical SIC). Use `comp.company` for stable SIC assignment.

### Function: `get_quarterly_market_equity(permnos: list[int], start_date: str, end_date: str, engine=None) -> pd.DataFrame`

**Purpose**: Pull market equity at quarter-end dates only (for η construction).

**Implementation**: Call `get_market_equity()` for the full period, then filter to quarter-end months (March, June, September, December).

**Returns**: DataFrame with columns `[permno, date, market_equity_k]` where `date` is the quarter-end month.

---

## 6. Compustat Module (`hkm/data/compustat.py`)

### Function: `get_balance_sheet(gvkeys: list[str], start_date: str, end_date: str, engine=None) -> pd.DataFrame`

**Purpose**: Pull quarterly balance sheet items for specified gvkeys.

**WRDS table**: `comp.fundq`

**SQL fields**: `gvkey`, `datadate`, `atq` (total assets), `ceqq` (common equity), `fyearq`, `fqtr`

**Returns**: DataFrame with columns `[gvkey, datadate, atq, ceqq]` where:
- `datadate` = quarter-end date of the Compustat observation
- `atq` = total assets (millions of dollars, Compustat default)
- `ceqq` = common equity (millions of dollars)
- Derived columns (added by this function):
  - `book_debt` = `atq − ceqq` (millions of dollars)
  - `book_equity` = `ceqq` (millions of dollars; alias column for clarity)
  - `total_assets` = `atq` (millions of dollars; alias column for clarity)

**Filters**:
- Keep only rows where `atq > 0` and `ceqq` is not null
- Keep `indfmt = 'INDL'` and `datafmt = 'STD'` and `popsrc = 'D'` and `consol = 'C'` (standard Compustat selection for US domestic firms)
- Drop duplicate `(gvkey, datadate)` pairs if any (keep the first)

**Date range**: `datadate` between `start_date` and `end_date`.

### Function: `get_latest_quarter(gvkeys: list[str], as_of_date: pd.Timestamp, engine=None) -> pd.DataFrame`

**Purpose**: For each gvkey, return the most recent Compustat quarterly observation available as of `as_of_date` (no look-ahead).

**Returns**: DataFrame with columns `[gvkey, datadate, atq, ceqq, book_debt, book_equity, total_assets]` — one row per gvkey (the most recent available).

**Implementation**: Query `datadate <= as_of_date`, group by `gvkey`, keep max `datadate`.

### Function: `get_comparison_balance_sheet(sic_filter: str, start_date: str, end_date: str, engine=None) -> pd.DataFrame`

**Purpose**: Pull quarterly balance sheet for all Compustat firms matching a SIC filter.

**Parameters**:
- `sic_filter`: one of `"bd"` (SIC 6211 or 6221), `"banks"` (SIC 6020–6099), or `"all"` (no filter)

**Returns**: DataFrame with `[gvkey, datadate, sic, atq, ceqq, book_debt, book_equity, total_assets]`

**SIC filter implementation**:
```python
# In SQL:
# bd:    WHERE sich IN ('6211', '6221')
# banks: WHERE sich BETWEEN '6020' AND '6099'
# all:   no WHERE clause on sich
```

### Function: `get_crsp_compustat_link(engine=None) -> pd.DataFrame`

**Purpose**: Pull the CRSP-Compustat linking table for merging market equity with balance sheet data.

**WRDS table**: `crsp.ccmxpf_lnkhist`

**Returns**: DataFrame with `[gvkey, permno, linktype, linkprim, linkdt, linkenddt]`

**Filters**: Keep `linktype IN ('LU', 'LC')` and `linkprim IN ('P', 'C')` (primary links only).

---

## 7. Intermediary Module (`hkm/data/intermediary.py`)

### Function: `build_capital_ratio(start_date: str = "1970-01-01", end_date: str = "2012-12-31", engine=None) -> pd.DataFrame`

**Purpose**: Construct the quarterly aggregate intermediary capital ratio η_t.

**Algorithm**:

1. Call `dealers.get_active_dealers(date, us_only=False)` for each quarter to get the set of active primary dealers.
2. For US firms: pull quarterly market equity from `crsp.get_quarterly_market_equity()` and book debt from `compustat.get_latest_quarter()`.
3. Aggregate at each quarter t:
   - `numerator_t = Σ_i Market_Equity_{i,t}` (sum over all US dealers with data at quarter t)
   - `denominator_t = Σ_i (Market_Equity_{i,t} + Book_Debt_{i,t})`
   - `η_t = numerator_t / denominator_t`
4. Require at least 5 primary dealers with non-null data at each quarter t; otherwise set η_t = NaN.

**Returns**: DataFrame with columns `[date, eta, n_dealers]` where:
- `date` = quarter-end date (last day of March/June/September/December)
- `eta` = capital ratio (dimensionless, typically 0.04 to 0.15 based on Fig. 1)
- `n_dealers` = number of primary dealers with data included at that quarter

**Units**: η is dimensionless (ratio of dollar amounts in same units).

### Function: `build_capital_factor(eta_series: pd.Series) -> pd.Series`

**Purpose**: Compute the AR(1) innovation factor η^Δ_t from the levels series.

**Algorithm**:
1. Estimate AR(1) by OLS: `η_t = ρ_0 + ρ η_{t-1} + u_t` using `statsmodels.OLS` on the full sample.
2. Extract residuals `û_t`.
3. Compute `η^Δ_t = û_t / η_{t-1}` (scaled by lagged capital ratio).
4. First observation is NaN (no lagged value).

**Input**: `eta_series` — a pd.Series indexed by quarter-end dates, sorted ascending, no NaNs.

**Returns**: pd.Series of η^Δ_t, same index as input, first element NaN.

**Validation**: The AR(1) coefficient ρ should be approximately 0.94. Log a warning if |ρ − 0.94| > 0.05.

### Function: `build_book_capital_ratio(start_date: str = "1970-01-01", end_date: str = "2012-12-31", engine=None) -> pd.DataFrame`

**Purpose**: Construct the quarterly aggregate book capital ratio using book equity instead of market equity.

**Algorithm**:
1. Same primary dealer set as `build_capital_ratio()` but use `ceqq` as numerator and `atq` as denominator.
2. `book_η_t = Σ_i ceqq_{i,t} / Σ_i atq_{i,t}`

**Returns**: DataFrame with columns `[date, book_eta, n_dealers]`

### Function: `build_book_capital_factor(book_eta_series: pd.Series) -> pd.Series`

**Purpose**: Compute AR(1) innovation factor for book capital ratio, analogous to `build_capital_factor()`.

### Function: `load_aem_series(source: str = "fred") -> pd.DataFrame`

**Purpose**: Load the AEM leverage series from Federal Reserve Flow of Funds.

**Algorithm** (FRED approach):
- Download FL664090005 (Total Financial Assets, Security Brokers and Dealers) from FRED.
- Download FL664190005 (Total Liabilities, Security Brokers and Dealers) from FRED.
- Book equity proxy = FL664090005 − FL664190005
- Book leverage = FL664090005 / (FL664090005 − FL664190005)
- AEM implied capital = 1 / book_leverage
- AEM leverage factor = seasonally adjusted growth rate of book_leverage: compute as `log(leverage_t / leverage_{t-1}) × 4` (annualized), then apply X-13ARIMA-SEATS seasonal adjustment or use the published series if available.

**Alternative**: Accept a pre-downloaded CSV file path as `source` parameter. The CSV should have columns `[date, aem_leverage, aem_levfac]`.

**FRED series IDs**:
- `FL664090005`: "Security Broker-Dealers; Total Financial Assets"
- Note: These Flow of Funds series may not be directly on FRED; they come from the Fed's DDP (Data Download Program) at https://www.federalreserve.gov/releases/z1/. Provide a download helper or accept CSV.

**Returns**: DataFrame with columns `[date, aem_leverage, aem_capital, aem_levfac]` at quarterly frequency.

### Function: `load_hkm_public_data(filepath: str | None = None) -> pd.DataFrame`

**Purpose**: Load the public HKM factor data from Asaf Manela's website as a reference series.

**URL**: `http://apps.olin.wustl.edu/faculty/manela/hkm/intermediary-capital-ratio/`

**Returns**: DataFrame with columns `[date, eta, eta_delta]` at quarterly frequency, 1970Q1–2012Q4.

---

## 8. Macro Module (`hkm/data/macro.py`)

### Function: `get_ep_ratio(start_date: str, end_date: str) -> pd.Series`

**Purpose**: Quarterly S&P 500 earnings-to-price ratio from Shiller's data.

**Source**: Download from Robert Shiller's website (http://www.econ.yale.edu/~shiller/data/ie_data.xls or CSV version). The relevant column is the E/P ratio (inverse of CAPE, or the monthly E/P from the raw data).

**Processing**: Convert monthly to quarterly by taking the last month of each quarter. Return as pd.Series indexed by quarter-end dates.

**Returns**: pd.Series `[date → ep_ratio]`

### Function: `get_unemployment(start_date: str, end_date: str) -> pd.Series`

**Purpose**: Quarterly U.S. civilian unemployment rate.

**Source**: FRED series `UNRATE` (Bureau of Labor Statistics, monthly). Convert to quarterly by taking the last month of each quarter.

**Returns**: pd.Series `[date → unemployment_rate]` (as a percentage, e.g., 6.5 means 6.5%)

### Function: `get_gdp(start_date: str, end_date: str) -> pd.Series`

**Purpose**: Quarterly U.S. real GDP (seasonally adjusted annual rate).

**Source**: FRED series `GDPC1` (Bureau of Economic Analysis, quarterly).

**Returns**: pd.Series `[date → real_gdp]` in billions of chained 2017 dollars.

### Function: `get_nfci(start_date: str, end_date: str) -> pd.Series`

**Purpose**: Quarterly Chicago Fed National Financial Conditions Index (NFCI).

**Source**: FRED series `NFCI` (weekly). Aggregate to quarterly by taking the last observation of each quarter (week ending in or closest to the quarter-end).

**Returns**: pd.Series `[date → nfci]`

### Function: `get_market_volatility(start_date: str, end_date: str, engine=None) -> pd.Series`

**Purpose**: Quarterly realized volatility of the CRSP value-weighted stock index return.

**Source**: CRSP monthly VW index return from `crsp.msi` (field `vwretd` — value-weighted return including distributions).

**Algorithm**:
1. Pull monthly CRSP VW returns.
2. For each quarter, compute realized variance as the sum of squared monthly returns within the quarter (3 months): `RealVar_t = Σ_{m=1}^{3} r²_m` where r_m is the monthly excess return (or raw return, consistent with paper).
3. Realized volatility = sqrt(RealVar_t × 4) (annualized). Note: paper says "realized volatility of CRSP value-weighted stock index" — use the realized standard deviation of monthly returns within the quarter.

**Returns**: pd.Series `[date → realized_vol]` at quarterly frequency.

### Function: `get_all_macro(start_date: str = "1970-01-01", end_date: str = "2012-12-31") -> pd.DataFrame`

**Purpose**: Return all macro series in a single DataFrame aligned to quarterly dates.

**Returns**: DataFrame with columns `[date, ep_ratio, unemployment, gdp, nfci, market_vol]` at quarterly frequency (1970Q1–2012Q4 where available, earlier macro series may extend further back).

---

## 9. Table 2 Module (`hkm/tables/table2.py`)

### Function: `compute_table2(engine=None, start_year: int = 1960, end_year: int = 2012) -> pd.DataFrame`

**Purpose**: Compute JFE Table 2 — monthly ratios of primary dealer aggregates to comparison group aggregates, averaged over three sample periods.

**Algorithm**:

**Step 1: Prepare primary dealer universe (numerator)**
For each calendar month from January 1960 to December 2012:
1. Identify active US-based primary dealers (using `dealers.get_active_dealers(month_end, us_only=True)`).
2. Get market equity from CRSP for those permnos: `ME_PD_t = Σ_{i∈PD_US} ME_{i,t}`
3. Get most recent Compustat quarterly data for those gvkeys: `AT_PD_t`, `BD_PD_t` (= AT − CEQ), `BE_PD_t` (= CEQ).

**Step 2: Prepare comparison group denominators**
For each calendar month, for each comparison group G ∈ {BD, Banks, All}:
1. Get market equity: `ME_G_t = Σ_{j∈G} ME_{j,t}` (using CRSP for all firms in group G)
2. Get most recent Compustat data: `AT_G_t`, `BD_G_t`, `BE_G_t`

**Step 3: Compute monthly ratios for each of four items**
```
total_assets_ratio_BD_t = AT_PD_t / AT_BD_t
total_assets_ratio_Banks_t = AT_PD_t / AT_Banks_t
total_assets_ratio_Cmpust_t = AT_PD_t / AT_All_t
# (and similarly for BD, BE, ME)
```

**Step 4: Average over sub-periods**
For each sub-period (1960–2012, 1960–1990, 1990–2012):
- Average the monthly ratio over all months in the sub-period where both numerator and denominator are available.

**Step 5: Format output**
Build a DataFrame with 3 rows (periods) × 12 columns (4 items × 3 comparison groups), matching the structure of JFE Table 2.

**Returns**: pd.DataFrame with:
- Index: `["1960-2012", "1960-1990", "1990-2012"]`
- Columns: MultiIndex with level 0 = item name, level 1 = comparison group:
  - `("total_assets", "BD")`, `("total_assets", "Banks")`, `("total_assets", "Cmpust.")`
  - `("book_debt", "BD")`, `("book_debt", "Banks")`, `("book_debt", "Cmpust.")`
  - `("book_equity", "BD")`, `("book_equity", "Banks")`, `("book_equity", "Cmpust.")`
  - `("market_equity", "BD")`, `("market_equity", "Banks")`, `("market_equity", "Cmpust.")`

### Function: `print_table2(df: pd.DataFrame) -> str`

Formats the DataFrame as a publication-style table with 3 decimal places, matching the layout of JFE Table 2. Returns a string.

---

## 10. Table 3 Module (`hkm/tables/table3.py`)

### Function: `compute_table3(engine=None, start_date: str = "1970-01-01", end_date: str = "2012-12-31") -> tuple[pd.DataFrame, pd.DataFrame]`

**Purpose**: Compute JFE Table 3 — pairwise correlations of capital ratio levels (Panel A) and factor innovations (Panel B) with macro variables.

**Algorithm**:

**Step 1: Build all level series (quarterly)**
Collect the following quarterly time series, aligned to the same quarter-end dates over 1970Q1–2012Q4:
- `eta`: intermediary market capital ratio (from `intermediary.build_capital_ratio()`)
- `book_eta`: intermediary book capital ratio (from `intermediary.build_book_capital_ratio()`)
- `aem_leverage`: AEM broker-dealer book leverage from Flow of Funds (from `intermediary.load_aem_series()`)
- `ep_ratio`: S&P 500 earnings-to-price ratio (from `macro.get_ep_ratio()`, last month of each quarter)
- `unemployment`: unemployment rate (from `macro.get_unemployment()`, last month of each quarter)
- `gdp`: real GDP level (from `macro.get_gdp()`, already quarterly)
- `nfci`: Chicago Fed NFCI (from `macro.get_nfci()`, last week of each quarter)
- `market_vol`: realized volatility of CRSP VW returns (from `macro.get_market_volatility()`)

**Step 2: Build all factor/innovation series (quarterly)**
- `eta_delta`: intermediary capital risk factor = AR(1) innovation / lagged η (from `intermediary.build_capital_factor()`)
- `book_eta_factor`: AR(1) innovation of book capital ratio / lagged (from `intermediary.build_book_capital_factor()`)
- `aem_levfac`: AEM leverage factor = seasonally adjusted growth rate of AEM leverage
- `market_excess_return`: quarterly CRSP VW return minus T-bill rate (from `crsp.msi` and FRED `TB3MS`)
- `ep_growth`: Δ log(ep_ratio) (log change, quarterly)
- `unemployment_growth`: Δ log(unemployment) (log change, quarterly)
- `gdp_growth`: Δ log(gdp) (log change = real GDP growth rate, quarterly)
- `nfci_change`: Δ nfci (first difference, since NFCI is already a standardized index)
- `market_vol_growth`: Δ log(market_vol) (log change, quarterly)

**Step 3: Panel A correlations (levels)**

Compute Pearson correlation matrix between:
- Column variables: `[eta, book_eta, aem_leverage]`
- Row variables: `[eta, book_eta, aem_leverage, ep_ratio, unemployment, gdp, nfci, market_vol]`

Use `pd.DataFrame.corr()` (pairwise complete cases). Report correlations rounded to 2 decimal places.

**Step 4: Panel B correlations (factors)**

Compute Pearson correlation matrix between:
- Column variables: `[eta_delta, book_eta_factor, aem_levfac]`
- Row variables: `[eta_delta, book_eta_factor, aem_levfac, market_excess_return, ep_growth, unemployment_growth, gdp_growth, nfci_change, market_vol_growth]`

Use `pd.DataFrame.corr()` (pairwise complete cases). Report correlations rounded to 2 decimal places.

**Returns**: Tuple of (panel_a_df, panel_b_df) — each a pd.DataFrame with row/column structure matching JFE Table 3.

### Function: `print_table3(panel_a: pd.DataFrame, panel_b: pd.DataFrame) -> str`

Formats both panels as a publication-style table with 2 decimal places. Returns a string.

---

## 11. Utilities (`hkm/utils.py`)

### Function: `quarter_end(date: pd.Timestamp) -> pd.Timestamp`

Returns the last calendar day of the quarter containing `date`. Uses `pd.offsets.QuarterEnd(0)`.

### Function: `to_quarterly(series: pd.Series, method: str = "last") -> pd.Series`

Converts a monthly or daily pd.Series to quarterly frequency by taking the last observation of each quarter.

### Function: `log_change(series: pd.Series) -> pd.Series`

Computes `log(x_t / x_{t-1})` = `log(x_t) − log(x_{t-1})`. Returns pd.Series with same index, first element NaN.

### Function: `align_to_quarter_end(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame`

Converts the date column to quarter-end dates (last day of March/June/September/December) using `pd.offsets.QuarterEnd`. Used to align data from different sources to the same quarterly grid.

---

## 12. Input Validation Contracts

### All WRDS pull functions
- Raise `ValueError` if `start_date > end_date`
- Raise `ConnectionError` if WRDS connection fails (from `wrds_connect.query`)
- Return empty DataFrame (with correct columns) if no rows match, do not raise error

### `build_capital_ratio()`
- Raise `ValueError` if fewer than 10 quarters of data are returned (likely a data pull failure)
- Raise `RuntimeWarning` (log warning) if any quarter has fewer than 5 primary dealers with data

### `compute_table2()`
- Raise `ValueError` if the PD aggregate total assets is zero for any month (indicates missing dealer data)
- Validate that all ratios are in (0, 1] — raise `ValueError` if any ratio > 1 (PDs cannot exceed the total sector)

### `compute_table3()`
- Require that the common sample of `eta`, `book_eta`, and `aem_leverage` covers at least 100 quarters; raise `ValueError` otherwise
- Drop NaN rows pairwise before computing each correlation coefficient (do not drop the full row)

---

## 13. Output Contracts

### `compute_table2()` output
- Returns pd.DataFrame, shape (3, 12)
- All values are floats in (0.0, 1.0]
- No NaN values (if a ratio cannot be computed for a sub-period, raise `ValueError`)
- Index = `["1960-2012", "1960-1990", "1990-2012"]`
- Column MultiIndex as specified in §9

### `compute_table3()` output — each panel
- Returns pd.DataFrame with float values in [−1.0, 1.0]
- Diagonal values in Panel A self-correlations = 1.00 (within numerical precision)
- No NaN values for the primary intermediary ratio series
- Some macro variable cells may be NaN at the start of the sample (acceptable for alignment reasons)

---

## 14. Write Surface

Builder may only create or modify:
```
hkm/                   # entire package directory (new)
tests/                 # test directory (new)
pyproject.toml         # package config (new)
README.md              # usage docs (new)
```

Builder must NOT modify:
- Any existing StatsClaw framework files (agents/, skills/, profiles/, templates/)
- CLAUDE.md
- Any file in `.repos/workspace/`

---

## 15. Implementation Notes (Python-Package Profile)

- Use `pandas` DataFrames throughout; avoid raw loops over rows — use vectorized operations.
- All date columns should be `pd.Timestamp` or `pd.DatetimeIndex` type, not strings.
- Use `pd.merge()` for data joins; specify `how` and `on` explicitly.
- Use `statsmodels.OLS` for the AR(1) estimation (fits natively with pandas Series).
- FRED data via `pandas_datareader.data.DataReader(series_id, "fred", start, end)`.
- All monetary amounts from Compustat are in millions of dollars; from CRSP (`shrout × |prc|`) the result is in thousands of dollars. Before computing ratios, ensure all amounts for a given comparison group use the same units (convert all to millions: Compustat already in millions; CRSP ME in thousands → divide by 1000 to get millions).
- Module-level `logger = logging.getLogger(__name__)` for diagnostic output; do not print to stdout from library code.
- Type annotations on all public functions.
- `__all__` defined in each `__init__.py` listing public API.

---

## 16. Reference Values (for builder self-check, not for tests)

After implementation, builder may manually check a few cells:

**Table 2 reference (1960–2012 row)**:
- Total assets / BD ≈ 0.959
- Total assets / Banks ≈ 0.596
- Total assets / Cmpust. ≈ 0.240
- Market equity / BD ≈ 0.911

**Table 3 Panel A reference (selected correlations)**:
- corr(η, book_η) ≈ 0.50
- corr(η, AEM leverage) ≈ −0.42
- corr(η, E/P) ≈ −0.83

**Table 3 Panel B reference (selected correlations)**:
- corr(η^Δ, book capital factor) ≈ 0.30
- corr(η^Δ, market excess return) ≈ 0.78
- corr(η^Δ, E/P growth) ≈ −0.75

These are from JFE Tables 2 and 3 of the paper (pp. 7 and 9).
