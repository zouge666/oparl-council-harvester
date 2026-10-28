from pathlib import Path

import pytest

from council_harvester.config import ConfigError, get_source, load_settings

REAL_CONFIG = Path(__file__).parent.parent / "config" / "harvester.toml"

GOOD_CONFIG = """
[http]
page_size = 10

[signals]
mega_substation = ["umspannwerk"]

[[sources]]
name = "dresden"
municipality = "Dresden"
system_url = "https://oparl.example.test/system"
"""


def write_config(tmp_path, text):
    path = tmp_path / "harvester.toml"
    path.write_text(text)
    return str(path)


def test_shipped_config_is_valid():
    settings = load_settings(str(REAL_CONFIG))
    dresden = get_source(settings, "dresden")
    assert dresden["system_url"].startswith("https://")
    assert dresden["enabled"] is True


def test_missing_http_values_get_defaults(tmp_path):
    settings = load_settings(write_config(tmp_path, GOOD_CONFIG))
    assert settings["http"]["page_size"] == 10
    assert settings["http"]["max_retries"] == 3


def test_config_path_can_come_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HARVESTER_CONFIG", write_config(tmp_path, GOOD_CONFIG))
    settings = load_settings()
    assert settings["sources"][0]["name"] == "dresden"


def test_missing_file_gives_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(str(tmp_path / "nope.toml"))


def test_broken_toml_gives_config_error(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(write_config(tmp_path, "[[sources]\nname = "))


def test_source_without_url_is_rejected(tmp_path):
    text = """
[[sources]]
name = "dresden"
municipality = "Dresden"
"""
    with pytest.raises(ConfigError):
        load_settings(write_config(tmp_path, text))


def test_same_source_name_twice_is_rejected(tmp_path):
    text = GOOD_CONFIG + """
[[sources]]
name = "dresden"
municipality = "Dresden"
system_url = "https://other.example.test/system"
"""
    with pytest.raises(ConfigError):
        load_settings(write_config(tmp_path, text))


def test_config_without_signals_is_rejected(tmp_path):
    text = GOOD_CONFIG.replace('mega_substation = ["umspannwerk"]', "")
    with pytest.raises(ConfigError, match="signals"):
        load_settings(write_config(tmp_path, text))


def test_too_short_keyword_is_rejected(tmp_path):
    text = GOOD_CONFIG.replace('["umspannwerk"]', '["umspannwerk", "kv"]')
    with pytest.raises(ConfigError, match="too short"):
        load_settings(write_config(tmp_path, text))


def test_exclude_list_defaults_to_empty(tmp_path):
    settings = load_settings(write_config(tmp_path, GOOD_CONFIG))
    assert settings["filter"]["exclude_keywords"] == []


def test_bad_min_paper_date_is_rejected(tmp_path):
    text = GOOD_CONFIG + """
[filter]
min_paper_date = "01.01.2022"
"""
    with pytest.raises(ConfigError, match="min_paper_date"):
        load_settings(write_config(tmp_path, text))


def test_unknown_source_name(tmp_path):
    settings = load_settings(write_config(tmp_path, GOOD_CONFIG))
    with pytest.raises(ConfigError):
        get_source(settings, "chemnitz")
