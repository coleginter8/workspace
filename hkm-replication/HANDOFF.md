# Handoff — hkm-replication

Last updated: 2026-05-20, run-20260520-hkm-tables-2-3

## Current state

Package `hkm/` is implemented and passing all tests. `compute_table2()` and `compute_table3()` are the main entry points.

## How to run

```bash
pip install -e ".[dev]"
python -c "from hkm.tables.table2 import compute_table2; print(compute_table2())"
python -c "from hkm.tables.table3 import compute_table3; pa, pb = compute_table3(); print(pa)"
```

Requires WRDS credentials in `~/.pgpass`:
```
wrds-pgdata.wharton.upenn.edu:9737:wrds:coleginter:<password>
```

## Known limitations

1. WRDS Compustat starts ~1978 -- Table 2 denominators understated for 1960-1977
2. No Datastream -- foreign primary dealers excluded; US-only from CRSP
3. AEM leverage from FRED BOGZ1FL664090005Q/664190005Q approximation
4. Table 2 Banks denominator may differ from paper's SIC definition
5. E/P growth uses simple (non-CAPE) E/P at quarterly frequency

## Next steps (if picking up this work)

- Source Compustat historical coverage pre-1978 (e.g., CRSP/Compustat annual file)
- Add Datastream foreign dealer data for more complete Table 3 coverage
- Validate AEM leverage against AEM (2014) paper's published leverage series
