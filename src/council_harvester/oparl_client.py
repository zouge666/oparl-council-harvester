"""a small http client for oparl apis.

oparl is a standard api for german council systems. the main objects are
system -> body (the city) -> paper (a council document).
lists in oparl come in pages, every page has a "next" link to the next one.
"""

import time

import requests

# these status codes are worth another try, the server is maybe just busy
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]


class OParlError(Exception):
    pass


class OParlClient:
    def __init__(self, http_settings, session=None):
        self.timeout = http_settings["timeout_seconds"]
        self.max_retries = http_settings["max_retries"]
        self.retry_wait = http_settings["retry_wait_seconds"]
        self.page_delay = http_settings["page_delay_seconds"]
        self.page_size = http_settings["page_size"]

        if session is None:
            session = requests.Session()
        self.session = session
        self.session.headers["User-Agent"] = http_settings["user_agent"]
        self.session.headers["Accept"] = "application/json"

        # we count the requests so the report can show them
        self.request_count = 0

    def get_json(self, url, params=None):
        """gets a url and gives back the json. gives back None for a 404.

        network errors and busy servers get a few more tries,
        and we wait a bit longer after each try.
        """
        problem = ""
        for attempt in range(1, self.max_retries + 1):
            self.request_count += 1
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                response = None
                problem = f"network error: {e}"

            if response is not None:
                if response.status_code == 200:
                    return read_json(response, url)
                if response.status_code == 404:
                    return None
                if response.status_code not in RETRY_STATUS_CODES:
                    raise OParlError(f"http {response.status_code} for {url}")
                problem = f"http {response.status_code}"

            if attempt < self.max_retries:
                time.sleep(self.retry_wait * attempt)

        raise OParlError(f"gave up on {url} after {self.max_retries} tries ({problem})")

    def get_page(self, url, params=None):
        """reads one page of a oparl list and gives back (items, next_url).

        items is None when the page is not there (404).
        next_url is None on the last page.
        """
        data = self.get_json(url, params)
        if data is None:
            return None, None
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise OParlError(f"page has no data list: {url}")

        next_url = None
        links = data.get("links")
        if isinstance(links, dict):
            next_url = links.get("next")
        return data["data"], next_url

    def wait_between_pages(self):
        if self.page_delay > 0:
            time.sleep(self.page_delay)


def read_json(response, url):
    try:
        return response.json()
    except ValueError:
        raise OParlError(f"answer is not json: {url}")
