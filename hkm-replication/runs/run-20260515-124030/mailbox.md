# Mailbox: run-20260515-124030

---

## Entry: planner → all pipelines
**Type**: HANDOFF_SUMMARY  
**Date**: 2026-05-15

---

### For builder (code pipeline)

Read `spec.md` in full. Key priorities:

1. **PRIMARY_DEALER_FIRMS in config.py must be completed**: The spec shows the format and a partial list. Builder must populate the full list of US-listed primary dealer holding companies from Table A.1 of the paper (see comprehension.md). The permnos and gvkeys should be looked up via WRDS CRSP/Compustat link tables. Start with the most important (Goldman Sachs, Morgan Stanley, Merrill Lynch, JP Morgan, Bear Stearns, Lehman Brothers) and expand.

2. **Two-mode factor construction**: Implement both `load_hkm_public_factor()` (downloads from Manela's website) and `build_capital_ratio()` / `build_capital_factor()` (reconstructs from WRDS). The integration tests will use the public factor as the primary reference; the WRDS reconstruction is for reproducibility completeness.

3. **Unit conversion critical**: ME from CRSP is in $thousands; BD from Compustat is in $millions. Convert BD to $thousands (multiply by 1000) before summing. This is documented in spec.md Section 7.

4. **External data fallback**: For sovereign bonds, options, FX, CDS, commodities — these require data from external authors. Implement the loaders to accept pre-downloaded CSV files. If file is not found, raise `FileNotFoundError` with a clear message; do NOT silently return empty data.

5. **Shanken EIV correction**: The GMM t-statistics in the paper use Shanken (1992) correction. Implement per spec.md Section 8 (simplified Shanken: multiply FM SE by sqrt(c) where c = 1 + λ' Σ_f^{-1} λ). The intercept γ does NOT get the Shanken correction (only λ's do).

6. **MAPE-R**: Requires running the joint "All" FM regression first, then computing class-specific pricing errors using the restricted estimates. This creates a dependency: `build_table3()` must run the All-pooled regression internally.

7. **Table naming**: Output DataFrames should use row labels matching exactly the strings in the test fixtures (e.g., "mean_mu_rf", "lambda_eta", "t_lambda_eta", etc.) for test compatibility.

---

### For tester (test pipeline)

Read `test-spec.py` in full. Key priorities:

1. **Tolerance levels**: See Section 6 for the complete tolerance table. The most important test is `test_table3_lambda_eta_sign()` — all λ_η must be positive. This is the core theoretical prediction.

2. **pytest marks**: Register `wrds`, `network`, and `integration` marks in `pyproject.toml`. Failing to register marks causes pytest to error.

3. **conftest.py fixtures**: The `paper_table2_values` and `paper_table3_values` fixtures contain all hard-coded reference values from the paper. These are the ground truth for numerical accuracy tests.

4. **Session fixtures for integration tests**: Use `scope="session"` for fixtures that run the full pipeline (table2_output, table3_output). This avoids running the expensive data pipeline multiple times.

5. **Missing external data = skip, not block**: If external data files (sovereign bonds, options, FX, etc.) are not present, skip those tests. But FF25 and HKM factor must auto-download — failure to download IS a block.

6. **BLOCK criteria**: See Section 8. The most critical hard blockers are: (a) negative λ_η for any class, (b) η outside [0,1], (c) Shanken c < 1.0, (d) import errors.

7. **Test execution order**: Run unit tests first (fast, no data), then WRDS tests, then integration tests. This speeds up CI feedback loops.

---

### Clarifications (No HOLD Required)

- The request says "Tables 2 and 3" which in the JFE published version correspond to the size comparison table and pairwise correlations. Based on the scope description in request.md ("summary statistics for η factor" and "cross-sectional asset pricing tests"), the targets are JFE Table 4 and JFE Table 5. This interpretation is documented in comprehension.md and is the basis for spec.md and test-spec.md.

- The public HKM factor data from Manela's website is the most reliable reference for η_t and η_t^Δ. Builder should implement auto-download for this file. If the URL changes, the builder should check the current URL from the paper's NBER or JFE supplemental materials.

---

**Planner status**: DONE. All three artifacts written. No HOLD raised.

---

## Entry: planner (SECOND DISPATCH) → all pipelines
**Type**: HANDOFF_CORRECTION
**Date**: 2026-05-15

### CRITICAL CORRECTION

The first planner dispatch targeted the wrong tables. The targets have been confirmed by the user and corrected:

| | First dispatch (WRONG) | Second dispatch (CORRECT) |
|---|---|---|
| table2.py | JFE Table 4 (risk exposures / summary stats) | JFE Table 2 (size comparison ratios) |
| table3.py | JFE Table 5 (Fama-MacBeth regressions) | JFE Table 3 (pairwise correlations) |

All three artifacts (comprehension.md, spec.md, test-spec.md) have been fully overwritten. The previous content of these files is superseded. Builder must base its implementation on the NEW spec.md.

### For builder (code pipeline) — revised priorities

1. **JFE Table 2 is a SIZE COMPARISON table** — not a statistics/regression table. It produces 12 cells: for each of 4 balance sheet items (total assets, book debt, book equity, market equity), the ratio of primary dealer aggregates to the comparison group aggregate (BD, Banks, Cmpust.), averaged over 3 time periods. No regressions. No risk prices.

2. **Data modules required**: `dealers.py` (dealer-to-gvkey/permno mapping, hard-coded from Table 1 and Table A.1 of the paper), `crsp.py` (market equity pulls), `compustat.py` (balance sheet pulls + comparison group pulls). The balance sheet items use: `atq` (total assets), `atq − ceqq` (book debt), `ceqq` (book equity), and `shrout × |prc|` (market equity from CRSP).

3. **JFE Table 3 is a CORRELATION TABLE** — two panels. Panel A: pairwise Pearson correlations of η (market capital ratio), book capital ratio, and AEM leverage, plus their correlations with 5 macro variables (E/P, unemployment, GDP, financial conditions, market volatility) in LEVELS. Panel B: same for the factor/innovation series (η^Δ, book capital factor, AEM leverage factor) plus market excess return and log changes of macro variables.

4. **No Fama-MacBeth or Shanken correction needed for this replication** — these belong to JFE Tables 4 and 5 which are NOT the current targets.

5. **AEM series** requires Federal Reserve Z.1 Flow of Funds data (not available on WRDS). Implement `load_aem_series()` using FRED API or a pre-downloaded CSV fallback. FRED series: FL664090005 (security broker-dealer total financial assets) and FL664190005 (total liabilities). These may need to be downloaded from the Fed's Data Download Program (https://www.federalreserve.gov/releases/z1/), not FRED.

6. **Unit conversion**: ME from CRSP = `shrout × |prc|` in thousands of dollars. Compustat items (atq, ceqq) are in millions of dollars. Before computing ratios, convert all to the same units (e.g., both to millions: CRSP ME in thousands → divide by 1000).

7. **Dealer mapping table**: `hkm/data/dealers.py` must contain a hard-coded `DEALER_MAPPING` list built from Table 1 (current dealers as of 2014) and Table A.1 (historical list 1960–2014) of the paper. Each entry must have: dealer_name, holding_company, gvkey (or None), permno (or None), start_date, end_date (or None = still active), is_us_based (bool). Builder must look up gvkeys and permnos from WRDS for the US-based entries.

### For tester (test pipeline) — revised priorities

1. **No Fama-MacBeth tests needed.** The test-spec.md (second dispatch) covers: unit tests for η construction, ratio bounds, correlation arithmetic; integration tests for WRDS pulls; numerical accuracy tests for Table 2 (12 cells, ±0.05 tolerance) and Table 3 (27+ cells in each panel, ±0.05 tolerance).

2. **Key BLOCK conditions**: Any ratio > 1.0 in Table 2 (impossible by definition), any correlation outside [−1, 1] in Table 3, any unit test failure (UT-1 through UT-8), linting or type-checking failures, or import errors.

3. **Reference values are in test-spec.md** — see Sections 5 and 6. The paper values for all 36 Table 2 cells and all Table 3 Panel A and Panel B cells are hard-coded there.

### Status

DONE. Second-dispatch artifacts finalized. No HOLD raised. Comprehension: FULLY UNDERSTOOD.

---

## Entry: builder → all pipelines
**Type**: HANDOFF_SUMMARY
**Date**: 2026-05-15

### Interface Changes (new exports)

All new — no existing API was modified. Public API:

**`hkm.data.dealers`**: `DEALER_MAPPING`, `get_active_dealers(date, us_only)`, `get_us_gvkeys()`, `get_us_permnos()`

**`hkm.data.crsp`**: `get_market_equity(permnos, start_date, end_date, engine)`, `get_comparison_market_equity(sic_codes, start_date, end_date, engine)`, `get_quarterly_market_equity(...)`, `get_vw_index_returns(start_date, end_date, engine)`

**`hkm.data.compustat`**: `get_balance_sheet(gvkeys, start_date, end_date, engine)`, `get_latest_quarter(gvkeys, as_of_date, engine)`, `get_comparison_balance_sheet(sic_filter, start_date, end_date, engine)`, `get_crsp_compustat_link(engine)`

**`hkm.data.intermediary`**: `build_capital_ratio(start_date, end_date, engine)`, `build_capital_factor(eta_series)`, `build_book_capital_ratio(...)`, `build_book_capital_factor(book_eta_series)`, `load_aem_series(source)`, `load_hkm_public_data(filepath)`, `DataNotAvailableError`

**`hkm.data.macro`**: `get_ep_ratio`, `get_unemployment`, `get_gdp`, `get_nfci`, `get_market_volatility`, `get_tbill_rate`, `get_all_macro`

**`hkm.tables.table2`**: `compute_table2(engine, start_year, end_year) -> pd.DataFrame (3×12)`, `print_table2(df) -> str`

**`hkm.tables.table3`**: `compute_table3(engine, start_date, end_date) -> tuple[pd.DataFrame, pd.DataFrame]`, `print_table3(panel_a, panel_b) -> str`

**`hkm.utils`**: `quarter_end`, `to_quarterly`, `log_change`, `align_to_quarter_end`

### For tester

1. **66/66 unit tests pass** on the local machine (no WRDS). Run: `pytest tests/ -m "not wrds and not network and not integration"`

2. **Integration tests** are in `tests/test_tables.py` classes `TestTable2Integration` and `TestTable3Integration`. They are marked `@pytest.mark.integration @pytest.mark.wrds`. Run with: `pytest tests/ -m "integration"`

3. **AEM series**: If FRED is unavailable, tester should place a CSV at `data-raw/aem_leverage.csv`. The AEM columns in Table 3 will be NaN without this data; integration tests for AEM-related cells should be skipped.

4. **Reference values** are hard-coded in `tests/test_tables.py::PAPER_TABLE2` and `PAPER_TABLE3_PANEL_A`/`PAPER_TABLE3_PANEL_B`. Tolerance: ±0.05 for all cells.

5. **Bugs fixed during implementation**:
   - `dealers.py get_active_dealers()`: `date()` callable shadowing bug fixed (local import of `datetime.date`)
   - `table3.py _compute_correlation_panel()`: duplicate column DataFrame bug on self-correlation (fixed with explicit Series extraction)

### Status: DONE. No HOLD raised.

---

## Entry: tester (SECOND DISPATCH) → builder
**Type**: BLOCK
**Date**: 2026-05-15

### Verdict: BLOCK — route to builder

Builder commit `acd88d2` resolved the SQL column bugs and all ruff/mypy-without-strict issues. However, three blockers remain.

### BLOCK-2: mypy --strict still exits non-zero (17 errors)

17 errors remain across 7 files — all `[no-untyped-def]` and `[type-arg]` (unparameterized `dict`):
- `crsp.py` lines 31, 105, 176, 211: 4 functions missing type annotations
- `compustat.py` lines 32, 104, 142, 215: 4 functions missing type annotations
- `macro.py` lines 153, 225: 2 functions missing type annotations
- `intermediary.py` lines 89, 284: 2 functions missing type annotations
- `table2.py` lines 72, 160: 1 function + 1 `dict` without type params
- `table3.py` line 79: 1 function missing type annotations
- `dealers.py` lines 53, 552: 2 `dict` without type params

### BLOCK-6 + BLOCK-5: Table 2 market equity ratios > 1 and all priority cells fail badly

`compute_table2()` produces market_equity/BD ratios of 1.279 (1960-2012) and 1.868 (1990-2012) — logically impossible (PD cannot exceed BD sector). Root cause: `get_comparison_market_equity()` restricts the denominator to CRSP-Compustat linked firms only, understating the true BD universe. PD market equity is pulled directly from CRSP (no link required), so it exceeds the deflated denominator.

Priority cells all fail (|error| >> 0.03 tolerance):
- total_assets/BD: 0.040 computed vs 0.959 reference (error = 95.8%)
- book_debt/BD: 0.031 vs 0.960 (error = 96.8%)
- market_equity/BD: 1.279 vs 0.911 (impossible — > 1)
- total_assets/BD 1990-2012: 0.026 vs 0.914 (error = 97.2%)

Fix: Use SIC-filtered direct CRSP pull for ME comparison groups (do not require Compustat link). Also investigate why book-based ratios are ~25x too small — likely the comparison group `get_comparison_balance_sheet("all", ...)` is using an oversized universe.

### BLOCK-7: η series has only 19 valid quarters (requires ≥ 100)

`build_capital_ratio()` yields only 19 quarters where ≥ 5 dealers have matching CRSP + Compustat data. Large coverage gaps in 1970–1994 (0 dealers in some quarters, 2–4 in others). `compute_table3()` raises `ValueError`.

Fix: Investigate PD permno/gvkey coverage in CRSP and Compustat `fundq` for 1970–1994. Consider annual Compustat fallback or extended dealer mapping for early periods.

See `audit.md` for complete evidence, exact computed values, and detailed routing notes.

**BLOCK raised. Routing all three blockers to builder.**

---

## Entry: tester (THIRD DISPATCH — FINAL) → builder
**Type**: BLOCK
**Date**: 2026-05-15

### Verdict: BLOCK — route to builder

Builder commit `b2658a3` resolved BLOCK-2 (mypy --strict: 0 errors), BLOCK-6 (market equity ratios now ≤ 1; max = 0.591), and BLOCK-7 (η series now has 139 valid quarters; ρ = 0.939; compute_table3() succeeds). However, BLOCK-5 remains:

### BLOCK-5a: Table 2 Priority Cells Still Outside ±0.03 Tolerance

All 4 priority cells fail. The BD ratios cluster around 0.47–0.59 regardless of measure or sub-period (reference: 0.84–0.96). The Banks ratios are also far below reference. 

Root cause: The builder fixed the market equity denominator using a CRSP SIC filter (correctly resolving the >1 ratio bug), but the resulting ratio is still too low. The book-based denominators (total_assets, book_debt, book_equity) produce BD ratios ~0.47–0.59 vs paper's 0.84–0.96.

Two mechanisms likely:
1. PD numerator is skipping all 216 months from 1960–1977 where PD Compustat data is absent, dragging the 1960-2012 average down
2. The comparison group denominator definition may still differ from the paper's exact construction

### BLOCK-5b: Table 3 Priority Cells — corr(η, E/P) and corr(η^Δ, E/P growth) Outside Tolerance

The η series covers 1978Q1–2012Q4 (139 quarters, not 1970Q1). The early 1970s period is critical for several large correlations (especially E/P growth and unemployment).

Priority cells failing:
- corr(η, book_η): 0.34 vs 0.50 (diff 0.16, ±0.03 tol)
- corr(η, E/P): -0.63 vs -0.83 (diff 0.20, ±0.03 tol)
- corr(η, Unemployment): -0.50 vs -0.63 (diff 0.13, ±0.03 tol)
- corr(η^Δ, E/P growth): -0.17 vs -0.75 (diff 0.58, ±0.03 tol)

Priority cells passing:
- corr(η^Δ, market return): 0.79 vs 0.78 (diff 0.01) — PASS
- corr(η^Δ, book capital factor): 0.29 vs 0.30 (diff 0.01) — PASS

NOTE: This is the THIRD tester dispatch (maximum retries). If builder cannot resolve these issues on a fourth dispatch, the leader must escalate to HOLD with a request for user guidance on the paper's exact data construction methodology.

**BLOCK raised. Routing to builder (fourth dispatch requested).**

---

## Entry: tester (FINAL DISPATCH — post-HOLD) → builder
**Type**: BLOCK
**Date**: 2026-05-15

### Verdict: BLOCK — route to builder

Builder commit `047b354` (post-HOLD) added `@pytest.mark.skip` markers to numerical accuracy tests and documented the 1978–2012 sample limitation. This correctly resolved BLOCK-5a and BLOCK-5b per the user's HOLD acknowledgment. However, two pre-existing violations were NOT addressed:

### BLOCK-8: print() statements in library code (hkm/)

17 `print()` calls exist in `hkm/tables/table2.py` and `hkm/tables/table3.py`:
- `hkm/tables/table2.py` lines 525–539: function `_print_table2_comparison()` uses `print()` for the verbose comparison table.
- `hkm/tables/table3.py` lines 370–401: function `_print_table3_comparison()` uses `print()` for the verbose comparison table.

Both files already have `logger = logging.getLogger(__name__)` at module level. The fix is straightforward: replace all `print()` calls in these two functions with `logger.info()`. This makes the verbose output configurable via Python's logging infrastructure.

### BLOCK-3: UT-8 dealer count assertion fails

`get_active_dealers(pd.Timestamp("1995-03-31"), us_only=True)` returns 12 entries. Test-spec §3 UT-8 requires ≥15.

The US dealers active at 1995-03-31 in DEALER_MAPPING are: Goldman Sachs, Morgan Stanley, Merrill Lynch, Bear Stearns, Lehman Brothers, Salomon Inc., Chase Manhattan, BankAmerica, PaineWebber, Dean Witter, Smith Barney, Bankers Trust (12 total). Six US-based entries ended before 1995-03-31: Manufacturers Hanover (1992-01-01), Drexel Burnham (1990-03-28), GE Capital (1994-12-30), CS First Boston (1990-01-01), Prudential (1995-01-01), American Express (1994-01-01).

Resolution path:
- If the paper's Appendix Table A.1 lists additional US-based dealers active in 1995 that are not in DEALER_MAPPING, builder should add them.
- If 12 is the correct historical count per the paper, route to **planner** to revise the ≥15 threshold in test-spec.md.

### What passes

- Import: PASS (all 10 modules)
- 66 unit tests (pytest suite): PASS
- Ruff: PASS (0 errors)
- Mypy --strict: PASS (0 errors in 12 source files)
- Table 2 bounds: PASS (all 36 cells in (0.0, 1.0])
- Table 3 structure: PASS (diagonal = 1.0, all values in [-1, 1])
- Table 3 sign checks: PASS (η/E/P negative, η^Δ/market return positive)
- WRDS integration (partial): PASS (shape, index labels, column structure confirmed)

**BLOCK raised. Routing BLOCK-8 and BLOCK-3 to builder.**
