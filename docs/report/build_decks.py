"""مِرصاد · العرضان التقديميان بصيغة PDF (16:9).

التشغيل:  python docs/report/build_decks.py
المخرج:   docs/presentations/Mirsad_Presentation.pdf  (العرض الشامل)
          docs/presentations/Mirsad_UI_Docs_Track.pdf (مسار الواجهة والتوثيق)
"""
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as ST  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "presentations"
CARD = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
U = lambda p: (ROOT / p).as_uri()
LOGO, EMB = U("web/logo.png"), U("web/emblem.png")
SH = lambda n: U(f"docs/screenshots/{n}.jpg")
f = lambda n: f"{n:,}"
SITE, REPO = ST.SITE, ST.REPO

CSS = """
@page{size:1920px 1080px;margin:0}
*{box-sizing:border-box}html,body{margin:0}
body{font-family:'DejaVu Sans',sans-serif;color:#13242A}
.s{width:1920px;height:1080px;position:relative;overflow:hidden;break-after:page;padding:100px 120px 130px;display:flex;flex-direction:column;gap:34px;background:#FBF6EE}
.s.dark{background:radial-gradient(ellipse at 70% 35%,#1C3A40 0%,#13242A 60%,#0E1B20 100%);color:#EAF2F0}
.s.gold{background:#D59A4D}
.eb{font-size:24px;font-weight:700;color:#257C83;letter-spacing:.5px}.dark .eb{color:#38C7B8}.gold .eb{color:#13242A}
h1{font-size:64px;margin:0;line-height:1.2}h2{font-size:30px;margin:0 0 6px}
p,li,td,th{font-size:26px;line-height:1.55}.mut{color:#4A5F66}.dark .mut{color:#BFD8D5}
.row{display:flex;gap:28px}.col{display:flex;flex-direction:column;gap:18px;flex:1}
.card{flex:1;background:#fff;border:2px solid #E2D6C2;border-radius:22px;padding:30px 32px;display:flex;flex-direction:column;gap:10px}
.dark .card{background:#1C3A40;border-color:#2B4A50}
.card .n{font-size:26px;font-weight:700;color:#B4742D}.dark .card .n{color:#D59A4D}
.card h2{font-size:42px}.card p{margin:0;font-size:27px;line-height:1.6}
.s > .row{flex:1;max-height:640px}.s > .row > .card{justify-content:center}
.dark td{color:#EAF2F0;border-bottom-color:#2B4A50}.dark tr:nth-child(even) td{background:rgba(255,255,255,.04)}.dark .ok{color:#38C7B8}.dark .pt{color:#F0C285}.dark .no{color:#FF9C8A}
.s > table td{font-size:23px;padding:13px 16px}
.big{font-size:110px;font-weight:700;line-height:1;color:#257C83}.dark .big{color:#38C7B8}
table{width:100%;border-collapse:collapse}th{background:#113637;color:#fff;text-align:right;padding:12px 16px;font-size:22px}
td{padding:10px 16px;border-bottom:1.5px solid #E2D6C2;font-size:21px;vertical-align:top;line-height:1.45}
tr:nth-child(even) td{background:#FFFDF8}
.mono{font-family:'DejaVu Sans Mono',monospace;direction:ltr;unicode-bidi:embed;font-size:.88em}
.ft{position:absolute;bottom:44px;right:120px;left:120px;display:flex;justify-content:space-between;font-size:20px;color:#4A5F66}
.dark .ft{color:#9FB3B5}.gold .ft{color:#3B2A12}
.ft .pn{direction:ltr}
.cr{position:absolute;width:90px;height:90px;border-style:solid;border-width:0}
.cr.a{top:48px;right:48px;border-top-width:5px;border-right-width:5px;border-color:#38C7B8}.cr.b{top:48px;left:48px;border-top-width:5px;border-left-width:5px;border-color:#38C7B8}
.cr.c{bottom:48px;right:48px;border-bottom-width:5px;border-right-width:5px;border-color:#D59A4D}.cr.d{bottom:48px;left:48px;border-bottom-width:5px;border-left-width:5px;border-color:#D59A4D}
.pill{display:inline-block;border-radius:999px;padding:8px 26px;font-size:24px;font-weight:700}
.bar{display:grid;grid-template-columns:440px 1fr 110px;gap:22px;align-items:center;font-size:26px}
.bar .t{height:22px;background:#E9E1D3;border-radius:11px;overflow:hidden}.dark .bar .t{background:#2B4A50}
.bar .t i{display:block;height:100%;background:#38C7B8}.bar b{text-align:left}
img.sh{width:100%;border-radius:16px;border:2px solid #2B4A50;object-fit:contain}
.flow{display:flex;align-items:stretch;gap:14px}.flow div{flex:1;background:#113637;color:#fff;border-radius:16px;padding:22px 14px;text-align:center;font-size:24px;font-weight:700}
.flow small{display:block;color:#D59A4D;font-size:18px;font-weight:400;margin-top:6px}.flow em{align-self:center;color:#D59A4D;font-style:normal;font-size:34px;font-weight:700}
.warn{background:#F8E9D2;border:2px solid #D59A4D;color:#5F3D0E;border-radius:18px;padding:22px 28px;font-size:24px;font-weight:600;line-height:1.5}
.ok{color:#1E6A70;font-weight:700}.pt{color:#8A5A12;font-weight:700}.no{color:#A32A16;font-weight:700}
.links{display:flex;gap:24px}.links div{flex:1;border-radius:18px;padding:22px 28px;background:#113637;color:#fff}
.links b{display:block;font-size:22px;color:#D59A4D;margin-bottom:6px}.links span{font-family:'DejaVu Sans Mono',monospace;direction:ltr;unicode-bidi:embed;font-size:26px;color:#38C7B8}
"""


def foot(title, i, n, dark=False):
    return f'<div class="ft"><span>مِرصاد · {title}</span><span class="pn">{i} / {n}</span></div>'


def cover(title, sub, line):
    return f'''<section class="s dark" style="align-items:center;justify-content:center;text-align:center;gap:26px">
<span class="cr a"></span><span class="cr b"></span><span class="cr c"></span><span class="cr d"></span>
<img src="{LOGO}" style="width:900px">
<h1 style="font-size:70px">{title}</h1>
<p style="font-size:30px;color:#D59A4D;margin:0">{sub}</p>
<p class="mono" style="font-size:24px;color:#9FB3B5;margin:8px 0 0">{SITE}  ·  {REPO}</p>
<p style="font-size:22px;color:#9FB3B5;margin:0">{line}</p></section>'''


def slide(eb, title, body, cls=""):
    return f'<section class="s {cls}"><div><div class="eb">{eb}</div><h1>{title}</h1></div>{body}__FOOT__</section>'


def links_slide():
    return slide("الروابط", "كل شيء في مكانين", f'''
<div class="links"><div><b>الموقع الحي</b><span>{SITE}</span></div><div><b>المستودع على GitHub</b><span>{REPO}</span></div></div>
<table><tr><th style="width:38%">الملف</th><th>وش فيه ولمن</th></tr>
<tr><td class="mono">docs/Mirsad_Project_Report.pdf</td><td>التقرير الشامل: كل ما تم، المتطلبات الـ26 بالأدلة، المتبقي. للمشرف والفريق</td></tr>
<tr><td class="mono">docs/Mirsad_Introduction.pdf</td><td>الدليل التعريفي في 5 صفحات. لأي شخص جديد على المشروع</td></tr>
<tr><td class="mono">docs/user_guide.md</td><td>دليل استخدام الموقع: الحسابات، الخريطة، الإنذارات، التقارير</td></tr>
<tr><td class="mono">docs/team/Mirsad_Team_Sheet.xlsx</td><td>شيت الفريق: كل عضو يسجل ما أنجزه مع الدليل، والقائد يعتمد</td></tr>
<tr><td class="mono">docs/presentations/</td><td>هذا العرض وعرض مسار الواجهة والتوثيق</td></tr></table>''')


def files_slide():
    return slide("الملفات", "ملفات الفريق: وش نظفنا وبأي اسم", '''
<table><tr><th style="width:36%">الملف الأصلي</th><th style="width:16%">الإجراء</th><th>النتيجة</th></tr>
<tr><td class="mono">grid_points_1.csv</td><td class="no">حُذف</td><td>نسخة مطابقة بايت ببايت لـ grid_points.csv</td></tr>
<tr><td class="mono">landslide_points_clean_2.csv</td><td class="no">حُذف</td><td>نسخة مطابقة لـ landslide_points_clean.csv</td></tr>
<tr><td class="mono">All_Saudi_Rainfall_Combined_Final_1.xlsx</td><td class="no">حُذف</td><td>نسخة مطابقة لملف الأمطار المدموج</td></tr>
<tr><td class="mono">grid_points.qmd (النسخة الثانية)</td><td class="no">حُذف</td><td>نسخة مكررة</td></tr>
<tr><td class="mono">All_Saudi_Rainfall_Combined_Final.xlsx</td><td class="pt">فُصل</td><td>جدولان مدموجان → <span class="mono">rainfall_monthly_by_region.csv</span> و<span class="mono">conditioning_factors_282.csv</span></td></tr>
<tr><td class="mono">landslide_points_clean.csv + ناسا</td><td class="pt">دُمج</td><td><span class="mono">landslide_inventory.csv</span>: 27 حدثًا = 13 موقعًا، والتقريبي موسوم</td></tr>
<tr><td class="mono">risk_scores.csv</td><td class="pt">استُبدل</td><td><span class="mono">risk_scores_v1.csv</span> من النموذج الجديد بعتبات الـPRD 0.40/0.60/0.80</td></tr>
<tr><td class="mono">training_table.csv</td><td class="ok">نُظف</td><td>1,689 صفًا (12 انهيارًا)، وتقرير كامل في <span class="mono">cleaning_report.json</span></td></tr></table>''')


def repo_slide():
    return slide("المستودع", "وش في كل مجلد", '''
<table><tr><th style="width:26%">المجلد</th><th>المحتوى والغرض</th></tr>
<tr><td class="mono">data/raw/</td><td>ملفات الفريق كما أُرسلت بعد حذف النسخ المكررة. لا تُعدَّل يدويًا</td></tr>
<tr><td class="mono">data/processed/</td><td>البيانات المنظفة، درجات الخطر، تقريرا التنظيف والجودة</td></tr>
<tr><td class="mono">pipeline/</td><td>خطوات المعالجة: 01 التضاريس (Colab) · 02 التنظيف · 03 التدريب · 04 الجودة · 05 التفسير · 06 Google Earth · run_all يشغلها كلها</td></tr>
<tr><td class="mono">model/</td><td>النموذج المدرّب، المعايرة، بطاقة النموذج بكل المقاييس</td></tr>
<tr><td class="mono">backend/ · api/</td><td>الخادم والصلاحيات والإنذارات، مخطط PostGIS، تحميل القاعدة، مدخل Vercel</td></tr>
<tr><td class="mono">web/</td><td>الموقع: الخريطة، الإنذارات، الشفافية، تقرير القطاع، الدليل التفاعلي</td></tr>
<tr><td class="mono">tests/</td><td>14 اختبارًا آليًا تعمل على كل تعديل (معايير القبول والصلاحيات)</td></tr>
<tr><td class="mono">docs/</td><td>التقارير، الأدلة، العروض، الشيت، وثيقة المتطلبات والهوية، خرائط QGIS، لقطات النظام</td></tr></table>''')


def progress_slide(dark=True):
    bars = "".join(f'<div class="bar"><span>{n}</span><span class="t"><i style="width:{v}%"></i></span><b>{v}%</b></div>' for n, v, _ in ST.area_pct())
    return slide("نسبة الإنجاز الفعلية", "أين وصل المشروع مقابل الـPRD", f'''
<div class="row" style="align-items:center;gap:70px">
<div style="width:420px;text-align:center"><div class="big">{ST.OVERALL}%</div><p class="mut" style="margin:10px 0 0">من 26 متطلبًا وظيفيًا<br>كل واحد مقيس بدليل</p></div>
<div class="col" style="gap:26px">{bars}</div></div>
<div class="row">
<div class="card"><span class="n">مكتمل</span><h2>{ST.DONE} متطلبًا</h2></div>
<div class="card"><span class="n">جزئي</span><h2>{ST.PARTIAL} متطلبًا</h2></div>
<div class="card"><span class="n">غير منفذ</span><h2>{ST.NONE}: التنبؤ 72 ساعة</h2></div>
<div class="card"><span class="n">Must · معايير القبول</span><h2>{ST.MUST}% · 5/5</h2></div></div>''', "dark" if dark else "")


def honest_slide():
    sp = CARD["spatial_cv"]["roc_auc"]
    return slide("بصراحة", "مكتمل تقنيًا، والدقة مقيّدة بالبيانات", f'''
<div class="col" style="gap:20px">
<p style="margin:0">• دقة التحقق المكاني ROC-AUC = <b>{sp}</b>، قريبة من العشوائي (0.5)</p>
<p style="margin:0">• السبب: 12 نقطة انهيار فقط في التدريب مقابل 1,677 نقطة بدون انهيار</p>
<p style="margin:0">• الأمطار لم تدخل النموذج: 24 من 30 منطقة إحداثياتها مؤقتة</p>
<p style="margin:0">• الزلازل: لا يوجد أي حدث من كتالوج USGS داخل منطقة الدراسة</p>
<p style="margin:0">• التنبؤ 72 ساعة غير متاح، والخادم يرجع 501 بدل أرقام وهمية</p>
<p style="margin:0">• الإرسال للجهات محاكى؛ الاعتماد البشري وسجل التدقيق حقيقيان</p></div>
<p style="font-size:30px;font-weight:700;margin:0">أي ادعاء «دقة 95%» في مواد الهوية أو العرض يُحذف.</p>''', "gold")


def finalize(slides, title):
    n = len(slides)
    out = []
    for i, s in enumerate(slides, 1):
        out.append(s.replace("__FOOT__", foot(title, i, n)))
    return f'<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{"".join(out)}</body></html>'


# ===================== العرض الشامل =====================
def deck_main():
    sec = CARD["sector_levels"]
    S = [cover("مِرصاد · العرض الشامل", "نظام التنبؤ بمخاطر الانهيارات الأرضية في جنوب غرب المملكة",
               f"القروب الثالث · القائد {ST.LEADER} · النائبة {ST.DEPUTY} · {ST.AS_OF}")]
    S.append(slide("المحاور", "ماذا سنعرض", '''<div class="row">
<div class="card"><span class="n">01</span><h2>المشروع</h2><p>المشكلة، الحل، المنطقة، البيانات، النموذج</p></div>
<div class="card"><span class="n">02</span><h2>النظام</h2><p>الموقع، الإنذارات، تقرير القطاع، التقنية والنشر</p></div>
<div class="card"><span class="n">03</span><h2>الحالة</h2><p>نسبة الإنجاز الفعلية، الحدود، الملفات</p></div>
<div class="card"><span class="n">04</span><h2>القادم</h2><p>متطلبات كل مسار، الخطة، طريقة المتابعة</p></div></div>'''))
    S.append(slide("المشكلة والهدف", "تحديد المناطق المعرضة للانهيار يدويًا بطيء ومكلف", '''<div class="row">
<div class="card"><span class="n">المشكلة</span><h2>خسائر مباشرة</h2><p>الانهيارات تقطع الطرق وتهدد الأرواح في جبال جازان وعسير والباحة</p></div>
<div class="card"><span class="n">المشكلة</span><h2>بيانات متفرقة</h2><p>تضاريس وأمطار وزلازل وغطاء أرضي من مصادر وصيغ مختلفة</p></div>
<div class="card"><span class="n">الهدف</span><h2>خريطة خطر وإنذار</h2><p>تقدير آلي لكل قطاع، وإنذار لا يخرج إلا بموافقة إنسان مخوّل</p></div></div>''', "dark"))
    S.append(slide("الحل", "من البيانات الخام إلى إنذار معتمد", '''
<div class="flow"><div>البيانات<small>تضاريس · غطاء · انهيارات</small></div><em>←</em><div>التنظيف<small>جودة آلية</small></div><em>←</em>
<div>النموذج<small>Random Forest</small></div><em>←</em><div>القاعدة<small>PostGIS · Supabase</small></div><em>←</em>
<div>الموقع<small>Vercel</small></div><em>←</em><div>الإنذار<small>موافقة بشرية</small></div></div>
<div class="row"><div class="card"><span class="n">آلي</span><p>خط المعالجة كاملًا يُعاد بأمر واحد، ويعمل تلقائيًا كل أسبوع على GitHub</p></div>
<div class="card"><span class="n">مُختبر</span><p>14 اختبارًا آليًا تعمل على كل تعديل، على SQLite وعلى PostGIS</p></div>
<div class="card"><span class="n">شفاف</span><p>كل رقم في الموقع له مصدر، وصفحة الشفافية تعرض المقاييس والحدود</p></div></div>'''))
    S.append(slide("المنطقة", "جنوب غرب المملكة: 1,166 قطاعًا", f'''<div class="row" style="align-items:center;gap:60px">
<img src="{U('docs/assets/places_map.png')}" style="height:720px;border-radius:16px">
<div class="col"><p style="margin:0">خط عرض 16.2 إلى 20.5 · خط طول 40.6 إلى 44.1</p>
<p style="margin:0">جازان · عسير · الباحة · غرب نجران · جنوب مكة</p>
<div class="row"><div class="card"><span class="n">خلية تنبؤ</span><h2>{f(CARD['grid_cells'])}</h2></div><div class="card"><span class="n">مرتفع/حرج</span><h2>{sec['high']} / {sec['critical']}</h2></div></div>
<p class="mut" style="margin:0">الأرقام على الخريطة: 13 مكان انهيار حقيقي مسجّل. 9 منها تقع في قطاعات مرتفعة أو حرجة، مع أن هذه القطاعات 17% فقط من المنطقة.</p></div></div>''', "dark"))
    S.append(files_slide())
    S.append(slide("النموذج", "Random Forest بتقييم مكاني صارم", f'''<div class="row">
<div class="col"><p style="margin:0">• 500 شجرة، أوزان متوازنة للفئات</p><p style="margin:0">• تحقق مكاني بكتل 0.5° كما يطلب الـPRD</p>
<p style="margin:0">• مقارنة مع شبكة عصبية MLP</p><p style="margin:0">• معايرة Isotonic للاحتمالات</p><p style="margin:0">• تفسير Shapley لأهم العوامل في كل قطاع</p></div>
<div class="col"><table><tr><th>النموذج</th><th>ROC-AUC مكاني</th></tr>
<tr><td>Random Forest (المعتمد)</td><td>{CARD['spatial_cv']['roc_auc']}</td></tr>
<tr><td>RF + الزلازل</td><td>{CARD['comparisons']['random_forest_plus_seismic']['roc_auc']}</td></tr>
<tr><td>شبكة عصبية MLP</td><td>{CARD['comparisons']['neural_network_mlp']['roc_auc']}</td></tr>
<tr><td>الانحدار وحده (مرجع)</td><td>{CARD['reference_slope_only_logistic_spatial_auc']}</td></tr></table>
<p class="mut" style="margin:0">حتى نموذج الانحدار وحده تفوق: المشكلة في حجم البيانات لا في الخوارزمية.</p></div></div>'''))
    S.append(slide("الموقع", "خريطة الخطر التفاعلية", f'''<div class="row" style="gap:30px">
<div class="col"><img class="sh" src="{SH('02_map_dark_ar')}"><p class="mut" style="margin:0;font-size:21px">القطاعات بمستوياتها والانهيارات التاريخية</p></div>
<div class="col"><img class="sh" src="{SH('18_drawer_shap_ar')}"><p class="mut" style="margin:0;font-size:21px">تفاصيل القطاع وأهم العوامل</p></div></div>
<p style="margin:0">عربي/إنجليزي · ليلي/نهاري · جوال وكمبيوتر · قمر صناعي · Google Earth · دليل تفاعلي من 9 خطوات</p>''', "dark"))
    S.append(slide("الإنذار والتقرير", "لا إنذار بدون إنسان، والتقرير يُختم", f'''<div class="row" style="gap:40px;align-items:flex-start">
<div class="col"><p style="margin:0">1. النظام يقترح إنذارًا لكل قطاع مرتفع أو حرج</p><p style="margin:0">2. المشغّل يراجع الأسباب ويعتمد أو يرفض</p>
<p style="margin:0">3. القرار يُسجّل باسمه ووقته في سجل التدقيق</p><p style="margin:0">4. لا إنذار ثانٍ للقطاع خلال 24 ساعة</p>
<p style="margin:0">5. تقرير القطاع يُختم «معتمد» باسم المعتمِد وتاريخه</p></div>
<img src="{U('docs/assets/sector_report_approved.png')}" style="height:720px;border-radius:12px;border:2px solid #E2D6C2"></div>'''))
    S.append(slide("التقنية والنشر", "يعمل الآن على السحابة", '''<table><tr><th style="width:24%">الطبقة</th><th>التقنية</th><th style="width:30%">الحالة</th></tr>
<tr><td>البيانات</td><td>Copernicus DEM 30 م · ESA WorldCover · NASA GLC · USGS</td><td class="ok">في المستودع</td></tr>
<tr><td>خط المعالجة</td><td>Python · pandas · scikit-learn</td><td class="ok">تشغيل أسبوعي ناجح</td></tr>
<tr><td>قاعدة البيانات</td><td>PostgreSQL + PostGIS على Supabase</td><td class="ok">1,166 قطاعًا · 126,467 خلية</td></tr>
<tr><td>الخادم</td><td>Starlette على Vercel · أدوار وتدقيق</td><td class="ok">حي</td></tr>
<tr><td>الواجهة</td><td>MapLibre GL · خرائط Esri</td><td class="ok">حي</td></tr>
<tr><td>الاختبارات</td><td>GitHub Actions على SQLite وPostGIS 3.4</td><td class="ok">14 / 14</td></tr></table>''', "dark"))
    S.append(progress_slide())
    S.append(honest_slide())
    S.append(repo_slide())
    AR = dict((n, v) for n, v, _ in ST.area_pct())
    S.append(slide("متطلبات المسارات", "المتبقي على كل مسار للوصول إلى 100%", f'''<div class="row">
<div class="card"><span class="n">البيانات · {AR['البيانات']}%</span><h2>بشري</h2><p>• سجل انهيارات بمئات المواقع (هيئة المساحة)<br>• الخريطة الجيولوجية التفصيلية<br>• أمطار 1991–2015 لعتبات أطول</p></div>
<div class="card"><span class="n">GIS · {AR['قاعدة البيانات المكانية']}%</span><h2>مكتمل</h2><p>• الطبقات والتنبؤ في PostGIS<br>• قرار الدقة (ق-1)<br>• تصدير GPKG اختياري</p></div>
<div class="card"><span class="n">الذكاء الاصطناعي · {AR['الذكاء الاصطناعي']}%</span><h2>مكتمل</h2><p>• مميزات v2 ومقارنة بقاعدة مسبقة (ق-4)<br>• TensorFlow مقارن (ق-2)<br>• إعادة آلية عند وصول السجل</p></div>
<div class="card"><span class="n">الواجهة والتوثيق · {AR['الواجهة والتوثيق']}%</span><h2>مراجعة</h2><p>• التنبؤ 72 ساعة: يعمل (ق-5)<br>• طبقات الخريطة: تعمل<br>• مراجعة الفريق واعتماد القائد</p></div></div>'''))
    S.append(slide("الخطة", f"من {ST.OVERALL}% إلى 100%: ما تبقى بشري", '''<div class="row">
<div class="card"><span class="n">1 · منجز</span><h2>v1.1 → v2.0</h2><p>طبقات عامة (أمطار، تربة، صخور، انحناء)، مميزات v2 بقاعدة مسبقة، تنبؤ 72 ساعة كل 6 ساعات</p></div>
<div class="card"><span class="n">2 · بشري</span><h2>سجل الانهيارات</h2><p>طلب السجل والخريطة الجيولوجية من هيئة المساحة الجيولوجية، وسجلات Youssef وآخرين 2015</p></div>
<div class="card"><span class="n">3 · آلي</span><h2>v2.1</h2><p>عند وصول السجل: إعادة 09 و03 بنفس القاعدة والطيّات، والنشر بأمر واحد</p></div>
<div class="card"><span class="n">4 · اعتماد</span><h2>الإغلاق</h2><p>مراجعة الفريق للتوثيق، واعتماد القائد، وإصدار نهائي</p></div></div>''', "dark"))
    S.append(slide("طريقة المتابعة", "شيت الفريق: سطر لكل عمل", '''<div class="row">
<div class="card"><span class="n">العضو</span><h2>يسجّل</h2><p>التاريخ · اسمه · المسار · ما أنجزه · رابط الدليل · نسبة الإنجاز</p></div>
<div class="card"><span class="n">القائد أو نائبته</span><h2>يعتمد</h2><p>يراجع الدليل ويكتب: معتمد أو باقي، مع ملاحظة</p></div>
<div class="card"><span class="n">الواجهة</span><h2>تتحدث تلقائيًا</h2><p>عدد الأعمال والمعتمد ومتوسط الإنجاز لكل مسار</p></div></div>
<p class="mut" style="margin:0">الملف: <span class="mono">docs/team/Mirsad_Team_Sheet.xlsx</span> · يُرفع على Google Sheets ويُشارك برابط واحد</p>'''))
    S.append(links_slide())
    S.append(f'''<section class="s dark" style="align-items:center;justify-content:center;text-align:center;gap:30px">
<span class="cr a"></span><span class="cr b"></span><span class="cr c"></span><span class="cr d"></span>
<img src="{EMB}" style="width:260px"><h1 style="font-size:110px">شكرًا</h1>
<div class="links" style="width:1400px"><div><b>الموقع</b><span>{SITE}</span></div><div><b>GitHub</b><span>{REPO}</span></div></div></section>''')
    return finalize(S, "العرض الشامل")


# ===================== عرض مسار الواجهة والتوثيق =====================
def deck_track():
    S = [cover("مسار الواجهة والتوثيق", "ما أنجزه المسار، الملفات، والمتطلبات حتى الإغلاق", f"مِرصاد · القروب الثالث · القائد {ST.LEADER} · النائبة {ST.DEPUTY}")]
    S.append(slide("المحاور", "ماذا سنعرض", '''<div class="row">
<div class="card"><span class="n">01</span><h2>الإنجاز</h2><p>نسبة المسار والمهام</p></div>
<div class="card"><span class="n">02</span><h2>الموقع</h2><p>الخريطة والإنذارات والتقرير</p></div>
<div class="card"><span class="n">03</span><h2>التوثيق</h2><p>كل ملف ووش فيه</p></div>
<div class="card"><span class="n">04</span><h2>المتطلبات</h2><p>المهام المتبقية ومعايير قبولها</p></div></div>'''))
    S.append(progress_slide())
    S.append(slide("مهام المسار", "16 مهمة: 8 مكتملة، و8 متبقية", '''<table><tr><th style="width:12%">الرقم</th><th style="width:30%">المهمة</th><th style="width:10%">الإنجاز</th><th>ما يلزم لإغلاقها</th></tr>
<tr><td class="mono">UI-01</td><td>اعتماد وثيقة المتطلبات</td><td>80%</td><td>اعتماد الفريق للنسخة v1.0</td></tr>
<tr><td class="mono">UI-02</td><td>الهوية ورموز التصميم</td><td>60%</td><td>اعتماد ألوان الشعار مصدرًا وحيدًا (القرار 15)</td></tr>
<tr><td class="mono">UI-04</td><td>لوحة القيادة والخريطة</td><td>90%</td><td>اختبار الفريق على الأجهزة</td></tr>
<tr><td class="mono">UI-10</td><td>الطبقات والخريطة الأساسية</td><td>90%</td><td>مراجعة الفريق</td></tr>
<tr><td class="mono">UI-12</td><td>تقرير القطاع PDF</td><td>90%</td><td>مراجعة الطباعة والختم</td></tr>
<tr><td class="mono">DOC-01</td><td>التقرير الفني</td><td>90%</td><td>مراجعة لغوية وعلمية</td></tr>
<tr><td class="mono">DOC-02</td><td>العرض التقديمي</td><td>90%</td><td>مراجعة الفريق وتوزيع أدوار التقديم</td></tr>
<tr><td class="mono">UI-09</td><td>التنبؤ 72 ساعة</td><td>100%</td><td>يعمل كل 6 ساعات (ق-5)</td></tr></table>'''))
    S.append(slide("الموقع", "ما بناه المسار ويعمل الآن", f'''<div class="row" style="gap:30px">
<div class="col"><img class="sh" src="{SH('02_map_dark_ar')}"></div><div class="col"><img class="sh" src="{SH('07_alert_approved_ar')}"></div></div>
<div class="row"><div class="card"><p>الخريطة بأربعة مستويات، قمر صناعي، Google Earth</p></div><div class="card"><p>إنذارات بموافقة بشرية وسجل تدقيق</p></div>
<div class="card"><p>عربي/إنجليزي، ليلي/نهاري، تباين 4.5:1</p></div><div class="card"><p>شاشة تحميل ودليل تفاعلي 9 خطوات</p></div></div>''', "dark"))
    S.append(slide("تقرير القطاع", "تقرير رسمي يُختم بعد الاعتماد", f'''<div class="row" style="gap:40px;align-items:flex-start">
<img src="{U('docs/assets/sector_report_approved.png')}" style="height:720px;border-radius:12px;border:2px solid #E2D6C2">
<div class="col"><p style="margin:0">• رقم مرجع لكل تقرير</p><p style="margin:0">• الدرجة على سلّم المستويات</p><p style="margin:0">• أهم العوامل وتوزيع الخلايا</p>
<p style="margin:0">• حالة الإنذار: معتمد · بانتظار · مرفوض · لا يتطلب</p><p style="margin:0">• ختم «معتمد» باسم المعتمِد وتاريخه</p><p style="margin:0">• يُطبع A4 أو يُحفظ PDF</p></div></div>'''))
    S.append(slide("ملفات التوثيق", "كل ملف ووش فيه", '''<table><tr><th style="width:36%">الملف</th><th>المحتوى</th><th style="width:16%">الحالة</th></tr>
<tr><td class="mono">README.md</td><td>واجهة المستودع: بانر، روابط، لقطات، حالة المشروع، التشغيل</td><td class="ok">محدّث</td></tr>
<tr><td class="mono">docs/Mirsad_Project_Report.pdf</td><td>التقرير الشامل 21 صفحة: سجل العمل والمتطلبات الـ26 بالأدلة</td><td class="ok">محدّث</td></tr>
<tr><td class="mono">docs/Mirsad_Introduction.pdf</td><td>الدليل التعريفي 5 صفحات لأي شخص جديد</td><td class="ok">جديد</td></tr>
<tr><td class="mono">docs/user_guide.md</td><td>دليل المستخدم: الحسابات والخريطة والإنذارات والتقارير</td><td class="ok">محدّث</td></tr>
<tr><td class="mono">docs/technical_report.md</td><td>التقرير الفني: المنهجية والقرارات والنتائج</td><td class="pt">للمراجعة</td></tr>
<tr><td class="mono">docs/presentations/</td><td>العرض الشامل وعرض المسار</td><td class="ok">جديد</td></tr>
<tr><td class="mono">docs/team/Mirsad_Team_Sheet.xlsx</td><td>شيت الفريق المبسّط</td><td class="ok">جديد</td></tr>
<tr><td class="mono">docs/reference/</td><td>وثيقة المتطلبات PRD والهوية والألوان</td><td class="pt">PRD للاعتماد</td></tr>
<tr><td class="mono">docs/screenshots/</td><td>21 لقطة للنظام</td><td class="ok">جاهزة</td></tr></table>'''))
    S.append(slide("متطلبات المسار", "المهام القادمة بمعايير قبول واضحة", '''<table><tr><th style="width:34%">المهمة</th><th>معيار القبول</th><th style="width:14%">المسؤول</th></tr>
<tr><td>اختبار الموقع على 4 أجهزة باللغتين والوضعين</td><td>كل البنود مختبرة، ولا خلل حرج مفتوح، وكل خلل بصورة</td><td>[الاسم]</td></tr>
<tr><td>مراجعة التقرير الفني ودليل المستخدم</td><td>لا تعارض بين أي رقم وملف model.json</td><td>[الاسم]</td></tr>
<tr><td>مراجعة النصوص الإنجليزية</td><td>قائمة تعديلات: الحالي · المقترح · السبب</td><td>[الاسم]</td></tr>
<tr><td>العرض النهائي وأدوار التقديم</td><td>بروفة كاملة في الوقت المسموح، وكل رقم مطابق</td><td>[الاسم]</td></tr>
<tr><td>حذف ادعاء «دقة 95%»</td><td>لا يبقى أي رقم دقة غير المقاس (0.545)</td><td>[الاسم]</td></tr>
<tr><td>جمع أسماء الأعضاء وتعبئة الشيت</td><td>13 اسمًا، وكل عمل برابط دليل</td><td>[الاسم]</td></tr></table>''', "dark"))
    S.append(slide("قرارات المسار", "مفتوحة في الشيت، وأغلبها مطبّق فعليًا", '''<table><tr><th style="width:6%">#</th><th style="width:44%">السؤال</th><th>الوضع الحالي في النظام</th></tr>
<tr><td>7</td><td>لغة واحدة أم لغتين؟</td><td class="ok">مطبّق: عربي وإنجليزي</td></tr>
<tr><td>6</td><td>ثنائي أم ثلاثي الأبعاد؟</td><td class="ok">مطبّق: ثنائي الأبعاد</td></tr>
<tr><td>5</td><td>قناة الإنذار؟</td><td class="ok">مطبّق: لوحة فقط، والإرسال محاكى</td></tr>
<tr><td>11</td><td>الواجهة إذا صار الهدف قابلية ثابتة</td><td class="ok">مطبّق: قابلية ثابتة، والتوقع يرجع 501</td></tr>
<tr><td>15</td><td>ألوان الشعار مصدر وحيد للتصميم</td><td class="pt">مطبّق، ينتظر الاعتماد</td></tr>
<tr><td>14</td><td>حذف ادعاء «دقة 95%»</td><td class="no">يُحذف: الدقة الفعلية 0.545</td></tr>
<tr><td>3</td><td>شريك ميداني للتجربة</td><td class="pt">لا يوجد بعد</td></tr></table>'''))
    S.append(slide("الشيت", "كيف يسجّل كل عضو عمله", '''<div class="row">
<div class="card"><span class="n">1</span><h2>افتح «سجل الإنجاز»</h2><p>من رابط Google Sheets الموحد</p></div>
<div class="card"><span class="n">2</span><h2>اكتب سطرًا</h2><p>التاريخ · اسمك · المسار · ما أنجزته · رابط الدليل · النسبة</p></div>
<div class="card"><span class="n">3</span><h2>انتظر الاعتماد</h2><p>القائد أو نائبته يكتب: معتمد أو باقي</p></div></div>'''))
    S.append(links_slide())
    return finalize(S, "مسار الواجهة والتوثيق")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        for name, html in (("Mirsad_Presentation", deck_main()), ("Mirsad_UI_Docs_Track", deck_track())):
            h = ROOT / "docs" / "report" / f"{name}.html"; h.write_text(html, encoding="utf-8")
            pg = await b.new_page(viewport={"width": 1920, "height": 1080})
            await pg.goto(h.as_uri()); await pg.wait_for_timeout(800)
            await pg.pdf(path=str(OUT / f"{name}.pdf"), width="1920px", height="1080px", print_background=True, prefer_css_page_size=True)
            print(OUT / f"{name}.pdf")
        await b.close()

asyncio.run(main())
