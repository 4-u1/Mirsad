"""مِرصاد · تحميل مخرجات خط المعالجة إلى قاعدة البيانات (SQLite أو PostGIS).

يقرأ: model/model_card.json · web/data/sectors.geojson · data/processed/risk_scores_v1.csv
التشغيل:  python backend/load_db.py
- مع DATABASE_URL (Supabase): يحمّل إلى PostgreSQL/PostGIS ويعيد إنشاء الجداول.
- بدونه: SQLite محلي.
كلمات المرور من MIRSAD_ADMIN_PASSWORD و MIRSAD_OPERATOR_PASSWORD و MIRSAD_VIEWER_PASSWORD.
مع DATABASE_URL هذه المتغيرات إلزامية (لا تُولَّد ولا تُطبع كلمات مرور في سجلات عامة).
"""
import os, sys, json, math, secrets
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from db import connect, add_user, audit, now, ROOT, DB_PATH  # noqa: E402
from rules import level_of, propose_alerts  # noqa: E402,F401  (level_of يُصدَّر للتوافق)

ROLES = [("admin", "admin", "MIRSAD_ADMIN_PASSWORD"), ("operator", "operator", "MIRSAD_OPERATOR_PASSWORD"),
         ("viewer", "viewer", "MIRSAD_VIEWER_PASSWORD")]


def main(db_path=None, fresh=True):
    remote = bool((os.environ.get("DATABASE_URL") or "").strip())
    if remote:
        missing = [env for _, _, env in ROLES[:2] if not (os.environ.get(env) or "").strip()]
        if missing:
            sys.exit("Set " + ", ".join(missing) + " before loading a remote database.")
    else:
        path = Path(db_path or DB_PATH)
        if fresh and path.exists():
            path.unlink()
    con = connect(db_path, create=False)
    if fresh and remote:
        con.drop_all()
    con.create_schema()

    card = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
    sectors = json.loads((ROOT / "web" / "data" / "sectors.geojson").read_text(encoding="utf-8"))
    th = card["thresholds"]
    g = pd.read_csv(ROOT / "data" / "processed" / "risk_scores_v1.csv", encoding="utf-8-sig")
    g["sector_id"] = ["S%03d-%03d" % (math.floor(a / 0.1), math.floor(b / 0.1)) for a, b in zip(g.lat, g.lon)]
    c = card["cleaning"]

    with con.transaction():
        con.execute("INSERT INTO settings(key, value) VALUES ('thresholds', ?) ON CONFLICT (key) DO UPDATE SET value=excluded.value",
                    (json.dumps(th),))
        run_id = con.execute("INSERT INTO model_runs(version, trained_at, metrics, data_snapshot, card) VALUES (?,?,?,?,?) RETURNING id",
                             (card["version"], card["trained_at"], json.dumps({"spatial_cv": card["spatial_cv"], "random_cv": card["random_cv"]}),
                              json.dumps(c, ensure_ascii=False), json.dumps(card, ensure_ascii=False))).fetchone()["id"]
        imp, ts = card["feature_importance"], now()
        sec_rows, risk_rows = [], []
        for f in sectors["features"]:
            p = f["properties"]
            ring = f["geometry"]["coordinates"][0]
            lons, lats = [x[0] for x in ring], [x[1] for x in ring]
            area = (max(lats) - min(lats)) * 110.574 * (max(lons) - min(lons)) * 111.320 * math.cos(math.radians(sum(lats) / len(lats)))
            sec_rows.append((p["id"], p["id"], json.dumps(f["geometry"]), min(lats), min(lons), max(lats), max(lons), round(area, 2)))
            shap = p.get("shap") or dict(imp)
            top = [{"feature": k, "contribution": v, "value": p["peak_vals"][k]} for k, v in list(shap.items())[:3]]
            risk_rows.append((p["id"], ts, p["score"], p["max"], p["mean"], level_of(p["score"], th), run_id,
                              json.dumps(top, ensure_ascii=False), json.dumps(p, ensure_ascii=False)))
        con.executemany(f"INSERT INTO sectors(id, name, geometry, min_lat, min_lon, max_lat, max_lon, area_km2) VALUES (?,?,{con.geom_in},?,?,?,?,?)", sec_rows)
        con.executemany('INSERT INTO risk_scores(sector_id, "timestamp", score, max_score, mean_score, level, model_run_id, top_factors, details) '
                        "VALUES (?,?,?,?,?,?,?,?,?)", risk_rows)
        con.copy_features([(float(r.lat), float(r.lon), r.sector_id, float(r.elevation), float(r.slope), float(r.aspect), int(r.landcover),
                            r.landcover_name, float(r.risk_score), r.risk_level, run_id) for r in g.itertuples()])
        srcs = [
            ("inventory", "Landslide inventory (news + NASA Global Landslide Catalog)", "NASA GLC: public; news: cited", c["landslide_events"], 1, "labels"),
            ("terrain", "Copernicus DEM 30 m + ESA WorldCover 2021", "Copernicus DEM licence; CC BY 4.0", c["training_rows"], 1, "elevation, slope, aspect, land cover"),
            ("grid", "Point grid (~1 km)", "team", c["grid_points_with_features"], 1, "prediction cells"),
            ("rainfall", "Monthly rainfall by region 2009-2019", "team-supplied", c["rainfall_rows"], 0,
             f"{len(c['rainfall_regions_placeholder_coords'])} of {c['rainfall_regions']} regions have placeholder coordinates"),
            ("earthquakes", "USGS earthquake catalog", "USGS public domain", c["earthquakes"], 0,
             f"{c['earthquakes_in_study_area']} events inside the study area"),
            ("factors", "Conditioning-factor table (282 rows)", "unknown", c["conditioning_factor_rows"], 0, "F_NF column undocumented")]
        con.executemany("INSERT INTO data_sources(id, name, license, last_updated, status, records, used_in_model, note) VALUES (?,?,?,?,?,?,?,?)",
                        [(i, n, lic, card["trained_at"], "ok" if u else "not_used", rec, u, note) for i, n, lic, rec, u, note in srcs])
    con.commit()

    creds = {}
    for user, role, env in ROLES:
        pw = (os.environ.get(env) or "").strip()
        if not pw:
            if remote:
                continue  # حساب المشاهد اختياري على قاعدة بعيدة
            pw = secrets.token_urlsafe(9)
            creds[user] = pw
        add_user(con, user, pw, role)
    n = propose_alerts(con, run_id)
    audit(con, "system", "db.loaded", {"model_run_id": run_id, "sectors": len(sectors["features"]), "cells": len(g), "alerts_proposed": n,
                                      "backend": con.dialect})
    print(f"loaded {len(sectors['features'])} sectors, {len(g)} cells, {n} pending alerts -> {con.dialect}")
    for u, pw in creds.items():
        print(f"generated password for '{u}': {pw}")
    return con


if __name__ == "__main__":
    main()
