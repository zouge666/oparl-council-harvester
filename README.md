# oparl-council-harvester

[![ci](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml/badge.svg)](https://github.com/zouge666/oparl-council-harvester/actions/workflows/ci.yml)

A small python tool that reads council papers from OParl APIs in Saxony (Dresden, Leipzig).
It looks for papers about big substations, chip fabs and data center parks and puts them
in a PostGIS staging table.

Still work in progress.

## Setup

```bash
uv sync --extra dev
```

## Check the sources

```bash
uv run council-harvester check
```

What we found about the sources is in [docs/data_source.md](docs/data_source.md).

## Checks

```bash
uv run ruff check .
uv run pytest
```
