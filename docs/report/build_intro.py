"""مِرصاد · الدليل التعريفي (PDF قصير بهوية المشروع).

التشغيل:  python docs/report/build_intro.py
المخرج:   docs/Mirsad_Introduction.pdf
"""
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as ST  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CARD = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
SHOT = (ROOT / "docs" / "screenshots").as_uri()
LOGO = (ROOT / "web" / "logo.png").as_uri()
EMB = (ROOT / "web" / "emblem.png").as_uri()
f = lambda n: f"{n:,}"
sec = CARD["sector_levels"]

area_bars = "".join(
    f'<div class="br"><span>{n}</span><span class="tr"><i style="width:{v}%"></i></span><b>{v}%</b></div>' for n, v, _ in ST.area_pct())
remaining = "".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in ST.REMAINING)

HTML = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:16mm 15mm 18mm 15mm; }}
:root{{--bg:#13242A;--teal:#38C7B8;--mteal:#257C83;--dteal:#113637;--gold:#D59A4D;--rust:#AC573A;--ink:#13242A;--muted:#4A5F66;--line:#E2D6C2;--sand:#FBF6EE}}
*{{box-sizing:border-box}} body{{font-family:"DejaVu Sans",sans-serif;color:var(--ink);font-size:10.5pt;line-height:1.75;margin:0}}
h2{{font-size:17pt;color:var(--mteal);margin:0 0 8pt;padding-bottom:5pt;border-bottom:2px solid var(--gold)}}
h3{{font-size:11.5pt;margin:12pt 0 4pt}} p{{margin:0 0 8pt}} .muted{{color:var(--muted)}}
.pg{{break-before:page}}
.cover{{height:263mm;background:var(--bg);color:#fff;margin:-16mm -15mm 0;padding:28mm 22mm;position:relative;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center}}
.cover img{{width:120mm}} .cover h1{{font-size:26pt;margin:14mm 0 3mm}} .cover .sub{{color:var(--gold);font-size:12.5pt}}
.cover .links{{margin-top:12mm;font-size:10.5pt;color:#B9CCD3;direction:ltr}}
.cover .meta{{position:absolute;bottom:20mm;inset-inline:22mm;display:flex;justify-content:space-between;font-size:9.5pt;color:#9FB3B5;border-top:1px solid #2B4A50;padding-top:6mm}}
.c{{position:absolute;width:24mm;height:24mm;border-style:solid;border-width:0}}
.c.a{{top:12mm;right:12mm;border-top-width:3px;border-right-width:3px;border-color:var(--teal)}} .c.b{{top:12mm;left:12mm;border-top-width:3px;border-left-width:3px;border-color:var(--teal)}}
.c.d{{bottom:12mm;right:12mm;border-bottom-width:3px;border-right-width:3px;border-color:var(--gold)}} .c.e{{bottom:12mm;left:12mm;border-bottom-width:3px;border-left-width:3px;border-color:var(--gold)}}
.lead{{font-size:12pt;line-height:1.85}}
.cards{{display:grid;grid-template-columns:1fr 1fr;gap:9pt;margin:8pt 0}} .card{{border:1px solid var(--line);border-radius:9pt;padding:10pt 12pt;background:#fff;break-inside:avoid}}
.card b{{display:block;font-size:11.5pt;color:var(--dteal);margin-bottom:2pt}} .card span{{font-size:9.8pt;color:var(--muted)}} .card i{{font-style:normal;color:var(--gold);font-weight:700;margin-left:4pt}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:7pt;margin:10pt 0}} .kpi{{border-radius:8pt;padding:8pt 10pt;background:var(--dteal);color:#fff}}
.kpi span{{font-size:8.5pt;color:#B9CCD3}} .kpi b{{display:block;font-size:16pt;color:var(--teal)}}
.flow{{display:flex;gap:5pt;align-items:center;margin:10pt 0}} .flow div{{flex:1;background:var(--dteal);color:#fff;border-radius:7pt;padding:7pt 6pt;text-align:center;font-size:9pt}}
.flow div small{{display:block;color:var(--gold);font-size:7.8pt}} .flow em{{color:var(--gold);font-style:normal;font-weight:700}}
figure{{margin:6pt 0;text-align:center;break-inside:avoid}} figure img{{width:100%;border:1px solid var(--line);border-radius:6pt}} figcaption{{font-size:8.8pt;color:var(--muted)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:9pt}}
table{{width:100%;border-collapse:collapse;margin:6pt 0 10pt;font-size:9.6pt}} th{{background:var(--dteal);color:#fff;text-align:right;padding:5pt 7pt}}
td{{border-bottom:1px solid var(--line);padding:5pt 7pt;vertical-align:top}} tr:nth-child(even) td{{background:#FDFAF5}}
.mono{{font-family:"DejaVu Sans Mono",monospace;direction:ltr;unicode-bidi:embed}}
.br{{display:grid;grid-template-columns:42mm 1fr 14mm;gap:6pt;align-items:center;font-size:10pt;margin:4pt 0}} .tr{{height:9pt;background:#EEE7DB;border-radius:5pt;overflow:hidden}} .tr i{{display:block;height:100%;background:var(--teal)}} .br b{{text-align:left}}
.warn{{background:#F8E9D2;border:1px solid var(--gold);color:#5F3D0E;border-radius:8pt;padding:9pt 11pt;margin:8pt 0;font-weight:600}}
.box{{background:var(--sand);border:1px solid var(--line);border-radius:8pt;padding:9pt 11pt;margin:8pt 0}}
.end{{text-align:center;margin-top:14pt}} .end img{{width:22mm}}
</style></head><body>

<section class="cover"><span class="c a"></span><span class="c b"></span><span class="c d"></span><span class="c e"></span>
<img src="{LOGO}"><h1>الدليل التعريفي</h1>
<div class="sub">نظام ذكاء اصطناعي لتقدير مخاطر الانهيارات الأرضية في جنوب غرب المملكة</div>
<div class="links">{ST.SITE}<br>{ST.REPO}</div>
<div class="meta"><span>القروب الثالث · القائد {ST.LEADER} · النائبة {ST.DEPUTY}</span><span>مشروع أكاديمي</span><span>{ST.AS_OF}</span></div></section>

<section class="pg">
<h2>مِرصاد في دقيقة</h2>
<p class="lead"><b>مِرصاد</b> يجمع بيانات التضاريس والغطاء الأرضي وسجل الانهيارات السابقة، ويدرّب نموذج ذكاء اصطناعي يقدّر قابلية كل منطقة للانهيار، ثم يعرض النتيجة على خريطة قطاعات تفاعلية، ويقترح إنذارات <b>لا تُعتمد إلا بموافقة إنسان مخوّل</b>.</p>
<h3>لماذا</h3>
<p>الانهيارات الأرضية في جبال جازان وعسير والباحة تقطع الطرق وتهدد الأرواح والمرافق. تحديد المناطق الخطرة يدويًا بطيء ومكلف، والبيانات المؤثرة متفرقة بين مصادر وصيغ مختلفة.</p>
<h3>ماذا يفعل</h3>
<div class="cards">
<div class="card"><b><i>1</i>يجمع البيانات وينظفها</b><span>ارتفاعات وانحدارات من صور أقمار صناعية بدقة 30 م، وغطاء أرضي، وسجل انهيارات من الأخبار وكتالوج ناسا</span></div>
<div class="card"><b><i>2</i>يقدّر الخطر</b><span>نموذج Random Forest يعطي كل خلية بحجم 1 كم درجة خطر، ويشرح أهم العوامل التي رفعتها</span></div>
<div class="card"><b><i>3</i>يعرض الخريطة</b><span>{f(CARD['sectors'])} قطاعًا بأربعة مستويات: منخفض، متوسط، مرتفع، حرج، مع تقرير قابل للطباعة لكل قطاع</span></div>
<div class="card"><b><i>4</i>يقترح الإنذار</b><span>كل قطاع مرتفع أو حرج يُقترح له إنذار، ويعتمده مشغّل مخوّل باسمه ووقته، ويُختم تقريره</span></div>
</div>
<h3>لمن</h3>
<table><tr><th>المستخدم</th><th>ما يستفيده</th></tr>
<tr><td>فرق الطوارئ</td><td>القطاعات الأعلى خطرًا واعتماد الإنذارات</td></tr>
<tr><td>المخططون العمرانيون</td><td>الانحدار والارتفاع والغطاء لكل قطاع قبل التخطيط</td></tr>
<tr><td>الباحثون والمشرفون</td><td>صفحة الشفافية، المقاييس، والكود القابل لإعادة الإنتاج</td></tr></table>
<div class="kpis"><div class="kpi"><span>خلية تنبؤ</span><b>{f(CARD['grid_cells'])}</b></div><div class="kpi"><span>قطاعًا</span><b>{f(CARD['sectors'])}</b></div>
<div class="kpi"><span>مرتفع أو حرج</span><b>{sec['high'] + sec['critical']}</b></div><div class="kpi"><span>اختبار ناجح</span><b>12/12</b></div></div>
</section>

<section class="pg">
<h2>كيف يعمل</h2>
<div class="flow"><div>البيانات<small>تضاريس · انهيارات</small></div><em>←</em><div>التنظيف<small>جودة آلية</small></div><em>←</em><div>النموذج<small>تحقق مكاني</small></div><em>←</em><div>القاعدة<small>PostGIS · Supabase</small></div><em>←</em><div>الموقع<small>Vercel</small></div><em>←</em><div>الإنذار<small>موافقة بشرية</small></div></div>
<p>كل خطوة كود في المستودع، وتُعاد كاملة بأمر واحد كل أسبوع تلقائيًا. الاختبارات تعمل على كل تعديل.</p>
<h2 style="margin-top:12pt">ماذا ترى في الموقع</h2>
<div class="two">
<figure><img src="{SHOT}/02_map_dark_ar.jpg"><figcaption>الخريطة: القطاعات بمستويات الخطر والانهيارات التاريخية</figcaption></figure>
<figure><img src="{SHOT}/18_drawer_shap_ar.jpg"><figcaption>تفاصيل القطاع: الدرجة وأهم العوامل المؤثرة</figcaption></figure>
<figure><img src="{SHOT}/07_alert_approved_ar.jpg"><figcaption>الإنذارات: اقتراح آلي واعتماد بشري</figcaption></figure>
<figure><img src="{SHOT}/09_transparency_light_en.jpg"><figcaption>الشفافية: المقاييس والمصادر والحدود</figcaption></figure>
</div>
<p class="muted">عربي وإنجليزي · وضع ليلي ونهاري · جوال وكمبيوتر · صور أقمار صناعية · فتح أي قطاع في Google Earth.</p>
</section>

<section class="pg">
<h2>أين وصلنا</h2>
<div class="kpis"><div class="kpi"><span>نسبة الإنجاز الفعلية</span><b>{ST.OVERALL}%</b></div><div class="kpi"><span>متطلبات Must</span><b>{ST.MUST}%</b></div>
<div class="kpi"><span>معايير القبول</span><b>5/5</b></div><div class="kpi"><span>دقة التحقق المكاني</span><b>{CARD['spatial_cv']['roc_auc']}</b></div></div>
<p>النسبة محسوبة من 26 متطلبًا وظيفيًا في وثيقة المتطلبات، كل واحد مقيس بدليل: {ST.DONE} مكتمل، {ST.PARTIAL} جزئي، {ST.NONE} غير منفذ.</p>
{area_bars}
<div class="warn">بصراحة: النظام مكتمل تقنيًا ويعمل من البيانات إلى الإنذار، لكن دقة التنبؤ ({CARD['spatial_cv']['roc_auc']}) قريبة من العشوائي لأن سجل الانهيارات فيه {CARD['training']['positives']} نقطة فقط. الخريطة اليوم أداة دعم قرار أكاديمية، لا أساس لقرار ميداني.</div>
<h3>المتبقي للوصول إلى 100%</h3>
<table><tr><th>المسار</th><th>المتبقي</th></tr>{remaining}</table>
<div class="box">أهم خطوة قادمة: سجل انهيارات بمئات المواقع. حددنا بحثين منشورين عن جازان فيهما 363 انهيارًا موثقًا (Youssef وآخرون 2015)، والطلب منهم أو من هيئة المساحة الجيولوجية يرفع الدقة فعليًا.</div>
</section>

<section class="pg">
<h2>ابدأ الآن</h2>
<table><tr><th>تريد</th><th>اذهب إلى</th></tr>
<tr><td>تجربة النظام</td><td class="mono">{ST.SITE}</td></tr>
<tr><td>الكود والبيانات</td><td class="mono">{ST.REPO}</td></tr>
<tr><td>كل التفاصيل</td><td class="mono">docs/Mirsad_Project_Report.pdf</td></tr>
<tr><td>طريقة الاستخدام</td><td class="mono">docs/user_guide.md</td></tr>
<tr><td>تسجيل ما أنجزته</td><td class="mono">docs/team/Mirsad_Team_Sheet.xlsx</td></tr></table>
<h3>الحسابات</h3>
<table><tr><th>الحساب</th><th>اسم المستخدم</th><th>يقدر</th></tr>
<tr><td>زائر</td><td>بدون دخول</td><td>الخريطة والتقارير والشفافية</td></tr>
<tr><td>مشغّل</td><td class="mono">operator</td><td>اعتماد الإنذارات أو رفضها</td></tr>
<tr><td>مسؤول</td><td class="mono">admin</td><td>تعديل العتبات وسجل التدقيق</td></tr></table>
<p class="muted">كلمات المرور عند قائد المشروع، ومحفوظة في أسرار المستودع فقط.</p>
<h3>الفريق</h3>
<p>القروب الثالث · القائد: <b>{ST.LEADER}</b> · النائبة: <b>{ST.DEPUTY}</b> · 13 عضوًا في 4 مسارات: البيانات الجيولوجية والمناخية · قاعدة البيانات المكانية (GIS) · نمذجة الذكاء الاصطناعي · واجهة الويب والتوثيق.</p>
<div class="end"><img src="{EMB}"><p class="muted">مِرصاد · رصد مبكر لمخاطر الانهيارات الأرضية</p></div>
</section>
</body></html>"""


async def main():
    out_html = ROOT / "docs" / "report" / "intro.html"
    out_html.write_text(HTML, encoding="utf-8")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        pg = await b.new_page()
        await pg.goto(out_html.as_uri()); await pg.wait_for_timeout(800)
        foot = ('<div style="font-family:DejaVu Sans;font-size:8px;color:#4A5F66;width:100%;padding:0 15mm;display:flex;justify-content:space-between">'
                '<span>مِرصاد · الدليل التعريفي</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        await pg.pdf(path=str(ROOT / "docs" / "Mirsad_Introduction.pdf"), format="A4", print_background=True,
                     display_header_footer=True, header_template="<span></span>", footer_template=foot, prefer_css_page_size=True)
        await b.close()
    print("docs/Mirsad_Introduction.pdf")

asyncio.run(main())
