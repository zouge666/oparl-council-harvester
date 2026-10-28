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
