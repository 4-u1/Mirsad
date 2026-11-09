"""مِرصاد · طبقة قاعدة البيانات (SQLite للتشغيل المحلي، مخطط مطابق لـ PRD 15.1).

مخطط PostGIS المكافئ للنشر في: backend/schema_postgis.sql
"""
import os, sqlite3, hashlib, secrets, json, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("MIRSAD_DB", ROOT / "backend" / "mirsad.db"))

SCHEMA = """
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
  landcover INTEGER, landcover_name TEXT, score REAL, level TEXT, model_run_id INTEGER);
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
"""

def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()

def connect(path=None) -> sqlite3.Connection:
    con = sqlite3.connect(str(path or DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(SCHEMA)
    return con

def hash_pw(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()
    return salt, h

def add_user(con, username: str, password: str, role: str):
    salt, h = hash_pw(password)
    con.execute("INSERT OR REPLACE INTO users(username, role, salt, pw_hash) VALUES (?,?,?,?)", (username, role, salt, h))
    con.commit()

def audit(con, username, action, detail=None):
    con.execute("INSERT INTO audit_log(at, username, action, detail) VALUES (?,?,?,?)",
                (now(), username, action, json.dumps(detail, ensure_ascii=False) if detail is not None else None))
    con.commit()
