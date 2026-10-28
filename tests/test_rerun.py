"""the big promise: running the harvest again never makes duplicates.

these tests need a postgis database (TEST_DATABASE_URL), see the README.
"""

import os
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlparse

import responses

from council_harvester import db
from council_harvester.cli import main
from council_harvester.oparl_client import OParlClient
from council_harvester.pipeline import harvest_source
from tests.helpers import PAGE_1_URL, PAGE_2_URL, PAPERS_URL, SYSTEM_URL, load_fixture

UTC = timezone.utc


def run(settings, source, conn, since=None):
    client = OParlClient(settings["http"])
    return harvest_source(client, settings, source, conn, since)


def count_rows(conn):
    return conn.execute("SELECT count(*) FROM iris_staging.signal_ingest").fetchone()[0]


def test_first_run_saves_the_matched_papers(fake_oparl, settings, source, conn):
    records, stats = run(settings, source, conn)
    assert stats["inserted"] == 5
    assert count_rows(conn) == 5


def test_second_run_makes_no_duplicates(fake_oparl, settings, source, conn):
    run(settings, source, conn)
    records, stats = run(settings, source, conn)

    assert stats["inserted"] == 0
    assert stats["updated"] == 0
    assert stats["unchanged"] == 5
    assert count_rows(conn) == 5


def test_changed_paper_is_updated_and_not_doubled(fake_oparl, settings, source, conn):
    run(settings, source, conn)

    page = load_fixture("papers_page1.json")
    page["data"][1]["name"] = "Ansiedlung einer Halbleiterfabrik im Industriegebiet Ost - Ergänzung"
    page["data"][1]["modified"] = "2026-06-01T09:00:00+02:00"
    fake_oparl.replace(responses.GET, PAGE_1_URL, json=page)

    records, stats = run(settings, source, conn)

    assert stats["updated"] == 1
    assert stats["unchanged"] == 4
    assert count_rows(conn) == 5
    row = conn.execute(
        "SELECT title FROM iris_staging.signal_ingest WHERE reference = 'V9002/26'"
    ).fetchone()
    assert row[0].endswith("Ergänzung")


def test_double_paper_in_one_run_is_saved_once(fake_oparl, settings, source, conn):
    # paper 1001 is on page 1 and on page 2 of the fixtures
    records, stats = run(settings, source, conn)
    assert stats["duplicates"] == 1

    row = conn.execute(
        "SELECT count(*) FROM iris_staging.signal_ingest WHERE source_record_id LIKE %s",
        ["%/vo/1001"],
    ).fetchone()
    assert row[0] == 1


def test_failed_run_can_just_be_started_again(fake_oparl, settings, source, conn):
    fake_oparl.replace(responses.GET, PAGE_2_URL, status=503)
    records, stats = run(settings, source, conn)
    assert stats["status"] == "failed"
    # what we got from page 1 is saved and stays
    assert count_rows(conn) == 3

    fake_oparl.replace(responses.GET, PAGE_2_URL, json=load_fixture("papers_page2.json"))
    records, stats = run(settings, source, conn)

    assert stats["status"] == "ok"
    assert stats["inserted"] == 2
    assert stats["unchanged"] == 3
    assert count_rows(conn) == 5


def test_no_watermark_before_the_first_run(conn):
    assert db.get_watermark(conn, "testcity") is None


def test_watermark_is_one_hour_before_the_newest_paper(conn):
    db.save_watermark(conn, "testcity", datetime(2026, 5, 4, 8, 0, tzinfo=UTC))
    since = datetime.fromisoformat(db.get_watermark(conn, "testcity"))
    assert since == datetime(2026, 5, 4, 7, 0, tzinfo=UTC)


def test_watermark_never_goes_back(conn):
    db.save_watermark(conn, "testcity", datetime(2026, 5, 4, 8, 0, tzinfo=UTC))
    db.save_watermark(conn, "testcity", datetime(2026, 1, 1, 8, 0, tzinfo=UTC))
    since = datetime.fromisoformat(db.get_watermark(conn, "testcity"))
    assert since == datetime(2026, 5, 4, 7, 0, tzinfo=UTC)


CONFIG = f"""
[http]
max_retries = 1
retry_wait_seconds = 0
page_delay_seconds = 0
page_size = 10

[signals]
mega_substation = ["umspannwerk", "110 kv"]
semiconductor_dc_park = ["halbleiter", "rechenzentrum", "tsmc"]

[filter]
min_paper_date = "2022-01-01"
exclude_keywords = ["kleinprojektförderung"]

[[sources]]
name = "testcity"
municipality = "Teststadt"
system_url = "{SYSTEM_URL}"
"""


def test_cli_second_run_only_asks_for_changed_papers(
    fake_oparl, conn, tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    config = tmp_path / "harvester.toml"
    config.write_text(CONFIG, encoding="utf-8")
    args = ["--config", str(config), "harvest", "testcity", "--report-dir", str(tmp_path)]

    assert main(args) == 0

    # the second run sends modified_since, so we answer that with a empty list
    fake_oparl.add(responses.GET, PAPERS_URL, json=load_fixture("papers_empty.json"))
    assert main(args) == 0

    assert "incremental run" in capsys.readouterr().out
    query = parse_qs(urlparse(fake_oparl.calls[-1].request.url).query)
    since = datetime.fromisoformat(query["modified_since"][0])
    # newest paper was 2026-05-04 10:00 +02:00, that is 08:00 utc, minus one hour
    assert since == datetime(2026, 5, 4, 7, 0, tzinfo=UTC)
    assert count_rows(conn) == 5
