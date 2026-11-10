"""مِرصاد · 08 — جلب طبقات البيانات العامة المجانية وحساب قيمها عند كل نقطة (FR-D1، FR-D3، FR-D4).

يعمل على GitHub Actions (يحتاج إنترنت): .github/workflows/public-data.yml
كل طبقة أمر مستقل، فتعمل بالتوازي وتُعاد وحدها عند الفشل:

  python pipeline/08_fetch_public_data.py terrain   # Copernicus DEM GLO-30 (AWS): انحناء + تضرّس 1 كم
  python pipeline/08_fetch_public_data.py soil      # SoilGrids 2.0 (ISRIC WCS، 250 م): طين، رمل، طمي، كثافة ظاهرية
  python pipeline/08_fetch_public_data.py geology   # Macrostrat: نوع الصخر وعمره عند مركز كل قطاع
  python pipeline/08_fetch_public_data.py rain_chunk 2020 2025   # CHIRPS v2.0 يومي (NOAA ERDDAP، 0.05°؛ السلسلة اليومية عليه تبدأ 2020)
  python pipeline/08_fetch_public_data.py rain_merge <مجلد>       # مناخ الأمطار والقيم القصوى من كل الدفعات

المدخلات: data/processed/grid_features.csv (126,467 نقطة) و training_table.csv (1,689) و web/data/sectors.geojson
المخرجات: out/<layer>_grid.csv و out/<layer>_training.csv (و out/<layer>_sectors.csv) و out/<layer>_meta.json
القيم المفقودة تبقى فارغة ولا تُملأ بمتوسطات.
"""
import gzip, io, json, math, os, sys, time, urllib.parse, urllib.request
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT = Path(os.environ.get("MIRSAD_OUT", ROOT / "out")); OUT.mkdir(exist_ok=True, parents=True)
BBOX = dict(lat0=16.2, lat1=20.6, lon0=40.6, lon1=44.2)
UA = {"User-Agent": "mirsad-pipeline"}


def fetch(url, tries=4, timeout=600):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # إعادة المحاولة بمهلة متزايدة
            if k == tries - 1: raise
            print(f"retry {k + 1}: {e}", flush=True); time.sleep(5 * (k + 1))


def points():
    g = pd.read_csv(P / "grid_features.csv", encoding="utf-8-sig", usecols=["lat", "lon"])
    t = pd.read_csv(P / "training_table.csv", encoding="utf-8-sig", usecols=["point_id", "lat", "lon"])
    return g, t


def save(name, grid, train, meta, sectors=None):
    grid.to_csv(OUT / f"{name}_grid.csv", index=False, float_format="%.4g")
    train.to_csv(OUT / f"{name}_training.csv", index=False, float_format="%.4g")
    if sectors is not None: sectors.to_csv(OUT / f"{name}_sectors.csv", index=False, float_format="%.4g")
    meta["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    meta["coverage_grid"] = {c: round(float(grid[c].notna().mean()), 4) for c in grid.columns}
    meta["coverage_training"] = {c: round(float(train[c].notna().mean()), 4) for c in train.columns if c != "point_id"}
    (OUT / f"{name}_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False), flush=True)


# ---------------------------------------------------------------- التضاريس
def terrain():
    """انحناء المقطع والمسقط (Zevenbergen & Thorne 1987) عند النقطة، وتضرّس النافذة 1 كم (أعلى − أدنى ارتفاع)."""
    import rasterio
    g, t = points()
    pts = pd.concat([g.assign(kind="g", idx=np.arange(len(g))), t.assign(kind="t", idx=np.arange(len(t)))], ignore_index=True)
    res = {c: np.full(len(pts), np.nan) for c in ("curv_profile", "curv_plan", "curv_total", "relief_1km", "slope_mean_1km")}
    pts["tile"] = [f"N{int(math.floor(a)):02d}_00_E{int(math.floor(b)):03d}_00" for a, b in zip(pts.lat, pts.lon)]
    W = 16  # نصف نافذة 1 كم تقريبًا (33 بكسل × 30 م)
    for tile, sub in pts.groupby("tile"):
        name = f"Copernicus_DSM_COG_10_{tile}_DEM"
        url = f"https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif"
        try:
            with rasterio.open(url) as ds:
                z = ds.read(1).astype("float64"); tr = ds.transform
        except Exception as e:
            print("missing tile", tile, e, flush=True); continue
        rows, cols = rasterio.transform.rowcol(tr, sub.lon.values, sub.lat.values)
        rows, cols = np.asarray(rows), np.asarray(cols)
        lat_c = sub.lat.values
        dx = abs(tr.a) * 111320.0 * np.cos(np.radians(lat_c)); dy = np.full(len(lat_c), abs(tr.e) * 110574.0)
        for k, (r, c) in enumerate(zip(rows, cols)):
            i = sub.index[k]
            if 1 <= r < z.shape[0] - 1 and 1 <= c < z.shape[1] - 1:
                w = z[r - 1:r + 2, c - 1:c + 2]
                z1, z2, z3, z4, z5, z6, z7, z8, z9 = w.ravel()
                X, Y = dx[k], dy[k]
                D = ((z4 + z6) / 2 - z5) / X ** 2; E = ((z2 + z8) / 2 - z5) / Y ** 2
                F = (-z1 + z3 + z7 - z9) / (4 * X * Y); G = (-z4 + z6) / (2 * X); H = (z2 - z8) / (2 * Y)
                s = G * G + H * H
                res["curv_total"][i] = -2 * (D + E) * 100
                if s > 1e-12:
                    res["curv_profile"][i] = -2 * (D * G * G + E * H * H + F * G * H) / s * 100
                    res["curv_plan"][i] = 2 * (D * H * H + E * G * G - F * G * H) / s * 100
                else:
                    res["curv_profile"][i] = res["curv_plan"][i] = 0.0
            r0, r1, c0, c1 = max(r - W, 0), min(r + W + 1, z.shape[0]), max(c - W, 0), min(c + W + 1, z.shape[1])
            if r1 - r0 > 2 and c1 - c0 > 2:
                win = z[r0:r1, c0:c1]
                res["relief_1km"][i] = float(win.max() - win.min())
                gy, gx = np.gradient(win, dy[k], dx[k])
                res["slope_mean_1km"][i] = float(np.degrees(np.arctan(np.hypot(gx, gy))).mean())
        print("tile", tile, len(sub), flush=True)
    df = pd.DataFrame(res).round(3)
    grid = df[pts.kind.values == "g"].reset_index(drop=True)
    train = pd.concat([t[["point_id"]], df[pts.kind.values == "t"].reset_index(drop=True)], axis=1)
    save("terrain", grid, train, {"source": "Copernicus DEM GLO-30 (AWS Open Data)", "url": "https://registry.opendata.aws/copernicus-dem/",
                                  "license": "Copernicus DEM licence (free use with attribution)",
                                  "method": "Zevenbergen & Thorne (1987) 3x3 at the point (1/100 m); relief and mean slope in a 33x33-pixel (~1 km) window"})


# ---------------------------------------------------------------- التربة
SOIL = {"clay": "clay_0-5cm_mean", "sand": "sand_0-5cm_mean", "silt": "silt_0-5cm_mean", "bdod": "bdod_0-5cm_mean"}
SOIL_SCALE = {"clay": 0.1, "sand": 0.1, "silt": 0.1, "bdod": 0.01}  # g/kg→%، cg/cm³→g/cm³


def soil():
    import rasterio
    from rasterio.io import MemoryFile
    g, t = points()
    out_g, out_t = pd.DataFrame(index=g.index), t[["point_id"]].copy()
    for var, cov in SOIL.items():
        q = {"map": f"/map/{var}.map", "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage", "COVERAGEID": cov,
             "FORMAT": "image/tiff", "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
             "OUTPUTCRS": "http://www.opengis.net/def/crs/EPSG/0/4326"}
        url = "https://maps.isric.org/mapserv?" + urllib.parse.urlencode(q) + \
              f"&SUBSET=long({BBOX['lon0']},{BBOX['lon1']})&SUBSET=lat({BBOX['lat0']},{BBOX['lat1']})"
        b = fetch(url)
        with MemoryFile(b) as mf, mf.open() as ds:
            a = ds.read(1).astype("float64"); nod = ds.nodata
            if nod is not None: a[a == nod] = np.nan
            a[a <= 0] = np.nan  # صفر = ماء/بلا بيانات في SoilGrids
            for df, src in ((out_g, g), (out_t, t)):
                rr, cc = rasterio.transform.rowcol(ds.transform, src.lon.values, src.lat.values)
                rr, cc = np.asarray(rr), np.asarray(cc)
                ok = (rr >= 0) & (rr < a.shape[0]) & (cc >= 0) & (cc < a.shape[1])
                v = np.full(len(src), np.nan); v[ok] = a[rr[ok], cc[ok]] * SOIL_SCALE[var]
                df[f"soil_{var}"] = np.round(v, 2)
        print("soil", var, a.shape, flush=True)
    save("soil", out_g, out_t, {"source": "SoilGrids 2.0 (ISRIC)", "url": "https://www.isric.org/explore/soilgrids",
                                "license": "CC BY 4.0", "layers": SOIL, "units": {"clay/sand/silt": "% (0-5 cm)", "bdod": "g/cm3 (0-5 cm)"},
                                "resolution": "250 m, EPSG:4326 via WCS 2.0.1"})


# ---------------------------------------------------------------- الجيولوجيا
LITH_CLASS = [  # ترتيب الفحص مهم: الأخص أولًا. المصطلحات بحسب الخرائط المصدر (BRGM 1:10M وChorlton 2007)
    ("volcano_sedimentary", ("volcaniclastic", "volcano-sedimentary", "volcanosedimentary")),
    ("volcanic", ("basalt", "volcanic", "lava", "andesite", "rhyolite", "tuff", "pyroclastic")),
    ("plutonic", ("granite", "granodiorite", "diorite", "gabbro", "plutonic", "tonalite", "intrusive", "syenite")),
    ("metamorphic", ("schist", "gneiss", "metamorphic", "amphibolite", "quartzite", "marble", "slate", "phyllite")),
    ("unconsolidated", ("alluvium", "unconsolidated", "eolian", "colluvium", "sabkha", "quaternary")),
    ("sedimentary", ("sedimentary", "sandstone", "shale", "mudstone", "conglomerate", "siltstone", "limestone", "dolomite", "carbonate", "marl")),
]


def lith_class(text):
    s = (text or "").lower()
    for cls, keys in LITH_CLASS:
        if any(k in s for k in keys): return cls
    return "other" if s else None


def geology():
    gj = json.loads((ROOT / "web" / "data" / "sectors.geojson").read_text(encoding="utf-8"))
    rows, sources = [], {}
    for f in gj["features"]:
        ring = f["geometry"]["coordinates"][0]
        lo = sum(p[0] for p in ring[:-1]) / (len(ring) - 1); la = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
        rec = {"sector_id": f["properties"]["id"], "lith_text": None, "lith_class": None, "age_ma": None, "map_source_id": None}
        try:
            d = json.loads(fetch(f"https://macrostrat.org/api/v2/geologic_units/map?lat={la:.4f}&lng={lo:.4f}", timeout=60))["success"]["data"]
            if d:
                u = d[0]; txt = str(u.get("lith") or u.get("name") or "")
                rec.update(lith_text=(u.get("lith") or u.get("name") or "")[:120], lith_class=lith_class(txt),
                           age_ma=round(((u.get("t_int_age") or 0) + (u.get("b_int_age") or 0)) / 2, 1) if u.get("t_int_age") is not None else None,
                           map_source_id=u.get("source_id"))
                sources[u.get("source_id")] = sources.get(u.get("source_id"), 0) + 1
        except Exception as e:
            print("geology fail", rec["sector_id"], e, flush=True)
        rows.append(rec); time.sleep(0.05)
    sec = pd.DataFrame(rows)
    refs = {}
    for sid in sources:
        try: refs[str(sid)] = json.loads(fetch(f"https://macrostrat.org/api/v2/defs/sources?source_id={sid}", timeout=60))["success"]["data"][0]
        except Exception: pass
    # الشبكة ونقاط التدريب تأخذ صخر القطاع الذي تقع فيه (الخرائط بمقياس 1:1–4 مليون، فالقطاع 11 كم كافٍ)
    g, t = points()
    key = lambda la, lo: f"S{int(math.floor(la * 10))}-{int(math.floor(lo * 10))}"
    m = sec.set_index("sector_id")
    def look(df):
        k = [key(a, b) for a, b in zip(df.lat, df.lon)]
        return pd.DataFrame({"lith_class": [m.lith_class.get(x) if x in m.index else None for x in k],
                             "age_ma": [m.age_ma.get(x) if x in m.index else None for x in k]})
    save("geology", look(g), pd.concat([t[["point_id"]], look(t)], axis=1),
         {"source": "Macrostrat geologic map units API", "url": "https://macrostrat.org/", "license": "CC BY 4.0",
          "map_sources": {k: {"name": v.get("name"), "ref_title": v.get("ref_title"), "authors": v.get("authors"),
                              "scale": v.get("scale"), "ref_year": v.get("ref_year"), "url": v.get("url")} for k, v in refs.items()},
          "sectors_by_source": {str(k): v for k, v in sources.items()},
          "classes": [c for c, _ in LITH_CLASS] + ["other"], "method": "unit at each sector centroid; points inherit their sector"},
         sectors=sec)


# ---------------------------------------------------------------- الأمطار
# CHIRPS v2.0 يومي 0.05° من خادم NOAA ERDDAP (اقتطاع جغرافي على الخادم؛ طلب لكل شهر)
ERDDAP = ["https://coastwatch.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05.nc",   # الخادمان من NOAA SWFSC بنفس البيانات
          "https://upwell.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05.nc"]


def fetch_any(urls, q, timeout=600):
    last = None
    for rnd in range(3):
        for u in urls:
            try:
                return fetch(u + q, tries=2, timeout=timeout)
            except Exception as e:
                last = e; print("mirror failed", u.split("/")[2], e, flush=True)
        time.sleep(30 * (rnd + 1))
    raise last


def rain_chunk(y0, y1):
    import calendar, xarray as xr
    y0, y1 = int(y0), int(y1); days, X, Y = [], None, None
    for y in range(y0, y1 + 1):
        t0 = time.time()
        for m in range(1, 13):
            last = calendar.monthrange(y, m)[1]
            q = (f"?precip[({y}-{m:02d}-01):1:({y}-{m:02d}-{last})][({BBOX['lat0']}):1:({BBOX['lat1']})]"
                 f"[({BBOX['lon0']}):1:({BBOX['lon1']})]")
            b = fetch_any(ERDDAP, q)
            ds = xr.open_dataset(io.BytesIO(b))
            p = ds["precip"].transpose("time", "latitude", "longitude").values.astype("float32")
            assert p.shape[0] == last, f"{y}-{m}: expected {last} days, got {p.shape[0]}"
            p[p < 0] = np.nan
            X, Y = ds["longitude"].values, ds["latitude"].values; days.append(p)
        print("rain", y, round(time.time() - t0, 1), "s", flush=True)
    d = np.concatenate(days, 0)
    np.savez_compressed(OUT / f"rain_{y0}_{y1}.npz", prcp=d.astype("float16"), X=X, Y=Y, years=np.arange(y0, y1 + 1))


def rain_merge(folder):
    """يدمج دفعات السنوات: متوسط الأمطار السنوية، متوسط أقصى يوم في السنة، المئين 95 و99 لمجموع 3 أيام متتالية."""
    files = sorted(Path(folder).rglob("rain_*.npz"))
    ann, max1, s3, X, Y, yrs = [], [], [], None, None, []
    for f in files:
        z = np.load(f); p = z["prcp"].astype("float32"); X, Y = z["X"], z["Y"]
        per = len(p) / len(z["years"]); k = 0
        for y in z["years"]:
            n = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
            a = p[k:k + n]; k += n
            ann.append(np.nansum(a, 0)); max1.append(np.nanmax(a, 0)); yrs.append(int(y))
        c = np.nancumsum(np.nan_to_num(p), 0)
        s3.append((c[2:] - np.concatenate([np.zeros((1,) + c.shape[1:], "float32"), c[:-3]])).astype("float32"))
    s3 = np.concatenate(s3, 0)
    clim = {"rain_annual_mm": np.mean(ann, 0), "rain_max1d_mm": np.mean(max1, 0),
            "rain_p95_3d_mm": np.percentile(s3, 95, axis=0), "rain_p99_3d_mm": np.percentile(s3, 99, axis=0)}
    g, t = points()
    def look(df):
        r = np.abs(Y[None, :] - df.lat.values[:, None]).argmin(1); c = np.abs(X[None, :] - df.lon.values[:, None]).argmin(1)
        return pd.DataFrame({k: np.round(v[r, c], 1) for k, v in clim.items()})
    cells = pd.DataFrame([(round(float(Y[i]), 3), round(float(X[j]), 3), *(round(float(clim[k][i, j]), 1) for k in clim))
                          for i in range(len(Y)) for j in range(len(X))], columns=["lat", "lon", *clim])
    cells.to_csv(OUT / "rain_cells.csv", index=False)
    save("rain", look(g), pd.concat([t[["point_id"]], look(t)], axis=1),
         {"source": "CHIRPS v2.0 daily, 0.05 deg (Climate Hazards Center, UCSB) via NOAA ERDDAP (chirps20GlobalDailyP05)",
          "url": "https://www.chc.ucsb.edu/data/chirps", "citation": "Funk et al. (2015), Scientific Data 2:150066",
          "license": "Public domain (CC0)", "years": [min(yrs), max(yrs)], "n_years": len(set(yrs)),
          "method": "per CHIRPS pixel: mean annual total; mean annual 1-day maximum; 95th and 99th percentile of 3-day running sums; points take the nearest pixel"})


if __name__ == "__main__":
    cmd = {"terrain": terrain, "soil": soil, "geology": geology, "rain_chunk": rain_chunk, "rain_merge": rain_merge}[sys.argv[1]]
    cmd(*sys.argv[2:])
