"""مِرصاد · 09 — جدول مميزات v2 وطبقات القطاعات وقرار النموذج (FR-A1، FR-U7).

المدخلات: مخرجات 08 في data/processed/public/ (terrain، soil، geology، rain) + جداول v1.
المخرجات:
- data/processed/training_table_v2.csv و grid_features_v2.csv.gz  (features_version = v2)
- data/processed/sector_layers.csv  (طبقات كل قطاع للخريطة وعتبة التنبؤ)
- data/processed/model_v2_decision.json  (مقارنة v1/v2 بنفس الطيّات وقرار الاعتماد)

قاعدة الاعتماد مكتوبة قبل التدريب ولا تتغير بعده (الخطة التنفيذية، برومبت مسار الذكاء الاصطناعي):
v2 يُعتمد فقط إذا ارتفع ROC-AUC المكاني ≥ 0.05، ولم ينخفض PR-AUC ولا الاستدعاء عند «مرتفع».
"""
import json, math
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, recall_score, precision_score

ROOT = Path(__file__).resolve().parents[1]
P, PUB, WEB = ROOT / "data" / "processed", ROOT / "data" / "processed" / "public", ROOT / "web" / "data"
SEED, BLOCK, SECTOR = 42, 0.5, 0.1
THRESHOLDS = {"medium": 0.40, "high": 0.60, "critical": 0.80}
LAYERS = ["terrain", "soil", "geology", "rain"]
LITH = ["plutonic", "volcanic", "volcano_sedimentary", "sedimentary"]
V1 = ["elevation", "slope", "aspect", "landcover"]
V2 = V1 + ["curv_profile", "curv_plan", "relief_1km", "slope_mean_1km", "soil_clay", "soil_sand", "soil_bdod",
           "rain_annual_mm", "rain_max1d_mm", "rain_p99_3d_mm"] + [f"lith_{c}" for c in LITH]
# مجموعات التفسير (Shapley على مستوى المجموعة) — مستخدمة في 05 عند اعتماد v2
GROUPS = {"elevation": ["elevation"], "slope": ["slope", "slope_mean_1km"], "relief": ["relief_1km"], "curvature": ["curv_profile", "curv_plan"],
          "aspect": ["aspect"], "landcover": ["landcover"], "soil": ["soil_clay", "soil_sand", "soil_bdod"],
          "geology": [f"lith_{c}" for c in LITH], "rain": ["rain_annual_mm", "rain_max1d_mm", "rain_p99_3d_mm"]}


def lith_onehot(df):
    for c in LITH:
        df[f"lith_{c}"] = np.where(df.lith_class.isna(), np.nan, (df.lith_class == c).astype(float))
    return df


def build():
    g = pd.read_csv(P / "grid_features.csv", encoding="utf-8-sig")
    t = pd.read_csv(P / "training_table.csv", encoding="utf-8-sig")
    for L in LAYERS:
        lg = pd.read_csv(PUB / f"{L}_grid.csv.gz")
        assert len(lg) == len(g), f"{L}: grid rows differ"
        g = pd.concat([g, lg], axis=1)
        t = t.merge(pd.read_csv(PUB / f"{L}_training.csv.gz"), on="point_id", how="left")
    g, t = lith_onehot(g), lith_onehot(t)
    g["features_version"] = t["features_version"] = "v2"
    t.to_csv(P / "training_table_v2.csv", index=False, encoding="utf-8-sig")
    g.to_csv(P / "grid_features_v2.csv.gz", index=False, encoding="utf-8-sig", float_format="%.4g")
    return g, t


def sector_layers(g):
    g = g.assign(si=np.floor(g.lat / SECTOR).astype(int), sj=np.floor(g.lon / SECTOR).astype(int))
    geo = pd.read_csv(PUB / "geology_sectors.csv.gz")
    out = []
    for (si, sj), c in g.groupby(["si", "sj"]):
        sid = f"S{si:03d}-{sj:03d}"
        r = {"sector_id": sid}
        for col, fn in (("rain_annual_mm", "mean"), ("rain_max1d_mm", "mean"), ("rain_p95_3d_mm", "mean"), ("rain_p99_3d_mm", "mean"),
                        ("soil_clay", "mean"), ("soil_sand", "mean"), ("relief_1km", "mean"), ("curv_plan", "mean")):
            v = getattr(c[col], fn)()
            r[col] = None if pd.isna(v) else round(float(v), 2 if col.startswith("curv") else 1)
        out.append(r)
    s = pd.DataFrame(out).merge(geo[["sector_id", "lith_class", "lith_text", "age_ma"]], on="sector_id", how="left")
    s.to_csv(P / "sector_layers.csv", index=False, encoding="utf-8-sig")
    return s


def compare(t):
    y = t.landslide.values
    groups = (np.floor(t.lat / BLOCK).astype(int).astype(str) + "_" + np.floor(t.lon / BLOCK).astype(int).astype(str)).values
    def oof(cols):
        X = t[cols].values.astype(float); p = np.zeros(len(y))
        for a, b in GroupKFold(n_splits=5).split(X, y, groups):
            m = RandomForestClassifier(n_estimators=500, min_samples_leaf=20, class_weight="balanced", random_state=SEED, n_jobs=-1)
            p[b] = m.fit(X[a], y[a]).predict_proba(X[b])[:, 1]
        return p
    def met(p):
        out = {"roc_auc": round(float(roc_auc_score(y, p)), 3), "pr_auc": round(float(average_precision_score(y, p)), 3)}
        for k in ("high", "critical"):
            pr = (p >= THRESHOLDS[k]).astype(int)
            out[f"recall_at_{k}"] = round(float(recall_score(y, pr)), 3)
            out[f"precision_at_{k}"] = round(float(precision_score(y, pr, zero_division=0)), 3)
        return out
    v1, v2 = met(oof(V1)), met(oof(V2))
    ablation = {name: met(oof(V1 + [c for c in cols if c not in V1]))["roc_auc"] for name, cols in GROUPS.items() if not set(cols) <= set(V1)}
    adopt = v2["roc_auc"] >= v1["roc_auc"] + 0.05 and v2["pr_auc"] >= v1["pr_auc"] and v2["recall_at_high"] >= v1["recall_at_high"]
    dec = {"rule": "adopt v2 only if spatial ROC-AUC rises by >= 0.05 and neither PR-AUC nor recall at 'high' falls (rule fixed before training)",
           "method": f"RandomForest(500, min_samples_leaf=20, balanced), GroupKFold(5) on {BLOCK}-degree blocks, seed {SEED}; same folds for v1 and v2",
           "features_v1": V1, "features_v2": V2, "groups": GROUPS, "v1": v1, "v2": v2,
           "ablation_roc_auc_v1_plus_group": ablation, "adopt_v2": bool(adopt),
           "rows": int(len(y)), "positives": int(y.sum())}
    (P / "model_v2_decision.json").write_text(json.dumps(dec, ensure_ascii=False, indent=2), encoding="utf-8")
    return dec


if __name__ == "__main__":
    g, t = build()
    s = sector_layers(g)
    d = compare(t)
    print(json.dumps({"sectors_with_rain_threshold": int(s.rain_p99_3d_mm.notna().sum()), "v1": d["v1"], "v2": d["v2"],
                      "adopt_v2": d["adopt_v2"], "ablation": d["ablation_roc_auc_v1_plus_group"]}, indent=2))
