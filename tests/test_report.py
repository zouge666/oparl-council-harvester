import responses

from council_harvester.oparl_client import OParlClient
from council_harvester.pipeline import harvest_source
from council_harvester.report import build_report, short_list, write_report
from tests.helpers import PAGE_2_URL


def run(settings, source):
    client = OParlClient(settings["http"])
    return harvest_source(client, settings, source)


def test_report_shows_counts_and_problems(fake_oparl, settings, source):
    records, stats = run(settings, source)
    text = build_report(stats, records)

    assert "# Harvest report: testcity" in text
    assert "- status: **ok**" in text
    assert "| papers seen | 12 |" in text
    assert "| matched and kept | 5 |" in text
    assert "| invalid | 1 |" in text
    # broken papers are listed
    assert "/vo/1004: paper has no title (name)" in text
    assert "(no id): paper is not a json object" in text
    # flags and locations that need a human
    assert "bad_date: 10.02.2026" in text
    assert "lon and lat look swapped" in text
    assert "`V9005/26` unresolved: Flughafenstraße 1, 01109, Dresden" in text


def test_report_of_a_failed_run_shows_the_error(fake_oparl, settings, source):
    fake_oparl.replace(responses.GET, PAGE_2_URL, status=503)
    records, stats = run(settings, source)
    text = build_report(stats, records)

    assert "- status: **failed**" in text
    assert "- error: gave up on" in text


def test_long_lists_are_cut():
    lines = []
    for i in range(250):
        lines.append(f"- line {i}")
    short = short_list(lines)
    assert len(short) == 201
    assert short[-1] == "- ... and 50 more"
    assert short_list([]) == ["none"]


def test_write_report_makes_a_file(fake_oparl, settings, source, tmp_path):
    records, stats = run(settings, source)
    path = write_report(stats, records, str(tmp_path / "reports"))
    with open(path, encoding="utf-8") as f:
        assert f.read().startswith("# Harvest report: testcity")
