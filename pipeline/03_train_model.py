"""مِرصاد · تدريب نموذج القابلية للانهيار وتوليد طبقة الخطر.

- المدخلات: data/processed/training_table.csv و grid_features.csv فقط.
- المميزات: نفس مميزات الفريق (elevation, slope, aspect, landcover).
- النموذج: Random Forest كنموذج أساسي (PRD · A-FR2) بأوزان فئات متوازنة.
- التقييم: تحقق متقاطع مكاني بكتل 0.5° (PRD · A-FR4) مقابل تقسيم عشوائي للمقارنة.
- المستويات: عتبات الـPRD (0.40 / 0.60 / 0.80).
التشغيل:  python pipeline/03_train_model.py
"""
from pathlib import Path
import json, datetime
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, average_precision_score, recall_score, precision_score

ROOT = Path(__file__).resolve().parents[1]
P, MODEL_DIR, WEB = ROOT / "data" / "processed", ROOT / "model", ROOT / "web" / "data"
MODEL_DIR.mkdir(exist_ok=True); WEB.mkdir(parents=True, exist_ok=True)
SEED = 42
import sys; sys.path.insert(0, str(ROOT / "pipeline"))
from model_spec import spec  # noqa: E402
SPEC = spec(); VERSION = SPEC["version"]
FEATURES = SPEC["features"]   # v1: مميزات الفريق الأربع · v2: + الطبقات العامة (09)
THRESHOLDS = {"medium": 0.40, "high": 0.60, "critical": 0.80}   # PRD 13.1
LEVELS = ["low", "medium", "high", "critical"]
BLOCK = 0.5          # حجم الكتلة المكانية بالدرجات للتحقق المتقاطع
SECTOR = 0.1         # حجم القطاع المعروض في الواجهة بالدرجات (~11 كم)
SECTOR_Q = 0.90      # درجة القطاع = المئين 90 لدرجات خلاياه (أقل حساسية لخلية شاذة واحدة من القيمة القصوى)

def level(s):
    return np.select([s >= THRESHOLDS["critical"], s >= THRESHOLDS["high"], s >= THRESHOLDS["medium"]],
                     ["critical", "high", "medium"], "low")

def make_model():
    return RandomForestClassifier(n_estimators=500, min_samples_leaf=20, class_weight="balanced",
                                  random_state=SEED, n_jobs=-1)

tr = pd.read_csv(SPEC["training"], encoding="utf-8-sig")
X, y = tr[FEATURES].values, tr["landslide"].values
groups = (np.floor(tr.lat / BLOCK).astype(int).astype(str) + "_" + np.floor(tr.lon / BLOCK).astype(int).astype(str)).values

def oof(splitter, use_groups):
    p = np.zeros(len(y))
    it = splitter.split(X, y, groups) if use_groups else splitter.split(X, y)
    for a, b in it:
        m = make_model().fit(X[a], y[a]); p[b] = m.predict_proba(X[b])[:, 1]
    return p

def metrics(p):
    pred_high = (p >= THRESHOLDS["high"]).astype(int)
    pred_crit = (p >= THRESHOLDS["critical"]).astype(int)
    return {"roc_auc": round(float(roc_auc_score(y, p)), 3),
            "pr_auc": round(float(average_precision_score(y, p)), 3),
            "recall_at_high": round(float(recall_score(y, pred_high)), 3),
            "precision_at_high": round(float(precision_score(y, pred_high, zero_division=0)), 3),
            "recall_at_critical": round(float(recall_score(y, pred_crit)), 3),
            "precision_at_critical": round(float(precision_score(y, pred_crit, zero_division=0)), 3)}

p_spatial = oof(GroupKFold(n_splits=5), True)
p_random = oof(StratifiedKFold(n_splits=4, shuffle=True, random_state=SEED), False)
m_spatial, m_random = metrics(p_spatial), metrics(p_random)
# مقارنة مرجعية فقط (غير معتمدة): انحدار لوجستي على الانحدار وحده
_p = np.zeros(len(y)); _X = tr[["slope"]].values
for a, b in GroupKFold(n_splits=5).split(_X, y, groups):
    _p[b] = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced")).fit(_X[a], y[a]).predict_proba(_X[b])[:, 1]
ref_slope_lr = round(float(roc_auc_score(y, _p)), 3)

model = make_model().fit(X, y)
joblib.dump(model, MODEL_DIR / f"mirsad_rf_{VERSION}.joblib")
importance = dict(sorted(zip(FEATURES, map(lambda v: round(float(v), 3), model.feature_importances_)),
                         key=lambda kv: -kv[1]))

# التنبؤ على الشبكة ---------------------------------------------------------
g = pd.read_csv(SPEC["grid"], encoding="utf-8-sig")
g["risk_score"] = model.predict_proba(g[FEATURES].values)[:, 1].round(3)
g["risk_level"] = level(g["risk_score"].values)
g[["lat", "lon", "elevation", "slope", "aspect", "landcover", "landcover_name", "risk_score", "risk_level"]].to_csv(
    P / f"risk_scores_{VERSION}.csv", index=False, encoding="utf-8-sig")
dist = g["risk_level"].value_counts().reindex(LEVELS, fill_value=0).astype(int).to_dict()

# القطاعات للواجهة ------------------------------------------------------------
g["si"] = np.floor(g.lat / SECTOR).astype(int); g["sj"] = np.floor(g.lon / SECTOR).astype(int)
pos = tr[tr.landslide == 1]
_lay = P / "sector_layers.csv"
LAY = pd.read_csv(_lay, encoding="utf-8-sig").set_index("sector_id") if _lay.exists() else pd.DataFrame()
features, sectors = [], []
for (si, sj), c in g.groupby(["si", "sj"]):
    lat0, lon0 = si * SECTOR, sj * SECTOR
    top = c.loc[c.risk_score.idxmax()]
    lc = c.landcover_name.mode().iat[0]
    counts = c.risk_level.value_counts().reindex(LEVELS, fill_value=0).astype(int).tolist()
    sid = f"S{si:03d}-{sj:03d}"
    inside = pos[(pos.lat >= lat0) & (pos.lat < lat0 + SECTOR) & (pos.lon >= lon0) & (pos.lon < lon0 + SECTOR)]
    sscore = float(c.risk_score.quantile(SECTOR_Q))
    props = {"id": sid, "score": round(sscore, 3), "max": round(float(c.risk_score.max()), 3), "mean": round(float(c.risk_score.mean()), 3),
             "level": str(level(np.array([sscore]))[0]), "cells": int(len(c)), "counts": counts,
             "elev": int(round(c.elevation.mean())), "slope_mean": round(float(c.slope.mean()), 1),
             "slope_max": round(float(c.slope.max()), 1), "landcover": lc,
             "peak": [round(float(top.lat), 5), round(float(top.lon), 5)],
             "peak_vals": {"elevation": int(top.elevation), "slope": float(top.slope), "aspect": float(top.aspect),
                           "landcover": str(top.landcover_name)},
             "events": int(len(inside))}
    if sid in LAY.index:  # طبقات البيانات العامة للخريطة (FR-U7) وعتبة التنبؤ (FR-U6)
        props.update({k: (None if pd.isna(v) else v) for k, v in LAY.loc[sid].items()})
    ring = [[lon0, lat0], [lon0 + SECTOR, lat0], [lon0 + SECTOR, lat0 + SECTOR], [lon0, lat0 + SECTOR], [lon0, lat0]]
    features.append({"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[round(a, 4), round(b, 4)] for a, b in ring]]},
                     "properties": props})
(WEB / "sectors.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                                ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
# خلايا 1 كم (مضغوطة): [lat, lon, score]
cells = g[["lat", "lon", "risk_score"]].round({"lat": 4, "lon": 4, "risk_score": 3}).values.tolist()
(WEB / "cells.json").write_text(json.dumps(cells, separators=(",", ":")), encoding="utf-8")

inv = pd.read_csv(P / "landslide_inventory.csv", encoding="utf-8-sig")
(WEB / "landslides.json").write_text(json.dumps(inv[["point_id", "event_date", "region", "place", "lat", "lon",
    "location_precision", "usable_for_terrain"]].fillna("").to_dict("records"), ensure_ascii=False), encoding="utf-8")
rain = pd.read_csv(P / "rainfall_monthly_by_region.csv", encoding="utf-8-sig")
rain_y = rain.groupby(["Region", "Year"])["Total Rainfall (mm)"].sum().round(1).reset_index()
(WEB / "rainfall.json").write_text(json.dumps(rain_y.rename(columns={"Total Rainfall (mm)": "mm"}).to_dict("records"),
                                              ensure_ascii=False), encoding="utf-8")

clean = json.loads((P / "cleaning_report.json").read_text(encoding="utf-8"))
card = {"version": VERSION, "risk_scores_file": f"risk_scores_{VERSION}.csv", "trained_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "algorithm": "RandomForestClassifier (n_estimators=500, min_samples_leaf=20, class_weight=balanced)",
        "seed": SEED, "features": FEATURES, "feature_groups": SPEC["groups"], "thresholds": THRESHOLDS,
        "training": {"rows": int(len(tr)), "positives": int(y.sum()), "negatives": int((y == 0).sum())},
        "spatial_cv": {"method": f"GroupKFold(5) on {BLOCK}° blocks", **m_spatial},
        "random_cv": {"method": "StratifiedKFold(4), for comparison only", **m_random},
        "reference_slope_only_logistic_spatial_auc": ref_slope_lr,
        "feature_importance": importance, "sector_rule": f"sector score = P{int(SECTOR_Q*100)} of its 1 km cell scores", "grid_cells": int(len(g)), "sectors": len(features),
        "v1_v2_comparison": SPEC["decision"] or None, "level_distribution": dist, "sector_levels": pd.Series([f["properties"]["level"] for f in features]).value_counts().reindex(LEVELS, fill_value=0).astype(int).to_dict(), "cleaning": clean}
pub = {}
for k in ("rain", "soil", "geology", "terrain"):  # الطبقات العامة (08): المصدر والترخيص والتغطية
    f = P / "public" / f"{k}_meta.json"
    if f.exists():
        mm = json.loads(f.read_text(encoding="utf-8")); cov = mm.get("coverage_grid") or {"x": 0}
        pub[k] = {"source": mm["source"], "url": mm.get("url"), "license": mm.get("license"), "generated_at": mm.get("generated_at"),
                  "coverage": round(min(cov.values()), 4), "cells": int(round(min(cov.values()) * len(g))),
                  "used": any(c in FEATURES for c in (mm.get("columns") or [])) or (VERSION == "v2")}
card["public_data"] = pub
(MODEL_DIR / "model_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
(WEB / "model.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: card[k] for k in ["training", "spatial_cv", "random_cv", "feature_importance", "level_distribution", "sectors"]}, indent=2))
