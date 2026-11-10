"""مِرصاد · العرض التقديمي الشامل (PDF بمقاس 16:9، الإصدار 2.0.0).

التشغيل:  python docs/report/build_decks.py
المخرج:   docs/presentations/Mirsad_Presentation.pdf
الأرقام كلها مقروءة من الملفات (بطاقة النموذج، قرار v2، حالة الـPRD، الطبقات العامة)، لا أرقام مكتوبة باليد.
الخط: Cairo من Google Fonts (خط الهوية) عند توفر الإنترنت، وإلا DejaVu Sans.
اللقطات: docs/screenshots/v2_*.jpg من الموقع الحي (pipeline/tools/capture_screens.py).
"""
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as ST  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "presentations"
P = ROOT / "data" / "processed"
CARD = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
DEC = json.loads((P / "model_v2_decision.json").read_text(encoding="utf-8"))
RAIN = json.loads((P / "public" / "rain_meta.json").read_text(encoding="utf-8"))
U = lambda p: (ROOT / p).as_uri()
SH = lambda n: U(f"docs/screenshots/v2_{n}.jpg")
LOGO_D, LOGO_L = U("web/brand/logo-ar-dark.svg"), U("web/brand/logo-ar-light.svg")
f = lambda n: f"{n:,}"
SITE, REPO = ST.SITE, ST.REPO
CM = CARD["comparisons"]; V1, V2 = DEC["v1"], DEC["v2"]
SEC = CARD["sector_levels"]; HIGH = SEC["high"] + SEC["critical"]
VERSION = (ROOT / "VERSION").read_text().strip()

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&family=IBM+Plex+Mono:wght@500&display=swap');
@page{size:1920px 1080px;margin:0}
*{box-sizing:border-box}html,body{margin:0}
body{font-family:'Cairo','DejaVu Sans',sans-serif;color:#13242A;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.s{width:1920px;height:1080px;position:relative;overflow:hidden;break-after:page;padding:92px 120px 124px;display:flex;flex-direction:column;gap:30px;background:#FBF6EE}
.s.dark{background:radial-gradient(ellipse at 72% 30%,#1E4148 0%,#13242A 58%,#0C171B 100%);color:#EAF2F0}
.s.gold{background:linear-gradient(135deg,#E3B06A,#D59A4D)}
.eb{font-size:24px;font-weight:700;color:#257C83;letter-spacing:.3px}.dark .eb{color:#38C7B8}.gold .eb{color:#13242A}
h1{font-size:60px;font-weight:800;margin:0;line-height:1.2}h2{font-size:30px;font-weight:700;margin:0 0 4px}
p,li,td,th{font-size:26px;line-height:1.6}.mut{color:#4A5F66}.dark .mut{color:#BFD8D5}
.row{display:flex;gap:26px}.col{display:flex;flex-direction:column;gap:18px;flex:1;min-width:0}
.card{flex:1;background:#fff;border:2px solid #E6DAC6;border-radius:24px;padding:28px 30px;display:flex;flex-direction:column;gap:8px;box-shadow:0 10px 30px rgba(19,36,42,.06)}
.dark .card{background:rgba(28,58,64,.85);border-color:#2B4A50;box-shadow:none}
.card .n{font-size:24px;font-weight:700;color:#B4742D}.dark .card .n{color:#D59A4D}
.card h2{font-size:38px}.card p{margin:0;font-size:25px;line-height:1.6}
.kpi{font-size:68px;font-weight:800;line-height:1;color:#257C83;font-variant-numeric:tabular-nums}.dark .kpi{color:#38C7B8}
.kpi.g{color:#B4742D}.dark .kpi.g{color:#D59A4D}.kpi.r{color:#C2543C}.dark .kpi.r{color:#FF9C8A}
.big{font-size:150px;font-weight:800;line-height:1;color:#38C7B8}
table{width:100%;border-collapse:separate;border-spacing:0;border-radius:16px;overflow:hidden}
th{background:#113637;color:#fff;text-align:right;padding:13px 18px;font-size:22px;font-weight:700}
td{padding:11px 18px;border-bottom:1.5px solid #E6DAC6;font-size:22px;vertical-align:top;line-height:1.45;background:#fff}
tr:nth-child(even) td{background:#FFFBF4}
.dark td{background:rgba(28,58,64,.7);color:#EAF2F0;border-bottom-color:#2B4A50}.dark tr:nth-child(even) td{background:rgba(28,58,64,.45)}
.mono{font-family:'IBM Plex Mono','DejaVu Sans Mono',monospace;direction:ltr;unicode-bidi:embed;font-size:.86em}
.ft{position:absolute;bottom:42px;right:120px;left:120px;display:flex;justify-content:space-between;align-items:center;font-size:19px;color:#4A5F66}
.dark .ft{color:#9FB3B5}.gold .ft{color:#3B2A12}.ft .pn{direction:ltr;font-weight:700}
.ft img{height:34px}
.cr{position:absolute;width:86px;height:86px;border-style:solid;border-width:0}
.cr.a{top:46px;right:46px;border-top-width:5px;border-right-width:5px;border-color:#38C7B8}.cr.b{top:46px;left:46px;border-top-width:5px;border-left-width:5px;border-color:#38C7B8}
.cr.c{bottom:46px;right:46px;border-bottom-width:5px;border-right-width:5px;border-color:#D59A4D}.cr.d{bottom:46px;left:46px;border-bottom-width:5px;border-left-width:5px;border-color:#D59A4D}
.bar{display:grid;grid-template-columns:400px 1fr 120px;gap:22px;align-items:center;font-size:27px;font-weight:600}
.bar .t{height:24px;background:#E9E1D3;border-radius:12px;overflow:hidden}.dark .bar .t{background:#2B4A50}
.bar .t i{display:block;height:100%;background:linear-gradient(90deg,#257C83,#38C7B8);border-radius:12px}.bar b{text-align:left;font-variant-numeric:tabular-nums}
.bar .t i.g{background:linear-gradient(90deg,#B4742D,#D59A4D)}
img.sh{width:100%;border-radius:18px;border:2px solid #2B4A50;display:block;box-shadow:0 18px 50px rgba(0,0,0,.25)}
.flow{display:flex;align-items:stretch;gap:12px}.flow div{flex:1;background:#113637;color:#fff;border-radius:18px;padding:22px 12px;text-align:center;font-size:23px;font-weight:700;line-height:1.35}
.flow div.hl{background:#D59A4D;color:#13242A}
.flow small{display:block;color:#D59A4D;font-size:17px;font-weight:600;margin-top:8px}.flow div.hl small{color:#13242A}
.flow em{align-self:center;color:#D59A4D;font-style:normal;font-size:32px;font-weight:800}
.note{background:#F8E9D2;border:2px solid #D59A4D;color:#5F3D0E;border-radius:18px;padding:18px 26px;font-size:23px;font-weight:600;line-height:1.55}
.dark .note{background:rgba(213,154,77,.12);color:#F0C285}
.ok{color:#1E6A70;font-weight:700}.pt{color:#8A5A12;font-weight:700}.no{color:#A32A16;font-weight:700}
.dark .ok{color:#38C7B8}.dark .pt{color:#F0C285}.dark .no{color:#FF9C8A}
.chip{display:inline-block;border-radius:999px;padding:4px 18px;font-size:20px;font-weight:700;background:#E4F3F1;color:#1E6A70}
.links{display:flex;gap:24px}.links div{flex:1;border-radius:20px;padding:26px 30px;background:#113637;color:#fff}
.links b{display:block;font-size:22px;color:#D59A4D;margin-bottom:8px}.links span{font-family:'IBM Plex Mono',monospace;direction:ltr;unicode-bidi:embed;font-size:28px;color:#38C7B8}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:22px}.grid2 img{width:100%;border-radius:14px;border:2px solid #2B4A50;display:block}
.cap{font-size:20px;text-align:center;margin:8px 0 0}
"""


def foot(i, n, dark):
    return f'<div class="ft"><span>مِرصاد · العرض الشامل · الإصدار {VERSION}</span><img src="{LOGO_D if dark else LOGO_L}"><span class="pn">{i} / {n}</span></div>'


def slide(eb, title, body, cls=""):
    return (cls, f'<section class="s {cls}"><div><div class="eb">{eb}</div><h1>{title}</h1></div>{body}__FOOT__</section>')


def finalize(slides):
    n = len(slides); out = []
    for i, (cls, s) in enumerate(slides, 1):
        out.append(s.replace("__FOOT__", foot(i, n, cls == "dark") if i > 1 and i < n else ""))
    return f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(out)}</body></html>'


def deck():
    S = []
    # 1 الغلاف
    S.append(("dark", f'''<section class="s dark" style="align-items:center;justify-content:center;text-align:center;gap:24px">
<span class="cr a"></span><span class="cr b"></span><span class="cr c"></span><span class="cr d"></span>
<img src="{LOGO_D}" style="width:980px">
<h1 style="font-size:66px">العرض الشامل للمشروع</h1>
<p style="font-size:30px;color:#D59A4D;margin:0">من البيانات إلى إنذار معتمد بشريًا، مع تنبؤ 72 ساعة · الإصدار {VERSION}</p>
<p class="mono" style="font-size:24px;color:#9FB3B5;margin:6px 0 0">{SITE}  ·  {REPO}</p>
<p style="font-size:22px;color:#9FB3B5;margin:0">القروب الثالث · القائد {ST.LEADER} · النائبة {ST.DEPUTY} · {ST.AS_OF}</p></section>__FOOT__'''))
    # 2 المحاور
    S.append(slide("المحاور", "ماذا سنعرض", '''<div class="row" style="flex:1">
<div class="card"><span class="n">01</span><h2>المشروع</h2><p>المشكلة، الحل، المنطقة، مصادر البيانات</p></div>
<div class="card"><span class="n">02</span><h2>العلم</h2><p>النموذج بصراحة، ما يحدد الخطر، التنبؤ 72 ساعة</p></div>
<div class="card"><span class="n">03</span><h2>النظام</h2><p>الخريطة، تفاصيل القطاع، الإنذار والاعتماد، اللغتان</p></div>
<div class="card"><span class="n">04</span><h2>الجودة والحالة</h2><p>التحقق، نسبة الإنجاز، القرارات، الإصدارات، المتبقي</p></div></div>'''))
    # 3 المشكلة
    S.append(slide("المشكلة", "الجبل ما يستأذن قبل ما ينهار", '''<div class="row" style="flex:1">
<div class="card"><span class="n">التضاريس</span><h2>منحدرات حادة</h2><p>انحدار يتجاوز 45° في مرتفعات جازان وعسير والباحة، وطرق وقرى على السفوح.</p></div>
<div class="card"><span class="n">المحفّز</span><h2>أمطار مفاجئة</h2><p>عواصف قصيرة تشبّع التربة خلال ساعات، والسيول تجرف الكتل الصخرية.</p></div>
<div class="card"><span class="n">الفجوة</span><h2>لا إنذار مبكر</h2><p>تحديد المناطق المعرضة يدويًا بطيء ومكلف، والمعلومة توصل بعد الحدث.</p></div></div>
<div class="note">الهدف: خريطة قابلية لكل كيلومتر في المنطقة، وتنبؤ قصير المدى، وإنذار لا يخرج إلا بموافقة إنسان مخوّل.</div>'''))
    # 4 الحل
    S.append(slide("الحل", "من البيانات الخام إلى إنذار مختوم", '''<div class="flow" style="flex:1">
<div>البيانات<small>تضاريس 30 م · غطاء أرضي · أمطار · تربة · صخور · انهيارات</small></div><em>←</em>
<div>النموذج<small>Random Forest بتحقق مكاني وتفسير لكل قطاع</small></div><em>←</em>
<div>الخريطة<small>1,166 قطاعًا بأربعة مستويات</small></div><em>←</em>
<div>التنبؤ<small>أمطار 72 ساعة ÷ عتبة القطاع</small></div><em>←</em>
<div>إنذار مقترح<small>لكل قطاع «مرتفع» فأعلى</small></div><em>←</em>
<div class="hl">اعتماد بشري<small>سجل تدقيق وتقرير مختوم</small></div></div>
<div class="row"><div class="card"><span class="n">آلي</span><p>يتحدّث النموذج أسبوعيًا والتنبؤ كل 6 ساعات على GitHub Actions</p></div>
<div class="card"><span class="n">بشري</span><p>المشغّل يراجع الأسباب ويعتمد أو يرفض، ولا يخرج إنذار بدونه</p></div>
<div class="card"><span class="n">شفاف</span><p>كل رقم معروض بمصدره وحدوده في صفحة الشفافية</p></div></div>'''))
    # 5 المنطقة
    S.append(slide("المنطقة", "جنوب غرب المملكة بالكامل", f'''<div class="row" style="flex:1;align-items:center;gap:50px">
<div style="flex:1.35"><img class="sh" src="{SH('map_level_ar')}"></div>
<div class="col" style="gap:26px">
<div><div class="kpi">{f(CARD["grid_cells"])}</div><p class="mut" style="margin:6px 0 0">خلية تنبؤ بدقة 1 كم</p></div>
<div><div class="kpi g">{f(CARD["sectors"])}</div><p class="mut" style="margin:6px 0 0">قطاعًا (0.1°) للعرض والإنذار</p></div>
<div><div class="kpi r">{HIGH}</div><p class="mut" style="margin:6px 0 0">قطاعًا قابليته مرتفعة أو حرجة</p></div>
<p style="margin:0">جازان · عسير · الباحة · نجران</p></div></div>''', "dark"))
    # 6 البيانات
    pub = CARD.get("public_data", {})
    cov = lambda k: f'{pub[k]["coverage"] * 100:.1f}%' if k in pub else "—"
    S.append(slide("البيانات", "ملفات الفريق + مصادر عامة موثوقة", f'''<table>
<tr><th style="width:22%">الطبقة</th><th style="width:34%">المصدر</th><th style="width:16%">الدقة</th><th style="width:12%">التغطية</th><th>الاستخدام</th></tr>
<tr><td>التضاريس</td><td>Copernicus DEM (وكالة الفضاء الأوروبية)</td><td>30 م</td><td class="ok">100%</td><td>النموذج + الانحناء والتضرّس</td></tr>
<tr><td>الغطاء الأرضي</td><td>ESA WorldCover 2021</td><td>10 م</td><td class="ok">100%</td><td>النموذج</td></tr>
<tr><td>الأمطار اليومية</td><td>CHIRPS v2.0 · {RAIN["years"][0]}–{RAIN["years"][1]}</td><td>0.05°</td><td class="ok">{cov("rain")}</td><td>الخريطة + عتبة التنبؤ</td></tr>
<tr><td>التربة</td><td>SoilGrids 2.0 (ISRIC)</td><td>250 م</td><td class="ok">{cov("soil")}</td><td>الخريطة + v2</td></tr>
<tr><td>الصخور</td><td>BRGM 1:10M عبر Macrostrat</td><td>1:10 مليون</td><td class="ok">{cov("geology")}</td><td>الخريطة + v2</td></tr>
<tr><td>الانهيارات</td><td>ناسا + تقارير إخبارية</td><td>13 موقعًا</td><td class="pt">محدود</td><td>التدريب والتحقق</td></tr>
<tr><td>توقعات الطقس</td><td>Open-Meteo</td><td>ساعي</td><td class="ok">1,166 قطاعًا</td><td>التنبؤ كل 6 ساعات</td></tr></table>
<div class="note">تحقق مستقل: أمطار فيفا 309 مم/سنة وأبها 245، مقابل 126 لمدينة جازان ونجران. الجبال أمطر من الساحل كما هو معروف.</div>'''))
    # 7 النموذج بصراحة
    S.append(slide("النموذج", "قاعدة اعتماد مكتوبة قبل التدريب", f'''<table>
<tr><th style="width:36%">النموذج (تحقق مكاني، نفس الطيّات)</th><th>ROC-AUC</th><th>PR-AUC</th><th>الاستدعاء عند «مرتفع»</th><th style="width:20%">القرار</th></tr>
<tr><td><b>Random Forest v1</b> · 4 مميزات</td><td>{V1["roc_auc"]}</td><td>{V1["pr_auc"]}</td><td>{V1["recall_at_high"]}</td><td class="ok">المعتمد</td></tr>
<tr><td>Random Forest v2 · {len(DEC["features_v2"])} مميزة</td><td><b>{V2["roc_auc"]}</b></td><td>{V2["pr_auc"]}</td><td>{V2["recall_at_high"]}</td><td class="pt">لم يحقق القاعدة</td></tr>
<tr><td>شبكة TensorFlow</td><td>{CM["neural_network_tensorflow"]["roc_auc"]}</td><td>{CM["neural_network_tensorflow"]["pr_auc"]}</td><td>0</td><td class="pt">ق-2</td></tr>
<tr><td>مرجع: الانحدار وحده</td><td>{CARD["reference_slope_only_logistic_spatial_auc"]}</td><td>—</td><td>—</td><td>مرجع</td></tr></table>
<div class="row"><div class="card"><span class="n">القاعدة</span><p>يُعتمد v2 فقط إذا ارتفع ROC-AUC ≥ 0.05 ولم ينخفض PR-AUC ولا الاستدعاء عند «مرتفع».</p></div>
<div class="card"><span class="n">النتيجة</span><p>v2 يرتّب المواقع أفضل بوضوح ({V2["roc_auc"]})، لكن ولا انهيار وصل عتبة «مرتفع»، فبقي v1 (ق-4).</p></div>
<div class="card"><span class="n">السبب الجذري</span><p>{CARD["training"]["positives"]} نقطة انهيار فقط مقابل {f(CARD["training"]["negatives"])}. الحل: سجل أكبر من هيئة المساحة.</p></div></div>'''))
    # 8 ما يحدد الخطر
    ab = DEC["ablation_roc_auc_v1_plus_group"]
    names = {"relief": "التضرّس 1 كم", "soil": "التربة", "slope": "متوسط الانحدار 1 كم", "curvature": "الانحناء", "geology": "الصخور", "rain": "الأمطار"}
    lo = 0.5
    bars = "".join(f'<div class="bar"><span>{names.get(k, k)}</span><span class="t"><i class="{"g" if v < 0.6 else ""}" style="width:{(v - lo) / 0.3 * 100:.0f}%"></i></span><b>{v}</b></div>'
                   for k, v in sorted(ab.items(), key=lambda kv: -kv[1]))
    S.append(slide("ما يحدد الخطر", "أي طبقة تضيف للنموذج؟", f'''<div class="row" style="flex:1;gap:60px;align-items:center">
<div class="col" style="flex:1.5;gap:24px">{bars}
<div class="bar"><span class="mut">v1 وحده (مرجع)</span><span class="t"><i class="g" style="width:{(V1["roc_auc"] - lo) / 0.3 * 100:.0f}%"></i></span><b>{V1["roc_auc"]}</b></div></div>
<div class="col"><div class="card"><span class="n">القراءة</span><p>ROC-AUC المكاني عند إضافة كل طبقة لمميزات v1، بنفس الطيّات.</p></div>
<div class="card"><span class="n">الأقوى</span><p>التضرّس والتربة: شكل السفح ونوع المادة أهم من الأمطار في <b>القابلية</b>.</p></div>
<div class="card"><span class="n">الأمطار</span><p>دورها في <b>التوقيت</b>، لذلك تُستخدم في التنبؤ 72 ساعة لا في القابلية.</p></div></div></div>''', "dark"))
    # 9 الخريطة
    S.append(slide("الموقع", "خريطة واحدة، تسع طبقات", f'''<div class="row" style="flex:1;gap:26px">
<div class="col"><img class="sh" src="{SH('map_fc72_ar')}"><p class="cap mut">الخطر المتوقع خلال 72 ساعة</p></div>
<div class="col"><img class="sh" src="{SH('map_lith_class_ar')}"><p class="cap mut">نوع الصخور</p></div>
<div class="col"><img class="sh" src="{SH('map_rain_annual_mm_ar')}"><p class="cap mut">متوسط الأمطار السنوية</p></div></div>''', "dark"))
    # 10 تفاصيل القطاع
    S.append(slide("تفاصيل القطاع", "لماذا هذا القطاع خطِر؟", f'''<div class="row" style="flex:1;gap:46px;align-items:center">
<div style="flex:1.4"><img class="sh" src="{SH('drawer_ar')}"></div>
<div class="col" style="gap:20px">
<div class="card"><span class="n">الدرجة والمستوى</span><p>درجة القطاع = المئين 90 لخلاياه، ومستوى من أربعة بعتبات قابلة للضبط.</p></div>
<div class="card"><span class="n">الأسباب</span><p>قيم Shapley لكل عامل عند أخطر خلية، بلا صندوق أسود.</p></div>
<div class="card"><span class="n">التنبؤ والطبقات</span><p>أمطار 24/48/72 ساعة ونسبتها للعتبة، والتربة والصخور والتضرّس.</p></div></div></div>''', "dark"))
    # 11 التنبؤ
    S.append(slide("التنبؤ 72 ساعة", "قاعدة شفافة تتحدّث كل 6 ساعات", '''<div class="flow">
<div>Open-Meteo<small>أمطار ساعية لمركز كل قطاع</small></div><em>←</em>
<div>المجموع حتى الأفق<small>24 · 48 · 72 ساعة</small></div><em>←</em>
<div>÷ عتبة القطاع<small>المئين 99 لأمطار 3 أيام (CHIRPS)</small></div><em>←</em>
<div class="hl">المستوى المتوقع<small>+1 عند 50% · +2 عند 100% · لا ينخفض</small></div></div>
<div class="row" style="flex:1">
<div class="card"><span class="n">أول تشغيل حي</span><div class="kpi">255</div><p>قطاعًا «مرتفع» فأعلى خلال 72 ساعة، مقابل 195 بالقابلية وحدها</p></div>
<div class="card"><span class="n">أعلى أمطار متوقعة</span><div class="kpi g">35.5 مم</div><p>في قطاع واحد خلال 72 ساعة</p></div>
<div class="card"><span class="n">الصدق</span><p>قاعدة لا نموذج مُعايَر بأحداث (27 حدثًا مؤرخًا لا تكفي)، ومكتوب ذلك في الواجهة والقرار ق-5. وتنبيه ظاهر إذا تقادم التنبؤ أكثر من 12 ساعة.</p></div></div>'''))
    # 12 الإنذار والاعتماد
    S.append(slide("الإنذار والاعتماد", "لا إنذار يخرج بدون إنسان", f'''<div class="row" style="flex:1;gap:46px;align-items:flex-start">
<div class="col" style="gap:20px">
<div class="card"><span class="n">1 · اقتراح آلي</span><p>كل قطاع «مرتفع» فأعلى يظهر في صفحة الإنذارات بأسبابه.</p></div>
<div class="card"><span class="n">2 · قرار بشري</span><p>المشغّل أو المسؤول يدخل ويعتمد أو يرفض. التصفية بالمستوى والحالة والتاريخ.</p></div>
<div class="card"><span class="n">3 · أثر محفوظ</span><p>سجل تدقيق لكل خطوة، وتقرير قطاع بختم الاعتماد ورقم مرجعي. تحديث النموذج لا يمسح القرارات.</p></div></div>
<div style="flex:1.05;max-height:740px;overflow:hidden;border-radius:18px"><img class="sh" src="{SH('report_ar')}"></div></div>'''))
    # 13 اللغتان
    S.append(slide("لغتان ووضعان", "الشعار والتواريخ يتبعان المستخدم", f'''<div class="grid2" style="flex:1">
<div><img src="{SH('about_ar_dark')}"></div><div><img src="{SH('about_en_dark')}"></div>
<div><img src="{SH('about_ar_light')}"></div><div><img src="{SH('about_en_light')}"></div></div>
<p class="mut" style="margin:0;font-size:22px">أربع نسخ من الشعار بخط Cairo · تواريخ «10 نوفمبر 2026» / «10 Nov 2026» بتوقيت الرياض · تباين نص ≥ 14:1</p>''', "dark"))
    # 14 التقنية
    S.append(slide("التقنية", "يعمل الآن على السحابة", '''<table>
<tr><th style="width:22%">الطبقة</th><th>التقنية</th><th style="width:26%">الحالة</th></tr>
<tr><td>خط المعالجة</td><td>Python · pandas · scikit-learn · TensorFlow للمقارنة</td><td class="ok">أسبوعي آلي</td></tr>
<tr><td>البيانات العامة</td><td>CHIRPS · SoilGrids · Macrostrat · Copernicus عبر GitHub Actions</td><td class="ok">قابلة للإعادة</td></tr>
<tr><td>قاعدة البيانات</td><td>PostgreSQL + PostGIS على Supabase، فهارس GiST</td><td class="ok">حية</td></tr>
<tr><td>الخادم</td><td>Starlette على Vercel · أدوار مشاهد/مشغّل/مسؤول · سجل تدقيق</td><td class="ok">حي</td></tr>
<tr><td>الواجهة</td><td>HTML/CSS/JS · MapLibre GL · خرائط Esri · عربي/إنجليزي · ليلي/نهاري</td><td class="ok">حية</td></tr>
<tr><td>التنبؤ</td><td>Open-Meteo كل 6 ساعات → جدول forecasts</td><td class="ok">آلي</td></tr>
<tr><td>Google Earth</td><td>ملف KMZ بالقطاعات والانهيارات فوق التضاريس ثلاثية الأبعاد</td><td class="ok">للتنزيل</td></tr></table>'''))
    # 15 الجودة
    S.append(slide("الجودة والتحقق", "كل ادعاء له اختبار", '''<div class="row" style="flex:1">
<div class="card"><span class="n">اختبارات آلية</span><div class="kpi">14 / 14</div><p>على SQLite وPostGIS 3.4 مع كل تعديل: معايير القبول، الصلاحيات، التنبؤ، حفظ الاعتمادات</p></div>
<div class="card"><span class="n">فحص المتصفح</span><div class="kpi">118 / 118</div><p>لغتان × وضعان × كمبيوتر وجوال، ومنطقة الجهاز على UTC عمدًا</p></div>
<div class="card"><span class="n">الموقع الحي</span><div class="kpi">0</div><p>أخطاء في المتصفح: الخريطة، الطبقات، التنبؤ، الإنذارات، الشفافية، التقرير</p></div>
<div class="card"><span class="n">معايير القبول</span><div class="kpi">5 / 5</div><p>AC-1 إلى AC-5 من وثيقة المتطلبات</p></div></div>''', "dark"))
    # 16 الإنجاز
    bars = "".join(f'<div class="bar"><span>{n}</span><span class="t"><i style="width:{v}%"></i></span><b>{v}%</b></div>' for n, v, _ in ST.area_pct())
    S.append(slide("نسبة الإنجاز الفعلية", "مقابل وثيقة المتطلبات", f'''<div class="row" style="flex:1;align-items:center;gap:80px">
<div style="width:440px;text-align:center"><div class="big">{ST.OVERALL}%</div><p class="mut" style="margin:10px 0 0">من 26 متطلبًا وظيفيًا<br>Must: {ST.MUST}%</p></div>
<div class="col" style="gap:30px">{bars}</div></div>
<div class="row"><div class="card"><span class="n">مكتمل</span><h2>{ST.DONE} متطلبًا</h2></div>
<div class="card"><span class="n">جزئي</span><h2>{ST.PARTIAL}: سجل الانهيارات، مراجعة الفريق</h2></div>
<div class="card"><span class="n">غير منفذ</span><h2>{ST.NONE}</h2></div></div>''', "dark"))
    # 17 القرارات
    S.append(slide("القرارات", "خمسة قرارات موثّقة بالأرقام", '''<table>
<tr><th style="width:8%">#</th><th style="width:34%">القرار</th><th>المبرر</th></tr>
<tr><td>ق-1</td><td>شبكة 1 كم من تضاريس 30 م، وقطاعات 11 كم</td><td>مواقع الانهيار تقريبية، و30 م تعني 138 مليون خلية</td></tr>
<tr><td>ق-2</td><td>Random Forest بدل الشبكة العصبية</td><td>TensorFlow لم يلتقط أي انهيار عند «مرتفع»</td></tr>
<tr><td>ق-3</td><td>الزلازل خارج النموذج</td><td>صفر زلازل داخل المنطقة، وأقرب حدث 176 كم</td></tr>
<tr><td>ق-4</td><td>v1 باقٍ رغم ROC-AUC أعلى لـv2</td><td>قاعدة مكتوبة قبل التدريب: الاستدعاء نزل</td></tr>
<tr><td>ق-5</td><td>التنبؤ قاعدة شفافة لا نموذج</td><td>27 حدثًا مؤرخًا لا تكفي لمعايرة نموذج زمني</td></tr></table>
<p class="mut" style="margin:0;font-size:22px">التفاصيل والأرقام: <span class="mono">docs/decisions.md</span></p>'''))
    # 18 الإصدارات
    S.append(slide("الإصدارات", f"من 85% إلى {ST.OVERALL}% في إصدارين", f'''<table>
<tr><th style="width:14%">الإصدار</th><th>المحتوى</th><th style="width:14%">الإنجاز</th></tr>
<tr><td><b>{VERSION}</b></td><td>شعار وتواريخ بلغتين، فحص الموقع الحي، سجل القرارات كاملًا</td><td class="ok"><b>{ST.OVERALL}%</b></td></tr>
<tr><td>1.3.0</td><td>تنبؤ 24/48/72 ساعة كل 6 ساعات، وحفظ الاعتمادات عند التحديث</td><td>—</td></tr>
<tr><td>1.2.0</td><td>مميزات v2 ومقارنة v1/v2 بقاعدة مسبقة</td><td>—</td></tr>
<tr><td>1.1.0</td><td>الأمطار والتربة والصخور والانحناء على الخريطة وفي PostGIS</td><td>—</td></tr>
<tr><td>1.0.0</td><td>النسخة الأساسية من البيانات إلى الإنذار المختوم</td><td>85%</td></tr></table>
<p class="mut" style="margin:0;font-size:22px">السجل الكامل: <span class="mono">CHANGELOG.md</span></p>'''))
    # 19 بصراحة
    S.append(slide("بصراحة", "مكتمل تقنيًا، والدقة مقيّدة بالبيانات", f'''<div class="col" style="gap:16px">
<p style="margin:0">• النموذج المعتمد ROC-AUC = <b>{CARD["spatial_cv"]["roc_auc"]}</b> لأن التدريب فيه {CARD["training"]["positives"]} انهيارًا فقط</p>
<p style="margin:0">• v2 أفضل ترتيبًا ({V2["roc_auc"]}) لكنه لم يحقق القاعدة، ولن نغيّرها بعد رؤية النتائج</p>
<p style="margin:0">• الصخور من خريطة قارية 1:10 مليون، والأمطار 10 سنوات فقط</p>
<p style="margin:0">• التنبؤ قاعدة شفافة، والإرسال للجهات محاكى؛ الاعتماد وسجل التدقيق حقيقيان</p>
<p style="margin:0">• الخريطة أداة دعم قرار أكاديمية، وليست أساسًا لقرار ميداني</p></div>
<p style="font-size:30px;font-weight:800;margin:0">لا يُعرض أي رقم دقة غير المقاس فعليًا.</p>''', "gold"))
    # 20 المتبقي
    S.append(slide("المتبقي", f"الـ{100 - ST.OVERALL}% الباقية عمل بشري", '''<div class="row" style="flex:1">
<div class="card"><span class="n">مسار البيانات · FR-D5</span><h2>سجل الانهيارات</h2><p>طلب رسمي لهيئة المساحة الجيولوجية السعودية، وسجلات Youssef وآخرين 2015 (363 انهيارًا في جازان).</p></div>
<div class="card"><span class="n">آلي بعد وصوله</span><h2>الإصدار 2.1</h2><p>إعادة بناء المميزات والتدريب بنفس القاعدة والطيّات، والنشر بأمر واحد.</p></div>
<div class="card"><span class="n">الفريق · FR-T1</span><h2>المراجعة والاعتماد</h2><p>مراجعة التقرير والعرض والأدلة، واعتماد القائد للإصدار.</p></div></div>'''))
    # 21 الفريق والروابط
    S.append(slide("الفريق والروابط", "القروب الثالث · 13 عضوًا · 4 مسارات", f'''<div class="row">
<div class="card"><span class="n">القائد</span><h2>{ST.LEADER}</h2></div><div class="card"><span class="n">النائبة</span><h2>{ST.DEPUTY}</h2></div>
<div class="card" style="flex:2"><span class="n">المسارات</span><p>البيانات الجيولوجية والمناخية · قاعدة البيانات المكانية (GIS) · نمذجة الذكاء الاصطناعي · واجهة الويب والتوثيق</p></div></div>
<div class="links"><div><b>الموقع الحي</b><span>{SITE}</span></div><div><b>المستودع على GitHub</b><span>{REPO}</span></div></div>
<table><tr><th style="width:40%">الملف</th><th>وش فيه</th></tr>
<tr><td class="mono">docs/Mirsad_Project_Report.pdf</td><td>التقرير الشامل بكل المتطلبات والأدلة</td></tr>
<tr><td class="mono">docs/decisions.md · CHANGELOG.md</td><td>القرارات الخمسة، وسجل الإصدارات</td></tr>
<tr><td class="mono">web/data/mirsad_google_earth.kmz</td><td>الخريطة في Google Earth ثلاثية الأبعاد</td></tr></table>''', "dark"))
    # 22 الختام
    S.append(("dark", f'''<section class="s dark" style="align-items:center;justify-content:center;text-align:center;gap:30px">
<span class="cr a"></span><span class="cr b"></span><span class="cr c"></span><span class="cr d"></span>
<img src="{LOGO_D}" style="width:760px">
<h1 style="font-size:64px">لأن دقيقة إنذار… <span style="color:#38C7B8">ممكن تنقذ حياة</span></h1>
<p class="mono" style="font-size:26px;color:#9FB3B5;margin:0">{SITE}</p>
<p style="font-size:24px;color:#D59A4D;margin:0">شكرًا · القروب الثالث</p></section>__FOOT__'''))
    return finalize(S)


async def main():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    html = ROOT / "docs" / "report" / "Mirsad_Presentation.html"
    html.write_text(deck(), encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        await pg.goto(html.as_uri(), wait_until="networkidle"); await pg.wait_for_timeout(2500)
        await pg.pdf(path=str(OUT / "Mirsad_Presentation.pdf"), width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
        await b.close()
    print(OUT / "Mirsad_Presentation.pdf")


if __name__ == "__main__":
    asyncio.run(main())
