import pytest


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
