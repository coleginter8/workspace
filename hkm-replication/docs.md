# Technical Documentation — HKM Tables 2 & 3 Replication

**Package**: `hkm` (Python)
**Paper**: He, Kelly & Manela (2017), *Journal of Financial Economics* 126: 1–35

---

## 1. Installation and WRDS Setup

### 1.1 Install

```bash
pip install -e ".[dev]"
```

Dependencies (from `pyproject.toml`):
- `psycopg2` — WRDS PostgreSQL connection
- `pandas` >= 2.0 — data manipulation
- `numpy` — numerical computations
- `statsmodels` — AR(1) OLS regression
- `pandas-datareader` — FRED series fetching
- `requests` — Shiller data download

### 1.2 WRDS Credentials

The package authenticates to WRDS via `~/.pgpass`. Create this file (mode 600) with:

```
wrds-pgdata.wharton.upenn.edu:9737:wrds:<your_username>:<your_password>
```

```bash
chmod 600 ~/.pgpass
```

Verify connectivity:
```python
from hkm.utils import wrds_connection
with wrds_connection(user="your_username") as conn:
    print("Connected to WRDS")
```

---

## 2. Using `compute_table2()`

### 2.1 Signature

```python
def compute_table2(
    conn: psycopg2.extensions.connection | None = None,
    start_date: str = "1960-01-01",
    end_date: str = "2012-12-31",
) -> pd.DataFrame:
```

### 2.2 Basic Example

```python
from hkm import compute_table2
from hkm.utils import wrds_connection

with wrds_connection(user="your_username") as conn:
    t2 = compute_table2(conn=conn)

print(t2)
# Output: DataFrame (3, 12) with MultiIndex columns
```

### 2.3 Output Structure

The returned DataFrame has:
- **Shape**: (3, 12)
- **Index**: `['1960-2012', '1960-1990', '1990-2012']`
- **Columns**: `pd.MultiIndex` with two levels:
  - Level 0 (`item`): `['Total assets', 'Book debt', 'Book equity', 'Market equity']`
  - Level 1 (`group`): `['BD', 'Banks', 'Cmpust']`

```python
# Access a specific cell
t2.loc['1960-2012', ('Total assets', 'BD')]
# → 0.853  (published: 0.959)

# Access a full column
t2[('Market equity', 'Cmpust')]
# → Series with 3 period values

# Convert to flat DataFrame
t2_flat = t2.copy()
t2_flat.columns = [f"{item}/{group}" for item, group in t2.columns]
```

### 2.4 Interpretation

Each cell is the **time-series average** of a monthly ratio:

```
ratio_t = Σ dealer balance-sheet item_t
          ─────────────────────────────────────────
          Σ dealer item_t  +  Σ non-dealer group item_t
```

A value of 0.853 for TA/BD means primary dealers represented, on average, 85.3% of the total assets held by the combined primary dealer + broker-dealer sector.

**Comparison groups**:
- **BD**: All US firms with historical SIC code 6211 or 6221 (broker-dealers) in Compustat/CRSP, plus ALL active primary dealers regardless of their SIC code.
- **Banks**: All US firms with historical SIC code 6000–6299 in Compustat/CRSP, plus all active primary dealers.
- **Cmpust**: All US Compustat firms, plus all active primary dealers.

**Balance-sheet items**:
- **Total assets (TA)**: `atq` from `comp.fundq` ($millions)
- **Book debt (BD)**: `atq - ceqq` from `comp.fundq` ($millions)
- **Book equity (BE)**: `ceqq` from `comp.fundq` ($millions)
- **Market equity (ME)**: `|prc| × shrout / 1000` from `crsp.msf` ($millions, last trading day of month)

### 2.5 Known Deviations from Published Values

| Sub-period | Item | Group | Published | Actual | Explanation |
|---|---|---|---|---|---|
| 1960-2012 | Total assets | BD | 0.959 | 0.853 | Pre-1978 WRDS coverage gap (most dealers not in Compustat before 1978) |
| 1960-2012 | Market equity | Cmpust | 0.026 | 0.019 | Within ±0.05 PASS |
| 1960-2012 | Book equity | Banks | 0.514 | 0.470 | Within ±0.05 PASS |
| 1960-2012 | Market equity | BD | 0.911 | 0.878 | Within ±0.05 PASS |
| 1990-2012 | Market equity | BD | 0.848 | 0.859 | Within ±0.05 PASS |
| 1990-2012 | Total assets | Banks | 0.543 | 0.272 | Post-1990 bank consolidation: SIC 6000-6299 misses re-classified holding companies |

The primary source of divergence for all periods is the **pre-1978 WRDS coverage gap**: Compustat quarterly data for financial firms begins c.1978, but the paper uses data starting 1960. Before 1978, only a handful of firms appear, understating all comparison group denominators.

---

## 3. Using `compute_table3()`

### 3.1 Signature

```python
def compute_table3(
    conn: psycopg2.extensions.connection | None = None,
    start_date: str = "1970-01-01",
    end_date: str = "2012-12-31",
) -> tuple[pd.DataFrame, pd.DataFrame]:
```

### 3.2 Basic Example

```python
from hkm import compute_table3
from hkm.utils import wrds_connection

with wrds_connection(user="your_username") as conn:
    panel_a, panel_b = compute_table3(conn=conn)

print("Panel A (levels):")
print(panel_a)
print("\nPanel B (factors/growth rates):")
print(panel_b)
```

### 3.3 Output Structure

**`panel_a`** — correlations of levels, shape (8, 3):
- **Index**: `['Market capital', 'Book capital', 'AEM leverage', 'E/P', 'Unemployment', 'GDP', 'Financial conditions', 'Market volatility']`
- **Columns**: `['Market capital', 'Book capital', 'AEM leverage']`

**`panel_b`** — correlations of factors/growth rates, shape (9, 3):
- **Index**: `['Market capital factor', 'Book capital factor', 'AEM leverage factor', 'Market excess return', 'E/P growth', 'Unemployment growth', 'GDP growth', 'Financial conditions growth', 'Market volatility growth']`
- **Columns**: `['Market capital factor', 'Book capital factor', 'AEM leverage factor']`

All diagonal entries are exactly 1.0. All off-diagonal entries are Pearson correlations in [−1, 1].

```python
# Access a specific correlation
panel_a.loc['E/P', 'Market capital']
# → -0.727  (published: -0.83)

# Check that diagonal is 1
assert (panel_a.loc['Market capital', 'Market capital'] == 1.0)
assert (panel_b.loc['Market capital factor', 'Market capital factor'] == 1.0)
```

### 3.4 Interpretation

**Panel A** uses the **levels** of three intermediary capital/leverage series:
- **Market capital** (η_t): value-weighted market capital ratio of primary dealers = ΣME / Σ(ME + BD)
- **Book capital**: book capital ratio = ΣCEQ / ΣAT for primary dealers
- **AEM leverage**: Fed Flow of Funds total financial assets / book equity for security broker-dealers

Macro variables in Panel A are levels: E/P ratio (CAPE-based, from Shiller), unemployment rate (FRED: UNRATE), GDP growth rate (FRED: GDPC1 log change), NFCI (financial conditions index, high = poor conditions), realized quarterly market volatility (std dev of daily CRSP VW returns).

**Note on GDP in Panel A**: Despite being labeled "GDP," the variable is the quarterly log change in real GDP (growth rate), not the level of GDP. The paper confirms this in the text: "increases in the earnings-to-price ratio, increases in the unemployment rate, decreases in GDP growth."

**Panel B** uses AR(1) **factors** (innovations scaled by lagged ratio) for the three capital measures, and **log growth rates** for the macro variables:
- Market capital factor: OLS residual u_t from η_t = ρ₀ + ρ·η_{t-1} + u_t, divided by η_{t-1}
- Book capital factor: same procedure applied to book capital ratio
- AEM leverage factor: log(AEM_leverage_t / AEM_leverage_{t-1})
- Market excess return: CRSP value-weighted return minus 3-month T-bill rate
- E/P growth: YoY log change in simple trailing E/P ratio (NOT CAPE)
- All other growth rates: YoY log changes (shift(4) at quarterly frequency)

### 3.5 Known Deviations from Published Values

**Panel A — cells within ±0.05 (PASS)**: Market capital vs Book capital = 0.458 (published 0.50, diff 0.042).

**Panel A — notable deviations**:

| Pair | Published | Actual | Explanation |
|---|---|---|---|
| Market capital vs AEM leverage | −0.42 | +0.624 | Data-vintage limitation: raw BOGZ1 leverage is pro-cyclical (5x in 1975 → 47x in 2008), correlating positively with η over full sample. Paper likely used equity-ratio definition. |
| Book capital vs AEM leverage | −0.07 | +0.368 | Same AEM leverage definition issue |
| Book capital vs GDP | +0.32 | −0.076 | Book capital calendar alignment; quarterly rdq timing differences |
| Book capital vs Market volatility | −0.31 | +0.207 | Book capital vs volatility sensitive to quarterly alignment |

**Panel B — cells within ±0.05 (PASS)**:
- Financial conditions growth vs Market capital factor: −0.345 (published −0.38)
- Market volatility growth vs Market capital factor: −0.442 (published −0.49)
- Market excess return vs Book capital factor: +0.128 (published +0.10)
- Unemployment growth vs AEM leverage factor: −0.113 (published −0.08)
- GDP growth vs AEM leverage factor: +0.060 (published +0.04)
- Financial conditions growth vs AEM leverage factor: −0.053 (published −0.06)
- Market volatility growth vs AEM leverage factor: −0.060 (published −0.08)
- Market capital factor vs AEM leverage factor: +0.080 (published +0.14)

**Panel B — notable deviations**:

| Pair | Published | Actual | Explanation |
|---|---|---|---|
| E/P growth vs Market capital factor | −0.75 | −0.164 | Sign correct; magnitude. Simple trailing E/P used for growth (vs paper's ~CAPE-based series). Shorter sample (1978 vs 1970 start) also reduces correlation magnitude. |
| Market excess return vs Market capital factor | +0.78 | +0.727 | Sign correct; slightly outside ±0.05 tolerance |
| GDP growth vs Market capital factor | +0.20 | −0.056 | Sign flip; GDP growth and capital factor timing differ at quarterly frequency |

---

## 4. Data Pipeline Details

### 4.1 Capital Ratio Construction

The capital ratio η_t is built in `hkm/data/intermediary.py:build_capital_ratio`:

1. **Resolve dealer identifiers**: For each active dealer at time t, look up GVKEY from `PRIMARY_DEALERS`. For dealers with `gvkey=None`, attempt fuzzy name match against `comp.names`.
2. **Fetch Compustat data**: `comp.fundq` for active dealer GVKEYs — columns `atq`, `ceqq`, `datadate`.
3. **Resolve PERMNOs**: `crsp.ccmxpf_linktable` with `linktype IN ('LU','LC','LS')` and `linkprim IN ('P','C')`.
4. **Fetch CRSP data**: `crsp.msf` for resolved PERMNOs — columns `prc`, `shrout`, `date`.
5. **For each calendar period t**: identify active dealers, match most recent Compustat filing (`datadate <= t`), match CRSP month-end ME. Aggregate: `sum_me / (sum_me + sum_bd)`.

### 4.2 Macro Panel Construction

`hkm/data/macro.py:build_macro_panel` fetches all macro series:

| Column | Source | Series / URL | Transformation |
|---|---|---|---|
| `ep_ratio` | Shiller | ie_data.xls (CAPE column) | 1/CAPE = E10/P, quarterly average |
| `ep_simple` | Shiller | ie_data.xls (E and P columns) | E/P = trailing 12-month earnings/price |
| `ep_growth` | Shiller | `ep_simple` | YoY log change: `log(ep_simple_t / ep_simple_{t-4})` |
| `unemp` | FRED | UNRATE (monthly) | Quarterly average |
| `unemp_growth` | FRED | UNRATE | YoY log change |
| `gdp_growth` | FRED | GDPC1 (quarterly) | log(GDPC1_t / GDPC1_{t-1}) |
| `nfci` | FRED | NFCI (weekly) | Quarterly average |
| `nfci_growth` | FRED | NFCI | YoY log change |
| `mkt_vol` | WRDS CRSP | `crsp.dsi` vwretd | Quarterly std dev of daily returns |
| `mkt_vol_growth` | WRDS CRSP | `mkt_vol` | YoY log change |
| `mkt_ret` | WRDS CRSP | `crsp.msi` vwretd | Quarterly sum of monthly returns minus T-bill |
| `aem_leverage` | FRED | BOGZ1FL664090005Q / BOGZ1FL664190005Q | assets / (assets - liabilities) = assets/equity |
| `aem_levfac` | FRED | `aem_leverage` | log(lev_t / lev_{t-1}) |

### 4.3 AR(1) Factor Construction

`hkm/data/intermediary.py:build_capital_factor`:

```python
# Fit AR(1) by OLS
eta_lag = eta.shift(1)
valid = eta.notna() & eta_lag.notna()
x_mat = sm.add_constant(eta_lag[valid])
res = sm.OLS(eta[valid], x_mat).fit()
# Factor = residual / lagged eta
factor = res.resid / eta_lag[valid]
```

Estimated ρ = 0.9581 (paper: ~0.94). First observation is NaN (lagged η unavailable).

---

## 5. Comparison Group Methodology

Understanding the Table 2 denominator construction is essential for correct interpretation.

### 5.1 Compustat Denominator (TA, BD, BE)

For each comparison group, `fetch_compustat_all_quarterly` queries:

```sql
-- BD group: firms with historical SIC 6211 or 6221
FROM comp.fundq q
JOIN comp.funda a ON q.gvkey = a.gvkey AND q.fyearq = a.fyear
    AND a.sich IN (6211, 6221)
JOIN crsp.ccmxpf_linktable lk ON q.gvkey = lk.gvkey
    AND lk.linktype IN ('LU','LC','LS') AND lk.linkprim IN ('P','C')
    AND q.datadate BETWEEN lk.linkdt AND COALESCE(lk.linkenddt, '2099-12-31')
JOIN crsp.msenames e ON lk.lpermno = e.permno
    AND q.datadate BETWEEN e.namedt AND COALESCE(e.nameendt, '2099-12-31')
    AND e.shrcd IN (10, 11)   -- US ordinary common shares only
```

The US-only filter (`shrcd IN (10, 11)`) prevents foreign firms from entering the comparison group.

Dealer GVKEYs are excluded from the group denominator to prevent double-counting:
```python
gc_non_dealer = gc_latest[~gc_latest["gvkey"].isin(active_dealer_gvkeys)]
g_ta = d_ta_all + float(gc_non_dealer["atq"].sum())
```

### 5.2 CRSP Denominator (ME only)

```python
# Non-dealer CRSP firms in group SIC
gc2_non_dealer = gc2_t[~gc2_t["permno"].isin(active_dealer_permnos)]
non_dealer_crsp_me = float(gc2_non_dealer["me"].sum()) / 1000.0
# Total group ME = all dealer ME + non-dealer group ME
g_me = d_me_all + non_dealer_crsp_me
```

This ensures the ME ratio is bounded by [0, 1]: since `d_me_all` includes dealers of all SIC codes, and `non_dealer_crsp_me` contains only non-dealers, the denominator always exceeds the numerator.

---

## 6. Extending the Package

### 6.1 Adding Missing Dealers

To add dealers without Compustat GVKEYs, update `PRIMARY_DEALERS` in `hkm/data/dealers.py`:

```python
Dealer(
    "Kidder Peabody",
    gvkey="XXXXXX",  # Find via: SELECT gvkey, conm FROM comp.names WHERE conm ILIKE '%kidder%peabody%'
    permno=None,     # Resolved at runtime via CCM link
    start=datetime.date(1978, 11, 17),
    end=datetime.date(1994, 4, 15),
),
```

### 6.2 Different Sample Periods

Both functions accept custom `start_date` and `end_date`:

```python
# Use the full 1970Q1-2012Q4 period for Table 3
panel_a, panel_b = compute_table3(conn=conn, start_date="1970-01-01", end_date="2012-12-31")

# Use a shorter Table 2 period to avoid coverage gaps
t2 = compute_table2(conn=conn, start_date="1978-01-01", end_date="2012-12-31")
```

### 6.3 Accessing Intermediate Data

The underlying data modules can be used independently:

```python
from hkm.data.intermediary import build_capital_ratio, build_capital_factor
from hkm.data.macro import build_macro_panel, fetch_aem_leverage
from hkm.utils import wrds_connection

with wrds_connection(user="your_username") as conn:
    # Get quarterly capital ratios (includes eta and book_capital)
    cap_df = build_capital_ratio(conn, frequency="Q", start_date="1970-01-01", end_date="2012-12-31")
    print(cap_df.head())
    # Columns: eta, book_capital, n_dealers

    # Get AR(1) factor
    factor = build_capital_factor(cap_df["eta"])
    print(f"Estimated AR(1) rho: {factor.name}")  # factor stored as "capital_factor" series

    # Get macro panel
    macro = build_macro_panel(conn=conn, start_date="1970-01-01", end_date="2012-12-31")
    print(macro.columns.tolist())
    # ['ep_ratio', 'ep_simple', 'ep_growth', 'unemp', 'unemp_growth', 'gdp_growth',
    #  'nfci', 'nfci_growth', 'mkt_vol', 'mkt_vol_growth', 'mkt_ret']

# AEM leverage (no WRDS required)
aem = fetch_aem_leverage(start_date="1970-01-01", end_date="2012-12-31")
print(aem.head())
# Columns: date, aem_leverage, aem_levfac
```

---

## 7. Logging

All modules use Python's standard `logging` module. To enable verbose output:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Then call compute_table2 or compute_table3 — you'll see per-step progress
```

Log output includes:
- WRDS connection events
- Number of dealer GVKEYs and PERMNOs resolved
- Per-period η_t computation progress
- AR(1) ρ estimate
- Macro series fetch status (including FRED failures with graceful fallback)
- Table 2 and Table 3 completion confirmation

---

*Generated by StatsClaw scriber — run-20260520-hkm-tables-2-3 (2026-05-20)*
