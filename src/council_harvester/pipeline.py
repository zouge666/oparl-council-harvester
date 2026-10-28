"""the main harvest loop: oparl pages -> filter -> normalize -> postgis.

for one source it does this:
  1. read the system and the bodies
  2. walk through all paper pages by following the "next" link
  3. skip broken, deleted and double papers
  4. keep only papers that match our keywords (and are not too old)
  5. normalize them and save them (inserted / updated / unchanged)
"""

from datetime import datetime

from council_harvester import db
from council_harvester.keywords import is_excluded, match_signal
from council_harvester.normalize import normalize_paper
from council_harvester.oparl_client import OParlError


def harvest_source(client, settings, source, conn=None, since=None, max_pages=None):
    """runs one harvest and gives back (records, stats).

    conn=None is a dry run, then nothing gets saved.
    since is sent as modified_since, so the server only gives papers that changed.
    max_pages stops early, handy for demos.
    """
    harvest = Harvest(client, settings, source, conn, since, max_pages)
    harvest.run()
    return harvest.records, harvest.stats


def new_stats(source_name):
    return {
        "source": source_name,
        "status": "running",
        "error": None,
        "since": None,
        "pages": 0,
        "papers_seen": 0,
        "malformed": 0,
        "deleted": 0,
        "duplicates": 0,
        "excluded": 0,
        "not_relevant": 0,
        "too_old": 0,
        "matched": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
        "geo": {"resolved": 0, "ambiguous": 0, "invalid": 0, "unresolved": 0, "no_location": 0},
        "newest_modified": None,
        "warnings": [],
        "problems": [],
    }


class Harvest:
    def __init__(self, client, settings, source, conn=None, since=None, max_pages=None):
        self.client = client
        self.settings = settings
        self.source = source
        self.conn = conn
        self.since = since
        self.max_pages = max_pages

        self.stats = new_stats(source["name"])
        self.stats["since"] = since
        self.records = []
        self.seen_ids = set()

    def run(self):
        # a network error does not crash the whole program. it goes into the stats
        # and the status is "failed". rows we saved before that are still fine
        try:
            system, bodies = self.client.get_bodies(self.source["system_url"])
            if len(bodies) == 0:
                self.stats["warnings"].append("the system has no bodies with papers")

            for body in bodies:
                stopped_early = self.harvest_body(body)
                if stopped_early:
                    self.stats["status"] = "partial"
                    return
        except OParlError as e:
            self.stats["status"] = "failed"
            self.stats["error"] = str(e)
            return

        self.stats["status"] = "ok"

    def harvest_body(self, body):
        """walks through the paper pages of one body. gives back True if max_pages stopped it"""
        url = body["paper"]
        params = {"limit": self.client.page_size}
        if self.since:
            params["modified_since"] = self.since

        visited = set()
        pages_here = 0
        while url:
            # a broken server could send us around in a circle
            if url in visited:
                self.stats["warnings"].append(f"page links go in a circle, stopped at {url}")
                break
            visited.add(url)

            items, next_url = self.client.get_page(url, params)
            # the next link already has limit and modified_since in it
            params = None

            if items is None:
                if pages_here == 0:
                    raise OParlError(f"paper list not found: {url}")
                # dresden gives 404 for a page that is not there anymore, we take it as the end
                self.stats["warnings"].append(f"page is gone (404), stopped at {url}")
                break

            pages_here += 1
            self.stats["pages"] += 1
            for paper in items:
                self.handle_paper(paper)

            url = next_url
            if not url:
                break
            if self.max_pages and self.stats["pages"] >= self.max_pages:
                return True
            self.client.wait_between_pages()
        return False

    def handle_paper(self, paper):
        stats = self.stats
        stats["papers_seen"] += 1

        # deleted papers are only a empty shell in oparl
        if isinstance(paper, dict) and paper.get("deleted") is True:
            stats["deleted"] += 1
            return

        problem = check_paper(paper)
        if problem:
            stats["malformed"] += 1
            paper_id = None
            if isinstance(paper, dict):
                paper_id = paper.get("id")
            stats["problems"].append({"id": paper_id, "problem": problem})
            return

        # the same paper can show up twice when the list changes while we read it
        if paper["id"] in self.seen_ids:
            stats["duplicates"] += 1
            return
        self.seen_ids.add(paper["id"])
        stats["newest_modified"] = newer_time(stats["newest_modified"], paper.get("modified"))

        title = paper["name"]
        if is_excluded(title, self.settings["filter"]["exclude_keywords"]):
            stats["excluded"] += 1
            return

        signal_type, matched = match_signal(title, self.settings["signals"])
        if signal_type is None:
            stats["not_relevant"] += 1
            return

        record = normalize_paper(paper, self.source, signal_type, matched)

        # old papers are most likely about things that are already built
        min_date = self.settings["filter"].get("min_paper_date")
        if min_date and record["published_date"] and record["published_date"] < min_date:
            stats["too_old"] += 1
            return

        stats["matched"] += 1
        stats["geo"][record["geo_status"]] += 1
        if self.conn is not None:
            result = db.save_record(self.conn, record)
            stats[result] += 1
        self.records.append(record)


def check_paper(paper):
    """gives back a problem text if the paper is not usable, else None"""
    if not isinstance(paper, dict):
        return "paper is not a json object"
    if not isinstance(paper.get("id"), str) or not paper["id"].strip():
        return "paper has no id"
    if not isinstance(paper.get("name"), str) or not paper["name"].strip():
        return "paper has no title (name)"
    return None


def newer_time(current, value):
    """gives back the newer one of two times. value is a iso text from the api"""
    if not isinstance(value, str):
        return current
    try:
        new_time = datetime.fromisoformat(value)
    except ValueError:
        return current
    # without a timezone we cant compare it safely
    if new_time.tzinfo is None:
        return current
    if current is None or new_time > current:
        return new_time
    return current
