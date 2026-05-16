# Impact Analysis: run-20260515-124030

## Task

Replicate Tables 2 and 3 from He, Kelly & Manela (2017), "Intermediary Asset Pricing."

## Current State

The target repo (`coleginter8/hkm-replication`) contains only the StatsClaw framework files. There is no existing replication code. This is a greenfield implementation.

## Write Surface

All new files to be created by builder:

```
hkm/                          # main Python package
  __init__.py
  data/
    __init__.py
    wrds_connect.py            # WRDS PostgreSQL connection using ~/.pgpass
    crsp.py                    # CRSP monthly returns & market cap pull
    compustat.py               # Compustat (primary broker-dealer) balance sheet pull
    intermediary.py            # construct η (capital ratio) factor from CRSP/Compustat
  tables/
    __init__.py
    table2.py                  # Table 2: summary statistics for η and test portfolios
    table3.py                  # Table 3: Fama-MacBeth cross-sectional asset pricing tests
  utils.py                     # shared utilities (date alignment, regression helpers)
tests/
  __init__.py
  test_data.py                 # unit tests for data pipeline
  test_tables.py               # numerical tests for Table 2 & 3 values
pyproject.toml                 # package metadata, deps
README.md                      # usage and data requirements
```

## Affected Surfaces

| Surface | Risk | Notes |
|---------|------|-------|
| New Python package `hkm/` | Low (greenfield) | No existing code to break |
| WRDS data pull | Medium | Must match exact sample period and filter criteria from paper |
| Intermediary factor construction | High | η definition is the critical replication target |
| Table 2 statistics | Medium | Must match within rounding |
| Table 3 FM regressions | High | Test assets, weighting, and standard errors must match paper spec |

## Key Paper Details (preliminary scan)

- **Sample period**: 1970-2012 (quarterly/annual intermediary data; monthly asset returns)
- **Intermediary definition**: Primary dealer sector (NY Fed), capital ratio η = (equity) / (equity + debt)
- **Table 2**: Summary statistics for η-shock factor plus test portfolios (equity, bonds, FX, options, CDS, etc.)
- **Table 3**: Fama-MacBeth two-pass regressions: Table 3 likely shows λ (price of risk) across multiple asset classes

## Required Teammates

1. **planner** — deep comprehension of Tables 2 & 3 methodology from paper; produce `spec.md`, `test-spec.md`
2. **builder** — implement Python package per `spec.md`
3. **tester** — validate implementation per `test-spec.md`
4. **scriber** — document and record
5. **reviewer** — cross-pipeline quality gate

## Profile

`python-package`

## Risk Areas

- HKM use a specific definition of broker-dealer sector from NY Fed flow of funds — must match exactly
- Test portfolio construction varies by asset class (some from Ken French, some from other sources)
- Fama-MacBeth standard errors may use specific EIV correction (Shanken 1992)
- Sample period alignment between quarterly intermediary data and monthly returns requires careful frequency conversion

## Workflow Selected

Workflow 1 (Code Change) — implement, test, document. No ship requested yet.

## Simplified Workflow Check

NOT eligible — this is a complex greenfield implementation involving data engineering, econometrics, and numerical validation against published results.
