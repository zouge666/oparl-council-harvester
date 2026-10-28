-- staging table for the oparl harvester
-- it is safe to run this file more then once

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS iris_staging;

CREATE TABLE IF NOT EXISTS iris_staging.signal_ingest (
    id                 bigserial PRIMARY KEY,
    source_system      text        NOT NULL,
    source_name        text        NOT NULL,
    source_record_id   text        NOT NULL,
    signal_type        text        NOT NULL,
    title              text        NOT NULL,
    reference          text,
    paper_type         text,
    published_date     date,
    source_url         text        NOT NULL,
    municipality       text        NOT NULL,
    region             text,
    location_text      text,
    geom               geometry(Point, 25832),
    geo_status         text        NOT NULL,
    matched_keywords   text[]      NOT NULL DEFAULT '{}',
    quality_flags      text[]      NOT NULL DEFAULT '{}',
    source_modified_at timestamptz,
    content_hash       text        NOT NULL,
    raw_record         jsonb       NOT NULL,
    first_seen_at      timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),

    -- one row per paper. this is what makes a re-run safe
    CONSTRAINT signal_ingest_source_record_uq UNIQUE (source_system, source_record_id),

    CONSTRAINT signal_ingest_signal_type_ck
        CHECK (signal_type IN ('mega_substation', 'semiconductor_dc_park')),

    CONSTRAINT signal_ingest_geo_status_ck
        CHECK (geo_status IN ('resolved', 'ambiguous', 'invalid', 'unresolved', 'no_location')),

    -- only resolved rows have a point, so a bad point can not sneak in
    CONSTRAINT signal_ingest_geom_status_ck
        CHECK ((geo_status = 'resolved') = (geom IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS signal_ingest_geom_idx
    ON iris_staging.signal_ingest USING gist (geom);

CREATE INDEX IF NOT EXISTS signal_ingest_published_date_idx
    ON iris_staging.signal_ingest (published_date);
