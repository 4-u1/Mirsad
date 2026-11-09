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
    import sqlite3
    con = sqlite3.connect(os.environ["MIRSAD_DB"])
    con.execute("INSERT INTO alerts(sector_id, level, score, reasons, status, created_at) VALUES (?,?,?,?, 'pending', datetime('now'))",
                (approved["sector_id"], approved["level"], approved["score"], "[]")); con.commit()
    new_id = con.execute("SELECT max(id) FROM alerts").fetchone()[0]; con.close()
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

def test_forecast_is_honest_501(server):
    assert call(server, "/api/v1/sectors/S181-422/forecast")[0] == 501

def test_sources_and_model(server):
    s = call(server, "/api/v1/sources")[1]["items"]
    assert {i["id"] for i in s} >= {"inventory", "terrain", "rainfall", "earthquakes"}
    m = call(server, "/api/v1/model/runs/latest")[1]
    assert m["version"] == "v1" and "spatial_cv" in m

def test_bad_inputs(server):
    assert call(server, "/api/v1/risk?level=nope")[0] == 400
    assert call(server, "/api/v1/risk?bbox=1,2")[0] == 400
    assert call(server, "/api/v1/sectors/NOPE")[0] == 404
