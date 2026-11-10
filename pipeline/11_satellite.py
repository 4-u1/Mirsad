"""مِرصاد · 11 — تحليل صور الأقمار الصناعية الحديثة (Sentinel-2 L2A).

المصدر: Copernicus Sentinel-2 عبر فهرس Earth Search (Element 84) على AWS Open Data — مجاني وبلا مفتاح.
1. يبحث عن المشاهد فوق منطقة الدراسة في نافذتين: آخر WINDOW يومًا، ونفس النافذة قبل سنة (أساس يزيل أثر الموسم).
2. يقرأ من كل مشهد النطاقات red/nir وقناع التصنيف SCL ونسخة الألوان الحقيقية visual بدقة مخفّضة ~200 م
   (طبقات overview داخل ملفات COG، فلا يُنزَّل المشهد كاملًا)، ويستبعد الغيوم والظلال بالقناع (SCL ∈ {4 نبات، 5 أرض مكشوفة}).
3. يركّب شبكة موحّدة 0.002° فوق المنطقة:
   - NDVI متوسط المشاهد الصافية لكل بكسل في كل نافذة.
   - فسيفساء ألوان حقيقية: أحدث بكسل صافٍ (تُعرض طبقةً فوق الخريطة).
4. لكل قطاع (0.1°): NDVI الحالي، NDVI الأساس، التغيّر، نسبة البكسلات الصافية، وعلامة backend/rules.ndvi_flag (ق-6).
5. يكتب في satellite_runs (مع الصورة WebP) وsatellite، ويبقي آخر KEEP_RUNS تشغيلات.

يعمل أسبوعيًا من .github/workflows/satellite.yml. لا قيم افتراضية: قطاع غائم يُكتب بقيم فارغة.
"""
import datetime, io, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

STAC = "https://earth-search.aws.element84.com/v1/search"
COLLECTION = os.environ.get("MIRSAD_S2_COLLECTION", "sentinel-2-l2a")
SOURCE = "Copernicus Sentinel-2 L2A (ESA), via Earth Search / AWS Open Data — contains modified Copernicus Sentinel data"
BBOX = (40.6, 16.2, 44.2, 20.6)           # حدود القطاعات (web/data/sectors.geojson)
RES = 0.002                               # ~220 م
SECTOR = 0.1
WINDOW = int(os.environ.get("MIRSAD_S2_DAYS", "30"))
MAX_CLOUD = 60
READ = 549                                # 10980 بكسل ÷ 20 ≈ 200 م
KEEP_RUNS = 4
VALID_SCL = (4, 5)
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif,.TIF")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "4")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "2")


def post(url, body, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", "User-Agent": "mirsad-pipeline"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            if k == tries - 1: raise
            print("retry", k + 1, e, flush=True); time.sleep(5 * (k + 1))


def search(start, end):
    body = {"collections": [COLLECTION], "bbox": list(BBOX), "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
            "limit": 200, "query": {"eo:cloud_cover": {"lt": MAX_CLOUD}}}
    items, url = [], STAC
    while True:
        d = post(url, body)
        items += d.get("features", [])
        nxt = [l for l in d.get("links", []) if l.get("rel") == "next"]
        if not nxt: break
        url, body = nxt[0]["href"], nxt[0].get("body", body)
    # مشهد واحد لكل (بلاطة، يوم): يستبعد النسخ المكررة بخطوط معالجة مختلفة
    best = {}
    for it in items:
        p = it["properties"]
        key = (p.get("grid:code") or p.get("s2:mgrs_tile") or it["id"].split("_")[1], p["datetime"][:10])
        if key not in best or p.get("s2:processing_baseline", "") > best[key]["properties"].get("s2:processing_baseline", ""):
            best[key] = it
    return sorted(best.values(), key=lambda i: i["properties"]["datetime"])


def scale_offset(asset, props):
    b = (asset.get("raster:bands") or [{}])[0]
    if "scale" in b: return b["scale"], b.get("offset", 0.0)
    pb = props.get("s2:processing_baseline", "00.00")
    return 1e-4, (-0.1 if pb >= "04.00" else 0.0)


class Grid:
    def __init__(self):
        self.lon = BBOX[0] + RES * (np.arange(round((BBOX[2] - BBOX[0]) / RES)) + 0.5)
        self.lat = BBOX[3] - RES * (np.arange(round((BBOX[3] - BBOX[1]) / RES)) + 0.5)   # الصف 0 = الشمال
        self.shape = (len(self.lat), len(self.lon))


def read_scene(it, grid, want_rgb):
    """يرجع (نافذة الشبكة، NDVI، قناع صافٍ، RGB) لمشهد واحد بعد إسقاطه على الشبكة."""
    import rasterio
    from rasterio.warp import transform_bounds
    from pyproj import Transformer
    A, P = it["assets"], it["properties"]
    with rasterio.Env():
        with rasterio.open(A["red"]["href"]) as ds:
            crs, bounds = ds.crs, ds.bounds
            red = ds.read(1, out_shape=(READ, READ)).astype(np.float32)
            tr = ds.transform * ds.transform.scale(ds.width / READ, ds.height / READ)
        with rasterio.open(A["nir"]["href"]) as ds:
            nir = ds.read(1, out_shape=(READ, READ)).astype(np.float32)
        with rasterio.open(A["scl"]["href"]) as ds:
            scl = ds.read(1, out_shape=(READ, READ), resampling=rasterio.enums.Resampling.nearest)
        rgb = None
        if want_rgb:
            with rasterio.open(A["visual"]["href"]) as ds:
                rgb = ds.read(out_shape=(3, READ, READ))
    w, s, e, n = transform_bounds(crs, "EPSG:4326", *bounds)
    c0, c1 = np.searchsorted(grid.lon, w), np.searchsorted(grid.lon, e)
    r0, r1 = np.searchsorted(-grid.lat, -n), np.searchsorted(-grid.lat, -s)
    if c1 <= c0 or r1 <= r0: return None
    LON, LAT = np.meshgrid(grid.lon[c0:c1], grid.lat[r0:r1])
    x, y = Transformer.from_crs("EPSG:4326", crs, always_xy=True).transform(LON, LAT)
    inv = ~tr
    col, row = inv * (x, y)
    col, row = np.floor(col).astype(int), np.floor(row).astype(int)
    inside = (col >= 0) & (col < READ) & (row >= 0) & (row < READ)
    col, row = np.clip(col, 0, READ - 1), np.clip(row, 0, READ - 1)
    sr, so = scale_offset(A["red"], P); sn, on = scale_offset(A["nir"], P)
    R, N = red[row, col] * sr + so, nir[row, col] * sn + on
    raw_ok = (red[row, col] > 0) & (nir[row, col] > 0)
    ok = inside & raw_ok & np.isin(scl[row, col], VALID_SCL) & ((R + N) > 0.02)
    nd = np.where(ok, (N - R) / np.where(ok, N + R, 1), np.nan).astype(np.float32)
    out_rgb = np.moveaxis(rgb[:, row, col], 0, -1) if rgb is not None else None
    return (r0, r1, c0, c1), nd, ok, out_rgb


def composite(items, grid, want_rgb, label):
    s = np.zeros(grid.shape, np.float64); n = np.zeros(grid.shape, np.int32)
    rgb = np.zeros(grid.shape + (4,), np.uint8) if want_rgb else None
    last = np.full(grid.shape, "", dtype=object) if want_rgb else None
    used, failed = [], 0

    def job(it):
        try: return it, read_scene(it, grid, want_rgb)
        except Exception as e:
            print("skip", it["id"], type(e).__name__, str(e)[:120], flush=True); return it, None

    with ThreadPoolExecutor(8) as ex:
        results = list(ex.map(job, items))
    for it, res in results:                      # بترتيب زمني: الأحدث يكتب فوق الأقدم في الفسيفساء
        if res is None: failed += 1; continue
        (r0, r1, c0, c1), nd, ok, out = res
        if not ok.any(): continue
        sub = (slice(r0, r1), slice(c0, c1))
        s[sub] += np.where(ok, nd, 0); n[sub] += ok
        if want_rgb:
            v = rgb[sub]; v[ok, :3] = out[ok]; v[ok, 3] = 255
            last[sub][ok] = it["properties"]["datetime"][:10]
        used.append(it["properties"]["datetime"][:10])
    print(f"{label}: {len(items)} scenes, {len(used)} used, {failed} failed", flush=True)
    ndvi = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    return ndvi, n, rgb, used, failed


def sector_stats(ndvi, n, grid, ids):
    k = round(SECTOR / RES); out = {}
    for sid in ids:
        lat0, lon0 = int(sid[1:4]) / 10, int(sid.split("-")[1]) / 10
        r0 = round((BBOX[3] - (lat0 + SECTOR)) / RES); c0 = round((lon0 - BBOX[0]) / RES)
        blk, cnt = ndvi[r0:r0 + k, c0:c0 + k], n[r0:r0 + k, c0:c0 + k]
        valid = float((cnt > 0).mean()) if cnt.size else 0.0
        out[sid] = (round(float(np.nanmean(blk)), 4) if valid > 0 else None, round(valid, 3))
    return out


def webp(rgb):
    from PIL import Image
    im = Image.fromarray(rgb, "RGBA")
    b = io.BytesIO(); im.save(b, "WEBP", quality=78, method=5); return b.getvalue()


def main():
    from db import connect, now
    from rules import ndvi_flag
    gj = json.loads((ROOT / "web" / "data" / "sectors.geojson").read_text(encoding="utf-8"))
    ids = [f["properties"]["id"] for f in gj["features"]]
    today = datetime.date.today()
    now_w = (today - datetime.timedelta(days=WINDOW), today)
    base_w = (now_w[0].replace(year=now_w[0].year - 1), now_w[1].replace(year=now_w[1].year - 1))
    grid = Grid()
    it_now, it_base = search(*map(str, now_w)), search(*map(str, base_w))
    print("search", COLLECTION, len(it_now), len(it_base), flush=True)
    if not it_now: raise SystemExit("no Sentinel-2 scenes found for the current window")
    nd_now, n_now, rgb, used_now, f_now = composite(it_now, grid, True, "now")
    nd_base, n_base, _, used_base, f_base = composite(it_base, grid, False, "base")
    st_now, st_base = sector_stats(nd_now, n_now, grid, ids), sector_stats(nd_base, n_base, grid, ids)
    run_at = now()
    rows = []
    for sid in ids:
        (a, va), (b, vb) = st_now[sid], st_base[sid]
        a = a if va > 0 else None; b = b if vb > 0 else None
        ch = round(a - b, 4) if a is not None and b is not None else None
        rows.append((run_at, sid, a, b, ch, va, vb, ndvi_flag(b, ch, va, vb)))
    img = webp(rgb)
    meta = {"window_now": [str(d) for d in now_w], "window_base": [str(d) for d in base_w],
            "scenes_now": len(used_now), "scenes_base": len(used_base), "failed": f_now + f_base,
            "first_date": min(used_now) if used_now else None, "last_date": max(used_now) if used_now else None,
            "bounds": list(BBOX), "res_deg": RES, "collection": COLLECTION, "max_cloud": MAX_CLOUD,
            "coverage_now": round(float((n_now > 0).mean()), 3), "image_kb": round(len(img) / 1024, 1)}
    con = connect()
    with con.transaction():
        con.execute("INSERT INTO satellite_runs(run_at, meta, source, image, image_type) VALUES (?,?,?,?,?)",
                    (run_at, json.dumps(meta), SOURCE, img, "image/webp"))
        con.copy_rows("satellite", ["run_at", "sector_id", "ndvi_now", "ndvi_base", "ndvi_change", "valid_now", "valid_base", "flag"], rows)
        old = [r["run_at"] for r in con.execute("SELECT run_at FROM satellite_runs ORDER BY run_at DESC").fetchall()][KEEP_RUNS:]
        for t in old:
            con.execute("DELETE FROM satellite WHERE run_at=?", (t,)); con.execute("DELETE FROM satellite_runs WHERE run_at=?", (t,))
    con.commit()
    flags = [r[7] for r in rows]
    ch = np.array([r[4] for r in rows if r[4] is not None])
    summary = meta | {"run_at": run_at, "sectors": len(rows), "with_now": sum(r[2] is not None for r in rows),
                      "with_change": len(ch), "drop": flags.count("drop"), "stable": flags.count("stable"),
                      "insufficient": flags.count(None), "change_p5_p50_p95": [round(float(np.percentile(ch, q)), 3) for q in (5, 50, 95)] if len(ch) else None,
                      "ndvi_now_p50": round(float(np.nanmedian([r[2] for r in rows if r[2] is not None])), 3) if any(r[2] is not None for r in rows) else None,
                      "backend": con.dialect}
    print("MIRSAD_SATELLITE " + json.dumps(summary), flush=True)
    out = os.environ.get("MIRSAD_OUT")
    if out:
        Path(out).mkdir(parents=True, exist_ok=True)
        (Path(out) / "satellite_preview.webp").write_bytes(img)
        (Path(out) / "satellite_summary.json").write_text(json.dumps(summary, indent=2))
        import csv
        with open(Path(out) / "satellite_sectors.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["run_at", "sector_id", "ndvi_now", "ndvi_base", "ndvi_change", "valid_now", "valid_base", "flag"]); w.writerows(rows)
    return summary


if __name__ == "__main__":
    main()
