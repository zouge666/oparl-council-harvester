"""turns one oparl paper into one record for iris_staging.signal_ingest.

the field mapping is explained in docs/mapping.md.
"""

import hashlib
import json
from datetime import date, datetime

from council_harvester.geo import resolve_location

SOURCE_SYSTEM = "oparl"


def normalize_paper(paper, source, signal_type, matched_keywords, today=None):
    """builds the staging record for one paper and gives it back as a dict.

    problems we find (no date, bad point, ...) go into quality_flags,
    so they stay visible and dont just get lost.
    """
    if today is None:
        today = date.today()

    flags = []

    published_date, problem = read_date(paper.get("date"), today)
    if problem:
        flags.append(problem)

    modified_at, problem = read_timestamp(paper.get("modified"))
    if problem:
        flags.append(problem)

    geo = resolve_location(paper.get("location"))
    for problem in geo["problems"]:
        flags.append("location: " + problem)

    record = {
        "source_system": SOURCE_SYSTEM,
        "source_name": source["name"],
        "source_record_id": paper["id"],
        "signal_type": signal_type,
        "title": clean_title(paper.get("name")),
        "reference": text_or_none(paper.get("reference")),
        "paper_type": text_or_none(paper.get("paperType")),
        "published_date": published_date,
        "source_url": make_web_url(paper, source),
        "municipality": source["municipality"],
        "region": source.get("region"),
        "location_text": geo["location_text"],
        "lon": geo["lon"],
        "lat": geo["lat"],
        "geo_status": geo["geo_status"],
        "matched_keywords": matched_keywords,
        "quality_flags": flags,
        "source_modified_at": modified_at,
        "raw_record": paper,
    }
    record["content_hash"] = make_hash(record)
    return record


def read_date(value, today):
    """checks the paper date (YYYY-MM-DD). gives back (date as text, problem)"""
    if value is None or value == "":
        return None, "missing_date"
    if not isinstance(value, str):
        return None, f"bad_date: {value}"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None, f"bad_date: {value}"

    # we keep a future date, but we want to see it in the report
    if parsed > today:
        return parsed.isoformat(), f"future_date: {value}"
    return parsed.isoformat(), None


def read_timestamp(value):
    """checks the "modified" time, we need it for incremental runs"""
    if value is None or value == "":
        return None, "missing_modified"
    if not isinstance(value, str):
        return None, f"bad_modified: {value}"
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return None, f"bad_modified: {value}"
    return value, None


def make_web_url(paper, source):
    """a link for humans. we use the "web" field if the paper has one,
    else we build it with a template from the config, else we use the api url.

    the template depends on the kind of paper. in dresden that is the part
    before the number in the id, like .../papers/vo/30035 or .../papers/ag/12193
    """
    web = paper.get("web")
    if isinstance(web, str) and web.startswith("http"):
        return web

    templates = source.get("web_urls", {})
    parts = paper["id"].rstrip("/").split("/")
    if len(parts) >= 2:
        kind = parts[-2]
        number = parts[-1]
        if kind in templates:
            return templates[kind].replace("{number}", number)

    # we dont know this kind of paper, the api url always works
    return paper["id"]


def make_hash(record):
    """a fingerprint of the record. if the hash changes, the paper has changed"""
    data = {}
    for key, value in record.items():
        if key != "content_hash":
            data[key] = value
    text = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_title(value):
    # some titles have double spaces or line breaks in them
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())


def text_or_none(value):
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
