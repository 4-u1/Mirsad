"""فحص سريع لإتاحة مصادر البيانات المجانية من GitHub Actions (لا يكتب شيئًا في المستودع)."""
import time, urllib.request
for name, url in [("chc_p05_2020", "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p05/chirps-v2.0.2020.days_p05.nc"),
                  ("chc_p25_2020", "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/netcdf/p25/chirps-v2.0.2020.days_p25.nc")]:
    t = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "mirsad-probe"}), timeout=600) as r:
            size = int(r.headers.get("Content-Length") or 0); got = 0
            while got < 300_000_000:
                b = r.read(8 << 20)
                if not b: break
                got += len(b)
        dt = time.time() - t
        print(f"PROBE {name}: size={size/1e6:.0f}MB read={got/1e6:.0f}MB secs={dt:.1f} rate={got/1e6/dt:.1f}MB/s")
    except Exception as e:
        print(f"PROBE {name}: ERR {e} secs={time.time()-t:.1f}")
