"""مِرصاد · تنظيف البيانات المرسلة من الفريق.

يقرأ من data/raw ويكتب إلى data/processed. لا يضيف أي مصدر بيانات جديد.
التشغيل:  python pipeline/02_clean_data.py
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
STUDY = {"lat_min": 16.2, "lat_max": 20.5, "lon_min": 40.6, "lon_max": 44.1}
report = {}

# 1) سجل الانهيارات ---------------------------------------------------------
ls = pd.read_csv(RAW / "landslide_points_clean.csv", encoding="utf-8-sig")
glc = pd.read_csv(RAW / "landslide_points_nasa_glc.csv", encoding="utf-8-sig")
ls = ls.drop_duplicates()
ls = ls.merge(glc[["point_id", "landslide_trigger", "landslide_size", "fatality_count", "source"]],
              on="point_id", how="left")
ls["source"] = ls["source"].fillna("News reports")
ls["usable_for_terrain"] = ~ls["point_id"].str.startswith("GLC")  # نقاط NASA تقريبية 25–50 كم
ls.to_csv(OUT / "landslide_inventory.csv", index=False, encoding="utf-8-sig")
report["landslide_events"] = int(len(ls))
report["landslide_unique_locations_usable"] = int(
    ls[ls.usable_for_terrain].drop_duplicates(["lat", "lon"]).shape[0])

# 2) جدول التدريب -----------------------------------------------------------
tr = pd.read_csv(RAW / "training_table.csv", encoding="utf-8-sig")
before = len(tr)
tr = tr.drop_duplicates(subset=["lat", "lon"])
tr = tr.dropna(subset=["elevation", "slope", "aspect", "landcover"])
tr["landcover"] = tr["landcover"].astype(int)
not_in_inventory = sorted(set(tr.loc[tr.landslide == 1, "point_id"]) - set(ls.point_id))
tr.to_csv(OUT / "training_table.csv", index=False, encoding="utf-8-sig")
report["training_rows"] = int(len(tr))
report["training_rows_removed"] = int(before - len(tr))
report["training_positives"] = int(tr.landslide.sum())
report["training_negatives"] = int((tr.landslide == 0).sum())
report["positives_not_in_inventory"] = not_in_inventory

# 3) شبكة التنبؤ بخصائصها (من risk_scores الأصلي، بدون الدرجة القديمة) --------
rs = pd.read_csv(RAW / "risk_scores_original.csv", encoding="utf-8-sig")
grid = rs.drop(columns=["risk_score", "risk_level"]).drop_duplicates(subset=["lat", "lon"])
grid = grid.dropna(subset=["elevation", "slope", "aspect", "landcover"])
grid["landcover"] = grid["landcover"].astype(int)
grid.to_csv(OUT / "grid_features.csv", index=False, encoding="utf-8-sig")
allgrid = pd.read_csv(RAW / "grid_points.csv").drop_duplicates()
report["grid_points_total"] = int(len(allgrid))
report["grid_points_with_features"] = int(len(grid))

# 4) الأمطار: فصل الجدولين المدموجين في ملف واحد ------------------------------
rain_fixed = pd.read_excel(RAW / "All_Saudi_Rainfall_Fixed.xlsx")
rain_fixed = rain_fixed.dropna(subset=["Region", "Total Rainfall (mm)"]).drop_duplicates()
rain_fixed["Year"] = rain_fixed["Year"].astype(int)
rain_fixed.to_csv(OUT / "rainfall_monthly_by_region.csv", index=False, encoding="utf-8-sig")
comb = pd.read_excel(RAW / "All_Saudi_Rainfall_Combined_Final.xlsx")
factors = comb[comb["F_NF"].notna()].drop(
    columns=["Year", "Month", "Region", "lat", "lon", "Total Rainfall (mm)",
             "Year;Month;Region;Total Rainfall (mm)"])
factors.to_csv(OUT / "conditioning_factors_282.csv", index=False, encoding="utf-8-sig")
coords = comb.dropna(subset=["Region"]).groupby("Region")[["lat", "lon"]].first()
placeholder = coords[(coords.lat == 24.0) & (coords.lon == 45.0)].index.tolist()
report["rainfall_rows"] = int(len(rain_fixed))
report["rainfall_years"] = [int(rain_fixed.Year.min()), int(rain_fixed.Year.max())]
report["rainfall_regions"] = int(rain_fixed.Region.nunique())
report["rainfall_regions_placeholder_coords"] = placeholder
report["conditioning_factor_rows"] = int(len(factors))

# 5) الزلازل ---------------------------------------------------------------
eq = pd.read_csv(RAW / "earthquakes_usgs_query.csv").drop_duplicates(subset=["id"])
eq.to_csv(OUT / "earthquakes_usgs.csv", index=False, encoding="utf-8-sig")
inside = eq[eq.latitude.between(STUDY["lat_min"], STUDY["lat_max"])
            & eq.longitude.between(STUDY["lon_min"], STUDY["lon_max"])]
report["earthquakes"] = int(len(eq))
report["earthquakes_in_study_area"] = int(len(inside))

report["study_area"] = STUDY
(OUT / "cleaning_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
