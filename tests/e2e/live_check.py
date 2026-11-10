"""فحص المتصفح على الموقع الحي (v2.0 · معايير القبول). يعمل على GitHub Actions: .github/workflows/ui-check.yml

يفتح الخريطة، يبدّل كل خيار تلوين، يفتح قطاعًا ويتحقق من التنبؤ والطبقات، ثم الإنذارات والشفافية وتقرير القطاع،
بالعربية والإنجليزية، ويفشل عند أي خطأ في المتصفح أو عنصر ناقص. يحفظ لقطات في out/.
"""
import asyncio, json, os, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("MIRSAD_URL", "https://mirsad-rho.vercel.app").rstrip("/")
OUT = Path("out"); OUT.mkdir(exist_ok=True)
OPTS = ["fc72", "rain_annual_mm", "rain_p99_3d_mm", "soil_clay", "relief_1km", "lith_class", "slope_mean", "elev", "level"]


async def main():
    res, errors = {}, []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1440, "height": 900})
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        pg.on("console", lambda c: errors.append(f"console: {c.text}") if c.type == "error" else None)
        await pg.add_init_script("try{localStorage.setItem('mirsad.tourSeen','1')}catch(e){}")
        await pg.goto(BASE + "/#map", wait_until="networkidle"); await pg.wait_for_timeout(4000)
        res["health"] = await pg.evaluate("fetch('/api/v1/health').then(r=>r.json())")
        fc = await pg.evaluate("fetch('/api/v1/forecast').then(async r=>({status:r.status, body: r.ok ? await r.json() : null}))")
        res["forecast_status"] = fc["status"]
        if fc["body"]:
            res["forecast"] = {k: fc["body"][k] for k in ("issued_at", "age_hours", "stale", "count")}
        res["fc_side"] = await pg.inner_text("#fcSide")
        await pg.screenshot(path=str(OUT / "01_map.jpg"), type="jpeg", quality=80)
        res["color_options"] = {}
        for i, v in enumerate(OPTS):
            await pg.select_option("#colorBy", v); await pg.wait_for_timeout(1200)
            res["color_options"][v] = await pg.evaluate("[!document.getElementById('ramp').hidden, !document.getElementById('catLegend').hidden]")
            if v in ("fc72", "rain_p99_3d_mm", "lith_class"):
                await pg.screenshot(path=str(OUT / f"02_color_{v}.jpg"), type="jpeg", quality=80)
        top = await pg.evaluate("window.MirsadApp.topSector()")
        await pg.evaluate(f"window.MirsadApp.openDrawer({json.dumps(top)})"); await pg.wait_for_timeout(2500)
        txt = await pg.inner_text("#drawerBody")
        res["drawer"] = {"sector": top, "forecast_table": await pg.locator("#drawerBody table.fc").count(),
                         "layers": "طبقات القطاع" in txt}
        await pg.screenshot(path=str(OUT / "03_drawer.jpg"), type="jpeg", quality=80)
        await pg.goto(BASE + "/#alerts"); await pg.wait_for_timeout(2500)
        res["alerts_count"] = await pg.inner_text("#fCount")
        await pg.goto(BASE + "/#transparency"); await pg.wait_for_timeout(2500)
        res["transparency_sources"] = await pg.locator("#trSources tbody tr").count()
        res["transparency_models"] = await pg.inner_text("#trCompare")
        await pg.screenshot(path=str(OUT / "04_transparency.jpg"), type="jpeg", quality=80, full_page=True)
        await pg.goto(BASE + f"/report.html#{top}"); await pg.wait_for_timeout(3000)
        await pg.screenshot(path=str(OUT / "05_report.jpg"), type="jpeg", quality=80, full_page=True)
        res["report_title"] = await pg.title()
        await pg.goto(BASE + "/#map"); await pg.wait_for_timeout(2500)
        await pg.click("#langBtn"); await pg.wait_for_timeout(1500)
        res["fc_side_en"] = await pg.inner_text("#fcSide")
        await pg.screenshot(path=str(OUT / "06_map_en.jpg"), type="jpeg", quality=80)
        await b.close()
    res["errors"] = errors
    (OUT / "live_check.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MIRSAD_UI " + json.dumps(res, ensure_ascii=False))
    ok = (res["health"]["status"] == "ok" and res["drawer"]["layers"] and res["transparency_sources"] >= 10
          and all(any(v) or k in ("level",) for k, v in res["color_options"].items()) and not errors
          and (res["forecast_status"] == 200 and res["drawer"]["forecast_table"] == 1 or os.environ.get("ALLOW_NO_FORECAST")))
    sys.exit(0 if ok else 1)


asyncio.run(main())
