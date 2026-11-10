"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import time, urllib.request, urllib.error
E = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05"
q = ".nc?precip[(2020-01-01):1:(2020-01-31)][(16.2):1:(20.6)][(40.6):1:(44.2)]"
for ua in ["mirsad-probe", "mirsad-pipeline", "Mozilla/5.0 (X11; Linux x86_64)", "python-requests/2.32"]:
    for url in [E + q, E + ".csv?time[last]"]:
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=120) as r:
                print(f"PROBE ua={ua!r} {url[-30:]}: {r.status} {len(r.read())}")
        except urllib.error.HTTPError as e:
            print(f"PROBE ua={ua!r} {url[-30:]}: {e.code} {e.read()[:300]!r}")
        time.sleep(2)
