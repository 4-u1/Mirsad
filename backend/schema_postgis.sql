-- مِرصاد · مخطط PostgreSQL + PostGIS للنشر (PRD 11 و 15.1)
-- مكافئ لمخطط SQLite في backend/db.py. لم يُختبر على خادم PostGIS في بيئة البناء.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE sectors (
  id        text PRIMARY KEY,
  name      text,
  geometry  geometry(Polygon, 4326) NOT NULL,
  area_km2  numeric(10,2)
);
CREATE INDEX sectors_gix ON sectors USING gist (geometry);

CREATE TABLE model_runs (
  id            serial PRIMARY KEY,
  version       text NOT NULL,
  trained_at    date NOT NULL,
  metrics       jsonb NOT NULL,
  data_snapshot jsonb NOT NULL,
  card          jsonb NOT NULL
);

CREATE TABLE features (
  id             bigserial PRIMARY KEY,
  geom           geometry(Point, 4326) NOT NULL,
  sector_id      text REFERENCES sectors(id),
  elevation      real, slope real, aspect real,
  landcover      smallint, landcover_name text,
  score          real, level text, model_run_id int REFERENCES model_runs(id)
);
CREATE INDEX features_gix ON features USING gist (geom);
CREATE INDEX features_sector_ix ON features (sector_id);

CREATE TABLE risk_scores (
  sector_id    text NOT NULL REFERENCES sectors(id),
  "timestamp"  timestamptz NOT NULL,
  score        real NOT NULL,
  max_score    real, mean_score real,
  level        text NOT NULL CHECK (level IN ('low','medium','high','critical')),
  model_run_id int NOT NULL REFERENCES model_runs(id),
  top_factors  jsonb NOT NULL,
  details      jsonb NOT NULL,
  PRIMARY KEY (sector_id, model_run_id)
);

CREATE TABLE alerts (
  id           serial PRIMARY KEY,
  sector_id    text NOT NULL REFERENCES sectors(id),
  level        text NOT NULL,
  score        real NOT NULL,
  reasons      jsonb NOT NULL,
  status       text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','dismissed')),
  approved_by  text,
  decided_at   timestamptz,
  created_at   timestamptz NOT NULL DEFAULT now(),
  model_run_id int REFERENCES model_runs(id)
);
CREATE INDEX alerts_sector_ix ON alerts (sector_id, status);

CREATE TABLE data_sources (
  id text PRIMARY KEY, name text NOT NULL, license text, last_updated date,
  status text NOT NULL, records int, used_in_model boolean NOT NULL, note text
);

CREATE TABLE settings (key text PRIMARY KEY, value jsonb NOT NULL);

CREATE TABLE users (
  username text PRIMARY KEY,
  role     text NOT NULL CHECK (role IN ('viewer','operator','admin')),
  salt     text NOT NULL,
  pw_hash  text NOT NULL
);
CREATE TABLE sessions (token text PRIMARY KEY, username text NOT NULL REFERENCES users(username), expires_at timestamptz NOT NULL);
CREATE TABLE audit_log (id bigserial PRIMARY KEY, at timestamptz NOT NULL DEFAULT now(), username text, action text NOT NULL, detail jsonb);
