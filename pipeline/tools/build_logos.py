"""مِرصاد · بناء الشعار بلغتين ووضعين: web/brand/logo-{ar,en}-{dark,light}.svg

- الرمز (emblem) وكلمة «مرصاد» الفنية تؤخذان من web/logo.png الأصلي كما هما (صورة مضمّنة)،
  وفي الوضع الداكن تُفتَّح حروف الكلمة لتقرأ على الخلفية الداكنة.
- كلمة «Mirsad» والشعار النصي (tagline) بخط الهوية Cairo محوّلًا إلى مسارات متجهة (HarfBuzz + fontTools)،
  فلا يعتمد الملف على أي خط مثبت عند المستخدم.
- الألوان من هوية المشروع، وتباين النص مقيس ومطبوع (WCAG).

يعمل على GitHub Actions (يجلب خط Cairo من مستودع Google Fonts): .github/workflows/brand.yml
"""
import base64, io, json, sys, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "brand"; OUT.mkdir(parents=True, exist_ok=True)
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/cairo/Cairo%5Bslnt%2Cwght%5D.ttf"
BG = {"dark": "#0F1E23", "light": "#F6F1E8"}                       # خلفيات الموقع (styles.css)
INK = {"dark": "#E6EEEC", "light": "#13242A"}                      # نص أساسي
GOLD = {"dark": "#D59A4D", "light": "#924224"}                     # الكلمة المميّزة في الشعار النصي
TAG = {"ar": [("نظام التنبؤ بمخاطر ", "ink"), ("الانهيارات الأرضية", "gold")],
       "en": [("Landslide", "gold"), (" Risk Prediction System", "ink")]}
W, H = 2000, 790


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def png_uri(im, max_w):
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


def font():
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    raw = urllib.request.urlopen(urllib.request.Request(FONT_URL, headers={"User-Agent": "mirsad-brand"}), timeout=120).read()
    out = {}
    for w in (700, 800):
        f = TTFont(io.BytesIO(raw)); inst = instancer.instantiateVariableFont(f, {"wght": w, "slnt": 0})
        b = io.BytesIO(); inst.save(b); out[w] = b.getvalue()
    return out


def text_path(fontbytes, text, size, rtl):
    """يشكّل النص بـHarfBuzz ويحوّله إلى مسار SVG. يرجع (d، العرض) بوحدات البكسل وخط الأساس عند y=0."""
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    face = hb.Face(fontbytes); fnt = hb.Font(face); upem = face.upem
    buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
    buf.direction = "rtl" if rtl else "ltr"
    hb.shape(fnt, buf, {"kern": True, "liga": True})
    tt = TTFont(io.BytesIO(fontbytes)); gs = tt.getGlyphSet(); order = tt.getGlyphOrder()
    s = size / upem; x = 0; parts = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(gs)
        gs[order[info.codepoint]].draw(TransformPen(pen, (s, 0, 0, -s, (x + pos.x_offset) * s, -pos.y_offset * s)))
        parts.append(pen.getCommands()); x += pos.x_advance
    return " ".join(p for p in parts if p), x * s


def wordmark_ar(theme):
    """كلمة «مرصاد» الفنية من الشعار الأصلي؛ في الوضع الداكن تُفتَّح الحروف الداكنة مع إبقاء الخط الفيروزي."""
    im = Image.open(ROOT / "web" / "logo.png").convert("RGBA").crop((820, 30, 1994, 545))
    a = np.asarray(im).astype(np.float32)
    if theme == "dark":
        rgb, al = a[..., :3], a[..., 3]
        l = rgb @ np.array([0.299, 0.587, 0.114])
        dark = (l < 70) & (al > 40)
        ink = np.array([int(INK["dark"][i:i + 2], 16) for i in (1, 3, 5)], np.float32)
        rgb[dark] = ink
        a[..., :3] = rgb
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def build():
    f = font()
    emblem = png_uri(Image.open(ROOT / "web" / "logo.png").convert("RGBA").crop((0, 0, 800, 790)), 420)
    report = {"palette": {"ink": INK, "gold": GOLD, "bg": BG}, "contrast": {}}
    for lang in ("ar", "en"):
        for theme in ("dark", "light"):
            body = [f'<image href="{emblem}" x="0" y="0" width="800" height="790"/>']
            if lang == "ar":
                body.append(f'<image href="{png_uri(wordmark_ar(theme), 700)}" x="820" y="30" width="1174" height="515"/>')
            else:
                d, w = text_path(f[800], "Mirsad", 400, False)
                sc = min(1.0, 1120 / w)
                body.append(f'<path transform="translate(850 470) scale({sc:.4f})" fill="{INK[theme]}" d="{d}"/>')
                body.append('<rect x="856" y="505" width="190" height="14" rx="7" fill="#38C7B8"/>')
            # الشعار النصي: مقاطع متتالية بلونين، تُحاذى يمينًا للعربية ويسارًا للإنجليزية
            segs = [(text_path(f[700], txt, 78, lang == "ar"), col) for txt, col in TAG[lang]]
            total = sum(w for (_, w), _ in segs); sc = min(1.0, 1140 / total)
            x = 1990 if lang == "ar" else 850
            for (d, w), col in segs:
                w *= sc
                x0 = x - w if lang == "ar" else x
                body.append(f'<path transform="translate({x0:.1f} 640) scale({sc:.4f})" fill="{(INK if col == "ink" else GOLD)[theme]}" d="{d}"/>')
                x = x0 if lang == "ar" else x0 + w
            title = "مِرصاد · نظام التنبؤ بمخاطر الانهيارات الأرضية" if lang == "ar" else "Mirsad · Landslide Risk Prediction System"
            svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
                   f'aria-label="{title}"><title>{title}</title>{"".join(body)}</svg>')
            (OUT / f"logo-{lang}-{theme}.svg").write_text(svg, encoding="utf-8")
            report["contrast"][f"{lang}-{theme}"] = {"ink_vs_bg": contrast(INK[theme], BG[theme]),
                                                     "gold_vs_bg": contrast(GOLD[theme], BG[theme]),
                                                     "ink_vs_white" if theme == "light" else "ink_vs_surface":
                                                         contrast(INK[theme], "#FFFFFF" if theme == "light" else "#16292F")}
    report["sizes_kb"] = {p.name: round(p.stat().st_size / 1024, 1) for p in sorted(OUT.glob("*.svg"))}
    (OUT / "brand_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    build()
