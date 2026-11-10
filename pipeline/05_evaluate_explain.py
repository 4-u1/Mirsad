"""مِرصاد · المقارنات والتفسير والمعايرة (PRD · D-FR2, A-FR3, A-FR5, 12.3).

1) مميزات زلزالية من كتالوج USGS (المسافة لأقرب زلزال، العدد والقوة القصوى ضمن 200 كم) وتقييم أثرها.
2) شبكة عصبية (MLP) ومقارنتها بالنموذج الأساسي بنفس التحقق المكاني.
   ملاحظة: الـPRD يذكر TensorFlow؛ في بيئة البناء لا يتوفر TensorFlow فاستُخدم MLPClassifier من scikit-learn.
3) معايرة الاحتمالات (Isotonic على تنبؤات التحقق المكاني) مع Brier score.
4) قيم Shapley الدقيقة لكل قطاع (4 مميزات = 16 تركيبة) على الخلية الأعلى خطرًا في القطاع.
التشغيل بعد 03:  python pipeline/05_evaluate_explain.py
"""
from pathlib import Path
from itertools import combinations
from math import factorial
import json
import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.isotonic import IsotonicRegression

ROOT = Path(__file__).resolve().parents[1]
P, MD, WEB = ROOT / "data" / "processed", ROOT / "model", ROOT / "web" / "data"
SEED, BLOCK = 42, 0.5
FEATURES = ["elevation", "slope", "aspect", "landcover"]
rng = np.random.default_rng(SEED)

tr = pd.read_csv(P / "training_table.csv", encoding="utf-8-sig")
y = tr["landslide"].values
groups = (np.floor(tr.lat / BLOCK).astype(int).astype(str) + "_" + np.floor(tr.lon / BLOCK).astype(int).astype(str)).values
card = json.loads((MD / "model_card.json").read_text(encoding="utf-8"))
model = joblib.load(MD / "mirsad_rf_v1.joblib")

def rf():
    return RandomForestClassifier(n_estimators=500, min_samples_leaf=20, class_weight="balanced", random_state=SEED, n_jobs=-1)

def spatial_oof(make, X, oversample=False):
    p = np.zeros(len(y))
    for a, b in GroupKFold(n_splits=5).split(X, y, groups):
        Xa, ya = X[a], y[a]
        if oversample:  # MLP لا يدعم أوزان الفئات: تكرار الحالات الإيجابية في التدريب فقط
            pos = np.where(ya == 1)[0]
            if len(pos):
                k = max(1, (ya == 0).sum() // len(pos))
                Xa = np.vstack([Xa] + [Xa[pos]] * (k - 1)); ya = np.concatenate([ya] + [ya[pos]] * (k - 1))
        p[b] = make().fit(Xa, ya).predict_proba(X[b])[:, 1]
    return p

def m(p):
    return {"roc_auc": round(float(roc_auc_score(y, p)), 3), "pr_auc": round(float(average_precision_score(y, p)), 3)}

# 1) المميزات الزلزالية --------------------------------------------------------
eq = pd.read_csv(P / "earthquakes_usgs.csv", encoding="utf-8-sig")
def seismic(lat, lon):
    la1, lo1 = np.radians(lat)[:, None], np.radians(lon)[:, None]
    la2, lo2 = np.radians(eq.latitude.values)[None], np.radians(eq.longitude.values)[None]
    d = 6371 * 2 * np.arcsin(np.sqrt(np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2))
    near = d <= 200
    mags = np.where(near, eq.mag.values[None], 0)
    return pd.DataFrame({"eq_dist_km": d.min(1).round(1), "eq_count_200km": near.sum(1), "eq_maxmag_200km": mags.max(1).round(1)})
tr_s = pd.concat([tr, seismic(tr.lat.values, tr.lon.values)], axis=1)
tr_s[["point_id", "lat", "lon", "eq_dist_km", "eq_count_200km", "eq_maxmag_200km"]].to_csv(P / "seismic_features_training.csv", index=False, encoding="utf-8-sig")
SEIS = FEATURES + ["eq_dist_km", "eq_count_200km", "eq_maxmag_200km"]

p_base = spatial_oof(rf, tr[FEATURES].values)
p_seis = spatial_oof(rf, tr_s[SEIS].values)
p_mlp = spatial_oof(lambda: make_pipeline(StandardScaler(), MLPClassifier(hidden_layer_sizes=(16, 8), alpha=1e-2, max_iter=600, random_state=SEED)),
                    tr[FEATURES].values, oversample=True)

# 3) المعايرة -------------------------------------------------------------------
iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p_base, y)
p_cal = iso.predict(p_base)
joblib.dump(iso, MD / "calibrator_isotonic_v1.joblib")
calib = {"method": "Isotonic regression fitted on spatial-CV out-of-fold scores",
         "brier_raw": round(float(brier_score_loss(y, p_base)), 4), "brier_calibrated": round(float(brier_score_loss(y, p_cal)), 4),
         "base_rate": round(float(y.mean()), 4),
         "note": "With 12 positives the calibrated probability is near the base rate everywhere; levels keep using the relative score (PRD 13.1 thresholds)."}

# 4) Shapley لكل قطاع -------------------------------------------------------------
sectors = json.loads((WEB / "sectors.geojson").read_text(encoding="utf-8"))
X_sec = np.array([[f["properties"]["peak_vals"]["elevation"], f["properties"]["peak_vals"]["slope"], f["properties"]["peak_vals"]["aspect"],
                   0] for f in sectors["features"]], dtype=float)
g = pd.read_csv(P / "risk_scores_v1.csv", encoding="utf-8-sig")
key = g.set_index(["lat", "lon"])["landcover"]
for k, f in enumerate(sectors["features"]):
    la, lo = f["properties"]["peak"]
    X_sec[k, 3] = key.get((round(la, 5), round(lo, 5)), np.nan) if (round(la, 5), round(lo, 5)) in key.index else np.nan
miss = np.isnan(X_sec[:, 3])
if miss.any():  # مطابقة أقرب خلية إن اختلف التقريب
    for k in np.where(miss)[0]:
        la, lo = sectors["features"][k]["properties"]["peak"]
        j = ((g.lat - la) ** 2 + (g.lon - lo) ** 2).idxmin(); X_sec[k, 3] = g.landcover[j]
bg = tr[FEATURES].sample(n=100, random_state=SEED).values
n, F = len(X_sec), len(FEATURES)
subsets = [frozenset(c) for r in range(F + 1) for c in combinations(range(F), r)]
rows = np.empty((n, len(subsets), len(bg), F))
for si, S in enumerate(subsets):
    for j in range(F):
        rows[:, si, :, j] = X_sec[:, None, j] if j in S else bg[None, :, j]
pred = model.predict_proba(rows.reshape(-1, F))[:, 1].reshape(n, len(subsets), len(bg)).mean(2)
v = {S: pred[:, si] for si, S in enumerate(subsets)}
phi = np.zeros((n, F))
for i in range(F):
    for S in subsets:
        if i in S: continue
        w = factorial(len(S)) * factorial(F - len(S) - 1) / factorial(F)
        phi[:, i] += w * (v[S | {i}] - v[S])
base = float(v[frozenset()].mean())
for k, f in enumerate(sectors["features"]):
    contrib = {FEATURES[i]: round(float(phi[k, i]), 4) for i in range(F)}
    f["properties"]["shap"] = dict(sorted(contrib.items(), key=lambda kv: -abs(kv[1])))
    f["properties"]["shap_base"] = round(base, 4)
    f["properties"]["calibrated"] = round(float(iso.predict([f["properties"]["score"]])[0]), 4)
(WEB / "sectors.geojson").write_text(json.dumps(sectors, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
check = float(np.abs(phi.sum(1) + base - v[frozenset(range(F))]).max())

card["comparisons"] = {
    "method": "GroupKFold(5) on 0.5° blocks, same folds for all",
    "random_forest_baseline": m(p_base),
    "random_forest_plus_seismic": m(p_seis),
    "neural_network_mlp": {**m(p_mlp), "architecture": "MLP(16, 8), alpha=0.01, positives oversampled in training folds",
                           "note": "Same architecture as the TensorFlow network (07_tensorflow_compare.py, run on GitHub Actions)."},
    "decision": "Baseline Random Forest kept (PRD 12.3: adopt the simpler model when performance is not clearly better)."}
_tf = P / "tensorflow_comparison.json"  # ناتج 07 على GitHub Actions (FR-A3)
if _tf.exists():
    _t = json.loads(_tf.read_text(encoding="utf-8"))
    card["comparisons"]["neural_network_tensorflow"] = {"roc_auc": _t["tensorflow_mlp"]["roc_auc"], "pr_auc": _t["tensorflow_mlp"]["pr_auc"],
                                                        "framework": _t["framework"], "architecture": _t["architecture"], "run": _t.get("workflow_run")}
card["seismic_features"] = {"features": ["eq_dist_km", "eq_count_200km", "eq_maxmag_200km"],
                            "training_eq_dist_km_min": float(tr_s.eq_dist_km.min()),
                            "training_points_with_quake_within_200km": int((tr_s.eq_count_200km > 0).sum()),
                            "adopted": False, "reason": "No earthquake inside the study area; distances mostly encode latitude, not seismic hazard."}
card["calibration"] = calib
card["explanations"] = {"method": "Exact interventional Shapley values (4 features, 16 coalitions) at each sector's highest-risk cell, 100-row background",
                        "base_value": round(base, 4), "additivity_max_error": round(check, 6)}
card["quality"] = json.loads((P / "quality_report.json").read_text(encoding="utf-8"))["status"]
(MD / "model_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")
(WEB / "model.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: card[k] for k in ["comparisons", "seismic_features", "calibration", "explanations"]}, ensure_ascii=False, indent=1))
