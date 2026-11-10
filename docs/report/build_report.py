"""مِرصاد · توليد التقرير الشامل (PDF) من بيانات المستودع.

التشغيل:  python docs/report/build_report.py   (يتطلب playwright + Chrome)
المخرج:   docs/Mirsad_Project_Report.pdf
"""
import json, asyncio, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as ST  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CARD = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
CL = CARD["cleaning"]
REPO = "https://github.com/4-u1/Mirsad"
SHOT = (ROOT / "docs" / "screenshots").as_uri()
LOGO = (ROOT / "web" / "logo.png").as_uri()
EMB = (ROOT / "web" / "emblem.png").as_uri()
f = lambda n: f"{n:,}"

def bars(rows, color="var(--teal)", fmt=lambda v: f"{v}", mx=None):
    mx = mx or max(v for _, v in rows) or 1
    return "".join(f'<div class="br"><span>{k}</span><span class="tr"><i style="width:{v/mx*100:.1f}%;background:{c if isinstance(c:=color, str) else color[i]}"></i></span><b>{fmt(v)}</b></div>'
                   for i, (k, v) in enumerate(rows))

def prd_table():
    lab = lambda v: ('ok', 'مكتمل') if v >= 1 else (('no', 'غير منفذ') if v == 0 else ('part', 'جزئي'))
    rows = "".join(f'<tr><td class="mono">{i}</td><td>{t}</td><td>{p}</td><td class="{lab(v)[0]}">{lab(v)[1]} · {round(v*100)}%</td><td>{e}</td></tr>' for i, t, p, v, e in ST.PRD)
    return '<table><tr><th>المعرّف</th><th>المتطلب</th><th>الأولوية</th><th>التحقق</th><th>الدليل أو الناقص</th></tr>' + rows + '</table>'

def worklog():
    return '<table><tr><th>التاريخ</th><th>المجال</th><th>ما تم</th></tr>' + "".join(f'<tr><td style="white-space:nowrap">{d}</td><td>{a}</td><td>{w}</td></tr>' for d, a, w in ST.WORKLOG) + '</table>'

def fig(name, cap):
    return f'<figure><img src="{SHOT}/{name}.jpg"><figcaption>{cap}</figcaption></figure>'

LV = {"low": "منخفض", "medium": "متوسط", "high": "مرتفع", "critical": "حرج"}
LVC = ["#5E7F8C", "#D59A4D", "#AC573A", "#D9412B"]
dist, secl = CARD["level_distribution"], CARD["sector_levels"]
sp, rc = CARD["spatial_cv"], CARD["random_cv"]

HTML = f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
@page {{ size:A4; margin:18mm 16mm 20mm 16mm; }}
:root{{--bg:#13242A;--teal:#38C7B8;--mteal:#257C83;--dteal:#113637;--gold:#D59A4D;--ochre:#B4742D;--rust:#AC573A;--ink:#13242A;--muted:#4A5F66;--line:#E2D6C2;--sand:#FBF6EE}}
*{{box-sizing:border-box}} body{{font-family:"DejaVu Sans",sans-serif;color:var(--ink);font-size:10.5pt;line-height:1.75;margin:0}}
h1{{font-size:21pt;margin:0 0 6pt;color:var(--ink)}} h2{{font-size:15pt;color:var(--mteal);margin:18pt 0 6pt;padding-bottom:4pt;border-bottom:2px solid var(--gold);break-after:avoid}}
h3{{font-size:11.5pt;margin:12pt 0 4pt;color:var(--ink);break-after:avoid}} p{{margin:0 0 7pt}} .muted{{color:var(--muted)}}
.cover{{height:257mm;background:var(--bg);color:#fff;margin:-18mm -16mm 0;padding:28mm 22mm;position:relative;break-after:page;display:flex;flex-direction:column;justify-content:center}}
.cover img{{width:118mm;align-self:center}} .cover h1{{color:#fff;font-size:24pt;text-align:center;margin-top:16mm}}
.cover .sub{{text-align:center;color:var(--gold);font-size:12pt}} .cover .meta{{position:absolute;bottom:22mm;inset-inline:22mm;display:flex;justify-content:space-between;font-size:9.5pt;color:#9FB3B5;border-top:1px solid #2B4A50;padding-top:6mm}}
.cover .c{{position:absolute;width:26mm;height:26mm;border-style:solid;border-width:0}} .c.a{{top:12mm;right:12mm;border-top-width:3px;border-right-width:3px;border-color:var(--teal)}}
.c.b{{top:12mm;left:12mm;border-top-width:3px;border-left-width:3px;border-color:var(--teal)}} .c.d{{bottom:12mm;right:12mm;border-bottom-width:3px;border-right-width:3px;border-color:var(--gold)}} .c.e{{bottom:12mm;left:12mm;border-bottom-width:3px;border-left-width:3px;border-color:var(--gold)}}
.box{{background:var(--sand);border:1px solid var(--line);border-radius:8pt;padding:9pt 11pt;margin:8pt 0;break-inside:avoid}}
.warn{{background:#F8E9D2;border:1px solid var(--gold);color:#5F3D0E;border-radius:8pt;padding:9pt 11pt;margin:8pt 0;font-weight:600;break-inside:avoid}}
table{{width:100%;border-collapse:collapse;margin:6pt 0 10pt;font-size:9.5pt;break-inside:auto}} th{{background:var(--dteal);color:#fff;text-align:right;padding:5pt 7pt;font-weight:700}}
td{{border-bottom:1px solid var(--line);padding:5pt 7pt;vertical-align:top}} tr:nth-child(even) td{{background:#FDFAF5}} tr{{break-inside:avoid}}
.mono{{font-family:"DejaVu Sans Mono",monospace;direction:ltr;unicode-bidi:embed}}
code{{font-family:"DejaVu Sans Mono",monospace;font-size:8.8pt;background:#F1ECE2;border-radius:3pt;padding:0 3pt;direction:ltr;unicode-bidi:embed}}
pre{{font-family:"DejaVu Sans Mono",monospace;font-size:8.6pt;background:var(--bg);color:#E6EEEC;border-radius:6pt;padding:8pt 10pt;direction:ltr;text-align:left;white-space:pre-wrap;break-inside:avoid}}
figure{{margin:8pt 0 12pt;break-inside:avoid;text-align:center}} figure img{{width:100%;border:1px solid var(--line);border-radius:6pt}} figcaption{{font-size:9pt;color:var(--muted);margin-top:3pt}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:10pt}} .two figure img{{max-height:118mm;object-fit:contain}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:7pt;margin:8pt 0}} .kpi{{border:1px solid var(--line);border-radius:7pt;padding:7pt 9pt;background:#fff;break-inside:avoid}}
.kpi span{{font-size:8.5pt;color:var(--muted)}} .kpi b{{display:block;font-size:15pt}}
.br{{display:grid;grid-template-columns:34mm 1fr 18mm;gap:6pt;align-items:center;font-size:9.5pt;margin:3pt 0}} .tr{{height:8pt;background:#EEE7DB;border-radius:4pt;overflow:hidden}} .tr i{{display:block;height:100%}} .br b{{text-align:left;font-weight:600}}
.flow{{display:flex;flex-wrap:wrap;gap:5pt;align-items:center;margin:8pt 0;break-inside:avoid}} .flow div{{background:var(--dteal);color:#fff;border-radius:6pt;padding:6pt 8pt;font-size:8.8pt;text-align:center;flex:1;min-width:24mm}}
.flow div small{{display:block;color:var(--gold);font-size:7.8pt}} .flow em{{color:var(--gold);font-style:normal;font-weight:700}}
.toc li{{margin:2pt 0}} .ok{{color:#1E6A70;font-weight:700}} .no{{color:#A32A16;font-weight:700}} .part{{color:#7A4E12;font-weight:700}}
.pb{{break-before:page}}
</style></head><body>

<section class="cover"><span class="c a"></span><span class="c b"></span><span class="c d"></span><span class="c e"></span>
<img src="{LOGO}"><h1>التقرير الشامل لمشروع مِرصاد</h1>
<div class="sub">نظام التنبؤ بمخاطر الانهيارات الأرضية · كل ما تم، والحالة الفعلية مقابل الـPRD، والمتبقي</div>
<div class="sub" style="margin-top:6mm;color:#9FB3B5;font-size:10.5pt" dir="ltr">{ST.SITE} · {REPO}</div>
<div class="meta"><span>القروب الثالث · 13 عضوًا · 4 مسارات</span><span class="mono">{REPO}</span><span>{ST.AS_OF}</span></div></section>

<h2>المحتويات</h2>
<ol class="toc"><li>الملخص التنفيذي والروابط</li><li>المشكلة والأهداف</li><li>المستخدمون</li><li>معمارية النظام</li><li>البيانات والتنظيف</li><li>النموذج والنتائج</li>
<li>منطق الخطر والإنذار</li><li>Google Earth والخرائط</li><li>الواجهة: جولة مصوّرة</li><li>الخادم وواجهات البرمجة</li><li>الأمان والصلاحيات</li><li>الاختبار ومعايير القبول</li>
<li>سجل العمل ونسبة الإنجاز الفعلية مقابل الـPRD</li><li>الحدود المعروفة</li><li>المتبقي وخارطة الطريق</li><li>التشغيل والنشر</li><li>هيكل المستودع</li><li>الفريق وطريقة المتابعة</li></ol>

<h2>1. الملخص التنفيذي</h2>
<p>مِرصاد منصة ذكاء اصطناعي تقدّر قابلية الانهيارات الأرضية في جنوب غرب المملكة (عرض 16.2°–20.5°، طول 40.6°–44.1°)، وتعرضها على خريطة قطاعات تفاعلية، وتقترح إنذارات لا تُعتمد إلا بموافقة بشرية. النظام مكتمل تقنيًا من البيانات الخام إلى الإنذار: خط معالجة قابل لإعادة التشغيل، نموذج مدرّب، خادم API بصلاحيات وسجل تدقيق، وواجهة ويب بالعربية والإنجليزية بوضعين ليلي ونهاري.</p>
<div class="kpis"><div class="kpi"><span>خلايا التنبؤ (≈1 كم)</span><b>{f(CARD['grid_cells'])}</b></div><div class="kpi"><span>القطاعات (≈11 كم)</span><b>{f(CARD['sectors'])}</b></div>
<div class="kpi"><span>قطاعات مرتفعة/حرجة</span><b>{secl['high']} / {secl['critical']}</b></div><div class="kpi"><span>ROC-AUC (تحقق مكاني)</span><b>{sp['roc_auc']}</b></div></div>
<div class="warn">حدود الدقة: أداء النموذج في التحقق المكاني ROC-AUC = {sp['roc_auc']} لأن جدول التدريب يحتوي {CARD['training']['positives']} نقطة انهيار فقط. النظام مكتمل ويعمل من البيانات إلى الإنذار، لكن جودة التنبؤ مقيّدة بسجل الانهيارات، ولا يُعتمد عليها لقرار ميداني قبل توسيعه.</div>
<div class="kpis"><div class="kpi"><span>نسبة الإنجاز الفعلية (PRD)</span><b>{ST.OVERALL}%</b></div><div class="kpi"><span>متطلبات Must</span><b>{ST.MUST}%</b></div>
<div class="kpi"><span>معايير القبول</span><b>5 / 5</b></div><div class="kpi"><span>اختبارات آلية</span><b>12 / 12</b></div></div>
<table><tr><th>المخرج</th><th>الرابط</th></tr>
<tr><td>الموقع الحي (Vercel + Supabase)</td><td class="mono">{ST.SITE}</td></tr>
<tr><td>المستودع: الكود والبيانات والتوثيق</td><td class="mono">{REPO}</td></tr>
<tr><td>هذا التقرير الشامل</td><td class="mono">docs/Mirsad_Project_Report.pdf</td></tr>
<tr><td>الدليل التعريفي</td><td class="mono">docs/Mirsad_Introduction.pdf</td></tr>
<tr><td>دليل المستخدم · التقرير الفني</td><td class="mono">docs/user_guide.md · docs/technical_report.md</td></tr>
<tr><td>شيت الفريق</td><td class="mono">docs/team/Mirsad_Team_Sheet.xlsx</td></tr>
<tr><td>وثيقة المتطلبات والهوية</td><td class="mono">docs/reference/</td></tr></table>

<h2>2. المشكلة والأهداف</h2>
<p>الانهيارات الأرضية تسبب خسائر في الأرواح والطرق والمرافق، وتحديد المناطق الخطرة يدويًا بطيء ومكلف وصعب التحديث، والبيانات المؤثرة (التضاريس، الغطاء الأرضي، الأمطار، الزلازل) تأتي من مصادر وصيغ مختلفة.</p>
<table><tr><th>الهدف (PRD 4.1)</th><th>ما تحقق</th></tr>
<tr><td>G1 تحديد المناطق عالية الخطورة</td><td class="ok">خريطة بأربعة مستويات لـ{f(CARD['grid_cells'])} خلية و{f(CARD['sectors'])} قطاعًا</td></tr>
<tr><td>G2 تحليل العوامل</td><td class="ok">تفسير Shapley لكل قطاع؛ الأمطار والزلازل محسوبة لكنها غير صالحة للنموذج (انظر 5.2)</td></tr>
<tr><td>G3 إنذار مبكر موثّق</td><td class="ok">اقتراح آلي + اعتماد بشري + تهدئة 24 ساعة + سجل تدقيق</td></tr>
<tr><td>G4 دعم التخطيط العمراني</td><td class="ok">تلوين حسب الانحدار أو الارتفاع، قمر صناعي، تقرير قطاع قابل للطباعة، وتصدير Google Earth</td></tr>
<tr><td>G5 نظام متكامل قابل للتجربة الميدانية</td><td class="ok">بيانات ← نموذج ← API ← واجهة، يعمل من البداية للنهاية</td></tr></table>

<h2>3. المستخدمون</h2>
<table><tr><th>الشخصية</th><th>ما يستخدمه في النظام</th></tr>
<tr><td>ضابط عمليات الطوارئ</td><td>الخريطة، قائمة الأعلى خطرًا، اعتماد الإنذارات</td></tr>
<tr><td>المخطط العمراني</td><td>تفاصيل القطاع: الانحدار والارتفاع والغطاء، وطبقة خلايا 1 كم</td></tr>
<tr><td>المحلل الجيوتقني / مدير النظام</td><td>صفحة الشفافية، تعديل العتبات، سجل التدقيق</td></tr>
<tr><td>المشرف الأكاديمي</td><td>هذا التقرير، بطاقة النموذج، خط المعالجة القابل لإعادة الإنتاج</td></tr></table>

<h2 class="pb">4. معمارية النظام</h2>
<div class="flow"><div>ملفات الفريق<small>data/raw</small></div><em>←</em><div>التنظيف<small>02_clean_data.py</small></div><em>←</em><div>التدريب<small>03_train_model.py</small></div><em>←</em><div>قاعدة البيانات<small>PostGIS · Supabase</small></div><em>←</em><div>خادم API<small>Starlette · Vercel</small></div><em>←</em><div>لوحة القيادة<small>web/</small></div><em>←</em><div>الإنذار<small>موافقة بشرية</small></div></div>
<table><tr><th>الطبقة</th><th>التقنية</th><th>المسؤولية</th></tr>
<tr><td>استخراج التضاريس</td><td>Python · rasterio · Colab</td><td>الارتفاع والانحدار والاتجاه من Copernicus DEM 30م، والغطاء من ESA WorldCover</td></tr>
<tr><td>التنظيف</td><td>pandas</td><td>إزالة التكرار، فصل الجداول المدموجة، توحيد السجلات، تقرير تنظيف</td></tr>
<tr><td>النموذج</td><td>scikit-learn</td><td>تدريب، تحقق مكاني، تنبؤ للشبكة، تجميع القطاعات</td></tr>
<tr><td>التخزين</td><td>PostgreSQL + PostGIS على Supabase (الإنتاج) · SQLite (محلي)</td><td>الجداول الست في PRD 15.1 + المستخدمون والجلسات والتدقيق</td></tr>
<tr><td>الخدمة</td><td>Starlette + Uvicorn</td><td>واجهات PRD 15.2، الصلاحيات، قواعد الإنذار</td></tr>
<tr><td>الواجهة</td><td>HTML/CSS/JS · MapLibre GL · خرائط Esri</td><td>الخريطة، التفاصيل، الإنذارات، الشفافية، الدليل التفاعلي</td></tr></table>
<p class="muted">اختير Starlette (الإطار الذي بُني عليه FastAPI) لأن FastAPI لم يكن متاحًا للتثبيت في بيئة البناء؛ المسارات والعقود مطابقة للـPRD، والتحويل إلى FastAPI لا يغيّر العقد.</p>

<h2>5. البيانات والتنظيف</h2>
<table><tr><th>المصدر</th><th>السجلات</th><th>الاستخدام</th></tr>
<tr><td>سجل الانهيارات (أخبار + NASA GLC)</td><td>{CL['landslide_events']} حدثًا · {CL['landslide_unique_locations_usable']} موقعًا صالحًا</td><td class="ok">الوسم</td></tr>
<tr><td>جدول التدريب (DEM + WorldCover)</td><td>{f(CL['training_rows'])}</td><td class="ok">التدريب</td></tr>
<tr><td>شبكة النقاط بخصائصها</td><td>{f(CL['grid_points_with_features'])} من {f(CL['grid_points_total'])}</td><td class="ok">التنبؤ</td></tr>
<tr><td>الأمطار الشهرية {CL['rainfall_years'][0]}–{CL['rainfall_years'][1]}</td><td>{f(CL['rainfall_rows'])} · {CL['rainfall_regions']} منطقة</td><td class="no">غير مستخدمة</td></tr>
<tr><td>كتالوج زلازل USGS</td><td>{CL['earthquakes']}</td><td class="no">غير مستخدم</td></tr>
<tr><td>جدول عوامل مشروطة</td><td>{CL['conditioning_factor_rows']}</td><td class="no">غير مستخدم</td></tr></table>
<h3>5.1 ما تم في التنظيف</h3>
<ul><li>حذف 4 ملفات مطابقة بايت ببايت لملفات أخرى.</li><li>فصل ملف الأمطار المدموج إلى جدولين مستقلين: الأمطار الشهرية، وجدول عوامل مشروطة لا علاقة له بالأمطار.</li>
<li>دمج تفاصيل NASA (المحفّز، الحجم، الوفيات) في سجل الانهيارات، ووسم نقاطها كتقريبية (25–50 كم).</li><li>استبعاد الدرجات والمستويات القديمة واستخدام خصائص الخلايا فقط.</li></ul>
<h3>5.2 أخطاء لم يمكن إصلاحها من الملفات المرسلة</h3>
<ul><li><b>الأمطار:</b> {len(CL['rainfall_regions_placeholder_coords'])} من {CL['rainfall_regions']} منطقة إحداثياتها قيمة مؤقتة (24°، 45°)، فلا تُربط مكانيًا.</li>
<li><b>الزلازل:</b> {CL['earthquakes_in_study_area']} من {CL['earthquakes']} زلزالًا داخل منطقة الدراسة.</li>
<li><b>الوسم:</b> {', '.join(CL['positives_not_in_inventory'])} في جدول التدريب وغير موجودة في السجل النظيف.</li>
<li><b>التغطية:</b> الدرجات متاحة لـ{CL['grid_points_with_features']/CL['grid_points_total']*100:.0f}% من الشبكة.</li></ul>


<h3>5.3 فحص الجودة الآلي (D-FR6)</h3>
<table><tr><th>الفحص</th><th>جدول التدريب</th><th>شبكة التنبؤ</th></tr>
<tr><td>القيم المفقودة</td><td>0</td><td>0</td></tr><tr><td>خارج النطاقات المنطقية</td><td>0</td><td>0</td></tr>
<tr><td>رموز غطاء أرضي غير صالحة</td><td>0</td><td>0</td></tr><tr><td>إحداثيات مكررة</td><td>0</td><td>0</td></tr>
<tr><td>نظام الإحداثيات</td><td colspan="2" class="mono">EPSG:4326 ✓</td></tr><tr><td>نقاط التدريب داخل امتداد الشبكة</td><td colspan="2">1,689 من 1,689</td></tr></table>
<p>النتيجة: <b>ناجح مع تحذير واحد</b> هو قلة نقاط الانهيار. التقرير الكامل في <code>data/processed/quality_report.json</code>.</p>
<h2 class="pb">6. النموذج والنتائج</h2>
<div class="box"><b>الإعداد:</b> {CARD['algorithm']} · المميزات: الارتفاع، الانحدار، اتجاه المنحدر، الغطاء الأرضي · تحقق {sp['method']} · بذرة {CARD['seed']} · العتبات {CARD['thresholds']['medium']} / {CARD['thresholds']['high']} / {CARD['thresholds']['critical']}</div>
<table><tr><th>المقياس</th><th>تحقق مكاني (المعتمد)</th><th>تقسيم عشوائي (للمقارنة)</th><th>هدف PRD 16</th></tr>
<tr><td>ROC-AUC</td><td><b>{sp['roc_auc']}</b></td><td>{rc['roc_auc']}</td><td>≥ 0.80 <span class="no">غير متحقق</span></td></tr>
<tr><td>PR-AUC</td><td><b>{sp['pr_auc']}</b></td><td>{rc['pr_auc']}</td><td>—</td></tr>
<tr><td>Recall عند «مرتفع»</td><td><b>{sp['recall_at_high']}</b></td><td>{rc['recall_at_high']}</td><td>—</td></tr>
<tr><td>Recall عند «حرج»</td><td><b>{sp['recall_at_critical']}</b></td><td>{rc['recall_at_critical']}</td><td>≥ 0.75 <span class="no">غير متحقق</span></td></tr></table>
<p>الفرق بين التقسيم العشوائي ({rc['roc_auc']}) والمكاني ({sp['roc_auc']}) يوضح كيف يضخّم الارتباط المكاني الأداء إذا لم تُفصل المناطق (PRD 12.3). نموذج مرجعي بسيط (انحدار لوجستي على الانحدار وحده) سجّل {CARD['reference_slope_only_logistic_spatial_auc']} في نفس التحقق، ولم يُعتمد لأنه اختير بعد رؤية النتائج على 12 نقطة فقط.</p>
<div class="two"><div><h3>أهمية المميزات</h3>{bars([(k_ar, v) for k_ar, v in zip(['اتجاه المنحدر','الانحدار','الارتفاع','الغطاء الأرضي'], CARD['feature_importance'].values())], fmt=lambda v: f'{v:.2f}')}
<p class="muted" style="font-size:9pt">تصدّر «اتجاه المنحدر» مع 12 نقطة مؤشر على حفظ ضوضاء أكثر من نمط حقيقي.</p></div>
<div><h3>توزيع خلايا 1 كم</h3>{bars([(LV[k], dist[k]) for k in LV], color=LVC, fmt=lambda v: f'{v:,}')}
<h3>توزيع القطاعات</h3>{bars([(LV[k], secl[k]) for k in LV], color=LVC, fmt=lambda v: f'{v:,}')}</div></div>


<h3>6.1 مقارنة النماذج بنفس التحقق المكاني (A-FR3)</h3>
<table><tr><th>النموذج</th><th>ROC-AUC</th><th>PR-AUC</th></tr>
<tr><td>غابة عشوائية (المعتمد)</td><td>{CARD['comparisons']['random_forest_baseline']['roc_auc']}</td><td>{CARD['comparisons']['random_forest_baseline']['pr_auc']}</td></tr>
<tr><td>غابة عشوائية + مميزات زلزالية</td><td>{CARD['comparisons']['random_forest_plus_seismic']['roc_auc']}</td><td>{CARD['comparisons']['random_forest_plus_seismic']['pr_auc']}</td></tr>
<tr><td>شبكة عصبية MLP(16, 8) · scikit-learn</td><td>{CARD['comparisons']['neural_network_mlp']['roc_auc']}</td><td>{CARD['comparisons']['neural_network_mlp']['pr_auc']}</td></tr>
<tr><td>شبكة عصبية (16, 8) · TensorFlow 2.21</td><td>{CARD['comparisons']['neural_network_tensorflow']['roc_auc']}</td><td>{CARD['comparisons']['neural_network_tensorflow']['pr_auc']}</td></tr></table>
<p>اعتُمد النموذج الأبسط لأن الفروق صغيرة وغير موثوقة إحصائيًا مع 12 نقطة (PRD 12.3). دُرّبت الشبكة بـTensorFlow فعليًا على GitHub Actions (<code>tensorflow.yml</code>) بنفس الطيّات: تحسّن ROC-AUC لا يرافقه تحسن في PR-AUC، ولا تلتقط أي انهيار عند عتبة «مرتفع»، فبقي Random Forest (القرار ق-2 في <code>docs/decisions.md</code>). المميزات الزلزالية لم تُعتمد لأن أقرب زلزال لنقاط التدريب على بعد {CARD['seismic_features']['training_eq_dist_km_min']:.0f} كم، فهي تعكس خط العرض لا الخطر الزلزالي.</p>
<h3>6.2 المعايرة (PRD 12.3)</h3>
<p>معايرة Isotonic على تنبؤات التحقق المكاني خفّضت Brier من {CARD['calibration']['brier_raw']} إلى {CARD['calibration']['brier_calibrated']}. الاحتمال المعاير يظهر في تفاصيل كل قطاع، والمستويات تبقى على الدرجة النسبية وعتبات الوثيقة لأن الاحتمال المعاير قريب من معدل الأساس ({CARD['calibration']['base_rate']*100:.1f}%) في كل مكان.</p>
<h3>6.3 التفسير لكل قطاع (A-FR5)</h3>
<p>قيم Shapley الدقيقة لكل قطاع عند خليته الأعلى خطرًا: 4 مميزات تعني 16 تركيبة فقط، فتُحسب القيم بالضبط بدل التقريب، بخلفية من 100 نقطة تدريب. أقصى خطأ في شرط الجمع {CARD['explanations']['additivity_max_error']}. تظهر في درج القطاع وتقريره كأشرطة موجبة (ترفع الخطر) وسالبة (تخفضه).</p>
<h2>7. منطق الخطر والإنذار</h2>
<table><tr><th>المستوى</th><th>الدرجة</th><th>الرمز</th><th>الدلالة</th></tr>
<tr><td>منخفض</td><td class="mono">&lt; 0.40</td><td>○</td><td>مراقبة اعتيادية</td></tr><tr><td>متوسط</td><td class="mono">0.40 – 0.60</td><td>◆</td><td>متابعة</td></tr>
<tr><td>مرتفع</td><td class="mono">0.60 – 0.80</td><td>▲</td><td>استعداد وإشعار داخلي</td></tr><tr><td>حرج</td><td class="mono">≥ 0.80</td><td>■</td><td>إنذار بعد موافقة بشرية</td></tr></table>
<ul><li><b>درجة القطاع</b> = المئين 90 لدرجات خلاياه. القيمة القصوى كانت ستضع 817 من 1,166 قطاعًا في «مرتفع» فأعلى، وهذا يناقض هدف تقليل الإنذارات الكاذبة.</li>
<li><b>الاقتراح:</b> يقترح النظام إنذارًا لكل قطاع «مرتفع» فأعلى ({secl['high'] + secl['critical']} إنذارًا حاليًا).</li>
<li><b>الموافقة:</b> لا يُعتمد إلا بحساب مشغّل، ويُسجّل باسمه ووقته. الإرسال للجهات محاكى في هذه المرحلة.</li>
<li><b>منع التكرار:</b> يُرفض اعتماد إنذار ثانٍ لنفس القطاع خلال 24 ساعة.</li>
<li><b>العتبات:</b> قابلة للتعديل من المسؤول، فيُعاد تصنيف القطاعات وتُقترح إنذارات جديدة ويُسجّل التغيير.</li></ul>


<h2 class="pb">8. Google Earth والخرائط</h2>
<div class="box"><b>ملف Google Earth:</b> <code>web/data/mirsad_google_earth.kmz</code> (46 كيلوبايت) يُفتح في Google Earth Pro أو Google Earth Web (Projects ← Import KML). يحتوي 1,166 قطاعًا ملوّنة بمستوى الخطر في مجلد لكل مستوى، و27 انهيارًا تاريخيًا (أيقونة تحذير للموقع الدقيق ومعيّن للتقريبي)، وحدود منطقة الدراسة، وبطاقة معلومات لكل قطاع بدرجته وعوامله.</div>
<ul><li><b>من الموقع:</b> زر «تنزيل الخريطة لـ Google Earth» في لوحة الطبقات.</li>
<li><b>لكل قطاع:</b> زر «عرض في Google Earth» يفتح Google Earth Web على الخلية الأعلى خطرًا بمنظور مائل.</li>
<li><b>قمر صناعي داخل الموقع:</b> مبدّل «خريطة / قمر صناعي» يعرض صور Esri World Imagery تحت القطاعات.</li>
<li><b>تلوين حسب العامل:</b> القطاعات بحسب متوسط الانحدار أو الارتفاع بدل مستوى الخطر (U-FR7).</li></ul>
<p class="muted">لم يُفتح الملف في Google Earth داخل بيئة البناء لعدم توفر البرنامج والإنترنت؛ تم التحقق من صحة بنية KML وعدد عناصره (1,194).</p>
{fig('19_color_by_slope_ar','تلوين القطاعات حسب متوسط الانحدار مع مبدّل الخريطة الأساسية وزر تصدير Google Earth.')}
<h2 class="pb">9. الواجهة: جولة مصوّرة</h2>
<p class="muted">لقطات من النظام وهو يعمل مع الخادم. ملاحظة: الخريطة الأساسية (بلاطات Esri) لا تظهر في هذه اللقطات لأنها التُقطت في بيئة بناء بلا إنترنت؛ على الموقع المنشور تظهر الخلفية وأسماء المدن. القطاعات والانهيارات المرسومة هي بيانات النظام الفعلية.</p>
{fig('01_splash','شاشة التحميل بهوية المشروع: رادار يدور، وشريط يتقدم مع مراحل التحميل الفعلية.')}
{fig('02_map_dark_ar','لوحة القيادة: المؤشرات، مستويات الخطر بلون ورمز ونطاق، الطبقات، وقائمة الأعلى خطرًا.')}
{fig('18_drawer_shap_ar','درج تفاصيل القطاع: الدرجة والمستوى، توزيع الخلايا، تفسير Shapley، الاحتمال المعاير، وروابط Google Earth والتقرير.')}
{fig('04_sector_drawer_light_en','نفس الشاشة بالإنجليزية والوضع النهاري.')}
{fig('05_alerts_ar','صفحة الإنذارات: كل قطاع مرتفع فأعلى بأسبابه، مع تصفية بالمستوى والحالة والتاريخ.')}
<div class="two">{fig('06_login_ar','الاعتماد يطلب دخول مشغّل.')}{fig('07_alert_approved_ar','بعد الاعتماد: الحالة واسم المعتمِد ووقته.')}</div>
{fig('09_transparency_light_en','صفحة الشفافية بالإنجليزية والوضع النهاري.')}
{fig('21_sector_report_ar','تقرير القطاع القابل للطباعة والحفظ PDF (U-FR9).')}
<h3>الدليل التفاعلي</h3><p>جولة من 9 خطوات تُعرض أول مرة، ويمكن إعادتها من زر «؟». تبرز كل خطوة عنصرًا وتشرحه، وتتنقل بين الصفحات تلقائيًا، وتعمل بالعربية والإنجليزية وبالأسهم من لوحة المفاتيح.</p>
<div class="two">{fig('11_tour_invite_ar','دعوة الجولة عند أول زيارة.')}{fig('13_tour_step2_ar','خطوة «مستويات الخطر».')}</div>
<div class="two">{fig('14_tour_step5_drawer_ar','خطوة «تفاصيل القطاع».')}{fig('15_tour_step6_alerts_ar','خطوة «الإنذارات».')}</div>
<div class="two">{fig('16_mobile_map_ar','الجوال: تخطيط عمودي.')}{fig('17_mobile_drawer_ar','الجوال: التفاصيل كورقة سفلية.')}</div>

<h2 class="pb">10. الخادم وواجهات البرمجة (PRD 15.2)</h2>
<table><tr><th>الطريقة</th><th>المسار</th><th>الوصف</th><th>الصلاحية</th></tr>
<tr><td>GET</td><td class="mono">/api/v1/risk?level=&amp;bbox=</td><td>القطاعات بدرجاتها (GeoJSON)</td><td>عامة</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/sectors/{{id}}</td><td>تفاصيل القطاع وعوامله وإنذاراته</td><td>عامة</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/sectors/{{id}}/forecast</td><td>يرجع 501: لا توجد بيانات توقع</td><td>عامة</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/alerts</td><td>سجل الإنذارات مع التصفية</td><td>عامة</td></tr>
<tr><td>POST</td><td class="mono">/api/v1/alerts</td><td>اعتماد أو رفض</td><td>مشغّل</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/model/runs/latest</td><td>بطاقة النموذج ومقاييسه</td><td>عامة</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/sources</td><td>المصادر وحالتها</td><td>عامة</td></tr>
<tr><td>GET/PUT</td><td class="mono">/api/v1/settings/thresholds</td><td>عرض/تعديل العتبات</td><td>PUT للمسؤول</td></tr>
<tr><td>GET</td><td class="mono">/api/v1/audit</td><td>سجل التدقيق</td><td>مسؤول</td></tr>
<tr><td>POST</td><td class="mono">/api/v1/auth/login</td><td>الدخول وإصدار رمز جلسة</td><td>—</td></tr></table>
<pre>curl -X POST localhost:8000/api/v1/alerts -H "Authorization: Bearer &lt;token&gt;" \\
     -H "Content-Type: application/json" -d '{{"sector_id":"S181-422","action":"approve"}}'</pre>

<h2>11. الأمان والصلاحيات</h2>
<ul><li>ثلاث صلاحيات: مشاهد، مشغّل (يعتمد الإنذارات)، مسؤول (العتبات وسجل التدقيق).</li><li>كلمات المرور مشفّرة PBKDF2-SHA256 بـ200,000 تكرار وملح عشوائي، وكلمات المرور الأولية من متغيرات البيئة، ولا أسرار في الشيفرة.</li>
<li>رموز جلسة عشوائية تنتهي بعد 12 ساعة، ومقارنة كلمات المرور بزمن ثابت.</li><li>سجل تدقيق لكل دخول فاشل واعتماد ورفض وتغيير عتبات.</li><li>ترويسات أمان على كل الاستجابات، ولا تخزين مؤقت لردود الـAPI.</li></ul>

<h2>12. الاختبار ومعايير القبول (PRD 19)</h2>
<table><tr><th>الرمز</th><th>السيناريو</th><th>النتيجة</th></tr>
<tr><td>AC-1</td><td>الخريطة تعرض كل القطاعات بمستوياتها خلال 3 ثوانٍ</td><td class="ok">ناجح</td></tr>
<tr><td>AC-2</td><td>قطاع ≥ 0.80 يظهر «حرج» مع أهم العوامل</td><td class="ok">ناجح</td></tr>
<tr><td>AC-3</td><td>الاعتماد يُسجّل باسم المعتمِد والوقت</td><td class="ok">ناجح</td></tr>
<tr><td>AC-4</td><td>علامة «بيانات متقادمة» عند تأخر مصدر</td><td class="ok">ناجح (بعد 30 يومًا من تاريخ البيانات)</td></tr>
<tr><td>AC-5</td><td>لا إنذار مكرر خلال فترة التهدئة</td><td class="ok">ناجح</td></tr></table>
<p>12 اختبارًا آليًا في <code>tests/test_api.py</code> تنجح كلها على SQLite وعلى PostgreSQL + PostGIS 3.4 في GitHub Actions، وتشمل الصلاحيات والمدخلات الخاطئة والاستعلام المكاني، إضافة إلى اختبار شامل للواجهة مع الخادم (الدخول، الاعتماد، تبديل اللغة والوضع، الجولة التفاعلية). كل أزواج النص والخلفية في الوضعين محققة بتباين ≥ 4.5:1.</p>

<h2 class="pb">13. سجل العمل ونسبة الإنجاز الفعلية</h2>
<h3>13.1 ما تم منذ بداية العمل</h3>
{worklog()}
<p class="muted">كل التعديلات في المستودع مسجّلة كـcommits باسم يزيد حمد الحارثي، وكل خطوة نشر لها سجل في GitHub Actions وVercel.</p>
<h3>13.2 مطابقة متطلبات الـPRD الوظيفية</h3>
<p>كل متطلب من الـ26 متطلبًا وظيفيًا أُعطي درجة تحقق بين 0 و100% حسب دليل في المستودع أو على الموقع الحي، والنسبة الفعلية هي متوسطها. آخر تحقق: {ST.AS_OF}.</p>
<div class="kpis"><div class="kpi"><span>النسبة الفعلية</span><b>{ST.OVERALL}%</b></div><div class="kpi"><span>مكتمل</span><b>{ST.DONE}</b></div><div class="kpi"><span>جزئي</span><b>{ST.PARTIAL}</b></div><div class="kpi"><span>غير منفذ</span><b>{ST.NONE}</b></div></div>
{bars([(n, v) for n, v, _ in ST.area_pct()], fmt=lambda v: f'{v}%', mx=100)}
{prd_table()}
<div class="box">النسبة تقيس تنفيذ المتطلبات، لا جودة التنبؤ. جودة التنبؤ يقيسها التحقق المكاني (ROC-AUC = {sp['roc_auc']})، وترتفع فقط بتوسيع سجل الانهيارات. شيت متابعة الفريق بعد تحديثات 10 نوفمبر يعطي نسبة قريبة (نحو 86%) لأنه يقيس المهام لا المتطلبات.</div>
<h2>14. الحدود المعروفة</h2>
<ol><li>{CARD['training']['positives']} نقطة انهيار فقط في التدريب مقابل {f(CARD['training']['negatives'])} نقطة بدون انهيار.</li>
<li>المخرج قابلية مكانية ثابتة وليس تنبؤًا زمنيًا؛ توقع 24/48/72 ساعة غير متاح.</li>
<li>الشبكة بتباعد ≈1 كم، والدرجات تغطي {CL['grid_points_with_features']/CL['grid_points_total']*100:.0f}% من الشبكة.</li>
<li>تفسير Shapley محسوب عند الخلية الأعلى خطرًا في كل قطاع، وليس لكل خلية.</li>
<li>المستويات مبنية على الدرجة النسبية؛ الاحتمال المعاير قريب من معدل الأساس لقلة نقاط الانهيار.</li>
<li>Google Earth لا يمكن تضمينه داخل موقع آخر؛ الموقع يفتحه على القطاع المختار ويوفر ملف KMZ، وصور الأقمار الصناعية داخل الخريطة من Esri.</li>
<li>إرسال الإنذارات للجهات محاكى؛ الاعتماد البشري وسجل التدقيق يعملان فعليًا على قاعدة الإنتاج.</li>
<li>مشروع QGIS <code>Mirsad_Landslide_Risk.qgz</code> يحتاج <code>mirsad_layers.gpkg</code> وهو غير موجود.</li></ol>

<h2>15. المتبقي وخارطة الطريق</h2>
<table><tr><th>المسار</th><th>المتبقي للوصول إلى 100%</th></tr>{"".join(f"<tr><td>{a}</td><td>{b}</td></tr>" for a, b in ST.REMAINING)}</table>
<table><tr><th>الأولوية</th><th>الخطوة</th><th>الأثر</th></tr>
<tr><td>1</td><td>توسيع سجل الانهيارات من مصادر رسمية إلى عشرات النقاط</td><td>الشرط الأساسي لأي تحسن في الأداء</td></tr>
<tr><td>2</td><td>أمطار بإحداثيات صحيحة أو شبكية (CHIRPS/GPM)</td><td>تمكين التنبؤ الزمني والتوقع</td></tr>
<tr><td>3</td><td>استعلام زلازل بحدود منطقة الدراسة</td><td>عامل ديناميكي ثانٍ</td></tr>
<tr><td>4</td><td>الانحناء والجيولوجيا والتربة</td><td>إكمال D-FR3 وD-FR4</td></tr>
<tr><td>5</td><td>إعادة التدريب بالبيانات الجديدة عبر <code>pipeline/run_all.py</code></td><td>لا تغيير في الكود</td></tr>
<tr><td>6</td><td>قناة إرسال إنذارات حقيقية وحساسات IoT</td><td>ما بعد MVP</td></tr></table>

<h2>16. التشغيل والنشر</h2>
<pre>git clone {REPO}.git && cd Mirsad
pip install -r requirements-pipeline.txt
export MIRSAD_ADMIN_PASSWORD=... MIRSAD_OPERATOR_PASSWORD=... MIRSAD_VIEWER_PASSWORD=...
python pipeline/run_all.py               # التنظيف ← الجودة ← التدريب ← التفسير ← Google Earth ← قاعدة البيانات
uvicorn backend.app:app --port 8000     # http://localhost:8000
pytest -q</pre>
<p><b>الإنتاج:</b> الموقع والخادم على Vercel (<span class="mono">https://mirsad-rho.vercel.app</span>)، وقاعدة البيانات PostgreSQL + PostGIS على Supabase. يُحمَّل النموذج إلى القاعدة عبر سير العمل <code>load-supabase.yml</code> في GitHub Actions، وكلمات المرور في أسرار المستودع ولا تُطبع في أي سجل. خط المعالجة كاملًا يُعاد أسبوعيًا عبر <code>scheduled-run.yml</code>، وجُرّب بنجاح في 10 نوفمبر. بدون خادم يعمل مجلد <code>web/</code> وحده في «وضع العرض».</p>

<h2>17. هيكل المستودع</h2>
<pre>data/raw/          ملفات الفريق بعد حذف النسخ المكررة
data/processed/    البيانات المنظفة + درجات الخطر v1 + تقارير التنظيف والجودة
pipeline/          01 التضاريس · 02 التنظيف · 03 التدريب · 04 الجودة · 05 التفسير · 06 Google Earth · run_all
model/             النموذج + المعايرة + بطاقة النموذج
backend/           app.py · db.py · load_db.py · rules.py · schema_postgis.sql
api/               مدخل الخادم على Vercel
web/               الموقع: الخريطة، الإنذارات، الشفافية، تقرير القطاع، الدليل التفاعلي
tests/             12 اختبارًا (AC-1..AC-5 والصلاحيات والاستعلام المكاني)
docs/              هذا التقرير · الدليل التعريفي · دليل المستخدم · التقرير الفني
docs/team/         شيت الفريق المبسّط
docs/reference/    وثيقة المتطلبات PRD · الهوية والألوان
docs/maps/         مشاريع QGIS والخرائط · docs/screenshots/ لقطات النظام</pre>

<h2>18. الفريق وطريقة المتابعة</h2>
<p>القروب الثالث بقيادة <b>{ST.LEADER}</b>، ونائبة القائد <b>{ST.DEPUTY}</b>: 13 عضوًا في 4 مسارات (البيانات الجيولوجية والمناخية، قاعدة البيانات المكانية، نمذجة الذكاء الاصطناعي، واجهة الويب والتوثيق).</p>
<div class="box"><b>شيت الفريق</b> (<code>docs/team/Mirsad_Team_Sheet.xlsx</code>): ورقة «الواجهة» فيها نبذة المشروع واسم القائد ونائبته ونسبة الإنجاز وحالة الاعتماد، وورقة «سجل الإنجاز» يضيف فيها كل عضو سطرًا لكل عمل (التاريخ، الاسم، المسار، ما أنجزه، رابط الدليل، النسبة)، ويعتمده القائد أو نائبته. الملخص يتحدث تلقائيًا.</div>
</body></html>"""

async def main():
    out_html = ROOT / "docs" / "report" / "report.html"
    out_html.write_text(HTML, encoding="utf-8")
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        exe = sys.argv[1] if len(sys.argv) > 1 else None
        b = await p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--no-sandbox"])
        pg = await b.new_page()
        await pg.goto(out_html.as_uri()); await pg.wait_for_timeout(800)
        foot = ('<div style="font-family:DejaVu Sans;font-size:8px;color:#4A5F66;width:100%;padding:0 16mm;display:flex;justify-content:space-between">'
                '<span>مِرصاد · التقرير الشامل</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
        await pg.pdf(path=str(ROOT / "docs" / "Mirsad_Project_Report.pdf"), format="A4", print_background=True,
                     display_header_footer=True, header_template="<span></span>", footer_template=foot,
                     margin={"top": "18mm", "bottom": "20mm", "left": "16mm", "right": "16mm"})
        await b.close()
    print("docs/Mirsad_Project_Report.pdf")

asyncio.run(main())
