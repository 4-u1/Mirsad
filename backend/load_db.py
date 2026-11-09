"""مِرصاد · تحميل مخرجات خط المعالجة إلى قاعدة البيانات.

يقرأ: model/model_card.json · web/data/sectors.geojson · data/processed/risk_scores_v1.csv
التشغيل:  python backend/load_db.py
كلمات المرور الأولية من متغيرات البيئة MIRSAD_ADMIN_PASSWORD و MIRSAD_OPERATOR_PASSWORD،
وإن لم تُضبط تُولَّد عشوائيًا وتُطبع مرة واحدة.
"""
import os, sys, json, math, secrets
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, add_user, audit, now, ROOT, DB_PATH  # noqa: E402

LEVELS = ["low", "medium", "high", "critical"]

def level_of(s, th):
    return "critical" if s >= th["critical"] else "high" if s >= th["high"] else "medium" if s >= th["medium"] else "low"

def reasons_for(p, lc):
    r = []
    if p.get("events"): r.append({"key": "events", "value": p["events"]})
    r += [{"key": "slope_max", "value": p["slope_max"]}, {"key": "elevation", "value": p["peak_vals"]["elevation"]},
          {"key": "landcover", "value": lc}]
    return r

def propose_alerts(con, run_id, by="system"):
    rows = con.execute("""SELECT r.sector_id, r.level, r.score, r.details FROM risk_scores r
        WHERE r.model_run_id=? AND r.level IN ('high','critical')
        AND NOT EXISTS (SELECT 1 FROM alerts a WHERE a.sector_id=r.sector_id AND a.status='pending')""", (run_id,)).fetchall()
    for r in rows:
        d = json.loads(r["details"])
        con.execute("INSERT INTO alerts(sector_id, level, score, reasons, status, created_at, model_run_id) VALUES (?,?,?,?,?,?,?)",
                    (r["sector_id"], r["level"], r["score"], json.dumps(reasons_for(d, d["peak_vals"]["landcover"]), ensure_ascii=False),
                     "pending", now(), run_id))
    con.commit()
    if rows: audit(con, by, "alerts.proposed", {"count": len(rows), "model_run_id": run_id})
    return len(rows)

def main(db_path=None, fresh=True):
    path = Path(db_path or DB_PATH)
    if fresh and path.exists(): path.unlink()
    con = connect(path)
    card = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
    sectors = json.loads((ROOT / "web" / "data" / "sectors.geojson").read_text(encoding="utf-8"))
    th = card["thresholds"]
    con.execute("INSERT OR REPLACE INTO settings VALUES ('thresholds', ?)", (json.dumps(th),))
    cur = con.execute("INSERT INTO model_runs(version, trained_at, metrics, data_snapshot, card) VALUES (?,?,?,?,?)",
                      (card["version"], card["trained_at"], json.dumps({"spatial_cv": card["spatial_cv"], "random_cv": card["random_cv"]}),
                       json.dumps(card["cleaning"], ensure_ascii=False), json.dumps(card, ensure_ascii=False)))
    run_id = cur.lastrowid
    imp = card["feature_importance"]
    ts = now()
    for f in sectors["features"]:
        p = f["properties"]
        ring = f["geometry"]["coordinates"][0]
        lons, lats = [c[0] for c in ring], [c[1] for c in ring]
        area = (max(lats) - min(lats)) * 110.574 * (max(lons) - min(lons)) * 111.320 * math.cos(math.radians(sum(lats) / len(lats)))
        con.execute("INSERT INTO sectors VALUES (?,?,?,?,?,?,?,?)", (p["id"], p["id"], json.dumps(f["geometry"]),
                    min(lats), min(lons), max(lats), max(lons), round(area, 2)))
        shap = p.get("shap") or {k: v for k, v in imp.items()}
        top = [{"feature": k, "contribution": v, "value": p["peak_vals"][k]} for k, v in list(shap.items())[:3]]
        con.execute("INSERT INTO risk_scores VALUES (?,?,?,?,?,?,?,?,?)",
                    (p["id"], ts, p["score"], p["max"], p["mean"], level_of(p["score"], th), run_id,
                     json.dumps(top, ensure_ascii=False), json.dumps(p, ensure_ascii=False)))
    g = pd.read_csv(ROOT / "data" / "processed" / "risk_scores_v1.csv", encoding="utf-8-sig")
    g["sector_id"] = ["S%03d-%03d" % (math.floor(a / 0.1), math.floor(b / 0.1)) for a, b in zip(g.lat, g.lon)]
    con.executemany("INSERT INTO features VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    [(r.lat, r.lon, r.sector_id, r.elevation, r.slope, r.aspect, int(r.landcover), r.landcover_name,
                      r.risk_score, r.risk_level, run_id) for r in g.itertuples()])
    c = card["cleaning"]
    srcs = [
        ("inventory", "Landslide inventory (news + NASA Global Landslide Catalog)", "NASA GLC: public; news: cited", c["landslide_events"], 1, "labels"),
        ("terrain", "Copernicus DEM 30 m + ESA WorldCover 2021", "Copernicus DEM licence; CC BY 4.0", c["training_rows"], 1, "elevation, slope, aspect, land cover"),
        ("grid", "Point grid (~1 km)", "team", c["grid_points_with_features"], 1, "prediction cells"),
        ("rainfall", "Monthly rainfall by region 2009-2019", "team-supplied", c["rainfall_rows"], 0,
         f"{len(c['rainfall_regions_placeholder_coords'])} of {c['rainfall_regions']} regions have placeholder coordinates"),
        ("earthquakes", "USGS earthquake catalog", "USGS public domain", c["earthquakes"], 0,
         f"{c['earthquakes_in_study_area']} events inside the study area"),
        ("factors", "Conditioning-factor table (282 rows)", "unknown", c["conditioning_factor_rows"], 0, "F_NF column undocumented")]
    con.executemany("INSERT INTO data_sources VALUES (?,?,?,?,?,?,?,?)",
                    [(i, n, lic, card["trained_at"], "ok" if u else "not_used", rec, u, note) for i, n, lic, rec, u, note in srcs])
    con.commit()
    creds = {}
    for user, role, env in [("admin", "admin", "MIRSAD_ADMIN_PASSWORD"), ("operator", "operator", "MIRSAD_OPERATOR_PASSWORD"),
                            ("viewer", "viewer", "MIRSAD_VIEWER_PASSWORD")]:
        pw = os.environ.get(env) or secrets.token_urlsafe(9)
        if not os.environ.get(env): creds[user] = pw
        add_user(con, user, pw, role)
    n = propose_alerts(con, run_id)
    audit(con, "system", "db.loaded", {"model_run_id": run_id, "sectors": len(sectors["features"]), "cells": len(g), "alerts_proposed": n})
    print(f"loaded {len(sectors['features'])} sectors, {len(g)} cells, {n} pending alerts -> {path}")
    for u, pw in creds.items():
        print(f"generated password for '{u}': {pw}")
    return con

if __name__ == "__main__":
    main()
