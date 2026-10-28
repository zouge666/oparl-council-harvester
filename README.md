# oparl-council-harvester

[![ci](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml)

A small python tool that reads council papers from OParl APIs in Saxony (Dresden, Leipzig).
It looks for papers about big substations, chip fabs and data center parks and puts them
in a PostGIS staging table.

Still work in progress.

## Setup

You need python 3.11+, [uv](https://docs.astral.sh/uv/) and docker.

```bash
uv sync --extra dev
cp .env.example .env
docker compose up -d
uv run council-harvester init-db
```

## Check the sources

```bash
uv run council-harvester check
```

What we found about the sources is in [docs/data_source.md](docs/data_source.md).
How a paper becomes a row is in [docs/mapping.md](docs/mapping.md).

## Harvest

```bash
# first run, only papers changed since 2024 (dresden is slow, ~30 sec per page)
uv run council-harvester harvest dresden --since 2024-01-01

# next runs are incremental, it remembers how far it got
uv run council-harvester harvest dresden

# try it without a database, just write a file
uv run council-harvester harvest dresden --since 2026-09-01 --no-db --jsonl output/dresden.jsonl
```

Running it again does not make duplicates, it updates changed papers and skips the rest.
After each run a quality report (counts, broken papers, flags, locations to check)
is written to `reports/`.

## Checks

```bash
uv run ruff check .
uv run pytest
```

The database tests need `TEST_DATABASE_URL`, without it they are skipped.
To run them local:

```bash
docker compose exec db createdb -U iris iris_test
export TEST_DATABASE_URL=postgresql://iris:change-me@localhost:5432/iris_test
uv run pytest
```
