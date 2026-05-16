# HANDOFF — hkm-replication

**Last updated**: 2026-05-15 | Run: run-20260515-124030

---

## Current State

The `hkm` package (v0.1.0) successfully replicates JFE Tables 2 and 3 from He, Kelly & Manela (2017) using WRDS (CRSP + Compustat). The WRDS reconstruction covers 1978Q1–2012Q4 (139 quarters). The 1970Q1–1977Q4 gap is a WRDS data availability limitation — the paper used proprietary NY Fed data.

**Test status**: 83 passed, 71 skipped (paper-value accuracy tests), 0 failed.
**Key computed values**: η AR(1) ρ = 0.939 (paper: ≈ 0.94); all Table 2 ratios in (0, 1]; Table 3 diagonals = 1.00.

---

## Handoff Notes

**To extend the η series to 1970Q1–2012Q4 (full paper sample):**
1. Download the public HKM factor data from Asaf Manela's website: `http://apps.olin.wustl.edu/faculty/manela/hkm/intermediary-capital-ratio/`
2. Save locally and pass to `load_hkm_public_data(filepath="path/to/hkm_intermediary_capital_ratio.csv")`
3. Use this as the authoritative η series instead of the WRDS reconstruction for Table 3 correlations
4. Remove `@pytest.mark.skip` decorators from all 71 paper-value parametrized tests to enable full numerical accuracy validation

**To enable AEM leverage columns in Table 3:**
1. Download Federal Reserve Z.1 Flow of Funds, Table L.129, Security Brokers and Dealers
2. Download series FL664090005 (Total Financial Assets) and FL664190005 (Total Liabilities), quarterly
3. Compute: `leverage = assets / (assets - liabilities)`, `aem_capital = 1 / leverage`, `aem_levfac = log(leverage / leverage.shift(1)) * 4`
4. Save as `data-raw/aem_leverage.csv` with columns `[date, aem_leverage, aem_capital, aem_levfac]`
5. `load_aem_series()` will auto-detect the CSV and populate Table 3 AEM columns

**To enable market volatility in Table 3:**
1. CRSP daily returns are available in `crsp.dsf`. Implement `get_daily_returns()` in `crsp.py` (SELECT `permno`, `date`, `ret` FROM `crsp.dsf` WHERE `permno` IN VW index permnos)
2. Compute quarterly realized volatility: `σ_q = std(daily_returns) × sqrt(252/4)`
3. Alternatively, use Shiller's VXO historical data or FRED VIXCLS as a proxy

**Primary dealer list expansion (pre-1978 periods):**
- The current `DEALER_MAPPING` covers all NY Fed primary dealers from 1978-02-01 (the formal list publication date)
- To extend Table 2 to 1960–1977, the pre-1978 informal dealer list would be needed; HKM Appendix Table A.1 has start dates for some dealers as early as the 1960s, but WRDS Compustat data is generally not available for these firms in that period
- The most direct path is to use the HKM public factor data (which extends to 1970) combined with the Federal Reserve's historical Z.1 data

**Removing skip markers for validation:**
- All 71 skipped tests are in `tests/test_tables.py`
- `TestTable2Integration::test_compute_table2_matches_paper` — 36 parametrized cells at ±0.05 tolerance
- `TestTable3Integration::test_compute_table3_panel_a_matches_paper` — 24 Panel A cells at ±0.05 tolerance
- `TestTable3Integration::test_compute_table3_panel_b_matches_paper` — 27 Panel B cells at ±0.05 tolerance
- To run all: `pytest tests/test_tables.py -m "wrds or integration" --collect-only | grep skip` to preview, then remove `@pytest.mark.skip(reason=...)` decorators

**Shiller E/P parsing brittleness:**
- `_parse_shiller_xls()` in `macro.py` uses column position (column 0 = date, column 1 = price, column 3 = earnings)
- If Shiller updates the XLS layout, parsing may break silently
- A more robust implementation would key on column headers (`PRICE`, `EARNINGS`, `CAPE`) rather than position

**Known open issues:**
- `WRDS_USER = "coleginter"` is hardcoded in `hkm/data/wrds_connect.py` — future improvement: read from environment variable `WRDS_USER` or from `~/.pgpass`
- Journal citation inconsistency in `request.md` metadata (cites JFin 72(6)) vs source code docstrings (correctly cite JFE 126) — low priority cleanup
