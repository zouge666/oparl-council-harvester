from council_harvester.geo import read_point, resolve_location

# frauenkirche dresden, good for tests
DRESDEN = [13.7416, 51.0519]


def point_location(coordinates, **extra):
    location = {"type": "https://schema.oparl.org/1.1/Location"}
    location["geojson"] = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": coordinates},
    }
    location.update(extra)
    return location


def test_one_good_point_is_resolved():
    result = resolve_location([point_location(DRESDEN, description="Neumarkt")])
    assert result["geo_status"] == "resolved"
    assert result["lon"] == 13.7416
    assert result["lat"] == 51.0519
    assert result["location_text"] == "Neumarkt"
    assert result["problems"] == []


def test_plain_geometry_without_feature_works_too():
    location = {"geojson": {"type": "Point", "coordinates": DRESDEN}}
    assert resolve_location([location])["geo_status"] == "resolved"


def test_no_locations():
    assert resolve_location(None)["geo_status"] == "no_location"
    assert resolve_location([])["geo_status"] == "no_location"


def test_address_without_point_is_unresolved():
    location = {"streetAddress": "Hauptstraße 1", "postalCode": "01067", "locality": "Dresden"}
    result = resolve_location([location])
    assert result["geo_status"] == "unresolved"
    assert result["location_text"] == "Hauptstraße 1, 01067, Dresden"
    assert result["lon"] is None


def test_point_outside_saxony_is_invalid():
    # this is in berlin
    result = resolve_location([point_location([13.40, 52.52])])
    assert result["geo_status"] == "invalid"
    assert "outside of saxony" in result["problems"][0]
    assert result["lon"] is None


def test_swapped_lon_lat_is_invalid():
    result = resolve_location([point_location([51.0519, 13.7416])])
    assert result["geo_status"] == "invalid"
    assert "swapped" in result["problems"][0]


def test_two_different_points_are_ambiguous():
    locations = [point_location(DRESDEN), point_location([13.80, 51.10])]
    result = resolve_location(locations)
    assert result["geo_status"] == "ambiguous"
    assert result["lon"] is None


def test_same_point_twice_is_still_resolved():
    result = resolve_location([point_location(DRESDEN), point_location(DRESDEN)])
    assert result["geo_status"] == "resolved"


def test_polygon_is_not_used():
    location = {"geojson": {"type": "Polygon", "coordinates": [[[13.7, 51.0], [13.8, 51.0]]]}}
    result = resolve_location([location])
    assert result["geo_status"] == "unresolved"
    assert "Polygon" in result["problems"][0]


def test_location_given_as_link_only():
    result = resolve_location(["https://oparl.example.test/locations/1"])
    assert result["geo_status"] == "unresolved"
    assert "not an object" in result["problems"][0]


def test_bad_coordinates():
    assert read_point(None)[2] == "point has no coordinates"
    assert read_point([13.7])[2] == "point has no coordinates"
    assert read_point(["13.7", "51.0"])[2] == "coordinates are not numbers"
    assert read_point([True, 51.0])[2] == "coordinates are not numbers"
    assert "out of range" in read_point([200.0, 51.0])[2]
    assert "outside of saxony" in read_point([float("nan"), 51.0])[2]
