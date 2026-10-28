-- checks for the staging data. run them after a harvest:
--   docker compose exec db psql -U iris -d iris -f /sql/validation_queries.sql
-- the checks that say "expect 0 rows" should give back nothing.

\echo '1. rows per source and signal type'
SELECT source_name, signal_type, count(*) AS rows
FROM iris_staging.signal_ingest
GROUP BY source_name, signal_type
ORDER BY source_name, signal_type;

\echo '2. duplicates (expect 0 rows)'
SELECT source_system, source_record_id, count(*)
FROM iris_staging.signal_ingest
GROUP BY source_system, source_record_id
HAVING count(*) > 1;

\echo '3. geo status counts'
SELECT geo_status, count(*) AS rows, count(geom) AS with_point
FROM iris_staging.signal_ingest
GROUP BY geo_status
ORDER BY geo_status;

\echo '4. resolved rows without a good EPSG:25832 point (expect 0 rows)'
SELECT id, source_record_id
FROM iris_staging.signal_ingest
WHERE geo_status = 'resolved'
  AND (geom IS NULL OR ST_SRID(geom) <> 25832 OR NOT ST_IsValid(geom));

\echo '5. points outside of saxony (expect 0 rows)'
SELECT id, source_record_id, ST_AsText(ST_Transform(geom, 4326)) AS lon_lat
FROM iris_staging.signal_ingest
WHERE geom IS NOT NULL
  AND NOT ST_Within(ST_Transform(geom, 4326), ST_MakeEnvelope(11.8, 50.1, 15.1, 51.8, 4326));

\echo '6. rows that can not be traced back to the source (expect 0 rows)'
SELECT id, source_record_id
FROM iris_staging.signal_ingest
WHERE raw_record ->> 'id' IS DISTINCT FROM source_record_id
   OR source_url IS NULL
   OR source_url NOT LIKE 'http%';

\echo '7. rows without a publication date'
SELECT id, reference, title
FROM iris_staging.signal_ingest
WHERE published_date IS NULL;

\echo '8. rows with a date in the future'
SELECT id, reference, published_date
FROM iris_staging.signal_ingest
WHERE published_date > current_date;

\echo '9. rows with quality flags'
SELECT reference, geo_status, quality_flags
FROM iris_staging.signal_ingest
WHERE cardinality(quality_flags) > 0
ORDER BY published_date DESC NULLS LAST;

\echo '10. newest rows'
SELECT published_date, reference, signal_type, left(title, 80) AS title, source_url
FROM iris_staging.signal_ingest
ORDER BY published_date DESC NULLS LAST
LIMIT 20;

\echo '11. last full run per source (incremental watermark)'
SELECT source_name, last_modified_seen, last_success_at
FROM iris_staging.harvest_state
ORDER BY source_name;
