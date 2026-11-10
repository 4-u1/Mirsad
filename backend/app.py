"""مِرصاد · خادم الـAPI (PRD 15.2) ويخدم الواجهة من نفس المنفذ.

مبني على Starlette (الإطار الذي بُني عليه FastAPI).
التشغيل:  python backend/load_db.py && uvicorn backend.app:app --port 8000
ثم افتح http://localhost:8000
"""
import sys, json, secrets, datetime, hmac
from pathlib import Path
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, hash_pw, audit, now, ROOT  # noqa: E402
from rules import level_of, propose_alerts, LEVELS as _LV  # noqa: E402,F401

COOLDOWN_HOURS = 24
STALE_DAYS = int(__import__("os").environ.get("MIRSAD_STALE_DAYS", "30"))  # AC-4: عمر البيانات قبل وسمها «متقادمة»
SESSION_HOURS = 12
ROLE_RANK = {"viewer": 0, "operator": 1, "admin": 2}
LEVELS = ["low", "medium", "high", "critical"]
CON = None

def db():
    global CON
    if CON is None: CON = connect(create=False)
    return CON

def err(status, code, msg):
    return JSONResponse({"error": code, "message": msg}, status_code=status)

def user_of(request):
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "): return None
    row = db().execute("SELECT s.username, u.role, s.expires_at FROM sessions s JOIN users u USING(username) WHERE token=?",
                       (h[7:].strip(),)).fetchone()
    if not row or row["expires_at"] < now(): return None
    return {"username": row["username"], "role": row["role"]}

def require(request, role):
    u = user_of(request)
    if not u: return None, err(401, "unauthorized", "Login required")
    if ROLE_RANK[u["role"]] < ROLE_RANK[role]: return None, err(403, "forbidden", f"Role '{role}' required")
    return u, None

def latest_run():
    return db().execute("SELECT * FROM model_runs ORDER BY id DESC LIMIT 1").fetchone()

def freshness():
    """AC-4: يحسب عمر البيانات من تاريخ آخر تحديث لكل مصدر مستخدم في النموذج."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    out = []
    for r in db().execute("SELECT id, name, last_updated, used_in_model FROM data_sources"):
        try: age = (today - datetime.date.fromisoformat(r["last_updated"][:10])).days
        except Exception: age = None
        out.append({"id": r["id"], "last_updated": r["last_updated"], "age_days": age,
                    "stale": bool(r["used_in_model"]) and age is not None and age > STALE_DAYS})
    return {"stale_after_days": STALE_DAYS, "stale": any(x["stale"] for x in out),
            "data_as_of": min((x["last_updated"] for x in out if x["last_updated"]), default=None), "sources": out}

def thresholds():
    return json.loads(db().execute("SELECT value FROM settings WHERE key='thresholds'").fetchone()["value"])

# ---------------- endpoints ----------------
async def health(request):
    r = latest_run()
    return JSONResponse({"status": "ok", "model_version": r["version"] if r else None, "time": now()})

async def login(request):
    try: body = await request.json()
    except Exception: return err(400, "bad_request", "JSON body required")
    u = db().execute("SELECT * FROM users WHERE username=?", (str(body.get("username", "")),)).fetchone()
    if not u or not hmac.compare_digest(hash_pw(str(body.get("password", "")), u["salt"])[1], u["pw_hash"]):
        audit(db(), body.get("username"), "auth.failed")
        return err(401, "invalid_credentials", "Wrong username or password")
    token = secrets.token_urlsafe(32)
    exp = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=SESSION_HOURS)).replace(microsecond=0).isoformat()
    db().execute("INSERT INTO sessions(token, username, expires_at) VALUES (?,?,?)", (token, u["username"], exp)); db().commit()
    audit(db(), u["username"], "auth.login")
    return JSONResponse({"token": token, "username": u["username"], "role": u["role"], "expires_at": exp})

async def me(request):
    u, e = require(request, "viewer")
    return e or JSONResponse(u)

async def risk(request):
    """GET /api/v1/risk → أحدث درجات الخطر لكل القطاعات (GeoJSON). ?level=high&bbox=minLon,minLat,maxLon,maxLat"""
    run = latest_run()
    q = f"""SELECT s.id, {db().geom_out}, r.score, r.max_score, r.mean_score, r.level, r.details, r.timestamp
           FROM sectors s JOIN risk_scores r ON r.sector_id=s.id WHERE r.model_run_id=?"""
    args = [run["id"]]
    lv = request.query_params.get("level")
    if lv:
        lvls = [x for x in lv.split(",") if x in LEVELS]
        if not lvls: return err(400, "bad_level", "level must be one of " + ",".join(LEVELS))
        q += " AND r.level IN (%s)" % ",".join("?" * len(lvls)); args += lvls
    bb = request.query_params.get("bbox")
    if bb:
        try: a, b, c, d = map(float, bb.split(","))
        except ValueError: return err(400, "bad_bbox", "bbox=minLon,minLat,maxLon,maxLat")
        clause, order = db().bbox_filter()
        q += " AND " + clause; args += order(a, b, c, d)
    feats = []
    for r in db().execute(q, args):
        p = json.loads(r["details"]); p.update({"score": r["score"], "level": r["level"], "max": r["max_score"], "mean": r["mean_score"]})
        feats.append({"type": "Feature", "geometry": json.loads(r["geometry"]), "properties": p})
    fr = freshness()
    return JSONResponse({"type": "FeatureCollection", "model_version": run["version"], "generated_at": now(),
                         "thresholds": thresholds(), "stale": fr["stale"], "data_as_of": fr["data_as_of"],
                         "stale_after_days": fr["stale_after_days"], "features": feats})

async def sector(request):
    sid = request.path_params["id"]; run = latest_run()
    r = db().execute(f"""SELECT s.id, s.area_km2, {db().geom_out}, r.score, r.max_score, r.mean_score, r.level, r.top_factors, r.details, r.timestamp
                        FROM sectors s JOIN risk_scores r ON r.sector_id=s.id WHERE s.id=? AND r.model_run_id=?""", (sid, run["id"])).fetchone()
    if not r: return err(404, "not_found", "Unknown sector")
    alerts = [dict(a) for a in db().execute("SELECT id, level, status, approved_by, decided_at, created_at FROM alerts WHERE sector_id=? ORDER BY id DESC", (sid,))]
    return JSONResponse({"id": r["id"], "area_km2": r["area_km2"], "geometry": json.loads(r["geometry"]), "score": r["score"],
                         "max": r["max_score"], "mean": r["mean_score"], "level": r["level"], "timestamp": r["timestamp"],
                         "model_version": run["version"], "top_factors": json.loads(r["top_factors"]),
                         "details": json.loads(r["details"]), "alerts": alerts})

FORECAST_STALE_HOURS = 12
FORECAST_METHOD = ("Expected level = susceptibility level raised one step when forecast rain up to the horizon reaches 0.5x the sector's "
                   "99th-percentile 3-day rainfall (CHIRPS 1991-2024), two steps at 1.0x; never lowered. A transparent rule, not a model "
                   "calibrated on landslide events.")

def _forecast_rows(where="", args=()):
    t = db().execute("SELECT MAX(issued_at) AS t FROM forecasts").fetchone()
    t = t["t"] if t else None
    if not t: return None, []
    rows = db().execute("SELECT * FROM forecasts WHERE issued_at=?" + where + " ORDER BY sector_id, horizon_h", (t, *args)).fetchall()
    return t, rows

def _forecast_meta(t, rows):
    age = (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(t)).total_seconds() / 3600
    return {"issued_at": t, "age_hours": round(age, 1), "stale": age > FORECAST_STALE_HOURS, "horizons_h": [24, 48, 72],
            "source": rows[0]["source"] if rows else None, "method": FORECAST_METHOD}

def _group(rows):
    out = {}
    for r in rows:
        s = out.setdefault(r["sector_id"], {"sector_id": r["sector_id"], "base_level": r["base_level"], "threshold_mm": r["threshold_mm"], "horizons": []})
        s["horizons"].append({"h": r["horizon_h"], "rain_mm": r["rain_mm"], "ratio": r["ratio"], "level": r["level"]})
    return list(out.values())

NO_FORECAST = ("No forecast has been issued yet. Forecasts are written every 6 hours by the forecast workflow "
               "(pipeline/10_forecast.py).")

async def forecast_all(request):
    """GET /api/v1/forecast → آخر تنبؤ لكل القطاعات (24/48/72 ساعة). ?min_level=high"""
    t, rows = _forecast_rows()
    if not t: return err(503, "forecast_not_ready", NO_FORECAST)
    items = _group(rows)
    ml = request.query_params.get("min_level")
    if ml:
        if ml not in LEVELS: return err(400, "bad_level", "min_level must be one of " + ",".join(LEVELS))
        items = [i for i in items if LEVELS.index(i["horizons"][-1]["level"]) >= LEVELS.index(ml)]
    return JSONResponse(_forecast_meta(t, rows) | {"count": len(items), "items": items})

async def forecast(request):
    """GET /api/v1/sectors/{id}/forecast → تنبؤ القطاع للآفاق 24/48/72 ساعة."""
    sid = request.path_params["id"]
    if not db().execute("SELECT 1 FROM sectors WHERE id=?", (sid,)).fetchone(): return err(404, "not_found", "Unknown sector")
    t, rows = _forecast_rows(" AND sector_id=?", (sid,))
    if not t: return err(503, "forecast_not_ready", NO_FORECAST)
    if not rows: return err(404, "not_found", "No forecast for this sector in the latest issue")
    return JSONResponse(_forecast_meta(t, rows) | _group(rows)[0])

async def list_alerts(request):
    q, args = "SELECT * FROM alerts WHERE 1=1", []
    for k in ("level", "status", "sector_id"):
        v = request.query_params.get(k)
        if v: q += f" AND {k}=?"; args.append(v)
    if request.query_params.get("from"): q += " AND created_at>=?"; args.append(request.query_params["from"])
    if request.query_params.get("to"): q += " AND created_at<=?"; args.append(request.query_params["to"])
    rows = [dict(r) | {"reasons": json.loads(r["reasons"])} for r in db().execute(q + " ORDER BY score DESC, id", args)]
    return JSONResponse({"count": len(rows), "items": rows})

async def decide_alert(request):
    """POST /api/v1/alerts  {alert_id | sector_id, action: approve|dismiss}  — صلاحية مشغّل. موافقة بشرية + فترة تهدئة."""
    u, e = require(request, "operator")
    if e: return e
    try: body = await request.json()
    except Exception: return err(400, "bad_request", "JSON body required")
    action = body.get("action")
    if action not in ("approve", "dismiss"): return err(400, "bad_action", "action must be approve or dismiss")
    if body.get("alert_id"):
        a = db().execute("SELECT * FROM alerts WHERE id=?", (body["alert_id"],)).fetchone()
    else:
        a = db().execute("SELECT * FROM alerts WHERE sector_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (body.get("sector_id"),)).fetchone()
    if not a: return err(404, "not_found", "No matching alert")
    if a["status"] != "pending": return err(409, "already_decided", f"Alert already {a['status']}")
    if action == "approve":
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=COOLDOWN_HOURS)).replace(microsecond=0).isoformat()
        recent = db().execute("SELECT id, decided_at FROM alerts WHERE sector_id=? AND status='approved' AND decided_at>=?",
                              (a["sector_id"], since)).fetchone()
        if recent: return err(409, "cooldown", f"An alert for this sector was approved at {recent['decided_at']} (cooldown {COOLDOWN_HOURS}h)")
    status = "approved" if action == "approve" else "dismissed"
    db().execute("UPDATE alerts SET status=?, approved_by=?, decided_at=? WHERE id=?", (status, u["username"], now(), a["id"]))
    db().commit()
    audit(db(), u["username"], "alert." + status, {"alert_id": a["id"], "sector_id": a["sector_id"], "level": a["level"],
                                                   "delivery": "simulated" if status == "approved" else None})
    return JSONResponse(dict(db().execute("SELECT * FROM alerts WHERE id=?", (a["id"],)).fetchone()) | {"delivery": "simulated"})

async def model_latest(request):
    r = latest_run()
    return JSONResponse({"id": r["id"], "version": r["version"], "trained_at": r["trained_at"], **json.loads(r["card"])})

async def sources(request):
    fr = {x["id"]: x for x in freshness()["sources"]}
    return JSONResponse({"items": [dict(r) | {"age_days": fr[r["id"]]["age_days"], "stale": fr[r["id"]]["stale"]}
                                   for r in db().execute("SELECT * FROM data_sources ORDER BY used_in_model DESC, id")],
                         "stale_after_days": STALE_DAYS})

async def get_thresholds(request):
    return JSONResponse(thresholds())

async def put_thresholds(request):
    """PUT /api/v1/settings/thresholds — للمسؤول فقط، مع إعادة تصنيف القطاعات وتسجيل التغيير."""
    u, e = require(request, "admin")
    if e: return e
    try:
        b = await request.json(); th = {k: float(b[k]) for k in ("medium", "high", "critical")}
    except Exception: return err(400, "bad_request", "medium, high, critical (numbers) required")
    if not (0 < th["medium"] < th["high"] < th["critical"] <= 1): return err(400, "bad_thresholds", "Need 0 < medium < high < critical <= 1")
    old = thresholds(); run = latest_run()
    db().execute("UPDATE settings SET value=? WHERE key='thresholds'", (json.dumps(th),))
    for r in db().execute("SELECT sector_id, score FROM risk_scores WHERE model_run_id=?", (run["id"],)).fetchall():
        db().execute("UPDATE risk_scores SET level=? WHERE sector_id=? AND model_run_id=?", (level_of(r["score"], th), r["sector_id"], run["id"]))
    db().commit()
    audit(db(), u["username"], "settings.thresholds", {"old": old, "new": th})
    n = propose_alerts(db(), run["id"], by=u["username"])
    return JSONResponse({"thresholds": th, "new_alerts_proposed": n})

async def audit_log(request):
    u, e = require(request, "admin")
    if e: return e
    lim = min(int(request.query_params.get("limit", 200)), 1000)
    return JSONResponse({"items": [dict(r) for r in db().execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (lim,))]})

class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"): resp.headers["Cache-Control"] = "no-store"
        return resp

API = "/api/v1"
routes = [
    Route(f"{API}/health", health), Route(f"{API}/auth/login", login, methods=["POST"]), Route(f"{API}/auth/me", me),
    Route(f"{API}/risk", risk), Route(f"{API}/sectors/{{id}}", sector), Route(f"{API}/sectors/{{id}}/forecast", forecast), Route(f"{API}/forecast", forecast_all),
    Route(f"{API}/alerts", list_alerts, methods=["GET"]), Route(f"{API}/alerts", decide_alert, methods=["POST"]),
    Route(f"{API}/model/runs/latest", model_latest), Route(f"{API}/sources", sources),
    Route(f"{API}/settings/thresholds", get_thresholds, methods=["GET"]), Route(f"{API}/settings/thresholds", put_thresholds, methods=["PUT"]),
    Route(f"{API}/audit", audit_log),
] + ([Mount("/", StaticFiles(directory=str(ROOT / "web"), html=True), name="web")] if (ROOT / "web").is_dir() else [])
app = Starlette(routes=routes, middleware=[Middleware(SecurityHeaders)])
