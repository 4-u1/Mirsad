"""مِرصاد · 10 — تنبؤ 24/48/72 ساعة لكل قطاع (FR-U6).

1. توقعات الأمطار الساعية للـ72 ساعة القادمة عند مركز كل قطاع من Open-Meteo Forecast API (CC BY 4.0).
2. النسبة = الأمطار المتراكمة حتى الأفق ÷ عتبة القطاع (المئين 99 لمجموع 3 أيام من CHIRPS 2016–2025،
   data/processed/sector_layers.csv من 09).
3. المستوى المتوقع = backend/rules.forecast_level(مستوى القابلية، النسبة): رفع درجة عند ≥ 0.5 ودرجتين عند ≥ 1، ولا ينخفض.
4. يكتب في جدول forecasts (DATABASE_URL أو SQLite المحلي)، ويحذف الإصدارات الأقدم من 7 أيام.

يعمل كل 6 ساعات من .github/workflows/forecast.yml. لا قيم افتراضية: قطاع بلا توقع أو بلا عتبة يُكتب بنسبة فارغة.
"""
import datetime, json, sys, time, urllib.parse, urllib.request
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from db import connect  # noqa: E402
from rules import forecast_level  # noqa: E402

API = "https://api.open-meteo.com/v1/forecast"
SOURCE = "Open-Meteo Forecast API (hourly precipitation, best-match models), CC BY 4.0"
BATCH, HORIZONS, KEEP_DAYS = 50, (24, 48, 72), 7


def sectors():
    gj = json.loads((ROOT / "web" / "data" / "sectors.geojson").read_text(encoding="utf-8"))
    rows = []
    for f in gj["features"]:
        ring = f["geometry"]["coordinates"][0][:-1]
        rows.append({"sector_id": f["properties"]["id"], "base_level": f["properties"]["level"],
                     "lat": round(sum(p[1] for p in ring) / len(ring), 4), "lon": round(sum(p[0] for p in ring) / len(ring), 4)})
    s = pd.DataFrame(rows)
    lay = ROOT / "data" / "processed" / "sector_layers.csv"
    if lay.exists():
        s = s.merge(pd.read_csv(lay, encoding="utf-8-sig")[["sector_id", "rain_p99_3d_mm"]], on="sector_id", how="left")
    else:
        s["rain_p99_3d_mm"] = None
    return s


def fetch(lat, lon, tries=4):
    q = {"latitude": ",".join(map(str, lat)), "longitude": ",".join(map(str, lon)), "hourly": "precipitation",
         "forecast_days": 4, "timezone": "UTC"}
    for k in range(tries):
        try:
            with urllib.request.urlopen(API + "?" + urllib.parse.urlencode(q), timeout=120) as r:
                d = json.loads(r.read())
                return d if isinstance(d, list) else [d]
        except Exception as e:
            if k == tries - 1: raise
            print("retry", k + 1, e, flush=True); time.sleep(10 * (k + 1))


def cumulative(series, start):
    """مجموع الأمطار من الساعة الحالية حتى كل أفق."""
    t = pd.to_datetime(series["time"], utc=True)
    p = pd.Series(series["precipitation"], index=t).loc[lambda x: x.index >= start]
    if len(p) < max(HORIZONS) or p.iloc[:max(HORIZONS)].isna().all():
        return {h: None for h in HORIZONS}
    return {h: round(float(p.iloc[:h].fillna(0).sum()), 1) for h in HORIZONS}


def main():
    s = sectors()
    now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    issued = now.isoformat()
    rows = []
    for i in range(0, len(s), BATCH):
        b = s.iloc[i:i + BATCH]
        for (_, sec), res in zip(b.iterrows(), fetch(b.lat.tolist(), b.lon.tolist())):
            cum = cumulative(res["hourly"], now)
            thr = sec.rain_p99_3d_mm if pd.notna(sec.rain_p99_3d_mm) and sec.rain_p99_3d_mm > 0 else None
            for h in HORIZONS:
                ratio = round(cum[h] / thr, 3) if cum[h] is not None and thr else None
                rows.append((issued, sec.sector_id, h, cum[h], round(float(thr), 1) if thr else None, ratio,
                             sec.base_level, forecast_level(sec.base_level, ratio), SOURCE))
        time.sleep(1)
    con = connect()
    with con.transaction():
        con.execute("DELETE FROM forecasts WHERE issued_at=?", (issued,))
        con.executemany("INSERT INTO forecasts(issued_at, sector_id, horizon_h, rain_mm, threshold_mm, ratio, base_level, level, source) "
                        "VALUES (?,?,?,?,?,?,?,?,?)", rows)
        con.execute("DELETE FROM forecasts WHERE issued_at<?", ((now - datetime.timedelta(days=KEEP_DAYS)).isoformat(),))
    con.commit()
    df = pd.DataFrame(rows, columns=["issued_at", "sector_id", "h", "rain", "thr", "ratio", "base", "level", "src"])
    d72 = df[df.h == 72]
    summary = {"issued_at": issued, "sectors": int(d72.sector_id.nunique()), "with_rain_forecast": int(d72.rain.notna().sum()),
               "with_threshold": int(d72.thr.notna().sum()), "max_rain_72h_mm": float(d72.rain.max() or 0),
               "raised_72h": int((d72.level != d72.base).sum()), "levels_72h": d72.level.value_counts().to_dict(), "backend": con.dialect}
    print("MIRSAD_FORECAST " + json.dumps(summary), flush=True)
    return summary


if __name__ == "__main__":
    main()
