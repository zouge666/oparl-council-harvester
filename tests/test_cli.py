import json

import responses

from council_harvester.cli import main
from tests.helpers import PAGE_2_URL

SYSTEM_URL = "https://oparl.example.test/system"
BODIES_URL = "https://oparl.example.test/bodies"
PAPERS_URL = "https://oparl.example.test/bodies/1/papers"
BROKEN_URL = "https://broken.example.test/oparl/system"

CONFIG = f"""
[http]
max_retries = 1
retry_wait_seconds = 0
page_delay_seconds = 0

[signals]
mega_substation = ["umspannwerk"]

[[sources]]
name = "testcity"
municipality = "Teststadt"
system_url = "{SYSTEM_URL}"

[[sources]]
name = "brokencity"
municipality = "Kaputtstadt"
system_url = "{BROKEN_URL}"
enabled = false
"""


def write_config(tmp_path, text=CONFIG):
    path = tmp_path / "harvester.toml"
    path.write_text(text)
    return str(path)


def add_working_source():
    system = {
        "name": "Test System",
        "oparlVersion": "https://schema.oparl.org/1.1/",
        "body": BODIES_URL,
    }
    body = {"id": "https://oparl.example.test/bodies/1", "name": "Teststadt", "paper": PAPERS_URL}
    paper = {"id": PAPERS_URL + "/1", "name": "Erster Antrag", "date": "2026-01-02"}
    responses.add(responses.GET, SYSTEM_URL, json=system)
    responses.add(responses.GET, BODIES_URL, json={"data": [body], "links": {}})
    responses.add(responses.GET, PAPERS_URL, json={"data": [paper], "links": {}})


@responses.activate
def test_check_prints_what_it_finds(tmp_path, capsys):
    add_working_source()
    responses.add(responses.GET, BROKEN_URL, status=500)

    exit_code = main(["--config", write_config(tmp_path), "check"])

    out = capsys.readouterr().out
    assert "Test System" in out
    assert "first paper: 2026-01-02 Erster Antrag" in out
    assert "brokencity (disabled in config)" in out
    assert "FAILED" in out
    # the broken source is disabled so the check is still ok
    assert exit_code == 0


@responses.activate
def test_check_fails_when_a_enabled_source_is_broken(tmp_path):
    responses.add(responses.GET, BROKEN_URL, status=500)
    text = CONFIG.replace("enabled = false", "enabled = true")

    exit_code = main(["--config", write_config(tmp_path, text), "check", "brokencity"])

    assert exit_code == 1


def test_unknown_source_is_a_config_problem(tmp_path, capsys):
    exit_code = main(["--config", write_config(tmp_path), "check", "chemnitz"])
    assert exit_code == 2
    assert "unknown source" in capsys.readouterr().err


HARVEST_CONFIG = f"""
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
region = "Sachsen"
system_url = "{SYSTEM_URL}"

[[sources]]
name = "brokencity"
municipality = "Kaputtstadt"
system_url = "{BROKEN_URL}"
enabled = false
"""


def test_harvest_dry_run_writes_jsonl(tmp_path, capsys, fake_oparl):
    out_file = str(tmp_path / "output" / "testcity.jsonl")
    config = write_config(tmp_path, HARVEST_CONFIG)

    exit_code = main(["--config", config, "harvest", "testcity", "--no-db", "--jsonl", out_file])

    assert exit_code == 0
    with open(out_file, encoding="utf-8") as f:
        lines = f.read().splitlines()
    assert len(lines) == 5
    first = json.loads(lines[0])
    assert first["source_name"] == "testcity"
    assert "raw_record" not in first
    assert "harvest testcity: ok" in capsys.readouterr().out


def test_harvest_failure_gives_exit_code_1(tmp_path, capsys, fake_oparl):
    fake_oparl.replace(responses.GET, PAGE_2_URL, status=503)
    config = write_config(tmp_path, HARVEST_CONFIG)

    exit_code = main(["--config", config, "harvest", "testcity", "--no-db"])

    assert exit_code == 1
    assert "harvest testcity: failed" in capsys.readouterr().out


def test_disabled_source_is_not_harvested(tmp_path, capsys):
    config = write_config(tmp_path, HARVEST_CONFIG)
    exit_code = main(["--config", config, "harvest", "brokencity", "--no-db"])
    assert exit_code == 2
    assert "disabled" in capsys.readouterr().err
