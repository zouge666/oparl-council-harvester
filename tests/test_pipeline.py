import responses

from council_harvester.oparl_client import OParlClient
from council_harvester.pipeline import harvest_source, newer_time
from tests.helpers import PAGE_1_URL, PAGE_2_URL, load_fixture


def run(settings, source, **options):
    client = OParlClient(settings["http"])
    return harvest_source(client, settings, source, **options)


def test_full_run_on_the_fixtures(fake_oparl, settings, source):
    records, stats = run(settings, source)

    assert stats["status"] == "ok"
    assert stats["pages"] == 2
    assert stats["papers_seen"] == 12
    assert stats["malformed"] == 2
    assert stats["deleted"] == 1
    assert stats["duplicates"] == 1
    assert stats["excluded"] == 1
    assert stats["not_relevant"] == 1
    assert stats["too_old"] == 1
    assert stats["matched"] == 5
    assert len(records) == 5


def test_records_have_the_right_signal_and_geo(fake_oparl, settings, source):
    records, stats = run(settings, source)
    by_ref = {}
    for record in records:
        by_ref[record["reference"]] = record

    assert by_ref["V9001/26"]["signal_type"] == "mega_substation"
    assert by_ref["V9001/26"]["geo_status"] == "resolved"
    assert by_ref["V9002/26"]["signal_type"] == "semiconductor_dc_park"
    assert by_ref["V9002/26"]["geo_status"] == "no_location"
    assert by_ref["V9005/26"]["geo_status"] == "unresolved"
    assert by_ref["V9009/26"]["geo_status"] == "invalid"
    # matches both, the substation comes first in the config
    assert by_ref["V9010/26"]["signal_type"] == "mega_substation"
    assert by_ref["V9010/26"]["matched_keywords"] == ["umspannwerk", "halbleiter"]
    assert "bad_date: 10.02.2026" in by_ref["V9010/26"]["quality_flags"]

    assert stats["geo"] == {
        "resolved": 1,
        "ambiguous": 0,
        "invalid": 1,
        "unresolved": 1,
        "no_location": 2,
    }


def test_broken_papers_are_listed(fake_oparl, settings, source):
    records, stats = run(settings, source)
    problems = []
    for item in stats["problems"]:
        problems.append(item["problem"])
    assert "paper has no title (name)" in problems
    assert "paper is not a json object" in problems


def test_newest_modified_time_is_remembered(fake_oparl, settings, source):
    records, stats = run(settings, source)
    assert stats["newest_modified"].isoformat() == "2026-05-04T10:00:00+02:00"


def test_empty_list(fake_oparl, settings, source):
    fake_oparl.replace(responses.GET, PAGE_1_URL, json=load_fixture("papers_empty.json"))
    records, stats = run(settings, source)
    assert stats["status"] == "ok"
    assert stats["papers_seen"] == 0
    assert records == []


def test_network_failure_on_page_2(fake_oparl, settings, source):
    fake_oparl.replace(responses.GET, PAGE_2_URL, status=503)
    records, stats = run(settings, source)

    assert stats["status"] == "failed"
    assert "gave up" in stats["error"]
    # the papers from page 1 are still there
    assert stats["pages"] == 1
    assert len(records) == 3


def test_page_that_is_gone_ends_the_list(fake_oparl, settings, source):
    fake_oparl.replace(responses.GET, PAGE_2_URL, status=404)
    records, stats = run(settings, source)
    assert stats["status"] == "ok"
    assert stats["pages"] == 1
    assert "404" in stats["warnings"][0]


def test_missing_paper_list_is_a_failure(fake_oparl, settings, source):
    fake_oparl.replace(responses.GET, PAGE_1_URL, status=404)
    records, stats = run(settings, source)
    assert stats["status"] == "failed"
    assert "paper list not found" in stats["error"]


def test_next_link_going_in_a_circle(fake_oparl, settings, source):
    page = load_fixture("papers_page2.json")
    page["links"]["next"] = PAGE_2_URL
    fake_oparl.replace(responses.GET, PAGE_2_URL, json=page)

    records, stats = run(settings, source)
    assert stats["status"] == "ok"
    assert stats["pages"] == 2
    assert "circle" in stats["warnings"][0]


def test_max_pages_stops_early(fake_oparl, settings, source):
    records, stats = run(settings, source, max_pages=1)
    assert stats["status"] == "partial"
    assert stats["pages"] == 1


def test_max_pages_on_the_last_page_is_still_ok(fake_oparl, settings, source):
    records, stats = run(settings, source, max_pages=2)
    assert stats["status"] == "ok"
    assert stats["pages"] == 2


def test_since_is_sent_as_modified_since(fake_oparl, settings, source):
    url = PAGE_1_URL + "&modified_since=2026-04-01"
    fake_oparl.add(responses.GET, url, json=load_fixture("papers_empty.json"))

    records, stats = run(settings, source, since="2026-04-01")

    assert stats["status"] == "ok"
    assert stats["since"] == "2026-04-01"
    assert "modified_since=2026-04-01" in fake_oparl.calls[-1].request.url


def test_newer_time():
    first = newer_time(None, "2026-05-04T10:00:00+02:00")
    assert newer_time(first, "2026-01-01T10:00:00+01:00") == first
    assert newer_time(first, "not a time") == first
    assert newer_time(first, "2026-06-01T10:00:00") == first
    assert newer_time(first, "2026-06-01T10:00:00+02:00").month == 6
