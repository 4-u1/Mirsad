"""مِرصاد · اختبارات القبول (PRD 19) والصلاحيات. التشغيل: pytest -q"""
import os, sys, json, time, socket, threading, urllib.request, urllib.error
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

@pytest.fixture(scope="session")
def server(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ.update(MIRSAD_DB=str(db_path), MIRSAD_ADMIN_PASSWORD="admin-pass", MIRSAD_OPERATOR_PASSWORD="op-pass",
                      MIRSAD_VIEWER_PASSWORD="view-pass")
    import importlib, db as dbmod
    importlib.reload(dbmod)
    import rules; importlib.reload(rules)
    import load_db; importlib.reload(load_db); load_db.main(db_path)
    import app as appmod; importlib.reload(appmod)
    import uvicorn
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(appmod.app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started: break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    srv.should_exit = True

def call(base, path, method="GET", body=None, token=None):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"Authorization": "Bearer " + token} if token else {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b"null")

def login(base, u, p):
    return call(base, "/api/v1/auth/login", "POST", {"username": u, "password": p})[1]["token"]

def test_health_and_static(server):
    assert call(server, "/api/v1/health")[1]["status"] == "ok"
    with urllib.request.urlopen(server + "/") as r:
        assert b"mirsad" in r.read().lower()

def test_ac1_risk_map_fast_with_levels(server):
    t0 = time.time(); st, fc = call(server, "/api/v1/risk"); dt = time.time() - t0
    assert st == 200 and dt < 3 and len(fc["features"]) > 0
    assert all(f["properties"]["level"] in ("low", "medium", "high", "critical") for f in fc["features"])

def test_ac2_critical_sector_shows_level_and_factors(server):
    fc = call(server, "/api/v1/risk?level=critical")[1]
    sid = fc["features"][0]["properties"]["id"]
    st, s = call(server, f"/api/v1/sectors/{sid}")
    assert st == 200 and s["score"] >= 0.80 and s["level"] == "critical" and len(s["top_factors"]) == 3

def test_ac3_approval_logged_with_name_and_time(server):
    op = login(server, "operator", "op-pass")
    a = call(server, "/api/v1/alerts?status=pending")[1]["items"][0]
    st, r = call(server, "/api/v1/alerts", "POST", {"alert_id": a["id"], "action": "approve"}, op)
    assert st == 200 and r["status"] == "approved" and r["approved_by"] == "operator" and r["decided_at"]
    admin = login(server, "admin", "admin-pass")
    log = call(server, "/api/v1/audit", token=admin)[1]["items"]
    assert any(i["action"] == "alert.approved" and i["username"] == "operator" for i in log)

def test_ac5_cooldown_blocks_duplicate(server):
    op = login(server, "operator", "op-pass")
    approved = call(server, "/api/v1/alerts?status=approved")[1]["items"][0]
    import db as dbmod
    con = dbmod.connect(os.environ["MIRSAD_DB"], create=False)
    con.execute("INSERT INTO alerts(sector_id, level, score, reasons, status, created_at) VALUES (?,?,?,?, 'pending', ?)",
                (approved["sector_id"], approved["level"], approved["score"], "[]", dbmod.now())); con.commit()
    new_id = con.execute("SELECT max(id) AS m FROM alerts").fetchone()["m"]
    st, r = call(server, "/api/v1/alerts", "POST", {"alert_id": new_id, "action": "approve"}, op)
    assert st == 409 and r["error"] == "cooldown"

def test_roles_enforced(server):
    viewer = login(server, "viewer", "view-pass")
    a = call(server, "/api/v1/alerts?status=pending")[1]["items"][0]
    assert call(server, "/api/v1/alerts", "POST", {"alert_id": a["id"], "action": "approve"})[0] == 401
    assert call(server, "/api/v1/alerts", "POST", {"alert_id": a["id"], "action": "approve"}, viewer)[0] == 403
    assert call(server, "/api/v1/settings/thresholds", "PUT", {"medium": .3, "high": .5, "critical": .7}, viewer)[0] == 403
    assert call(server, "/api/v1/auth/login", "POST", {"username": "admin", "password": "wrong"})[0] == 401

def test_thresholds_admin_relevel_and_audit(server):
    admin = login(server, "admin", "admin-pass")
    before = call(server, "/api/v1/risk?level=high,critical")[1]["features"]
    st, r = call(server, "/api/v1/settings/thresholds", "PUT", {"medium": 0.4, "high": 0.55, "critical": 0.8}, admin)
    assert st == 200
    after = call(server, "/api/v1/risk?level=high,critical")[1]["features"]
    assert len(after) >= len(before)
    assert call(server, "/api/v1/settings/thresholds", "PUT", {"medium": 0.9, "high": 0.5, "critical": 0.7}, admin)[0] == 400
    call(server, "/api/v1/settings/thresholds", "PUT", {"medium": 0.4, "high": 0.6, "critical": 0.8}, admin)

def test_forecast_rule():
    from rules import forecast_level
    assert forecast_level("low", None) == "low" and forecast_level("low", 0.49) == "low"
    assert forecast_level("low", 0.5) == "medium" and forecast_level("medium", 1.0) == "critical"
    assert forecast_level("high", 3.0) == "critical" and forecast_level("critical", 0) == "critical"


def test_forecast_endpoints(server, monkeypatch):
    sid = "S181-422"
    assert call(server, f"/api/v1/sectors/{sid}/forecast")[0] == 503      # لا تنبؤ بعد: رسالة واضحة لا أرقام
    assert call(server, "/api/v1/forecast")[0] == 503
    import importlib, datetime
    spec = importlib.util.spec_from_file_location("fc10", ROOT / "pipeline" / "10_forecast.py")
    fc = importlib.util.module_from_spec(spec); spec.loader.exec_module(fc)
    start = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    times = [(start + datetime.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(96)]
    monkeypatch.setattr(fc, "fetch", lambda lat, lon: [{"hourly": {"time": times, "precipitation": [2.0] * 96}} for _ in lat])
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    summary = fc.main()
    assert summary["sectors"] == 1166 and summary["with_rain_forecast"] == 1166
    st, r = call(server, f"/api/v1/sectors/{sid}/forecast")
    assert st == 200 and [h["h"] for h in r["horizons"]] == [24, 48, 72]
    assert [h["rain_mm"] for h in r["horizons"]] == [48.0, 96.0, 144.0] and r["stale"] is False
    st, allf = call(server, "/api/v1/forecast?min_level=critical")
    assert st == 200 and all(i["horizons"][-1]["level"] == "critical" for i in allf["items"])
    assert call(server, "/api/v1/forecast?min_level=nope")[0] == 400
    assert call(server, "/api/v1/sectors/NOPE/forecast")[0] == 404


def test_reload_keeps_decisions(server, tmp_path):
    """إعادة تحميل القاعدة (نموذج أو طبقات جديدة) لا تمسح الاعتمادات ولا سجل التدقيق."""
    import shutil, load_db, db as dbmod
    copy = tmp_path / "copy.db"; shutil.copy(os.environ["MIRSAD_DB"], copy)
    old = dbmod.connect(copy, create=False)
    decided = {r["sector_id"]: r["status"] for r in old.execute("SELECT sector_id, status FROM alerts WHERE status<>'pending'")}
    n_audit = old.execute("SELECT count(*) AS n FROM audit_log").fetchone()["n"]
    assert decided
    con = load_db.main(copy)
    after = {r["sector_id"]: r["status"] for r in con.execute("SELECT sector_id, status FROM alerts WHERE status<>'pending'")}
    assert all(after.get(k) == v for k, v in decided.items())
    assert con.execute("SELECT count(*) AS n FROM audit_log").fetchone()["n"] > n_audit

def test_sources_and_model(server):
    s = call(server, "/api/v1/sources")[1]["items"]
    assert {i["id"] for i in s} >= {"inventory", "terrain", "rainfall", "earthquakes"}
    m = call(server, "/api/v1/model/runs/latest")[1]
    assert m["version"] == "v1" and "spatial_cv" in m

def test_bad_inputs(server):
    assert call(server, "/api/v1/risk?level=nope")[0] == 400
    assert call(server, "/api/v1/risk?bbox=1,2")[0] == 400
    assert call(server, "/api/v1/sectors/NOPE")[0] == 404

def test_ac4_stale_data_flag(server):
    import db as dbmod, datetime
    assert call(server, "/api/v1/risk")[1]["stale"] is False
    con = dbmod.connect(os.environ["MIRSAD_DB"], create=False)
    con.execute("UPDATE data_sources SET last_updated='2020-01-01' WHERE id='terrain'"); con.commit()
    fc = call(server, "/api/v1/risk")[1]
    src = {s["id"]: s for s in call(server, "/api/v1/sources")[1]["items"]}
    con.execute("UPDATE data_sources SET last_updated=? WHERE id='terrain'", (datetime.date.today().isoformat(),)); con.commit()
    assert fc["stale"] is True and src["terrain"]["stale"] is True

def test_bbox_filter_uses_spatial_query(server):
    allf = call(server, "/api/v1/risk")[1]["features"]
    sub = call(server, "/api/v1/risk?bbox=42.0,18.0,42.3,18.3")[1]["features"]
    assert 0 < len(sub) < len(allf)
    for f in sub:
        xs = [c[0] for c in f["geometry"]["coordinates"][0]]; ys = [c[1] for c in f["geometry"]["coordinates"][0]]
        assert max(xs) >= 42.0 and min(xs) <= 42.3 and max(ys) >= 18.0 and min(ys) <= 18.3
