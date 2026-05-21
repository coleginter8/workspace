# Comprehension — RUN-20260521-182205

## Paper Identity

**Title**: The U.S. Treasury Yield Curve: 1961 to the Present
**Authors**: Refet S. Gürkaynak, Brian Sack, Jonathan H. Wright
**Series**: Finance and Economics Discussion Series 2006-28, Federal Reserve Board

---

## What FEDS200628 Is and How the Data Is Structured

FEDS200628 is the Federal Reserve Board's public data release that accompanies the GSW (2007) paper. The Fed computes the Nelson-Siegel-Svensson (NSS) yield curve parameters daily from a cross-section of off-the-run Treasury coupon securities and then publishes the resulting fitted yields, par yields, forward rates, and estimated parameters as a single CSV file. The file is updated on an ongoing basis.

**URL**: `https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv`

**CSV layout** (confirmed by direct inspection):
- Rows 0–7: metadata and legend text (note, series descriptions, compounding conventions, mnemonics). These must be skipped.
- Row 8 (0-indexed): the actual column header row — `Date,BETA0,BETA1,...,SVENY01,...,SVENY30,...,TAU1,TAU2`
- Row 9 onward: daily data records, one row per trading date

**Confirmed column header format** (pandas `skiprows=8` gives the header on the first data line):
- `Date`: trading date, format `YYYY-MM-DD`
- `BETA0` through `TAU2`: NSS model parameters (not needed for our deliverable)
- `SVENY01` through `SVENY30`: continuously compounded zero-coupon yields at maturities 1 through 30 years, expressed in percent (e.g., `2.9825` means 2.9825%)
- `SVENPY01`–`SVENPY30`: par yields (coupon-equivalent)
- `SVENF01`–`SVENF30`: instantaneous forward rates (continuously compounded)
- `SVEN1F01`, `SVEN1F04`, `SVEN1F09`: one-year forward rates
- Missing values are encoded as `NA` in the CSV (not blank, not NaN text); pandas `read_csv` with `na_values='NA'` or default settings handles this correctly

---

## The Nelson-Siegel-Svensson Functional Form (Exact Equations)

### Nelson-Siegel (1987) — instantaneous forward rate (4 parameters)

Equation (20) from the paper:

```
f_t(n, 0) = β_0 + β_1 * exp(-n/τ_1) + β_2 * (n/τ_1) * exp(-n/τ_1)
```

Where:
- `β_0`: long-run level asymptote of the forward rate curve
- `β_1 + β_0`: level at horizon zero (the current short rate)
- `β_2`: magnitude and sign of the single "hump"
- `τ_1`: location parameter for the hump

### Svensson (1994) extension — instantaneous forward rate (6 parameters)

Equation (21) from the paper:

```
f_t(n, 0) = β_0 + β_1 * exp(-n/τ_1) + β_2 * (n/τ_1) * exp(-n/τ_1) + β_3 * (n/τ_2) * exp(-n/τ_2)
```

Where `β_3` and `τ_2` add a second "hump" to capture convexity effects at long maturities. The model reduces to Nelson-Siegel when `β_3 = 0`.

### NSS Zero-Coupon Yield Formula

Integrating the Svensson forward rates gives equation (22), the continuously compounded zero-coupon yield at maturity n:

```
y_t(n) = β_0
         + β_1 * [(1 - exp(-n/τ_1)) / (n/τ_1)]
         + β_2 * [(1 - exp(-n/τ_1)) / (n/τ_1) - exp(-n/τ_1)]
         + β_3 * [(1 - exp(-n/τ_2)) / (n/τ_2) - exp(-n/τ_2)]
```

### Estimation

Parameters are estimated daily by minimizing the weighted sum of squared deviations between actual and model-predicted Treasury prices, with weights equal to the inverse of each security's modified duration. This approximately minimizes the unweighted sum of squared yield deviations.

### Period-specific restrictions

- **Before 1980**: Nelson-Siegel is used (β_3 = 0, τ_2 unreported). The second hump cannot be reliably identified with short maturities only.
- **From 1980 onward**: Full Svensson 6-parameter model.

### Maximum maturity reported

- Through 15 August 1971: up to 7 years
- 16 August 1971 to 14 November 1971: up to 10 years
- 15 November 1971 to 1 July 1981: up to 15 years
- 2 July 1981 to 24 November 1985: up to 20 years
- From 25 November 1985 onward: up to 30 years

This is why SVENY08–SVENY30 are `NA` for early dates.

---

## What SVENY01–SVENY30 Represent

`SVENYxx` (where XX is 01–30) denotes the continuously compounded zero-coupon yield at maturity XX years, as estimated by the Svensson (NSS) model fitted to off-the-run Treasury notes and bonds. Values are expressed in **percent** (e.g., 2.9825 represents 2.9825% per year, not 0.029825). These are computed from equation (22) using the daily NSS parameter estimates and evaluated at integer maturities 1 through 30 years.

Per Table 1 of the paper:
- **Series**: Zero-coupon yield
- **Compounding Convention**: Continuously Compounded
- **Mnemonics**: SVENYXX (XX = 01 to 30)
- **Maturities**: All integers 1–30 (max, as available per date)

---

## How the Fed Publishes the Data

The Fed publishes the complete FEDS200628 dataset as a single CSV file at:

```
https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv
```

The file contains all series (zero-coupon yields, par yields, forward rates, parameters) for all dates from 1961-06-14 to the present in a wide-format CSV. Each row is one trading date; each column is one series. The file is updated daily on trading days. The header structure includes 8 rows of metadata before the actual column names.

---

## NaN Policy — Which Tenors Are Missing and Why

The oracle has 379,352 rows rather than the theoretical maximum of 16,194 dates × 30 tenors = 485,820. The gap (106,468 rows) reflects `NA` values that are dropped. This is expected and correct behavior.

**Why NAs exist**:
1. **Short-maturity cap in early sample**: Through mid-1971, only maturities up to 7 years were available (SVENY01–SVENY07). SVENY08–SVENY30 are `NA`.
2. **Gradual expansion**: The maximum reported maturity stepped up on specific dates (see above). Tenors beyond the maximum are `NA` until sufficient long-maturity securities existed for estimation.
3. **No forward-fill**: The Fed does not impute missing tenors — if the yield curve cannot be reliably estimated at a given maturity on a given date, the value is left as `NA`.

**NaN drop policy for our deliverable**: Drop all rows where `y` is `NA`. Do NOT forward-fill, back-fill, or interpolate. This exactly replicates what the oracle does.

---

## Confirmation of Implementation Approach

The task does NOT require re-implementing NSS fitting from scratch. The Fed already publishes the fully fitted SVENY01–SVENY30 yields in the CSV. Builder downloads that CSV, selects only the SVENY columns plus Date, melts to long format, drops NAs, and writes parquet. This is the correct and complete replication approach because:

1. The oracle is derived from the same Fed-published FEDS200628 data
2. The SVENY columns are the exact output of the NSS estimation described in the paper
3. Re-fitting would require the underlying proprietary CRSP/FRBNY price data (not publicly available), so downloading the published results is the only correct approach

---

## STATUS: FULLY UNDERSTOOD

No blockers. All required information is available from:
- The GSW (2007) paper (methodology, context, Table 1 mnemonics, NaN rationale)
- Direct inspection of the FEDS200628 CSV (confirmed 8 header rows, NA encoding, SVENY column positions, YYYY-MM-DD date format, percent units)
- Oracle metadata (row count, column names, date range)

Proceeding to produce spec.md and test-spec.md.
