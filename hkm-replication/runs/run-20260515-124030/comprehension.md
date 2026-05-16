# Comprehension Record — run-20260515-124030

**Timestamp**: 2026-05-15 (SECOND DISPATCH — full revision)
**HOLD Rounds Used**: 0
**Status**: FULLY UNDERSTOOD

---

## Correction from First Dispatch

The first planner dispatch incorrectly targeted JFE Tables 4 and 5 (risk exposures and FM cross-sectional regressions). The user has confirmed the literal targets are:

- **JFE Table 2** (p. 7): Primary dealer size comparison versus all broker-dealers, banks, and all Compustat firms — ratios of total assets, book debt, book equity, and market equity.
- **JFE Table 3** (p. 9): Pairwise time-series correlations of the capital ratio (η) and its AR(1) innovation factor (η^Δ) with the book capital ratio, AEM leverage measure, market return, and five macro variables.

All three artifacts (comprehension.md, spec.md, test-spec.md) are fully overwritten to reflect these corrected targets.

---

## Input Materials Read

| File | Type | Relevant Sections |
|------|------|-------------------|
| `hkm-paper.pdf` | JFE article (35 pp.) | Pages 6–9: Sections 3.1.1, Table 1, Table 2, Table 3; p. 32: Table A.1 (full historical dealer list) |
| `request.md` | Run artifact | Scope, acceptance criteria, data sources |
| `impact.md` | Run artifact | Write surface, risk areas |

---

## Core Requirement (restated without looking at source)

We need a Python pipeline that:

1. Pulls quarterly balance sheet data from Compustat and monthly equity data from CRSP for US-based primary dealer holding companies and three comparison groups (all broker-dealers, all banks, all Compustat firms). For each of four balance sheet items (total assets, book debt, book equity, market equity), it computes the monthly ratio of the primary-dealer aggregate to the comparison-group aggregate, then averages over three time periods (1960–2012, 1960–1990, 1990–2012). Output is JFE Table 2.

2. Constructs the quarterly aggregate intermediary capital ratio η from CRSP (market equity) and Compustat (book debt) for the primary dealer sector, estimates an AR(1) on η to extract the scaled innovation η^Δ (the capital risk factor), and pulls the book-capital ratio analog, AEM leverage series, and five macro series (E/P, Unemployment, GDP, Financial conditions, Market volatility). Computes a pairwise correlation matrix in levels (Panel A) and in factors/growth rates (Panel B) over 1970Q1–2012Q4. Output is JFE Table 3.

---

## JFE Table 2 — Exact Layout

**Title** (from paper): "Primary dealers as representative financial intermediaries."

**Caption**: "Average sizes of primary dealers relative to all broker-dealers (BD), all banks (Banks), and all firms in Compustat (Cmpust.). At the end of each month, we calculate the total assets (and book debt, book equity, and market equity) of primary dealers and divide them by the total for the comparison group. To make the samples comparable, we focus in this table only on US-based primary dealer holding companies that are in the CRSP-Compustat data. We report the time-series average of this ratio in each sample period."

### Column Structure

Four column groups, each with three sub-columns:

| Column group | Sub-columns |
|---|---|
| Total assets | BD, Banks, Cmpust. |
| Book debt | BD, Banks, Cmpust. |
| Book equity | BD, Banks, Cmpust. |
| Market equity | BD, Banks, Cmpust. |

Total: 12 data cells per row.

### Row Structure

| Row label | Sample period |
|---|---|
| 1960–2012 | Full sample (all available months) |
| 1960–1990 | First subperiod |
| 1990–2012 | Second subperiod |

### Published Cell Values (from paper, page 7)

|  | Total assets | | | Book debt | | | Book equity | | | Market equity | | |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Period | BD | Banks | Cmpust. | BD | Banks | Cmpust. | BD | Banks | Cmpust. | BD | Banks | Cmpust. |
| 1960–2012 | 0.959 | 0.596 | 0.240 | 0.960 | 0.602 | 0.280 | 0.939 | 0.514 | 0.079 | 0.911 | 0.435 | 0.026 |
| 1960–1990 | 0.927 | 0.635 | 0.286 | 0.998 | 0.639 | 0.305 | 0.908 | 0.568 | 0.095 | 0.961 | 0.447 | 0.015 |
| 1990–2012 | 0.914 | 0.543 | 0.202 | 0.916 | 0.550 | 0.240 | 0.883 | 0.444 | 0.058 | 0.848 | 0.419 | 0.039 |

**Units**: All values are pure ratios (dimensionless, 0 to 1). No dollar amounts in the table.

### Comparison Group Definitions

Drawn from paper text (Section 3.1.1 and footnote 19):

- **PD (numerator)**: US-based primary dealer holding companies only, requiring presence in both CRSP and Compustat. Foreign-incorporated dealers (Barclays, HSBC, Deutsche Bank, BNP Paribas, Mizuho, Nomura, Daiwa, RBS, Credit Suisse, UBS, SG Americas) are excluded.
- **BD (all broker-dealers)**: US primary dealers plus any US firms with broker-dealer SIC codes 6211 ("Security Brokers, Dealers, and Flotation Companies") or 6221 ("Commodity Contracts Dealers, Brokers") in CRSP-Compustat.
- **Banks**: All US CRSP-Compustat firms with SIC codes in the commercial banking / savings institution range (6020–6099). Non-BD financial intermediaries. The paper says "all banks" and contrasts with the BD sector.
- **Cmpust.**: All US firms in CRSP-Compustat regardless of SIC code.

### Timing Convention

- Market equity: from CRSP monthly stock file (`crsp.msf`), measured at the last trading day of each calendar month. Use `shrout × |prc|` (shares in thousands → ME in thousands of dollars).
- Balance sheet items (total assets, book debt, book equity): from Compustat quarterly (`comp.fundq`), using the most recently available quarter-end observation as of each calendar month (no look-ahead bias).
- Ratio computed each month, then averaged over all months within each sub-period.

### Balance Sheet Item Formulas

| Table 2 item | Formula |
|---|---|
| Total assets | `atq` from `comp.fundq` |
| Book debt | `atq − ceqq` (total assets minus common equity) |
| Book equity | `ceqq` (common equity) |
| Market equity | `shrout × |prc|` from `crsp.msf` (thousands of dollars) |

---

## JFE Table 3 — Exact Layout

**Title** (from paper): "Pairwise correlations."

**Caption (abbreviated)**: "Time-series pairwise correlations over the 1970Q1–2012Q4 sample. Market capital (ratio) is defined as the ratio of total market equity to total market assets (book debt plus market equity) of primary dealer holding companies, constructed using CRSP-Compustat and Datastream data. Market equity is outstanding shares multiplying stock price, and book debt is total assets minus common equity AT − CEQ. Market capital factor is our main asset pricing factor, defined as AR(1) innovations in the capital ratio, scaled by the lagged capital ratio. Book capital and Book capital factor are similarly defined, but use book equity instead of market equity. The AEM implied capital is the inverse of broker-dealer book leverage from Flow of Funds used in AEM, and the AEM leverage factor (LevFac) is defined as the seasonally adjusted growth rate in broker-dealer book leverage from Flow of Funds. Correlation for factors are with value-weighted stock market excess return, growth (log change) of the earnings-to-price (E/P) ratio, Unemployment, GDP, the Chicago Fed National Financial Conditions Index (high level means poor financial conditions), or realized volatility of CRSP value-weighted stock index."

### Panel A: Correlations of Levels

Three columns: Market capital (η level), Book capital (book η level), AEM leverage.

Rows (showing lower-triangular pairwise correlations plus macro variable rows):

| Row variable | Market capital | Book capital | AEM leverage |
|---|---|---|---|
| Market capital | 1.00 | 0.50 | −0.42 |
| Book capital | 0.50 | 1.00 | −0.07 |
| AEM leverage | −0.42 | −0.07 | 1.00 |
| E/P | −0.83 | −0.38 | −0.64 |
| Unemployment | −0.63 | −0.10 | −0.33 |
| GDP | 0.18 | 0.32 | −0.23 |
| Financial conditions | −0.48 | −0.53 | −0.19 |
| Market volatility | −0.06 | −0.31 | 0.33 |

### Panel B: Correlations of Factors (innovations/growth rates)

Four columns: Market capital factor (η^Δ), Book capital factor, AEM leverage factor, plus market excess return as a row variable.

| Row variable | Market capital factor | Book capital factor | AEM leverage factor |
|---|---|---|---|
| Market capital factor | 1.00 | 0.30 | 0.14 |
| Book capital factor | 0.30 | 1.00 | −0.06 |
| AEM leverage factor | 0.14 | −0.06 | 1.00 |
| Market excess return | 0.78 | 0.10 | 0.15 |
| E/P growth | −0.75 | −0.10 | −0.18 |
| Unemployment growth | −0.05 | 0.12 | −0.08 |
| GDP growth | 0.20 | 0.09 | 0.04 |
| Financial conditions growth | −0.38 | −0.29 | −0.06 |
| Market volatility growth | −0.49 | −0.18 | −0.08 |

**Correlation type**: Pearson time-series correlations. No significance stars. No p-values. Sample: 1970Q1–2012Q4 (N ≈ 172 quarters).

**Factor correlations for macro variables**: Log changes (growth rates) in levels — e.g., GDP growth = Δlog(GDP), E/P growth = Δlog(E/P), Market volatility growth = Δlog(realized vol). Financial conditions growth = first difference of the NFCI index (since NFCI is already a standardized index, not a log series). Unemployment growth = Δlog(unemployment rate) based on "log change" language in caption (though it says "growth (log change)" as the generic descriptor for factors).

---

## Capital Ratio η — Exact Construction

From Section 3.1.1 and Equation (6) of the paper:

```
η_t = Σ_i Market_Equity_{i,t} / Σ_i (Market_Equity_{i,t} + Book_Debt_{i,t})
```

where:
- i indexes all NY Fed primary dealer designees active during quarter t
- `Market_Equity_{i,t}` = shares outstanding × closing price at last trading day of quarter t (CRSP for US firms, Datastream for foreign firms — but we focus on CRSP-Compustat US firms)
- `Book_Debt_{i,t}` = `atq − ceqq` from Compustat quarterly, most recent quarter-end as of quarter t
- The ratio is the aggregate (sum over i then divide), not an average of individual ratios

**Quarterly, 1970Q1–2012Q4**. The paper reports the estimated AR(1) coefficient ρ ≈ 0.94 (footnote 22).

**Factor η^Δ** (the intermediary capital risk factor):

Step 1: Estimate OLS AR(1): η_t = ρ_0 + ρ η_{t-1} + u_t

Step 2: Extract residuals û_t

Step 3: Scale: η^Δ_t = û_t / η_{t-1}

**Book capital ratio**: Same formula but `ceqq` (book equity) replaces `Market_Equity` in the numerator, and denominator uses `atq` (total assets) instead of ME+BD. Specifically: book_η_t = Σ_i ceqq_{i,t} / Σ_i atq_{i,t}.

**AEM implied capital**: NOT constructed from CRSP/Compustat. It is the inverse of broker-dealer book leverage from the Federal Reserve Z.1 Flow of Funds release. Specifically, "AEM implied capital = 1 / (broker-dealer book leverage)" where book leverage = Total Financial Assets (FL664090005) / (Total Financial Assets − Total Liabilities (FL664190005)). The AEM leverage factor (LevFac) = seasonally adjusted growth rate of broker-dealer book leverage from Flow of Funds.

**Public HKM data**: The factor series η_t and η^Δ_t are publicly available at:
`http://apps.olin.wustl.edu/faculty/manela/hkm/intermediary-capital-ratio/`
This should be used as the reference crosscheck for the reconstructed series.

---

## Primary Dealer Identification

### Currently designated dealers (Table 1, p. 7 — as of Feb 11, 2014)

The 22 dealers listed in Table 1 with their holding companies, including:
Goldman Sachs Group Inc., Barclays PLC, HSBC Holdings PLC, BNP Paribas, Deutsche Bank AG, Mizuho Financial Group Inc., Citigroup Inc., UBS AG, Credit Suisse Group AG, Cantor Fitzgerald & Company, Royal Bank of Scotland Group PLC, Nomura Holdings Inc., Daiwa Securities Group Inc., JPMorgan Chase & Co., Bank of America Corporation, Royal Bank Holding Inc., Societe Generale, Morgan Stanley, Bank of Nova Scotia, Bank of Montreal, Jefferies LLC, Toronto-Dominion Bank.

### Historical primary dealers 1960–2014 (Table A.1, p. 32)

Full list of ~100 historical designees with start and end dates. Key US-based entities include Goldman Sachs (start 7/31/1984), Morgan Stanley (2/1/1978), Merrill Lynch (various), Bear Stearns (end 10/1/2008), Lehman (end 9/22/2008), Drexel Burnham (end 3/28/1990), Kidder Peabody (end 12/30/1994), Smith Barney (end 8/31/1998), Salomon Smith Barney (end 4/6/2003), etc.

### Matching to CRSP/Compustat

Builder must implement a hard-coded mapping table: `(dealer_name, holding_company_name, gvkey, permno, start_date, end_date, is_us_based)` derived from Table 1 and Table A.1. For Table 2, only `is_us_based = True` firms are used. For the η capital ratio used in Table 3 (correlations), the paper uses all primary dealers including foreign ones (with Datastream), but the Table 3 note says "CRSP-Compustat and Datastream data" — our replication uses CRSP-Compustat only, which approximates the paper's series for US dealers and is cross-checkable against the public HKM data.

---

## Data Sources — Table 3 Variables

| Variable | Level series | Factor/innovation | Source |
|---|---|---|---|
| Market capital (η) | η_t = Σ ME / Σ (ME + BD) | η^Δ_t = AR(1) residual / η_{t-1} | CRSP + Compustat + Datastream (HKM public data as reference) |
| Book capital | book_η_t = Σ CEQ / Σ AT | Book capital factor = AR(1) residual of book_η / lagged | Compustat |
| AEM implied capital | 1 / BD book leverage (Flow of Funds) | AEM LevFac = seas. adj. growth rate of BD book leverage | Fed Z.1 release, FRED series |
| Market excess return | — | CRSP VW excess return over T-bill (quarterly) | CRSP (crsp.msi) + FRED (TB3MS) |
| E/P | S&P 500 E/P ratio (Shiller) | Δ log(E/P) | Robert Shiller website (online data) |
| Unemployment | U.S. unemployment rate | Δ log(Unemployment) | FRED series UNRATE (BLS) |
| GDP | U.S. real GDP | Δ log(GDP) = GDP growth | FRED series GDPC1 (BEA) |
| Financial conditions | Chicago Fed NFCI | Δ NFCI (first difference) | FRED series NFCI |
| Market volatility | Realized vol of CRSP VW returns | Δ log(realized vol) | Computed from CRSP daily returns |

**AEM Flow of Funds series**: Federal Reserve Z.1, Security Brokers and Dealers:
- Total Financial Assets: FL664090005 (also coded as series in FRED as "DISCONTINUED" — may need manual download from Fed website or FRED historical data)
- Total Liabilities: FL664190005
- Book leverage = FL664090005 / (FL664090005 − FL664190005)
- AEM LevFac is the seasonally adjusted growth rate of this leverage series

---

## Sample Periods

| Table | Sample | Frequency |
|---|---|---|
| Table 2 | 1960 to 2012, split at 1990 | Monthly (ratio computed monthly, averaged) |
| Table 3 | 1970Q1–2012Q4 | Quarterly (η and all variables at quarterly frequency) |
| η construction | 1970Q1–2012Q4 | Quarterly |

---

## Comprehension Self-Test Answers

**Q1**: Yes — restated in Core Requirement above.

**Q2**: All formulas verified:
- Table 2: ratio = time_avg[Σ_{PD,US}(X_t) / Σ_{group}(X_t)] for each item X and comparison group
- η_t = Σ_i ME_{i,t} / Σ_i (ME_{i,t} + BD_{i,t}); BD = atq − ceqq
- η^Δ_t = û_t / η_{t-1} where û_t is the AR(1) residual
- Book_η_t = Σ_i ceqq_{i,t} / Σ_i atq_{i,t}
- Pearson correlation between quarterly time series

**Q3**: No undefined symbols. All resolved above.

**Q4**: Implementation decisions required:
- Exact SIC code range for "Banks": using 6020–6099 (standard commercial bank codes). This is consistent with footnote 19 which defines BD as SIC 6211 or 6221 and implies banks are other financial-SIC firms.
- dealer-to-gvkey/permno mapping requires manual construction from Table A.1 and Table 1. Builder encodes this as a Python dictionary.
- For Table 3, "AEM leverage" requires Fed Z.1 data not on WRDS; a download module from FRED is needed.

**Q5**: The capital ratio measures the soundness of the primary dealer sector. Low η means distressed intermediaries with high marginal utility of wealth — assets with low β_η pay less in bad states and so require high expected returns. Table 2 motivates using primary dealers as the representative financial intermediary (they are very large relative to the rest of the financial sector). Table 3 shows η is procyclical (correlates negatively with E/P, unemployment, and financial conditions deterioration) confirming its role as a financial distress measure.

**Q6**: Implicit assumptions:
- Book debt approximates market debt (defended in paper: financial firm liabilities are mostly short-term, so book ≈ market)
- The most recent Compustat quarterly observation at each month-end is used (no look-ahead)
- The AEM leverage series from Flow of Funds covers the same broker-dealer sector consistently from 1970 onward

---

## Open Questions

None. **Final verdict: FULLY UNDERSTOOD**
