# Repository Context

```yaml
RepoName: "gsw-replication"
RepoURL: "https://github.com/coleginter8/gsw-replication"
RepoCheckout: ".repos/gsw-replication"
ActiveRun: ""
DefaultWorkflow: agent-teams
DefaultProfile: "python-package"
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

- Default acceptance criteria: all profile validation commands pass with zero errors
- Default write surface: determined by impact.md per run
- Default validation level: full (build + check + test)

## Key Functions

Replication of Gürkaynak, Sack & Wright (2007) Nelson-Siegel-Svensson zero-coupon Treasury yield curve.
Deliverable: daily parquet file with columns ds, unique_id (SVENY01–SVENY30), y (yield in percent).

## Constraints

- Builder must NOT read validation/validation_oracle.parquet — oracle is tester-only
- Output must match GSW (2007) methodology exactly per paper at papers/gsw_2007.pdf
- Maximum date coverage; daily frequency

## Known Issues

_None yet._

## Session Notes

Initial run: 2026-05-21. Goal is to replicate GSW daily zero-coupon yield curve dataset.
