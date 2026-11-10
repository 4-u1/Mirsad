"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import time, urllib.request
E = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05"
for name, url in [("erddap_info", E + ".das"),
                  ("erddap_month", E + ".nc?precip[(2020-01-01):1:(2020-01-31)][(16.2):1:(20.6)][(40.6):1:(44.2)]"),
                  ("erddap_year", E + ".nc?precip[(2019-01-01):1:(2019-12-31)][(16.2):1:(20.6)][(40.6):1:(44.2)]")]:
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mirsad-probe"}), timeout=900) as r:
            b = r.read()
        print(f"PROBE {name}: bytes={len(b)} secs={time.time()-t:.1f} head={b[:200]!r}")
    except Exception as e:
        print(f"PROBE {name}: ERR {e} secs={time.time()-t:.1f}")
