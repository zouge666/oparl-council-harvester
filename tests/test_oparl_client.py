import pytest
import requests
import responses

from council_harvester.oparl_client import OParlClient, OParlError

URL = "https://oparl.example.test/papers"


@responses.activate
def test_get_json_works(http_settings):
    responses.add(responses.GET, URL, json={"data": []})
    client = OParlClient(http_settings)
    assert client.get_json(URL) == {"data": []}
    assert responses.calls[0].request.headers["User-Agent"] == "test-agent"


@responses.activate
def test_busy_server_gets_another_try(http_settings):
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, json={"data": []})
    client = OParlClient(http_settings)
    assert client.get_json(URL) == {"data": []}
    assert client.request_count == 2


@responses.activate
def test_network_error_gets_another_try(http_settings):
    responses.add(responses.GET, URL, body=requests.ConnectionError("no wifi"))
    responses.add(responses.GET, URL, json={"data": []})
    client = OParlClient(http_settings)
    assert client.get_json(URL) == {"data": []}


@responses.activate
def test_gives_up_after_max_retries(http_settings):
    for i in range(3):
        responses.add(responses.GET, URL, status=500)
    client = OParlClient(http_settings)
    with pytest.raises(OParlError, match="gave up"):
        client.get_json(URL)
    assert len(responses.calls) == 3


@responses.activate
def test_client_errors_are_not_retried(http_settings):
    responses.add(responses.GET, URL, status=400)
    client = OParlClient(http_settings)
    with pytest.raises(OParlError, match="http 400"):
        client.get_json(URL)
    assert len(responses.calls) == 1


@responses.activate
def test_404_gives_none(http_settings):
    responses.add(responses.GET, URL, status=404)
    client = OParlClient(http_settings)
    assert client.get_json(URL) is None


@responses.activate
def test_html_instead_of_json_is_an_error(http_settings):
    responses.add(responses.GET, URL, body="<html>oops</html>", content_type="text/html")
    client = OParlClient(http_settings)
    with pytest.raises(OParlError, match="not json"):
        client.get_json(URL)


@responses.activate
def test_get_page_gives_items_and_next_link(http_settings):
    page = {"data": [{"id": "a"}, {"id": "b"}], "links": {"next": URL + "?page=2"}}
    responses.add(responses.GET, URL, json=page)
    client = OParlClient(http_settings)
    items, next_url = client.get_page(URL)
    assert len(items) == 2
    assert next_url == URL + "?page=2"


@responses.activate
def test_last_page_has_no_next_link(http_settings):
    responses.add(responses.GET, URL, json={"data": [{"id": "a"}], "links": {}})
    client = OParlClient(http_settings)
    items, next_url = client.get_page(URL)
    assert len(items) == 1
    assert next_url is None


@responses.activate
def test_page_without_data_list_is_an_error(http_settings):
    responses.add(responses.GET, URL, json={"data": "nope"})
    client = OParlClient(http_settings)
    with pytest.raises(OParlError, match="no data list"):
        client.get_page(URL)


@responses.activate
def test_missing_page_gives_none(http_settings):
    responses.add(responses.GET, URL, status=404)
    client = OParlClient(http_settings)
    items, next_url = client.get_page(URL)
    assert items is None
    assert next_url is None
