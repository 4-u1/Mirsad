"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import time, urllib.request
E = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/chirps20GlobalDailyP05"
for name, q in [("jan1991_csv", ".csv?time[(1991-01-01):1:(1991-01-31)]"), ("jan2020_csv", ".csv?time[(2020-01-01):1:(2020-01-31)]"),
                ("y2019_csv", ".csv?time[(2019-01-01):1:(2019-12-31)]"), ("first_last", ".csv?time[0:1:2]"), ("last", ".csv?time[last]"),
                ("feb1991T", ".csv?time[(1991-02-01T00:00:00Z):1:(1991-02-28T00:00:00Z)]")]:
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(E + q, headers={"User-Agent": "mirsad-probe"}), timeout=300) as r:
            b = r.read().decode()
        lines = b.strip().splitlines()
        print(f"PROBE {name}: n={len(lines)-2} first={lines[2:3]} last={lines[-1:]} secs={time.time()-t:.1f}")
    except Exception as e:
        print(f"PROBE {name}: ERR {e}")
