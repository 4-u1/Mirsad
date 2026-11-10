"""مِرصاد · طبقة قاعدة البيانات.

- إذا ضُبط DATABASE_URL (مثل Supabase): PostgreSQL + PostGIS عبر psycopg، والمخطط في backend/schema_postgis.sql.
- وإلا: SQLite محلي (backend/mirsad.db أو MIRSAD_DB) بنفس الجداول (PRD 15.1).
الشيفرة تكتب الاستعلامات بعلامة ? وتُحوَّل تلقائيًا إلى %s في PostgreSQL.
"""
import os, sqlite3, hashlib, secrets, json, datetime, contextlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("MIRSAD_DB", ROOT / "backend" / "mirsad.db"))
TABLES = ["audit_log", "sessions", "users", "settings", "data_sources", "alerts", "features", "risk_scores", "model_runs", "sectors"]

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sectors (
  id TEXT PRIMARY KEY, name TEXT, geometry TEXT NOT NULL,
  min_lat REAL, min_lon REAL, max_lat REAL, max_lon REAL, area_km2 REAL);
CREATE TABLE IF NOT EXISTS model_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, version TEXT NOT NULL, trained_at TEXT NOT NULL,
  metrics TEXT NOT NULL, data_snapshot TEXT NOT NULL, card TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS risk_scores (
  sector_id TEXT NOT NULL REFERENCES sectors(id), timestamp TEXT NOT NULL, score REAL NOT NULL,
  max_score REAL, mean_score REAL, level TEXT NOT NULL, model_run_id INTEGER NOT NULL REFERENCES model_runs(id),
  top_factors TEXT NOT NULL, details TEXT NOT NULL, PRIMARY KEY (sector_id, model_run_id));
CREATE TABLE IF NOT EXISTS features (
  lat REAL NOT NULL, lon REAL NOT NULL, sector_id TEXT, elevation REAL, slope REAL, aspect REAL,
  landcover INTEGER, landcover_name TEXT, score REAL, level TEXT, model_run_id INTEGER,
  curv_plan REAL, relief_1km REAL, soil_clay REAL, rain_p99_3d_mm REAL, lith_class TEXT);
CREATE INDEX IF NOT EXISTS ix_features_sector ON features(sector_id);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, sector_id TEXT NOT NULL REFERENCES sectors(id), level TEXT NOT NULL,
  score REAL NOT NULL, reasons TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  approved_by TEXT, decided_at TEXT, created_at TEXT NOT NULL, model_run_id INTEGER);
CREATE INDEX IF NOT EXISTS ix_alerts_sector ON alerts(sector_id, status);
CREATE TABLE IF NOT EXISTS data_sources (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, license TEXT, last_updated TEXT, status TEXT NOT NULL,
  records INTEGER, used_in_model INTEGER NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS users (
  username TEXT PRIMARY KEY, role TEXT NOT NULL CHECK (role IN ('viewer','operator','admin')),
  salt TEXT NOT NULL, pw_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, username TEXT, action TEXT NOT NULL, detail TEXT);
CREATE TABLE IF NOT EXISTS forecasts (
  issued_at TEXT NOT NULL, sector_id TEXT NOT NULL, horizon_h INTEGER NOT NULL, rain_mm REAL, threshold_mm REAL,
  ratio REAL, base_level TEXT NOT NULL, level TEXT NOT NULL, source TEXT NOT NULL,
  PRIMARY KEY (issued_at, sector_id, horizon_h));
CREATE INDEX IF NOT EXISTS ix_forecasts_sector ON forecasts(sector_id, issued_at);
"""


class SQLiteDB:
    dialect = "sqlite"
    geom_in = "?"                       # كتابة هندسة القطاع (نص GeoJSON)
    geom_out = "s.geometry"              # قراءتها كنص GeoJSON

    def __init__(self, path):
        self.c = sqlite3.connect(str(path), check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.execute("PRAGMA foreign_keys = ON")

    def execute(self, sql, params=()):
        return self.c.execute(sql, params)

    def executemany(self, sql, seq):
        return self.c.executemany(sql, seq)

    def commit(self):
        self.c.commit()

    @contextlib.contextmanager
    def transaction(self):
        yield
        self.c.commit()

    def create_schema(self):
        self.c.executescript(SQLITE_SCHEMA)

    def drop_all(self):
        for t in TABLES:
            self.c.execute(f"DROP TABLE IF EXISTS {t}")
        self.c.commit()

    def bbox_filter(self):
        return "s.max_lon>=? AND s.min_lon<=? AND s.max_lat>=? AND s.min_lat<=?", lambda a, b, c, d: [a, c, b, d]

    def copy_features(self, rows):
        self.c.executemany("INSERT INTO features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


class PostgresDB:
    dialect = "postgres"
    geom_in = "ST_SetSRID(ST_GeomFromGeoJSON(?), 4326)"
    geom_out = "ST_AsGeoJSON(s.geometry) AS geometry"

    def __init__(self, url):
        import psycopg
        from psycopg.rows import dict_row
        self._psycopg, self._dict_row, self.url, self._c = psycopg, dict_row, url, None

    def conn(self):
        if self._c is None or self._c.closed:
            # prepare_threshold=None: متوافق مع Supabase pooler (لا جمل محضّرة على الخادم)
            self._c = self._psycopg.connect(self.url, autocommit=True, row_factory=self._dict_row,
                                            prepare_threshold=None, connect_timeout=15)
        return self._c

    @staticmethod
    def _q(sql):
        return sql.replace("?", "%s")

    def execute(self, sql, params=()):
        try:
            return self.conn().execute(self._q(sql), params)
        except self._psycopg.OperationalError:
            # إعادة الاتصال مرة واحدة إذا انقطع الاتصال الخامل (بيئة serverless)، للاستعلامات القرائية فقط
            if not sql.lstrip().upper().startswith("SELECT"):
                raise
            self._c = None
            return self.conn().execute(self._q(sql), params)

    def executemany(self, sql, seq):
        cur = self.conn().cursor()
        cur.executemany(self._q(sql), list(seq))
        return cur

    def commit(self):
        pass  # autocommit

    def transaction(self):
        return self.conn().transaction()

    def create_schema(self):
        script = (ROOT / "backend" / "schema_postgis.sql").read_text(encoding="utf-8")
        stmts = [s.strip() for s in script.split(";\n") if s.strip() and not all(l.strip().startswith("--") or not l.strip() for l in s.splitlines())]
        for s in stmts:
            self.conn().execute(s)

    def drop_all(self):
        self.conn().execute("DROP TABLE IF EXISTS " + ", ".join(TABLES) + " CASCADE")

    def bbox_filter(self):
        return "s.geometry && ST_MakeEnvelope(?, ?, ?, ?, 4326)", lambda a, b, c, d: [a, b, c, d]

    def copy_features(self, rows):
        cols = ("lat, lon, sector_id, elevation, slope, aspect, landcover, landcover_name, score, level, model_run_id, "
                "curv_plan, relief_1km, soil_clay, rain_p99_3d_mm, lith_class")
        with self.conn().cursor() as cur:
            with cur.copy(f"COPY features ({cols}) FROM STDIN") as cp:
                for r in rows:
                    cp.write_row(r)


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def connect(path=None, create=True):
    url = (os.environ.get("DATABASE_URL") or "").strip()
    con = PostgresDB(url) if url else SQLiteDB(path or DB_PATH)
    if create:
        con.create_schema()
    return con


def hash_pw(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return salt, h


def add_user(con, username: str, password: str, role: str):
    salt, h = hash_pw(password)
    con.execute("""INSERT INTO users(username, role, salt, pw_hash) VALUES (?,?,?,?)
                   ON CONFLICT (username) DO UPDATE SET role=excluded.role, salt=excluded.salt, pw_hash=excluded.pw_hash""",
                (username, role, salt, h))
    con.commit()


def audit(con, username, action, detail=None):
    con.execute("INSERT INTO audit_log(at, username, action, detail) VALUES (?,?,?,?)",
                (now(), username, action, json.dumps(detail, ensure_ascii=False) if detail is not None else None))
    con.commit()
