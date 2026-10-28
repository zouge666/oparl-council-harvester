# Mapping

How one OParl `Paper` becomes one row in `iris_staging.signal_ingest`.
The code for this is in `src/council_harvester/normalize.py`.

| column | comes from | note |
| --- | --- | --- |
| source_system | always `oparl` | |
| source_name | config `name` | like `dresden` |
| source_record_id | `Paper.id` | the full api url. together with source_system it is unique |
| signal_type | our keyword check | `mega_substation` or `semiconductor_dc_park` |
| title | `Paper.name` | double spaces removed |
| reference | `Paper.reference` | like `V0750/26` |
| paper_type | `Paper.paperType` | like `Vorlage Stadtrat` |
| published_date | `Paper.date` | must be `YYYY-MM-DD`, if not it stays empty and gets a flag |
| source_url | `Paper.web`, else the config template for this kind of paper, else `Paper.id` | link for humans |
| municipality, region | config | the dresden body is just called `Instance 0001` |
| location_text | `Location` description and address | |
| geom | `Location.geojson` point | lon/lat (EPSG:4326) in, EPSG:25832 point out |
| geo_status | our location check | see below |
| matched_keywords | our keyword check | all keywords that matched |
| quality_flags | our checks | like `missing_date`, `future_date: ...`, `location: ...` |
| source_modified_at | `Paper.modified` | we use it for incremental runs |
| content_hash | sha256 of the record | only changes when the paper changes |
| raw_record | the whole paper json | so we can always go back to the source |

## geo_status

- `resolved` - exactly one good point
- `ambiguous` - more than one different point. we dont guess, geom stays empty
- `invalid` - a point was there but broken, swapped or outside saxony. geom stays empty
- `unresolved` - there is a location but no point (only an address, a polygon or a link)
- `no_location` - the paper has no location at all

## Assumptions

- We only look at the title of a paper, not at the pdf files.
- If a paper matches both signal types, `mega_substation` wins, because it comes first
  in the config. `matched_keywords` still shows all words.
- `Paper.date` is the publication date. We check the format and we flag dates in the future,
  we dont make up a date when it is missing.
- GeoJSON in OParl is lon/lat in WGS84. PostGIS turns it into EPSG:25832
  (`ST_Transform`). Saxony itself mostly uses EPSG:25833 (UTM zone 33), but the task asks
  for 25832, so we do that. The raw lon/lat stays in `raw_record` if someone needs 25833 later.
- Dresden papers have no locations right now, so they all get `no_location`.
  The municipality and region columns still tell you where the paper is from.
