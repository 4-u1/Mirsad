"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import time, urllib.request
def get(url, n=600, timeout=900):
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mirsad-probe"}), timeout=timeout) as r:
            b = r.read(); return r.status, len(b), round(time.time() - t, 1), b[:n]
    except Exception as e:
        return "ERR", 0, round(time.time() - t, 1), str(e)[:300].encode()
B = "https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/.daily-improved/.global/.0p05/.prcp/X/40.6/44.2/RANGEEDGES/Y/16.2/20.6/RANGEEDGES/"
tests = {
 "iri_year_2019": B + "T/(1%20Jan%202019)/(31%20Dec%202019)/RANGEEDGES/data.nc",
 "iri_5y": B + "T/(1%20Jan%202015)/(31%20Dec%202019)/RANGEEDGES/data.nc",
 "macro_source": "https://macrostrat.org/api/v2/defs/sources?source_id=190",
}
for k, u in tests.items():
    s, n, dt, head = get(u)
    print(f"PROBE {k}: status={s} bytes={n} secs={dt} head={head[:500]!r}")
