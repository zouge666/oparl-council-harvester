"""reads the locations of a paper and decides if we can trust the point.

oparl locations have a "geojson" field with wgs84 coordinates (lon, lat).
we only check the point here. postgis turns it into EPSG:25832 when we save it.

geo_status can be:
  resolved     - exactly one good point
  ambiguous    - more than one different point, we dont pick one
  invalid      - there was a point but it is broken or not in saxony
  unresolved   - there is a location but no point (only an address for example)
  no_location  - the paper has no location at all
"""

# rough box around saxony. a point outside of it is most likely wrong
SAXONY_MIN_LON = 11.8
SAXONY_MAX_LON = 15.1
SAXONY_MIN_LAT = 50.1
SAXONY_MAX_LAT = 51.8


def resolve_location(locations):
    """looks at the location list of a paper and gives back a dict with
    geo_status, lon, lat, location_text and problems"""
    result = {
        "geo_status": "no_location",
        "lon": None,
        "lat": None,
        "location_text": None,
        "problems": [],
    }
    if not locations:
        return result
    if not isinstance(locations, list):
        result["geo_status"] = "unresolved"
        result["problems"].append("location field is not a list")
        return result

    points = []
    texts = []
    bad_points = 0
    for location in locations:
        if not isinstance(location, dict):
            result["problems"].append("location is not an object (maybe only a link)")
            continue

        text = location_to_text(location)
        if text:
            texts.append(text)

        geometry = get_geometry(location.get("geojson"))
        if geometry is None:
            continue
        if geometry.get("type") != "Point":
            result["problems"].append(f"geometry type {geometry.get('type')} is not supported")
            continue

        lon, lat, problem = read_point(geometry.get("coordinates"))
        if problem:
            result["problems"].append(problem)
            bad_points += 1
            continue
        if (lon, lat) not in points:
            points.append((lon, lat))

    if texts:
        result["location_text"] = "; ".join(texts)

    if len(points) == 1:
        result["geo_status"] = "resolved"
        result["lon"] = points[0][0]
        result["lat"] = points[0][1]
    elif len(points) > 1:
        result["geo_status"] = "ambiguous"
        result["problems"].append(f"{len(points)} different points, did not pick one")
    elif bad_points > 0:
        result["geo_status"] = "invalid"
    else:
        result["geo_status"] = "unresolved"
    return result


def get_geometry(geojson):
    """geojson can be a Feature or just a geometry, we want the geometry"""
    if not isinstance(geojson, dict):
        return None
    if geojson.get("type") == "Feature":
        geometry = geojson.get("geometry")
        if isinstance(geometry, dict):
            return geometry
        return None
    return geojson


def read_point(coordinates):
    """checks a geojson [lon, lat] pair. gives back (lon, lat, problem)"""
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None, None, "point has no coordinates"

    lon = coordinates[0]
    lat = coordinates[1]
    if not is_number(lon) or not is_number(lat):
        return None, None, "coordinates are not numbers"
    if lon < -180 or lon > 180 or lat < -90 or lat > 90:
        return None, None, f"coordinates out of range ({lon}, {lat})"
    if not in_saxony(lon, lat):
        if in_saxony(lat, lon):
            return None, None, f"lon and lat look swapped ({lon}, {lat})"
        return None, None, f"point is outside of saxony ({lon}, {lat})"
    return lon, lat, None


def is_number(value):
    # True and False are ints in python, we dont want them
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def in_saxony(lon, lat):
    # also false for nan, because every compare with nan is false
    return SAXONY_MIN_LON <= lon <= SAXONY_MAX_LON and SAXONY_MIN_LAT <= lat <= SAXONY_MAX_LAT


def location_to_text(location):
    parts = []
    for key in ["description", "streetAddress", "postalCode", "subLocality", "locality"]:
        value = location.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
    return ", ".join(parts)
