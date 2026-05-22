# Repository Context

```yaml
RepoName: "cds-replication"
RepoURL: "https://github.com/coleginter8/cds-replication"
RepoCheckout: "/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/CDS Replication/.repos/cds-replication"
ActiveRun: "cds-20260522-1354"
DefaultWorkflow: agent-teams
DefaultProfile: python-package
DefaultBranch: "main"
Language: "Python"
Version: ""
CredentialStatus: ""
CredentialMethod: ""
CredentialVerifiedAt: ""
BrainMode: "isolated"
BrainRepo: "statsclaw/brain"
SeedbankRepo: "statsclaw/brain-seedbank"
BrainLastPull: ""
```

## Request Defaults

- Default acceptance criteria: parquet outputs match validation oracles within tolerance
- Default write surface: determined by impact.md per run
- Default validation level: full (oracle comparison)

## Key Functions

- HKM (2017) CDS portfolio returns replication
- Palhares (2012) mark-to-market return methodology
- Output: ftsfr_cds_portfolio_returns.parquet, ftsfr_cds_contract_returns.parquet

## Constraints

- Builder must NOT read validation oracles (validation/validation_portfolio.parquet, validation/validation_contract.parquet)
- WRDS data source: wrds-pgdata.wharton.upenn.edu:9737 (username: coleginter)
- Tester reads both oracle files for validation

## Known Issues

_None yet._

## Session Notes

_Session started 2026-05-22._
