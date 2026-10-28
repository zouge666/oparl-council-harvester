import os

import pytest
import responses

from council_harvester import db
from tests.helpers import (
    BODIES_URL,
    PAGE_1_URL,
    PAGE_2_URL,
    SQL_DIR,
    SYSTEM_URL,
    load_fixture,
)


@pytest.fixture
def http_settings():
    # no waiting in tests, so they stay fast
    return {
        "timeout_seconds": 5,
        "max_retries": 3,
        "retry_wait_seconds": 0,
        "page_delay_seconds": 0,
        "page_size": 10,
        "user_agent": "test-agent",
    }


@pytest.fixture
def settings(http_settings):
    return {
        "http": http_settings,
        "signals": {
            "mega_substation": ["umspannwerk", "110 kv"],
            "semiconductor_dc_park": ["halbleiter", "rechenzentrum", "tsmc"],
        },
        "filter": {
            "exclude_keywords": ["kleinprojektförderung"],
            "min_paper_date": "2022-01-01",
        },
    }


@pytest.fixture
def source():
    return {
        "name": "testcity",
        "municipality": "Teststadt",
        "region": "Sachsen",
        "system_url": SYSTEM_URL,
        "enabled": True,
    }


@pytest.fixture
def fake_oparl():
    """a fake oparl server that answers with the files in tests/fixtures"""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        mock.add(responses.GET, SYSTEM_URL, json=load_fixture("system.json"))
        mock.add(responses.GET, BODIES_URL, json=load_fixture("bodies.json"))
        mock.add(responses.GET, PAGE_1_URL, json=load_fixture("papers_page1.json"))
        mock.add(responses.GET, PAGE_2_URL, json=load_fixture("papers_page2.json"))
        yield mock


@pytest.fixture
def conn():
    """a connection to a empty test database. the tests are skipped without one"""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("set TEST_DATABASE_URL to run the database tests")

    connection = db.connect(url)
    db.init_db(connection, SQL_DIR)
    connection.execute("TRUNCATE iris_staging.signal_ingest, iris_staging.harvest_state")
    yield connection
    connection.close()
