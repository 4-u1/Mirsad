"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import json, time, urllib.request, urllib.parse
def get(url, n=400, timeout=90):
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mirsad-probe"}), timeout=timeout) as r:
            b = r.read(); return r.status, len(b), round(time.time() - t, 1), b[:n]
    except Exception as e:
        return "ERR", 0, round(time.time() - t, 1), str(e)[:300].encode()
tests = {
 "iri_chirps_daily": "https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.daily-improved/.global/.0p05/.prcp/X/40.6/44.2/RANGEEDGES/Y/16.2/20.6/RANGEEDGES/T/(1%20Jan%202020)/(31%20Jan%202020)/RANGEEDGES/data.nc",
 "chc_annual_tif": "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_annual/tifs/",
 "soilgrids_wcs": "https://maps.isric.org/mapserv?map=/map/clay.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage&COVERAGEID=clay_0-5cm_mean&FORMAT=image/tiff&SUBSET=long(43.0,43.2)&SUBSET=lat(17.2,17.4)&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326",
 "cop_dem": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N17_00_E043_00_DEM/Copernicus_DSM_COG_10_N17_00_E043_00_DEM.tif",
 "macrostrat": "https://macrostrat.org/api/v2/geologic_units/map?lat=17.35&lng=43.15&scale=large",
 "macrostrat_small": "https://macrostrat.org/api/v2/geologic_units/map?lat=17.35&lng=43.15",
 "openmeteo_fc": "https://api.open-meteo.com/v1/forecast?latitude=17.35,18.1&longitude=43.15,42.3&daily=precipitation_sum&forecast_days=3&timezone=Asia%2FRiyadh",
 "openmeteo_archive": "https://archive-api.open-meteo.com/v1/archive?latitude=17.35&longitude=43.15&start_date=2020-01-01&end_date=2020-01-05&daily=precipitation_sum",
}
for k, u in tests.items():
    s, n, dt, head = get(u)
    print(f"PROBE {k}: status={s} bytes={n} secs={dt} head={head[:300]!r}")
