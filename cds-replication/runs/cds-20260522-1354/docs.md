# Documentation Summary — cds-replication
## Run: cds-20260522-1354 | 2026-05-22

---

## Documents Modified / Created

| File | Action | Description |
| --- | --- | --- |
| `ARCHITECTURE.md` | created | System architecture diagram with Mermaid graphs (module structure, function call graph, data flow); pattern notes; handoff observations. Written to both target repo root and run directory. |
| `evaluation.md` | created (by builder V5) | Achieved metrics vs oracle, documented gaps (universe gap, data availability gap, spread cap methodology), per-portfolio mean return table. |
| Module docstrings | created (by builder) | All four source modules (`data.py`, `returns.py`, `portfolios.py`, `pipeline.py`) have module-level docstrings. Every public function has a NumPy-style docstring with Parameters and Returns sections. |

---

## User-Facing Documentation: What the Pipeline Produces

### Output Files

#### `ftsfr_cds_portfolio_returns.parquet`

Equal-weight CDS carry portfolio returns, 2008-01-01 to 2023-11-01.

**Schema**:

| Column | dtype | Description |
| --- | --- | --- |
| `ds` | `datetime64[ns]` | First calendar day of the entry month (e.g., 2008-01-01 = the January 2008 holding period) |
| `unique_id` | `object` (str) | Portfolio identifier: `{TENOR}_Q{QUINTILE}`, e.g. `5Y_Q3` |
| `y` | `float64` | Equal-weight carry return (decimal). `y = mean(S_{t-1}/12)` across contracts in the portfolio cell. |

**Coverage**: 3,820 rows. Exactly 20 portfolios: tenors {3Y, 5Y, 7Y, 10Y} × quintiles {Q1, Q2, Q3, Q4, Q5}. 191 monthly observations per portfolio (2008-01-01 to 2023-11-01). No NaN. No duplicates.

**Interpretation**:
- `y` represents the monthly carry (coupon income) earned by an equal-weight portfolio of CDS protection sellers in the given tenor/quintile bucket.
- Q1 = lowest-spread (investment-grade) issuers; Q5 = highest-spread (distressed) issuers.
- Returns are decimals, not percentages: `y = 0.001` means 0.1% per month (1.2% annualized).
- All 20 portfolios have positive mean carry, and carry increases monotonically from Q1 to Q5 within each tenor, and from 3Y to 10Y within each quintile.
- 5Y_Q5 annualized mean carry: approximately 6.3%.

**Known limitations**:
- Output covers 2008–2023 only. WRDS Markit data under the standard CDS Big Bang convention (`runningcoupon=0.01`) is unavailable before 2008. The oracle covers 2001–2023, but the pre-2008 period cannot be replicated from WRDS.
- The oracle validation parquet (`validation_portfolio.parquet`) was constructed from a curated ~184-ticker/month universe; WRDS full universe produces ~808 tickers/month. Only the 3Y_Q1 portfolio achieves high oracle correlation (0.976); all other 19 portfolios are near-zero due to this universe mismatch (see `evaluation.md`).

---

#### `ftsfr_cds_contract_returns.parquet`

Individual CDS contract monthly total returns, 2008-01-01 to 2023-11-01.

**Schema**:

| Column | dtype | Description |
| --- | --- | --- |
| `ds` | `datetime64[ns]` | First calendar day of the entry month |
| `unique_id` | `object` (str) | Contract identifier: `{TICKER}_{TENOR}`, e.g. `GE_5Y`, `IBM_3Y` |
| `y` | `float64` | Monthly total return (decimal). `y = S_{t-1}/12 + (S_{t-1} − S_t) × RD_{t-1}` |

**Coverage**: 614,342 rows. 6,950 unique contracts. Sparse panel (not all tickers present in all months). 2008-01-01 to 2023-11-01. No NaN. No duplicates.

**Interpretation**:
- `y` is the total return to a CDS protection seller (long credit risk) for the monthly holding period.
- The two components are: carry `S_{t-1}/12` (positive, always earned by seller) and capital gain `(S_{t-1} − S_t) × RD_{t-1}` (positive when spreads narrow, negative when spreads widen).
- Contracts are indexed by Markit ticker. Tickers may contain alphanumeric characters, dots, hyphens, underscores, and plus signs (e.g., `CEG-BaltG+E_3Y`).
- Contract returns are retained even for extreme events (e.g., default/spread-spike during 2008–2009 financial crisis). The 99th percentile absolute return is 0.127 (12.7%/month); extreme tail events can reach -17.7%.
- Contracts where `S_{t-1} > 50%` are excluded (post-default stale Markit quotes; 2,005 rows removed). See `evaluation.md` §Spread Cap.

---

### How to Run the Pipeline

```python
from cds_replication import run_pipeline

# Run full pipeline (uses cached data/raw_cds.parquet if it exists)
run_pipeline(
    start_year=2001,     # WRDS query range (data available from 2008 under runningcoupon=0.01)
    end_year=2023,
    output_dir='.',      # directory for output parquets
    use_cache=True       # set False to force re-query from WRDS
)
```

Output parquets are written to `output_dir`:
- `ftsfr_cds_portfolio_returns.parquet`
- `ftsfr_cds_contract_returns.parquet`

**Prerequisites**: WRDS access credentials in `~/.pgpass` for the initial data pull. Subsequent runs use the local parquet cache and do not require a WRDS connection.

**Installation**:
```bash
pip install -e .
```

---

### How to Load the Output

```python
import pandas as pd

portfolios = pd.read_parquet('ftsfr_cds_portfolio_returns.parquet')
contracts  = pd.read_parquet('ftsfr_cds_contract_returns.parquet')

# Filter to a specific portfolio
q5_5y = portfolios[portfolios['unique_id'] == '5Y_Q5']

# Filter to a specific contract
ge_5y = contracts[contracts['unique_id'] == 'GE_5Y']

# Annualize mean carry for each portfolio
ann_carry = portfolios.groupby('unique_id')['y'].mean() * 12
```

---

## Architecture Documentation

`ARCHITECTURE.md` was produced and written to both:
- Target repo root: `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/CDS Replication/.repos/cds-replication/ARCHITECTURE.md`
- Run directory (for reviewer): `/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/CDS Replication/.repos/workspace/cds-replication/runs/cds-20260522-1354/ARCHITECTURE.md`

`ARCHITECTURE.md` contains:
- **Module Structure** (Mermaid graph TD): API layer (pipeline, __init__), Core layer (returns, portfolios), Data layer (data.py)
- **Function Call Graph** (Mermaid graph TD): Full call chain from `run_pipeline` down to leaf functions in all four modules
- **Data Flow** (Mermaid graph TD): WRDS → cache → RD fill → return computation → quintile assignment → portfolio + contract outputs
- **Module reference table**: all five source files with key exports and changed status
- **Function reference table**: all 14 functions with caller/callee relationships
- **Architectural patterns**: 8 patterns documented (linear pipeline, cache-first, SQL-side EOM sampling, docclause priority, flat hazard fallback, entry-month labeling, carry-only aggregation, symmetric spread cap)
- **Notes**: data availability gap, universe gap, V5 spread cap effect, data.py dead code observation

---

## Documentation Generation Commands

No documentation generation commands needed. This package does not use Sphinx, pdoc, or any doc-generation tool. All documentation is in:
- Source module docstrings (NumPy style, viewable via `help()` or IDE introspection)
- `ARCHITECTURE.md` (system architecture)
- `evaluation.md` (empirical metrics and methodology notes)
- `README.md` (if created separately)

---

## Deferred Items

- No README.md was created in this run (not in scope).
- The `data.py` dead code (first SQL string overwritten immediately by second SQL string) is noted in `ARCHITECTURE.md` Notes section but was not fixed in this run (out of scope for scriber).
- Type stubs / `py.typed` marker not added (out of scope).
