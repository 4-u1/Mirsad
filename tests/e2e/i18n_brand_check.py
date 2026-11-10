"""فحص اللغة والتواريخ والشعار (عربي/إنجليزي × داكن/نهاري) في المتصفح.

  MIRSAD_URL=https://mirsad-rho.vercel.app python tests/e2e/i18n_brand_check.py
محليًا بدون إنترنت: MIRSAD_STUB=<ملف بديل maplibre> يمرّر بديلًا لمكتبة الخرائط، ويتجاهل أخطاء تحميل الموارد الخارجية.
يحفظ لقطات ونتيجة JSON في out/i18n/ ويخرج بخطأ عند أي فشل.
"""
import asyncio, json, os, re, sys
from pathlib import Path
from playwright.async_api import async_playwright

BASE = os.environ.get("MIRSAD_URL", "https://mirsad-rho.vercel.app").rstrip("/")
STUB = os.environ.get("MIRSAD_STUB")
OUT = Path("out/i18n"); OUT.mkdir(parents=True, exist_ok=True)
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
AR_MONTHS = "يناير|فبراير|مارس|أبريل|إبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر"
EN_DATE = re.compile(r"\b\d{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}\b")
EASTERN = re.compile("[٠-٩]")
fails, log = [], {}


def check(cond, msg):
    (log.setdefault("passed", []) if cond else fails).append(msg)


async def page(ctx, errors):
    pg = await ctx.new_page()
    pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    pg.on("console", lambda c: errors.append(f"console: {c.text}") if c.type == "error" and not (STUB and "Failed to load resource" in c.text) else None)
    if STUB:
        body = Path(STUB).read_text()
        await pg.route("**/maplibre-gl.js", lambda r: r.fulfill(body=body, content_type="application/javascript"))
    return pg


async def visible_text(pg):
    return await pg.evaluate("document.body.innerText")


async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for vw, vh, tag in ((1440, 900, "desktop"), (390, 844, "mobile")):
            for lang in ("ar", "en"):
                for theme in ("dark", "light"):
                    key = f"{tag}-{lang}-{theme}"; errors = []
                    ctx = await b.new_context(viewport={"width": vw, "height": vh}, timezone_id="UTC", locale="fr-FR")  # لغة متصفح مختلفة عمدًا
                    await ctx.add_init_script(f"try{{localStorage.setItem('mirsad.lang',JSON.stringify('{lang}'));localStorage.setItem('mirsad.theme',JSON.stringify('{theme}'));localStorage.setItem('mirsad.tourSeen','1')}}catch(e){{}}")
                    pg = await page(ctx, errors)
                    await pg.goto(BASE + "/#about"); await pg.wait_for_timeout(4500)
                    src = await pg.get_attribute(".about-logo", "src")
                    check(f"logo-{lang}-{theme}" in (src or ""), f"{key}: About logo {src}")
                    # تنسيق التواريخ بتوقيت الرياض والمتصفح على UTC
                    s = await pg.evaluate("MirsadFmt.fmtDate('2026-11-10T19:07:00Z')")
                    check(("10:07" in s and "م" in s and "نوفمبر" in s) if lang == "ar" else ("22:07" in s and "Nov 2026" in s), f"{key}: Riyadh time '{s}'")
                    for hash_ in ("map", "alerts", "transparency"):
                        await pg.goto(BASE + f"/#{hash_}"); await pg.wait_for_timeout(1800)
                        txt = await visible_text(pg)
                        check(not ISO.search(txt), f"{key}/{hash_}: no raw ISO date" + (f" (found {ISO.search(txt).group()})" if ISO.search(txt) else ""))
                        check(not EASTERN.search(txt), f"{key}/{hash_}: no Eastern-Arabic digits")
                        if hash_ == "transparency":
                            check(bool(re.search(AR_MONTHS, txt)) if lang == "ar" else bool(EN_DATE.search(txt)), f"{key}/transparency: localized date present")
                    if tag == "desktop":
                        await pg.goto(BASE + "/#about"); await pg.wait_for_timeout(1200)
                        await pg.screenshot(path=str(OUT / f"about_{key}.jpg"), type="jpeg", quality=75)
                    # التقرير
                    top = await pg.evaluate("window.MirsadApp && window.MirsadApp.topSector()") or "S173-431"
                    rp = await page(ctx, errors); await rp.goto(BASE + f"/report.html#{top}"); await rp.wait_for_timeout(3500)
                    scr = await rp.get_attribute(".hd .logo-scr", "src"); prn = await rp.get_attribute(".hd .logo-prn", "src")
                    check(f"logo-{lang}-dark" in (scr or "") and f"logo-{lang}-light" in (prn or ""), f"{key}: report logos {scr} / {prn}")
                    rtxt = await visible_text(rp)
                    check(not ISO.search(rtxt), f"{key}/report: no raw ISO date")
                    check(bool(re.search(AR_MONTHS, rtxt)) if lang == "ar" else bool(EN_DATE.search(rtxt)), f"{key}/report: localized date")
                    await rp.emulate_media(media="print")
                    vis = await rp.evaluate("[getComputedStyle(document.querySelector('.hd .logo-prn')).display, getComputedStyle(document.querySelector('.hd .logo-scr')).display]")
                    check(vis == ["block", "none"], f"{key}: print uses light logo {vis}")
                    if tag == "desktop" and theme == "light":
                        await rp.screenshot(path=str(OUT / f"report_print_{lang}.jpg"), type="jpeg", quality=75, full_page=True)
                    await rp.emulate_media(media="screen")
                    check(not errors, f"{key}: no console/page errors {errors[:3]}")
                    await ctx.close()
        # التبديل أثناء التشغيل دون إعادة تحميل
        errors = []; ctx = await b.new_context(viewport={"width": 1440, "height": 900}, timezone_id="UTC")
        await ctx.add_init_script("try{localStorage.setItem('mirsad.lang','\"ar\"');localStorage.setItem('mirsad.theme','\"dark\"');localStorage.setItem('mirsad.tourSeen','1')}catch(e){}")
        pg = await page(ctx, errors); await pg.goto(BASE + "/#about"); await pg.wait_for_timeout(4500)
        await pg.evaluate("window.__noReload = 1")
        await pg.click("#langBtn"); await pg.wait_for_timeout(600)
        check("logo-en-dark" in (await pg.get_attribute(".about-logo", "src")), "runtime: language toggle swaps logo")
        await pg.click("#themeBtn"); await pg.wait_for_timeout(600)
        check("logo-en-light" in (await pg.get_attribute(".about-logo", "src")), "runtime: theme toggle swaps logo")
        await pg.goto(BASE + "/#transparency"); await pg.wait_for_timeout(1200)
        check(bool(EN_DATE.search(await visible_text(pg))), "runtime: dates re-rendered in English")
        await pg.click("#langBtn"); await pg.wait_for_timeout(800)
        check(bool(re.search(AR_MONTHS, await visible_text(pg))), "runtime: dates re-rendered in Arabic")
        check(await pg.evaluate("window.__noReload") == 1, "runtime: no page reload")
        check(not errors, f"runtime: no errors {errors[:3]}")
        await b.close()
    log["failed"] = fails
    (OUT / "result.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MIRSAD_I18N " + json.dumps({"passed": len(log.get("passed", [])), "failed": fails}, ensure_ascii=False))
    sys.exit(1 if fails else 0)


asyncio.run(run())
