# Samples

Real output from the Dresden OParl api, made on 2026-10-27 with a local PostGIS.
The data is public (license `dl-de/zero-2-0`), so nothing had to be anonymized.

What we ran:

```bash
uv run council-harvester init-db

# 1. first run, papers changed since 2024
uv run council-harvester harvest dresden --since 2024-01-01 --jsonl samples/dresden_signals.jsonl

# 2. second run, incremental (it uses the saved watermark)
uv run council-harvester harvest dresden

# 3. read a part again on purpose, to show that nothing gets doubled
uv run council-harvester harvest dresden --since 2026-09-20

# 4. checks
docker compose exec db psql -U iris -d iris -f /sql/validation_queries.sql
```

Files:

- `dresden_signals.jsonl` - the matched papers, one json per line (without `raw_record`)
- `report_1_first_run.md` - quality report of the first run
- `report_2_incremental_run.md` - the second run only asked for papers changed since the last one
- `report_3_rerun.md` - read the last weeks again: the matched papers come back as unchanged
- `validation_results.txt` - output of the validation queries (duplicates: 0 rows)

Results:

| run | pages | papers read | matched | new | updated | unchanged |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1. first run (since 2024-01-01, took about 28 min) | 53 | 5213 | 12 | 12 | 0 | 0 |
| 2. incremental run | 1 | 1 | 0 | 0 | 0 | 0 |
| 3. read again (since 2026-09-20) | 3 | 268 | 2 | 0 | 0 | 2 |

- the 12 matches: 10 `semiconductor_dc_park` (TSMC / ESMC, the "Halbleiterstandort"
  cooperation, Silicon Saxony) and 2 `mega_substation` (110-kV power lines in Rähnitz)
- 3 of them are false positives, they are about the city's own IT data center ("Rechenzentrum")
- all 12 are `no_location`, because dresden papers have no locations
- the validation queries find no duplicates and no bad points
