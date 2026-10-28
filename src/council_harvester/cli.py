"""command line for the harvester.

run `council-harvester --help` to see all commands.
"""

import argparse
import json
import os
import sys

import psycopg
from dotenv import load_dotenv

from council_harvester import db
from council_harvester.config import ConfigError, get_source, load_settings
from council_harvester.oparl_client import OParlClient, OParlError
from council_harvester.pipeline import harvest_source
from council_harvester.report import write_report


def main(argv=None):
    # reads the .env file in the current folder if there is one. real env vars still win
    load_dotenv(".env")

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings(args.config)
        if args.command == "check":
            return run_check(settings, args.source)
        if args.command == "init-db":
            return run_init_db(settings)
        if args.command == "harvest":
            return run_harvest(settings, args)
    except ConfigError as e:
        print(f"config problem: {e}", file=sys.stderr)
        return 2
    except psycopg.Error as e:
        print(f"database problem: {e}", file=sys.stderr)
        return 1

    parser.print_help()
    return 2


def build_parser():
    parser = argparse.ArgumentParser(
        prog="council-harvester",
        description="harvests council papers from oparl apis",
    )
    parser.add_argument("--config", help="path to the toml config (default: config/harvester.toml)")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check that the oparl sources answer")
    check.add_argument("source", nargs="?", help="only check this source")

    commands.add_parser("init-db", help="create the schema and tables in postgis")

    harvest = commands.add_parser("harvest", help="harvest the papers of one source")
    harvest.add_argument("source", help="name of the source in the config, like dresden")
    harvest.add_argument("--since", help="only papers changed since then (2026-01-31)")
    harvest.add_argument("--full", action="store_true", help="ignore the saved state, read all")
    harvest.add_argument("--max-pages", type=int, help="stop after this many pages")
    harvest.add_argument("--no-db", action="store_true", help="dry run, dont save anything")
    harvest.add_argument("--jsonl", help="also write the records to this jsonl file")
    harvest.add_argument("--report-dir", default="reports", help="where the report goes")
    return parser


def run_check(settings, only_source=None):
    """calls every source once and prints what it finds.

    handy to see if a endpoint still works or if the format changed.
    """
    sources = settings["sources"]
    if only_source:
        sources = [get_source(settings, only_source)]

    client = OParlClient(settings["http"])
    failed = 0
    for source in sources:
        title = f"== {source['name']}"
        if not source["enabled"]:
            title += " (disabled in config)"
        print(title)

        try:
            check_source(client, source)
        except OParlError as e:
            print(f"   FAILED: {e}")
            # a disabled source is allowed to be broken
            if source["enabled"]:
                failed += 1

    if failed > 0:
        return 1
    return 0


def check_source(client, source):
    system, bodies = client.get_bodies(source["system_url"])
    print(f"   name:    {system.get('name')}")
    print(f"   oparl:   {system.get('oparlVersion')}")
    print(f"   vendor:  {system.get('vendor')}")
    print(f"   product: {system.get('product')}")
    print(f"   license: {system.get('license')}")
    print(f"   bodies:  {len(bodies)}")

    for body in bodies:
        print(f"   - body '{body.get('name')}', papers at {body['paper']}")
        items, next_url = client.get_page(body["paper"])
        if items is None:
            print("     paper list is missing (404)")
        elif len(items) == 0:
            print("     paper list is empty")
        else:
            first = items[0]
            print(f"     first paper: {first.get('date')} {first.get('name')}")


def run_init_db(settings):
    conn = db.connect(settings["database_url"])
    names = db.init_db(conn)
    conn.close()
    print("ran sql files: " + ", ".join(names))
    return 0


def run_harvest(settings, args):
    source = get_source(settings, args.source)
    if not source["enabled"]:
        print(f"source '{source['name']}' is disabled in the config", file=sys.stderr)
        return 2

    conn = None
    if not args.no_db:
        conn = db.connect(settings["database_url"])

    # incremental run: only ask for papers that changed since the last full run
    since = args.since
    if since is None and conn is not None and not args.full:
        since = db.get_watermark(conn, source["name"])
        if since:
            print(f"incremental run, papers changed since {since}")

    client = OParlClient(settings["http"])
    records, stats = harvest_source(client, settings, source, conn, since, args.max_pages)

    # only move the watermark after a complete run, else we could miss papers next time
    if conn is not None and stats["status"] == "ok":
        db.save_watermark(conn, source["name"], stats["newest_modified"])
    if conn is not None:
        conn.close()

    if args.jsonl:
        write_jsonl(records, args.jsonl)
    print_summary(stats)
    report_path = write_report(stats, records, args.report_dir)
    print(f"  report: {report_path}")

    if stats["status"] == "failed":
        return 1
    return 0


def write_jsonl(records, path):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            row = dict(record)
            # the raw json is big, it only goes into the database
            del row["raw_record"]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records to {path}")


def print_summary(stats):
    print(f"harvest {stats['source']}: {stats['status']}")
    if stats["error"]:
        print(f"  error: {stats['error']}")
    print(f"  pages: {stats['pages']}, papers: {stats['papers_seen']}, matched: {stats['matched']}")
    print(
        f"  saved: {stats['inserted']} new, {stats['updated']} updated, "
        f"{stats['unchanged']} unchanged"
    )
    print(
        f"  skipped: {stats['malformed']} broken, {stats['duplicates']} double, "
        f"{stats['deleted']} deleted, {stats['excluded']} excluded, {stats['too_old']} too old, "
        f"{stats['not_relevant']} not relevant"
    )
    for warning in stats["warnings"]:
        print(f"  warning: {warning}")
