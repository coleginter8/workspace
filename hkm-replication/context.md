# Repository Context

```yaml
RepoName: "hkm-replication"
RepoURL: "https://github.com/coleginter8/hkm-replication"
RepoCheckout: "/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication"
ActiveRun: ""
DefaultWorkflow: agent-teams
DefaultProfile: "python-package"
DefaultBranch: "main"
Language: "Python"
Version: "0.1.0"
CredentialStatus: "PASS"
CredentialMethod: "gh-cli"
CredentialVerifiedAt: "2026-05-20 00:00"
BrainMode: "isolated"
BrainRepo: "statsclaw/brain"
SeedbankRepo: "statsclaw/brain-seedbank"
BrainLastPull: ""
```

## Request Defaults

- Default acceptance criteria: all profile validation commands pass with zero errors
- Default write surface: determined by impact.md per run
- Default validation level: full (build + check + test)

## Key Functions

- `hkm.tables.table2.compute_table2()` — primary dealer capital ratio vs comparison groups; returns (3, 12) DataFrame
- `hkm.tables.table3.compute_table3()` — pairwise Pearson correlations in levels and factors; returns (panel_a, panel_b) tuple
- `hkm.data.intermediary.fetch_primary_dealer_data()` — WRDS CRSP+Compustat for broker-dealer firms
- `hkm.data.crsp.fetch_market_equity()` — CRSP market cap for comparison groups
- `hkm.data.macro.fetch_macro_series()` — FRED macro data (UNRATE, GDPC1, NFCI, E/P via Shiller)

## Constraints

- WRDS PostgreSQL (wrds-pgdata.wharton.upenn.edu:9737) via ~/.pgpass; username: coleginter
- WRDS CRSP starts 1978Q1; paper sample uses 1970Q1 → gap requires Fed Z.1 or alternative source for 1970-1977
- Python ≥ 3.9; ruff + mypy --strict required to pass
- Paper sample: 1970Q1–2012Q4 (Table 2 sub-periods: 1970-1984, 1985-1994, 1995-2012)

## Known Issues

- Previous run (run-20260515-124030): 71 paper-value tests skipped because WRDS starts 1978Q1, not 1970Q1
- Z.1 aggregate splicing for 1970-1977 was chosen but not validated cell-by-cell against paper
- evaluation.md has empty cell-by-cell comparison tables — never filled in

## Session Notes

- Fresh replication run requested 2026-05-20 after workspace clear
- Paper at: /Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication/hkm-paper.pdf
- evaluation.md is an untracked file tracking comparison vs paper values
