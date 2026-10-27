"""command line for the harvester.

run `council-harvester --help` to see all commands.
"""

import argparse
import sys

from council_harvester.config import ConfigError, get_source, load_settings
from council_harvester.oparl_client import OParlClient, OParlError


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings(args.config)
        if args.command == "check":
            return run_check(settings, args.source)
    except ConfigError as e:
        print(f"config problem: {e}", file=sys.stderr)
        return 2

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
