import responses

from council_harvester.cli import main

SYSTEM_URL = "https://oparl.example.test/system"
BODIES_URL = "https://oparl.example.test/bodies"
PAPERS_URL = "https://oparl.example.test/bodies/1/papers"
BROKEN_URL = "https://broken.example.test/oparl/system"

CONFIG = f"""
[http]
max_retries = 1
retry_wait_seconds = 0
page_delay_seconds = 0

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
