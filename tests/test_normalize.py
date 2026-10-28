from datetime import date

from council_harvester.normalize import make_hash, normalize_paper

TODAY = date(2026, 10, 27)

SOURCE = {
    "name": "dresden",
    "municipality": "Dresden",
    "region": "Sachsen",
    "web_urls": {
        "vo": "https://ratsinfo.dresden.de/vo0050.asp?__kvonr={number}",
        "ag": "https://ratsinfo.dresden.de/ag0050.asp?__kagnr={number}",
    },
}


def make_paper(**changes):
    # looks like a real paper from the dresden api
    paper = {
        "id": "http://oparl.dresden.de/bodies/0001/papers/vo/30750",
        "type": "https://schema.oparl.org/1.1/Paper",
        "body": "http://oparl.dresden.de/bodies/0001",
        "name": "Entwicklung des  Halbleiterstandortes in der Region Dresden",
        "reference": "V0750/26",
        "date": "2026-03-17",
        "paperType": "Vorlage Stadtrat",
        "created": "2026-03-10T09:00:00+01:00",
        "modified": "2026-03-17T10:00:00+01:00",
    }
    paper.update(changes)
    return paper


def normalize(paper):
    return normalize_paper(paper, SOURCE, "semiconductor_dc_park", ["halbleiter"], today=TODAY)


def test_fields_are_mapped():
    record = normalize(make_paper())
    assert record["source_system"] == "oparl"
    assert record["source_name"] == "dresden"
    assert record["source_record_id"] == "http://oparl.dresden.de/bodies/0001/papers/vo/30750"
    assert record["signal_type"] == "semiconductor_dc_park"
    assert record["title"] == "Entwicklung des Halbleiterstandortes in der Region Dresden"
    assert record["reference"] == "V0750/26"
    assert record["paper_type"] == "Vorlage Stadtrat"
    assert record["published_date"] == "2026-03-17"
    assert record["source_url"] == "https://ratsinfo.dresden.de/vo0050.asp?__kvonr=30750"
    assert record["municipality"] == "Dresden"
    assert record["region"] == "Sachsen"
    assert record["geo_status"] == "no_location"
    assert record["matched_keywords"] == ["halbleiter"]
    assert record["quality_flags"] == []
    assert record["source_modified_at"] == "2026-03-17T10:00:00+01:00"
    assert len(record["content_hash"]) == 64


def test_web_field_wins_over_the_template():
    record = normalize(make_paper(web="https://ratsinfo.example.test/paper/1"))
    assert record["source_url"] == "https://ratsinfo.example.test/paper/1"


def test_web_url_depends_on_the_kind_of_paper():
    record = normalize(make_paper(id="http://oparl.dresden.de/bodies/0001/papers/ag/12193"))
    assert record["source_url"] == "https://ratsinfo.dresden.de/ag0050.asp?__kagnr=12193"


def test_unknown_kind_of_paper_gets_the_api_url():
    paper_id = "http://oparl.dresden.de/bodies/0001/papers/xy/5"
    record = normalize(make_paper(id=paper_id))
    assert record["source_url"] == paper_id


def test_api_url_when_there_is_no_web_link():
    source = {"name": "x", "municipality": "X"}
    record = normalize_paper(make_paper(), source, "mega_substation", [], today=TODAY)
    assert record["source_url"] == "http://oparl.dresden.de/bodies/0001/papers/vo/30750"


def test_missing_date_is_flagged():
    record = normalize(make_paper(date=None))
    assert record["published_date"] is None
    assert "missing_date" in record["quality_flags"]


def test_bad_date_is_flagged():
    record = normalize(make_paper(date="17.03.2026"))
    assert record["published_date"] is None
    assert "bad_date: 17.03.2026" in record["quality_flags"]


def test_future_date_is_kept_but_flagged():
    record = normalize(make_paper(date="2027-01-05"))
    assert record["published_date"] == "2027-01-05"
    assert "future_date: 2027-01-05" in record["quality_flags"]


def test_bad_modified_time_is_flagged():
    record = normalize(make_paper(modified="yesterday"))
    assert record["source_modified_at"] is None
    assert "bad_modified: yesterday" in record["quality_flags"]


def test_location_with_point():
    location = {
        "description": "Neumarkt",
        "geojson": {"type": "Point", "coordinates": [13.7416, 51.0519]},
    }
    record = normalize(make_paper(location=[location]))
    assert record["geo_status"] == "resolved"
    assert record["lon"] == 13.7416
    assert record["lat"] == 51.0519
    assert record["location_text"] == "Neumarkt"


def test_location_problems_become_flags():
    location = {"geojson": {"type": "Point", "coordinates": [51.0519, 13.7416]}}
    record = normalize(make_paper(location=[location]))
    assert record["geo_status"] == "invalid"
    assert record["quality_flags"][0].startswith("location: lon and lat look swapped")


def test_hash_stays_the_same_for_the_same_paper():
    assert normalize(make_paper())["content_hash"] == normalize(make_paper())["content_hash"]


def test_hash_changes_when_the_paper_changes():
    old = normalize(make_paper())
    new = normalize(make_paper(name="Entwicklung des Halbleiterstandortes - 2. Lesung"))
    assert old["content_hash"] != new["content_hash"]


def test_make_hash_ignores_the_old_hash():
    record = {"title": "a", "content_hash": "old"}
    assert make_hash(record) == make_hash({"title": "a"})
