from datetime import date
from pathlib import Path

import psycopg
import pytest

from council_harvester import db
from council_harvester.normalize import normalize_paper

SQL_DIR = str(Path(__file__).parent.parent / "sql")

SOURCE = {"name": "testcity", "municipality": "Teststadt", "region": "Sachsen"}


def make_record(**changes):
    paper = {
        "id": "https://oparl.example.test/papers/1",
        "name": "Neubau Umspannwerk Nord",
        "reference": "V0001/26",
        "date": "2026-05-04",
        "modified": "2026-05-04T10:00:00+02:00",
    }
    paper.update(changes)
    today = date(2026, 10, 27)
    return normalize_paper(paper, SOURCE, "mega_substation", ["umspannwerk"], today=today)


def count_rows(conn):
    return conn.execute("SELECT count(*) FROM iris_staging.signal_ingest").fetchone()[0]


def test_init_db_can_run_twice(conn):
    names = db.init_db(conn, SQL_DIR)
    assert names[0] == "001_create_signal_ingest.sql"


def test_new_record_is_inserted(conn):
    assert db.save_record(conn, make_record()) == "inserted"
    assert count_rows(conn) == 1


def test_same_record_again_changes_nothing(conn):
    db.save_record(conn, make_record())
    before = conn.execute("SELECT updated_at FROM iris_staging.signal_ingest").fetchone()[0]

    assert db.save_record(conn, make_record()) == "unchanged"

    after = conn.execute("SELECT updated_at FROM iris_staging.signal_ingest").fetchone()[0]
    assert count_rows(conn) == 1
    assert before == after


def test_changed_record_is_updated(conn):
    db.save_record(conn, make_record())
    assert db.save_record(conn, make_record(name="Neubau Umspannwerk Nord, 2. Lesung")) == "updated"

    title = conn.execute("SELECT title FROM iris_staging.signal_ingest").fetchone()[0]
    assert title == "Neubau Umspannwerk Nord, 2. Lesung"
    assert count_rows(conn) == 1


def test_point_is_saved_as_epsg_25832(conn):
    location = {"geojson": {"type": "Point", "coordinates": [13.7416, 51.0519]}}
    db.save_record(conn, make_record(location=[location]))

    row = conn.execute(
        "SELECT ST_SRID(geom), ST_X(geom), ST_Y(geom), geo_status FROM iris_staging.signal_ingest"
    ).fetchone()
    assert row[0] == 25832
    # frauenkirche dresden in utm zone 32. we checked the numbers with pyproj too
    assert row[1] == pytest.approx(832265.3, abs=1)
    assert row[2] == pytest.approx(5666299.8, abs=1)
    assert row[3] == "resolved"


def test_bad_point_is_not_saved(conn):
    location = {"geojson": {"type": "Point", "coordinates": [51.0519, 13.7416]}}
    db.save_record(conn, make_record(location=[location]))

    row = conn.execute("SELECT geom, geo_status FROM iris_staging.signal_ingest").fetchone()
    assert row[0] is None
    assert row[1] == "invalid"


def test_database_blocks_a_point_without_resolved_status(conn):
    record = make_record()
    record["lon"] = 13.7416
    record["lat"] = 51.0519
    # geo_status is still "no_location" here, so the check constraint has to stop it
    with pytest.raises(psycopg.errors.CheckViolation):
        db.save_record(conn, record)
