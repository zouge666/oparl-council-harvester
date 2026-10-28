# oparl-council-harvester

[![ci](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml)

A small python tool that reads council papers from OParl APIs in Saxony (Dresden, Leipzig).
It looks for papers about big substations, chip fabs and data center parks and loads them
into the PostGIS staging table `iris_staging.signal_ingest` (task IRIS-SIG-22).

## Setup

You need python 3.11+, [uv](https://docs.astral.sh/uv/) and docker.

```bash
uv sync --extra dev
cp .env.example .env
docker compose up -d
uv run council-harvester init-db
```

## Run

```bash
# see if the sources work
uv run council-harvester check

# first run, only papers changed since 2024 (dresden is slow, about 30 sec per page)
uv run council-harvester harvest dresden --since 2024-01-01

# next runs are incremental, it remembers how far it got
uv run council-harvester harvest dresden

# no database? just write a file
uv run council-harvester harvest dresden --since 2026-09-01 --no-db --jsonl output/dresden.jsonl

# check the data in the database
docker compose exec db psql -U iris -d iris -f /sql/validation_queries.sql
```

Running it again does not make duplicates. After each run a quality report goes to `reports/`.
Sources, keywords and filters are in `config/harvester.toml`. The database url is in `.env`.

## Tests

```bash
uv run ruff check .
uv run pytest
```

The database tests need `TEST_DATABASE_URL` (see `.env.example`), without it they are skipped:

```bash
docker compose exec db createdb -U iris iris_test
export TEST_DATABASE_URL=postgresql://iris:change-me@localhost:5432/iris_test
uv run pytest
```

## Data source

- Dresden: Somacos "Session" OParl 1.1 api at https://oparl.dresden.de/system. Works.
- Leipzig: ALLRIS OParl. The server says the module is turned off (http 500), so it is
  disabled in the config. The code is tested with fixture files instead.
- More details: [docs/data_source.md](docs/data_source.md)

## Mapping

- One OParl `Paper` is one row. The key is `(source_system, source_record_id)`,
  the record id is the paper url from the api.
- The signal type comes from keywords in the title.
- Location points (lon/lat) are turned into EPSG:25832 by PostGIS.
- Field by field: [docs/mapping.md](docs/mapping.md)

## Known limitations

- We only read the title, not the pdf files. So some matches are false positives
  (like the city's own IT "Rechenzentrum") and papers that only talk about it in the pdf are missed.
- Dresden papers have no locations, so they are all `no_location`. We dont guess points from titles.
- The task asks for EPSG:25832, but Saxony mostly uses EPSG:25833 (UTM zone 33).
  The lon/lat stays in `raw_record` if someone needs 25833 later.
- Deleted papers are skipped and counted, but a row we saved before is not removed.
- Leipzig stays off until the city turns the OParl module back on.
- Dresden needs about 30 seconds per 100 papers, so a full first run takes hours. Use `--since`.

## Sample output

`samples/` has a real run against Dresden: the records, the quality reports of the first and
the second run, and the output of the validation queries.
