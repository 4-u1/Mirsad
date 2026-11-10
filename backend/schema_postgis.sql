-- مِرصاد · مخطط PostgreSQL + PostGIS (PRD 11 و 15.1) — يُنفَّذ تلقائيًا من backend/db.py عند ضبط DATABASE_URL
-- القيم JSON والأوقات ISO-8601 مخزّنة نصًا لتطابق نسخة SQLite حرفيًا
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS sectors (
  id        text PRIMARY KEY,
  name      text,
  geometry  geometry(Polygon, 4326) NOT NULL,
  min_lat   double precision, min_lon double precision, max_lat double precision, max_lon double precision,
  area_km2  double precision
);
CREATE INDEX IF NOT EXISTS sectors_gix ON sectors USING gist (geometry);

CREATE TABLE IF NOT EXISTS model_runs (
  id            serial PRIMARY KEY,
  version       text NOT NULL,
  trained_at    text NOT NULL,
  metrics       text NOT NULL,
  data_snapshot text NOT NULL,
  card          text NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_scores (
  sector_id    text NOT NULL REFERENCES sectors(id),
  "timestamp"  text NOT NULL,
  score        double precision NOT NULL,
  max_score    double precision,
  mean_score   double precision,
  level        text NOT NULL CHECK (level IN ('low','medium','high','critical')),
  model_run_id int NOT NULL REFERENCES model_runs(id),
  top_factors  text NOT NULL,
  details      text NOT NULL,
  PRIMARY KEY (sector_id, model_run_id)
);

CREATE TABLE IF NOT EXISTS features (
  lat            double precision NOT NULL,
  lon            double precision NOT NULL,
  geom           geometry(Point, 4326) GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(lon, lat), 4326)) STORED,
  sector_id      text,
  elevation      real, slope real, aspect real,
  landcover      integer, landcover_name text,
  score          real, level text, model_run_id int
);
CREATE INDEX IF NOT EXISTS features_gix ON features USING gist (geom);
CREATE INDEX IF NOT EXISTS features_sector_ix ON features (sector_id);

CREATE TABLE IF NOT EXISTS alerts (
  id           serial PRIMARY KEY,
  sector_id    text NOT NULL REFERENCES sectors(id),
  level        text NOT NULL,
  score        double precision NOT NULL,
  reasons      text NOT NULL,
  status       text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','dismissed')),
  approved_by  text,
  decided_at   text,
  created_at   text NOT NULL,
  model_run_id int
);
CREATE INDEX IF NOT EXISTS alerts_sector_ix ON alerts (sector_id, status);

CREATE TABLE IF NOT EXISTS data_sources (
  id text PRIMARY KEY, name text NOT NULL, license text, last_updated text,
  status text NOT NULL, records int, used_in_model int NOT NULL, note text
);

CREATE TABLE IF NOT EXISTS settings (key text PRIMARY KEY, value text NOT NULL);

CREATE TABLE IF NOT EXISTS users (
  username text PRIMARY KEY,
  role     text NOT NULL CHECK (role IN ('viewer','operator','admin')),
  salt     text NOT NULL,
  pw_hash  text NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (token text PRIMARY KEY, username text NOT NULL, expires_at text NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (id bigserial PRIMARY KEY, at text NOT NULL, username text, action text NOT NULL, detail text);
