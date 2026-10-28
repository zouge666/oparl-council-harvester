-- remembers per source how far we got, so the next run only asks for changed papers
-- it is safe to run this file more then once

CREATE TABLE IF NOT EXISTS iris_staging.harvest_state (
    source_name        text PRIMARY KEY,
    last_modified_seen timestamptz NOT NULL,
    last_success_at    timestamptz NOT NULL DEFAULT now()
);
