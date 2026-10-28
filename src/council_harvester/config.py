"""loads the settings for the harvester.

normal settings live in config/harvester.toml.
secrets (like the database password) only come from env vars.
"""

import os
import tomllib
from datetime import date

DEFAULT_CONFIG_PATH = "config/harvester.toml"

HTTP_DEFAULTS = {
    "timeout_seconds": 60,
    "max_retries": 3,
    "retry_wait_seconds": 2,
    "page_delay_seconds": 1,
    "page_size": 100,
    "user_agent": "oparl-council-harvester",
}


class ConfigError(Exception):
    pass


def load_settings(path=None):
    """reads the toml file and gives back the settings as one dict"""
    if path is None:
        path = os.environ.get("HARVESTER_CONFIG", DEFAULT_CONFIG_PATH)

    if not os.path.exists(path):
        raise ConfigError(f"config file not found: {path}")

    with open(path, "rb") as f:
        try:
            settings = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"config file is broken: {e}")

    # fill in the http settings that are not in the file
    http = settings.get("http", {})
    for key, value in HTTP_DEFAULTS.items():
        if key not in http:
            http[key] = value
    settings["http"] = http

    check_sources(settings.get("sources"))
    check_signals(settings.get("signals"))

    if "filter" not in settings:
        settings["filter"] = {}
    if "exclude_keywords" not in settings["filter"]:
        settings["filter"]["exclude_keywords"] = []
    check_date(settings["filter"].get("min_paper_date"))

    # the db url has the password in it, so it only comes from the env (or .env file)
    settings["database_url"] = os.environ.get("DATABASE_URL", "")
    return settings


def check_sources(sources):
    if not sources:
        raise ConfigError("there are no sources in the config")

    names = []
    for source in sources:
        for key in ["name", "municipality", "system_url"]:
            if not source.get(key):
                raise ConfigError(f"a source is missing '{key}'")
        if source["name"] in names:
            raise ConfigError(f"source name is used twice: {source['name']}")
        names.append(source["name"])

        # sources are on unless the config says no
        if "enabled" not in source:
            source["enabled"] = True


def check_signals(signals):
    if not signals:
        raise ConfigError("there are no [signals] keywords in the config")

    for name, keywords in signals.items():
        if not isinstance(keywords, list) or len(keywords) == 0:
            raise ConfigError(f"signal '{name}' needs a list of keywords")
        for keyword in keywords:
            # very short keywords match way to much ("kv" is in "musikverein")
            if not isinstance(keyword, str) or len(keyword.strip()) < 4:
                raise ConfigError(f"keyword '{keyword}' in '{name}' is too short")


def check_date(value):
    if value is None:
        return
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ConfigError(f"min_paper_date must look like 2022-01-31, not '{value}'")


def get_source(settings, name):
    for source in settings["sources"]:
        if source["name"] == name:
            return source
    raise ConfigError(f"unknown source: {name}")
