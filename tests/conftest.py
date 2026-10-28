import os
from pathlib import Path

import pytest

from council_harvester import db

SQL_DIR = str(Path(__file__).parent.parent / "sql")


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
def conn():
    """a connection to a empty test database. the tests are skipped without one"""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("set TEST_DATABASE_URL to run the database tests")

    connection = db.connect(url)
    db.init_db(connection, SQL_DIR)
    connection.execute("TRUNCATE iris_staging.signal_ingest")
    yield connection
    connection.close()
