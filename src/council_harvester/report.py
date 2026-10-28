"""writes a small quality report (markdown) after each harvest run.

it shows the counts and lists everything that went wrong,
so problems are visible and dont get lost quietly.
"""

import os
from datetime import datetime

COUNT_ROWS = [
    ("pages read", "pages"),
    ("http requests", "requests"),
    ("papers seen", "papers_seen"),
    ("matched and kept", "matched"),
    ("saved as new", "inserted"),
    ("updated", "updated"),
    ("unchanged", "unchanged"),
    ("broken papers", "malformed"),
    ("double papers", "duplicates"),
    ("deleted papers", "deleted"),
    ("skipped by exclude word", "excluded"),
    ("matched but too old", "too_old"),
    ("not relevant", "not_relevant"),
]

# these geo statuses need a human to look at them
GEO_TO_CHECK = ["ambiguous", "invalid", "unresolved"]

# so a big run does not make a huge file
MAX_LIST_LINES = 200


def build_report(stats, records):
    """gives back the report as markdown text"""
    lines = [
        f"# Harvest report: {stats['source']}",
        "",
        f"- status: **{stats['status']}**",
        f"- started: {stats['started_at']}",
        f"- finished: {stats['finished_at']}",
        f"- papers changed since: {stats['since'] or 'all papers'}",
    ]
    if stats["error"]:
        lines.append(f"- error: {stats['error']}")

    lines += ["", "## Counts", "", "| what | count |", "| --- | ---: |"]
    for label, key in COUNT_ROWS:
        lines.append(f"| {label} | {stats[key]} |")

    lines += ["", "## Locations", "", "| geo_status | count |", "| --- | ---: |"]
    for status, count in stats["geo"].items():
        lines.append(f"| {status} | {count} |")

    lines += ["", "## Matched papers", ""]
    paper_lines = []
    for record in records:
        paper_lines.append(
            f"- {record['published_date']} `{record['reference']}` {record['signal_type']}: "
            f"{record['title']} ({record['source_url']})"
        )
    lines += short_list(paper_lines)

    lines += ["", "## Papers we could not use", ""]
    problem_lines = []
    for item in stats["problems"]:
        problem_lines.append(f"- {item['id'] or '(no id)'}: {item['problem']}")
    lines += short_list(problem_lines)

    lines += ["", "## Matched papers with quality flags", ""]
    flag_lines = []
    for record in records:
        if record["quality_flags"]:
            flags = ", ".join(record["quality_flags"])
            flag_lines.append(f"- `{record['reference']}` {record['title']}: {flags}")
    lines += short_list(flag_lines)

    lines += ["", "## Locations to check by hand", ""]
    geo_lines = []
    for record in records:
        if record["geo_status"] in GEO_TO_CHECK:
            text = record["location_text"] or "no address"
            geo_lines.append(f"- `{record['reference']}` {record['geo_status']}: {text}")
    lines += short_list(geo_lines)

    lines += ["", "## Warnings", ""]
    warning_lines = []
    for warning in stats["warnings"]:
        warning_lines.append(f"- {warning}")
    lines += short_list(warning_lines)

    return "\n".join(lines) + "\n"


def short_list(lines):
    if len(lines) == 0:
        return ["none"]
    if len(lines) > MAX_LIST_LINES:
        rest = len(lines) - MAX_LIST_LINES
        return lines[:MAX_LIST_LINES] + [f"- ... and {rest} more"]
    return lines


def write_report(stats, records, folder="reports"):
    """writes the report into the folder and gives back the file path"""
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = os.path.join(folder, f"{stats['source']}_{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(build_report(stats, records))
    return path
