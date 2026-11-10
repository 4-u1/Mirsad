"""مِرصاد · 07 — شبكة عصبية بـ TensorFlow (Keras) ومقارنتها بالنموذج الأساسي (FR-A3).

- نفس جدول التدريب ونفس المميزات الأربع ونفس التحقق المكاني (GroupKFold(5) على كتل 0.5°)
  المستخدمة في 03 و05، فالأرقام قابلة للمقارنة مباشرة مع Random Forest وMLP.
- نفس بنية MLP في 05: طبقتان (16، 8) بتنشيط ReLU وتنظيم L2 = 0.01، والحالات الإيجابية
  مكررة داخل طيّات التدريب فقط. المعايرة (StandardScaler) تُحسب على طيّة التدريب فقط.
- حتمي: بذرة ثابتة وعمليات حتمية.
- المخرج: data/processed/tensorflow_comparison.json

التشغيل:  pip install tensorflow-cpu  ثم  python pipeline/07_tensorflow_compare.py
(يعمل تلقائيًا في سير العمل .github/workflows/tensorflow.yml)
"""
import json, os, platform
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf

ROOT = Path(__file__).resolve().parents[1]
P, MD = ROOT / "data" / "processed", ROOT / "model"
SEED, BLOCK, EPOCHS = 42, 0.5, 150
FEATURES = ["elevation", "slope", "aspect", "landcover"]
THRESHOLDS = {"high": 0.60, "critical": 0.80}
tf.keras.utils.set_random_seed(SEED)
tf.config.experimental.enable_op_determinism()

tr = pd.read_csv(P / "training_table.csv", encoding="utf-8-sig")
X, y = tr[FEATURES].values.astype("float32"), tr["landslide"].values.astype("float32")
groups = (np.floor(tr.lat / BLOCK).astype(int).astype(str) + "_" + np.floor(tr.lon / BLOCK).astype(int).astype(str)).values

def build():
    reg = tf.keras.regularizers.l2(1e-2)
    m = tf.keras.Sequential([tf.keras.Input(shape=(len(FEATURES),)),
                             tf.keras.layers.Dense(16, activation="relu", kernel_regularizer=reg),
                             tf.keras.layers.Dense(8, activation="relu", kernel_regularizer=reg),
                             tf.keras.layers.Dense(1, activation="sigmoid")])
    m.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="binary_crossentropy")
    return m

def metrics(p):
    out = {"roc_auc": round(float(roc_auc_score(y, p)), 3), "pr_auc": round(float(average_precision_score(y, p)), 3)}
    for k, t in THRESHOLDS.items():
        pr = (p >= t).astype(int)
        out[f"recall_at_{k}"] = round(float(recall_score(y, pr)), 3)
        out[f"precision_at_{k}"] = round(float(precision_score(y, pr, zero_division=0)), 3)
    return out

p = np.zeros(len(y)); folds = []
for i, (a, b) in enumerate(GroupKFold(n_splits=5).split(X, y, groups)):
    Xa, ya = X[a], y[a]
    pos = np.where(ya == 1)[0]
    if len(pos):  # تكرار الإيجابيات في التدريب فقط (مثل 05)
        k = max(1, int((ya == 0).sum()) // len(pos))
        Xa, ya = np.vstack([Xa] + [Xa[pos]] * (k - 1)), np.concatenate([ya] + [ya[pos]] * (k - 1))
    sc = StandardScaler().fit(Xa)
    m = build()
    m.fit(sc.transform(Xa), ya, epochs=EPOCHS, batch_size=256, shuffle=True, verbose=0)
    p[b] = m.predict(sc.transform(X[b]), verbose=0).ravel()
    folds.append({"fold": i + 1, "test_rows": int(len(b)), "test_positives": int(y[b].sum())})

card = json.loads((MD / "model_card.json").read_text(encoding="utf-8"))
cmp = card.get("comparisons", {})
tf_m = metrics(p)
rf = cmp.get("random_forest_baseline", {})
better = tf_m["roc_auc"] > rf.get("roc_auc", 0) + 0.05
res = {
    "requirement": "FR-A3",
    "method": f"GroupKFold(5) on {BLOCK}° blocks, same folds as 03/05",
    "framework": f"TensorFlow {tf.__version__} (Keras), Python {platform.python_version()}",
    "architecture": "Dense(16, relu) → Dense(8, relu) → Dense(1, sigmoid); L2=0.01; Adam 1e-3; "
                    f"{EPOCHS} epochs, batch 256; positives oversampled in training folds; StandardScaler per fold",
    "seed": SEED, "rows": int(len(y)), "positives": int(y.sum()), "folds": folds,
    "tensorflow_mlp": tf_m,
    "random_forest_baseline": rf,
    "sklearn_mlp": cmp.get("neural_network_mlp", {}),
    "slope_only_logistic_spatial_auc": card.get("reference_slope_only_logistic_spatial_auc"),
    "decision": ("TensorFlow model is clearly better (> +0.05 ROC-AUC): review before adopting."
                 if better else
                 "Random Forest baseline kept: the TensorFlow network is not clearly better (PRD 12.3: adopt the simpler model when performance is equal)."),
}
(P / "tensorflow_comparison.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"tensorflow_mlp": tf_m, "random_forest": rf, "decision": res["decision"]}, indent=2))
