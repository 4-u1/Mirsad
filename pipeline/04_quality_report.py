"""مِرصاد · فحص جودة البيانات الآلي (PRD · D-FR6).

يفحص: القيم المفقودة، النطاقات المنطقية، القيم الشاذة، التكرار، نظام الإحداثيات، تطابق الامتدادات، توازن الفئات.
التشغيل:  python pipeline/04_quality_report.py   → data/processed/quality_report.json
"""
from pathlib import Path
import json, re
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P, RAW = ROOT / "data" / "processed", ROOT / "data" / "raw"
STUDY = json.loads((P / "cleaning_report.json").read_text(encoding="utf-8"))["study_area"]
RANGES = {"lat": (STUDY["lat_min"], STUDY["lat_max"]), "lon": (STUDY["lon_min"], STUDY["lon_max"]),
          "elevation": (-100, 4000), "slope": (0, 90), "aspect": (-1, 360)}
LC_CODES = {10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100}

def check(name, df, cols):
    out = {"rows": int(len(df)), "missing": {c: int(df[c].isna().sum()) for c in cols if c in df},
           "duplicates_latlon": int(df.duplicated(["lat", "lon"]).sum())}
    rng = {}
    for c, (lo, hi) in RANGES.items():
        if c in df:
            bad = df[(df[c] < lo) | (df[c] > hi)]
            rng[c] = {"min": float(df[c].min()), "max": float(df[c].max()), "allowed": [lo, hi], "out_of_range": int(len(bad))}
    out["ranges"] = rng
    if "landcover" in df:
        out["landcover_invalid_codes"] = int((~df["landcover"].isin(LC_CODES)).sum())
    out["outliers_iqr"] = {}
    for c in ("elevation", "slope"):
        if c in df:
            q1, q3 = df[c].quantile([.25, .75]); iqr = q3 - q1
            out["outliers_iqr"][c] = int(((df[c] < q1 - 3 * iqr) | (df[c] > q3 + 3 * iqr)).sum())
    return out

tr = pd.read_csv(P / "training_table.csv", encoding="utf-8-sig")
gr = pd.read_csv(P / "grid_features.csv", encoding="utf-8-sig")
qmd = (RAW / "grid_points.qmd").read_text(encoding="utf-8")
crs = re.search(r"<authid>(.*?)</authid>", qmd).group(1)
report = {
    "training_table": check("training", tr, ["elevation", "slope", "aspect", "landcover", "landslide"]),
    "grid_features": check("grid", gr, ["elevation", "slope", "aspect", "landcover"]),
    "crs": {"grid_points.qmd": crs, "expected": "EPSG:4326", "match": crs == "EPSG:4326"},
    "extent_match": {"training_inside_grid_bbox": int(((tr.lat.between(gr.lat.min(), gr.lat.max())) & (tr.lon.between(gr.lon.min(), gr.lon.max()))).sum()),
                     "training_rows": int(len(tr))},
    "class_balance": {"positives": int(tr.landslide.sum()), "negatives": int((tr.landslide == 0).sum()),
                      "positive_rate": round(float(tr.landslide.mean()), 4)},
}
issues = []
for k in ("training_table", "grid_features"):
    for c, v in report[k]["missing"].items():
        if v: issues.append(f"{k}.{c}: {v} missing")
    for c, v in report[k]["ranges"].items():
        if v["out_of_range"]: issues.append(f"{k}.{c}: {v['out_of_range']} out of range")
    if report[k].get("landcover_invalid_codes"): issues.append(f"{k}.landcover: invalid codes")
if not report["crs"]["match"]: issues.append("CRS mismatch")
if report["class_balance"]["positives"] < 30: issues.append(f"only {report['class_balance']['positives']} positive labels (severe imbalance)")
report["issues"] = issues
report["status"] = "pass_with_warnings" if issues else "pass"
(P / "quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "issues": issues, "crs": report["crs"], "extent": report["extent_match"]}, ensure_ascii=False, indent=1))
