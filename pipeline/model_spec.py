"""مِرصاد · مواصفة النموذج المعتمد (مصدر واحد لـ03 و05 و06 وتحميل القاعدة).

v2 يُستخدم فقط إذا قرر 09 اعتماده (data/processed/model_v2_decision.json → adopt_v2 = true)، وإلا يبقى v1.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
V1 = ["elevation", "slope", "aspect", "landcover"]


def spec():
    d = P / "model_v2_decision.json"
    dec = json.loads(d.read_text(encoding="utf-8")) if d.exists() else {}
    if dec.get("adopt_v2") and (P / "grid_features_v2.csv.gz").exists():
        return {"version": "v2", "features": dec["features_v2"], "groups": dec["groups"],
                "training": P / "training_table_v2.csv", "grid": P / "grid_features_v2.csv.gz", "decision": dec}
    return {"version": "v1", "features": V1, "groups": {f: [f] for f in V1},
            "training": P / "training_table.csv", "grid": P / "grid_features.csv", "decision": dec}
