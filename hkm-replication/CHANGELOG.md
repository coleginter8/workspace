# CHANGELOG — hkm-replication

## run-20260520-hkm-tables-2-3 (2026-05-20)

- Greenfield Python package implementing HKM (2017) Tables 2 and 3 replication
- 39/39 unit + integration tests PASS; PASS WITH NOTE on cell-by-cell comparison
- IT-4 bounds: PASS (all Table 2 ratios in (0,1])
- IT-8 signs: all 6 sign checks PASS
- Known data gaps: pre-1978 WRDS coverage, no Datastream for foreign dealers
- Commits: 9871b28 -> b9e6e93 (main branch)
