# Repository Context

```yaml
RepoName: "hkm-replication"
RepoURL: "https://github.com/coleginter8/hkm-replication"
RepoCheckout: "/Users/gregoryginter/Desktop/UChicago MSFM/FINM 33200/Final Project/HKM Replication"
ActiveRun: "run-20260515-124030"
DefaultWorkflow: agent-teams
DefaultProfile: "python-package"
DefaultBranch: "main"
Language: "Python"
Version: ""
CredentialStatus: ""
CredentialMethod: "gh-cli"
CredentialVerifiedAt: ""
BrainMode: "isolated"
BrainRepo: "statsclaw/brain"
SeedbankRepo: "statsclaw/brain-seedbank"
BrainLastPull: ""
```

## Request Defaults

- Default acceptance criteria: Table values match HKM (2017) Tables 2 & 3 within rounding tolerance
- Default write surface: determined by impact.md per run
- Default validation level: full (build + check + test)

## Key Functions

- WRDS PostgreSQL connection via ~/.pgpass (host: wrds-pgdata.wharton.upenn.edu:9737, user: coleginter)
- Target paper: He, Kelly & Manela (2017) "Intermediary Asset Pricing: New Theory and Evidence"
- Target tables: Table 2 (Summary Statistics), Table 3 (Asset Pricing Tests)

## Constraints

- Data sourced from WRDS (CRSP, Compustat, intermediary balance-sheet data)
- WRDS credentials: ~/.pgpass entry for wrds-pgdata.wharton.upenn.edu:9737
- Must match published HKM (2017) results within rounding tolerance

## Known Issues

_None yet._

## Session Notes

- Session started 2026-05-15. Goal: replicate Tables 2 and 3 of HKM (2017).
