"""everything that talks to postgres / postgis."""

import json
import os

import psycopg

SQL_DIR = "sql"

# insert a new row, or update the old one when the paper changed.
# the WHERE at the end makes sure we dont touch rows that are the same as before.
# postgis turns the lon/lat point (EPSG:4326) into EPSG:25832.
UPSERT_SQL = """
INSERT INTO iris_staging.signal_ingest (
    source_system, source_name, source_record_id, signal_type, title, reference,
    paper_type, published_date, source_url, municipality, region, location_text,
    geom, geo_status, matched_keywords, quality_flags, source_modified_at,
    content_hash, raw_record
) VALUES (
    %(source_system)s, %(source_name)s, %(source_record_id)s, %(signal_type)s, %(title)s,
    %(reference)s, %(paper_type)s, %(published_date)s::date, %(source_url)s,
    %(municipality)s, %(region)s, %(location_text)s,
    ST_Transform(ST_SetSRID(ST_MakePoint(%(lon)s::float8, %(lat)s::float8), 4326), 25832),
    %(geo_status)s, %(matched_keywords)s::text[], %(quality_flags)s::text[],
    %(source_modified_at)s::timestamptz, %(content_hash)s, %(raw_record)s::jsonb
)
ON CONFLICT (source_system, source_record_id) DO UPDATE SET
    source_name = EXCLUDED.source_name,
    signal_type = EXCLUDED.signal_type,
    title = EXCLUDED.title,
    reference = EXCLUDED.reference,
    paper_type = EXCLUDED.paper_type,
    published_date = EXCLUDED.published_date,
    source_url = EXCLUDED.source_url,
    municipality = EXCLUDED.municipality,
    region = EXCLUDED.region,
    location_text = EXCLUDED.location_text,
    geom = EXCLUDED.geom,
    geo_status = EXCLUDED.geo_status,
    matched_keywords = EXCLUDED.matched_keywords,
    quality_flags = EXCLUDED.quality_flags,
    source_modified_at = EXCLUDED.source_modified_at,
    content_hash = EXCLUDED.content_hash,
    raw_record = EXCLUDED.raw_record,
    updated_at = now()
WHERE iris_staging.signal_ingest.content_hash <> EXCLUDED.content_hash
RETURNING (xmax = 0) AS is_new
"""


def connect(database_url):
    if not database_url:
        raise psycopg.OperationalError("DATABASE_URL is not set, see .env.example")
    # autocommit means every saved row is its own small transaction.
    # if a run breaks in the middle, the rows we already saved are still fine
    return psycopg.connect(database_url, autocommit=True)


def init_db(conn, sql_dir=SQL_DIR):
    """runs the sql files that start with a number (001_..., 002_...) in order"""
    names = []
    for name in sorted(os.listdir(sql_dir)):
        if name.endswith(".sql") and name[0].isdigit():
            names.append(name)

    for name in names:
        with open(os.path.join(sql_dir, name), encoding="utf-8") as f:
            conn.execute(f.read())
    return names


def save_record(conn, record):
    """saves one record. gives back "inserted", "updated" or "unchanged"."""
    params = dict(record)
    params["raw_record"] = json.dumps(record["raw_record"], ensure_ascii=False)

    row = conn.execute(UPSERT_SQL, params).fetchone()
    # no row back means the WHERE said no, so nothing changed
    if row is None:
        return "unchanged"
    # xmax is 0 when postgres made a brand new row (a known postgres trick)
    if row[0]:
        return "inserted"
    return "updated"


def get_watermark(conn, source_name):
    """the newest "modified" time from the last full run, minus one hour.

    the hour is just to be safe with clocks. papers we get twice are no problem,
    they come back as "unchanged". gives back None if we never had a full run.
    """
    row = conn.execute(
        "SELECT last_modified_seen - interval '1 hour' FROM iris_staging.harvest_state "
        "WHERE source_name = %s",
        [source_name],
    ).fetchone()
    if row is None:
        return None
    return row[0].isoformat()


def save_watermark(conn, source_name, newest_modified):
    if newest_modified is None:
        return
    conn.execute(
        """
        INSERT INTO iris_staging.harvest_state (source_name, last_modified_seen)
        VALUES (%s, %s)
        ON CONFLICT (source_name) DO UPDATE SET
            last_modified_seen = GREATEST(harvest_state.last_modified_seen,
                                          EXCLUDED.last_modified_seen),
            last_success_at = now()
        """,
        [source_name, newest_modified],
    )
