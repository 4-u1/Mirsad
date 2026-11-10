"""يعرض الشعارات الأربعة على خلفيات الموقع ويحفظ لقطة للمراجعة: out/brand/preview.png"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
D = Path("out/brand").resolve()
html = "<html><body style='margin:0;display:grid;grid-template-columns:1fr 1fr'>" + "".join(
    f"<div style='background:{bg};padding:24px'><img src='file://{D}/logo-{l}-{t}.svg' style='width:100%'></div>"
    for l in ("ar", "en") for t, bg in (("dark", "#0F1E23"), ("light", "#F6F1E8"))) + "</body></html>"
(D / "preview.html").write_text(html, encoding="utf-8")
async def m():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1400, "height": 700})
        await pg.goto(f"file://{D}/preview.html"); await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(D / "preview.png"), full_page=True); await b.close()
asyncio.run(m())
