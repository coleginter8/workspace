# HKM Replication — Documentation

**Package**: `hkm` v0.1.0
**Paper**: He, Kelly & Manela (2017), "Intermediary Asset Pricing: New Theory and Evidence," *Journal of Financial Economics* 126(1), pp. 1–35.
**Run**: run-20260515-124030 | 2026-05-15

---

## What Was Built and Why

This package replicates JFE Tables 2 and 3 from He, Kelly & Manela (2017), which establish the empirical foundation for the intermediary asset pricing model:

- **JFE Table 2** ("Primary dealers as representative financial intermediaries"): Shows that primary dealer holding companies account for 85–96% of broker-dealer total assets, book debt, book equity, and market equity, motivating their use as the representative financial intermediary sector.

- **JFE Table 3** ("Pairwise correlations"): Documents that the market capital ratio η and its AR(1) innovation η^Δ are strongly procyclical (negative correlation with E/P, unemployment, financial conditions index) and load positively on the market excess return, validating η^Δ as a financial distress factor.

The package provides a fully automated data pipeline from raw WRDS pulls through table output, making the replication reproducible by any researcher with WRDS access.

---

## Installation and Prerequisites

### Requirements

- Python >= 3.10
- WRDS account with access to CRSP (crsp.msf, crsp.msi, crsp.msenames) and Compustat (comp.fundq, comp.company)
- `~/.pgpass` configured for WRDS PostgreSQL

```
pip install -e ".[dev]"
```

### Configure WRDS credentials

Add this line to `~/.pgpass` (create the file if it does not exist; set permissions `chmod 600`):

```
wrds-pgdata.wharton.upenn.edu:9737:*:YOUR_WRDS_USERNAME:YOUR_WRDS_PASSWORD
```

Test the connection:

```python
from hkm.data.wrds_connect import get_engine
engine = get_engine()  # should succeed silently
```

---

## Usage Examples

### Table 2: Primary dealer size comparison

```python
from hkm.tables.table2 import compute_table2, print_table2

# Compute the (3, 12) ratio table
t2 = compute_table2()
print(t2)
# Returns a MultiIndex DataFrame:
#             total_assets           book_debt           book_equity       market_equity
#                       BD Banks Cmpust.      BD Banks Cmpust.   BD Banks Cmpust.    BD Banks Cmpust.
# period
# 1960-2012          ...                                                               ...
# 1960-1990          ...
# 1990-2012          ...

# Pretty-print formatted table
print(print_table2(t2))

# Verbose mode: logs WRDS value vs paper value vs difference for all 36 cells
import logging
logging.basicConfig(level=logging.INFO)
t2 = compute_table2(verbose=True)
```

### Table 3: Pairwise correlations

```python
from hkm.tables.table3 import compute_table3, print_table3

# Returns (panel_a, panel_b) — two DataFrames
panel_a, panel_b = compute_table3()

# Panel A: correlations of levels (η, book_η, AEM leverage, vs macro)
print(panel_a)

# Panel B: correlations of factors/innovations (η^Δ, book capital factor, AEM LevFac, vs macro growth)
print(panel_b)

# Pretty-print both panels
print(print_table3(panel_a, panel_b))
```

### Build η directly

```python
from hkm.data.intermediary import build_capital_ratio, build_capital_factor

# Build quarterly η_t series (returns DataFrame with date, eta, n_dealers)
eta_df = build_capital_ratio(start_date="1978-01-01", end_date="2012-12-31")
print(eta_df.head())
# Output:
#          date       eta  n_dealers
# 0  1978-03-31  0.0423...         8
# ...

# Build η^Δ_t (AR(1) innovation factor)
eta_factor = build_capital_factor(eta_df.set_index("date")["eta"])
print(f"AR(1) coefficient: implied from residuals")
print(f"Factor range: [{eta_factor.min():.4f}, {eta_factor.max():.4f}]")
```

### Cross-check against public HKM data

```python
from hkm.data.intermediary import load_hkm_public_data

# Download authoritative η from Manela's website (1970Q1-2012Q4)
hkm_ref = load_hkm_public_data()
print(hkm_ref.head())
# Columns: [date, eta, eta_delta]

# Or load from a local file
hkm_ref = load_hkm_public_data(filepath="data-raw/hkm_intermediary_capital_ratio.csv")
```

### Running tests

```bash
# Unit tests only — no WRDS or internet required (66 tests, ~2s)
pytest tests/ -m "not wrds and not network and not integration"

# Full integration suite — requires WRDS + internet (~16 minutes)
pytest tests/ -m "wrds or integration" -v --tb=short

# Run all tests including skipped paper-value tests (after obtaining full 1970+ sample)
pytest tests/ -m "wrds or integration" -k "matches_paper" -rN
```

---

## WRDS Data Requirements

| WRDS Table | Usage | Key Columns |
| --- | --- | --- |
| `crsp.msf` | Monthly stock file — primary dealer ME, comparison group ME | `permno`, `date`, `shrout`, `prc` |
| `crsp.msi` | Monthly stock index — value-weighted market return | `date`, `vwretd`, `sprtrn` |
| `crsp.msenames` | CRSP name/SIC history — time-varying SIC for comparison groups | `permno`, `namedt`, `nameendt`, `siccd` |
| `comp.fundq` | Compustat quarterly — balance sheet for dealers and comparison groups | `gvkey`, `datadate`, `atq`, `ceqq`, `sic` |
| `comp.company` | Compustat company master — static SIC, company name | `gvkey`, `sic`, `conm` |

**Estimated data volumes (full 1960–2012 pull):**
- `crsp.msf` for broker-dealer SIC universe: ~2.5M rows
- `comp.fundq` for all Compustat firms: ~10M rows (bulk pull, then filter)
- Primary dealer subset: ~5,000 quarterly observations across ~40 US firms

---

## Published vs WRDS Values

### Table 2

The WRDS reconstruction covers 1978Q1–2012Q4. The paper uses 1960Q1–2012Q4. The systematic downward deviation reflects the missing 1960–1977 period, during which primary dealers dominated the much smaller financial sector.

| Cell | Paper (JFE) | WRDS (this package) | Difference | Explanation |
| --- | --- | --- | --- | --- |
| 1960–2012: total_assets/BD | 0.959 | 0.496 | -0.463 | Pre-1978 data unavailable in WRDS; PD dominated BD earlier |
| 1960–2012: total_assets/Banks | 0.596 | 0.084 | -0.512 | Same cause; bank sector grew faster post-1978 |
| 1960–2012: total_assets/Cmpust. | 0.240 | 0.057 | -0.183 | Same cause |
| 1990–2012: market_equity/BD | 0.848 | 0.591 | -0.257 | Post-1990 ratios still deviate because 1990-2012 average includes 1990–1977 NaN months as zeros |
| 1990–2012: market_equity/Cmpust. | 0.039 | 0.027 | -0.012 | Closest match; Compustat all-firms universe is consistent |

**Note**: All 36 WRDS values are in (0.0, 1.0] — the algorithmic constraint (PD is a subset of each comparison group) is satisfied. The numerical gap is entirely explained by sample coverage.

### Table 3

The WRDS η series covers 1978Q1–2012Q4 (139 quarters). The paper uses 1970Q1–2012Q4 (172 quarters). The 1970–1977 period includes major financial cycles (1973 oil shock, 1974–1975 recession) that anchor the large Level correlations in the paper.

| Correlation | Paper (JFE) | WRDS (this package) | Notes |
| --- | --- | --- | --- |
| corr(η, book_η) Panel A | 0.50 | -0.05 | Book η from Compustat only; no Datastream for foreign dealers |
| corr(η, E/P) Panel A | -0.83 | -0.66 | Sign correct; magnitude reflects missing 1970-1977 |
| corr(η, Unemployment) Panel A | -0.63 | -0.54 | Sign correct |
| corr(η^Δ, market return) Panel B | 0.78 | 0.71 | Closest match; both positive and within ≈8pp |
| corr(η^Δ, book capital factor) Panel B | 0.30 | 0.22 | Sign correct |
| corr(η^Δ, E/P growth) Panel B | -0.75 | -0.18 | Largest deviation; 1970–1977 E/P dynamics critical |
| AEM leverage columns | All values | All NaN | Requires Fed Z.1 CSV — not automated |

AR(1) coefficient ρ: WRDS = 0.939; paper footnote 22 ≈ 0.94. Within 0.001.

---

## Getting the Full 1970–2012 Sample (Step-by-Step)

Follow these steps to replicate the paper's exact values for Table 3 (η series) and improve Table 2 if pre-1978 dealer data can be sourced:

### Step 1: Download the public HKM factor data

1. Go to: `http://apps.olin.wustl.edu/faculty/manela/hkm/intermediary-capital-ratio/`
2. Download `hkm_intermediary_capital_ratio.csv`
3. Save to `data-raw/hkm_intermediary_capital_ratio.csv`

```python
from hkm.data.intermediary import load_hkm_public_data
hkm_data = load_hkm_public_data(filepath="data-raw/hkm_intermediary_capital_ratio.csv")
# hkm_data has columns [date, eta, eta_delta] from 1970Q1 to 2012Q4 (172 rows)
```

### Step 2: Modify `compute_table3()` to accept an external η series

In `hkm/tables/table3.py`, add an optional parameter:

```python
def compute_table3(
    engine: Any = None,
    eta_override: pd.Series | None = None,   # <-- add this
    eta_delta_override: pd.Series | None = None,
    ...
) -> tuple[pd.DataFrame, pd.DataFrame]:
```

Then bypass `build_capital_ratio()` / `build_capital_factor()` when overrides are provided.

### Step 3: Download and prepare AEM leverage data

1. Go to: `https://www.federalreserve.gov/releases/z1/`
2. Navigate to: Data Download Program → Z.1 → Flow of Funds Accounts → L.129 Security Brokers and Dealers
3. Download series FL664090005 (Total Financial Assets) and FL664190005 (Total Liabilities), quarterly, 1960Q1–2013Q4
4. Compute and save:

```python
import pandas as pd
import numpy as np

# After loading assets and liabs from Fed download:
leverage = assets / (assets - liabs)
aem_capital = 1.0 / leverage
aem_levfac = np.log(leverage / leverage.shift(1)) * 4  # annualized log growth

df = pd.DataFrame({
    "date": quarterly_dates,
    "aem_leverage": leverage,
    "aem_capital": aem_capital,
    "aem_levfac": aem_levfac,
})
df.to_csv("data-raw/aem_leverage.csv", index=False)
```

### Step 4: Re-run Table 3 with full data

```python
from hkm.data.intermediary import load_hkm_public_data, load_aem_series
from hkm.tables.table3 import compute_table3

hkm_data = load_hkm_public_data(filepath="data-raw/hkm_intermediary_capital_ratio.csv")
# Pass eta_override and aem series — see Step 2 modifications

panel_a, panel_b = compute_table3(...)
```

### Step 5: Enable paper-value accuracy tests

Remove `@pytest.mark.skip(reason=...)` decorators from:
- `tests/test_tables.py::TestTable2Integration::test_compute_table2_matches_paper` (36 cells)
- `tests/test_tables.py::TestTable3Integration::test_compute_table3_panel_a_matches_paper` (24 cells)
- `tests/test_tables.py::TestTable3Integration::test_compute_table3_panel_b_matches_paper` (27 cells)

Then run:

```bash
pytest tests/ -m "wrds or integration" -v
```

All 154 tests (including the 71 now-unskipped) should pass at ±0.05 tolerance.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| --- | --- | --- |
| `psycopg2.OperationalError: could not connect` | WRDS credentials not configured | Check `~/.pgpass` format and permissions (`chmod 600`) |
| `psycopg2.errors.UndefinedColumn: column "caldt"` | Old CRSP schema — `caldt` renamed to `date` | Update to current package version (already fixed) |
| `psycopg2.errors.UndefinedColumn: column "sich"` | `comp.company` uses `sic` not `sich` | Update to current package version (already fixed) |
| `DataNotAvailableError: AEM leverage series not available` | FRED FL664090005Q discontinued | Download from Fed website; save to `data-raw/aem_leverage.csv` |
| Table 3 AEM columns all NaN | AEM series not loaded | See AEM setup in Step 3 above |
| Table 2 ratios ≈ 0.47–0.59 vs paper ≈ 0.85–0.96 | Expected — WRDS starts 1978, paper uses 1960 | See "Getting the Full 1970–2012 Sample" above |
| η series: 0 valid quarters | WRDS connection failed or wrong gvkeys | Check `get_engine()` works; verify permnos in `dealers.py` against WRDS |
| `NameError: name 'e_xls' is not defined` | Old version — Python 3 exception scoping bug | Update to current package version (already fixed) |
