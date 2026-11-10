"""لقطات الموقع الحي للعرض والتقارير: docs/screenshots/v2_*.jpg (تعمل على GitHub Actions)."""
import asyncio, json, os
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("MIRSAD_URL", "https://mirsad-rho.vercel.app").rstrip("/")
OUT = Path("docs/screenshots"); OUT.mkdir(parents=True, exist_ok=True)


async def ctx_for(b, lang, theme, w=1600, h=900, dpr=1.5):
    c = await b.new_context(viewport={"width": w, "height": h}, device_scale_factor=dpr, timezone_id="Asia/Riyadh")
    await c.add_init_script(f"try{{localStorage.setItem('mirsad.lang',JSON.stringify('{lang}'));localStorage.setItem('mirsad.theme',JSON.stringify('{theme}'));localStorage.setItem('mirsad.tourSeen','1')}}catch(e){{}}")
    return c


async def shot(pg, name, full=False):
    await pg.screenshot(path=str(OUT / f"v2_{name}.jpg"), type="jpeg", quality=86, full_page=full)
    print("shot", name, flush=True)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        c = await ctx_for(b, "ar", "dark"); pg = await c.new_page()
        await pg.goto(BASE + "/#map", wait_until="networkidle"); await pg.wait_for_timeout(5000)
        await shot(pg, "map_level_ar")
        for v in ("fc72", "lith_class", "rain_annual_mm", "relief_1km"):
            await pg.select_option("#colorBy", v); await pg.wait_for_timeout(2000); await shot(pg, f"map_{v}_ar")
        await pg.select_option("#colorBy", "level"); await pg.wait_for_timeout(1000)
        top = await pg.evaluate("window.MirsadApp.topSector()")
        await pg.evaluate(f"window.MirsadApp.openDrawer({json.dumps(top)})"); await pg.wait_for_timeout(3000)
        await shot(pg, "drawer_ar")
        await pg.evaluate("const d=document.getElementById('drawer'); d.scrollTop = d.scrollHeight; document.getElementById('drawerBody').scrollTop = 99999"); await pg.wait_for_timeout(800)
        await shot(pg, "drawer_bottom_ar")
        for h in ("alerts", "transparency"):
            await pg.goto(BASE + f"/#{h}"); await pg.wait_for_timeout(3000); await shot(pg, f"{h}_ar")
        await c.close()
        c = await ctx_for(b, "en", "light"); pg = await c.new_page()
        await pg.goto(BASE + "/#map", wait_until="networkidle"); await pg.wait_for_timeout(5000)
        await pg.select_option("#colorBy", "fc72"); await pg.wait_for_timeout(2000); await shot(pg, "map_fc72_en_light")
        await pg.goto(BASE + "/#transparency"); await pg.wait_for_timeout(3000); await shot(pg, "transparency_en_light")
        await c.close()
        for lang in ("ar", "en"):
            for theme in ("dark", "light"):
                c = await ctx_for(b, lang, theme, 1440, 900, 1); pg = await c.new_page()
                await pg.goto(BASE + "/#about"); await pg.wait_for_timeout(3500); await shot(pg, f"about_{lang}_{theme}"); await c.close()
        c = await ctx_for(b, "ar", "dark", 1100, 1400, 1.5); pg = await c.new_page()
        await pg.goto(BASE + f"/report.html#{top}"); await pg.wait_for_timeout(4000); await shot(pg, "report_ar", True)
        await c.close()
        m = await b.new_context(**p.devices["iPhone 13"], timezone_id="Asia/Riyadh")
        await m.add_init_script("try{localStorage.setItem('mirsad.lang','\"ar\"');localStorage.setItem('mirsad.theme','\"dark\"');localStorage.setItem('mirsad.tourSeen','1')}catch(e){}")
        pg = await m.new_page(); await pg.goto(BASE + "/#map", wait_until="networkidle"); await pg.wait_for_timeout(5000)
        await shot(pg, "mobile_ar"); await b.close()


asyncio.run(main())
