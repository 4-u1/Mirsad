<p align="center">
  <img src="docs/assets/banner.png" alt="مِرصاد · نظام التنبؤ بمخاطر الانهيارات الأرضية" width="100%">
</p>

<p align="center">
  <a href="https://mirsad-rho.vercel.app"><img alt="Live" src="https://img.shields.io/badge/%D8%A7%D9%84%D9%85%D9%88%D9%82%D8%B9-%D8%B4%D8%BA%D8%A7%D9%84-38C7B8?style=for-the-badge&labelColor=13242A"></a>
  <a href="https://github.com/4-u1/Mirsad/actions/workflows/ci.yml"><img alt="Tests" src="https://img.shields.io/github/actions/workflow/status/4-u1/Mirsad/ci.yml?branch=main&style=for-the-badge&label=tests&labelColor=13242A&color=257C83"></a>
  <img alt="PRD" src="https://img.shields.io/badge/PRD-83%25-D59A4D?style=for-the-badge&labelColor=13242A">
  <img alt="PostGIS" src="https://img.shields.io/badge/PostGIS-Supabase-257C83?style=for-the-badge&labelColor=13242A">
  <a href="LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-AC573A?style=for-the-badge&labelColor=13242A"></a>
</p>

<p align="center">
  <b><a href="https://mirsad-rho.vercel.app">🌐 الموقع</a></b> ·
  <b><a href="docs/Mirsad_Project_Report.pdf">📘 التقرير الشامل</a></b> ·
  <b><a href="docs/Mirsad_Introduction.pdf">📗 الدليل التعريفي</a></b> ·
  <a href="docs/user_guide.md">دليل المستخدم</a> ·
  <a href="docs/technical_report.md">التقرير الفني</a> ·
  <a href="docs/team/Mirsad_Team_Sheet.xlsx">شيت الفريق</a> ·
  <a href="docs/presentations/Mirsad_Presentation.pdf">🎞️ العرض التقديمي</a> ·
  <a href="docs/team/Mirsad_Team_Sheet_Guide.mp4">🎬 فيديو الشيت</a>
</p>

---

## نبذة

**مِرصاد** نظام ذكاء اصطناعي يقدّر قابلية الانهيارات الأرضية في جنوب غرب المملكة العربية السعودية (جازان، عسير، الباحة، نجران)، ويعرضها على خريطة قطاعات تفاعلية، ويقترح إنذارات **لا تُعتمد إلا بموافقة بشرية**. مشروع أكاديمي للقروب الثالث: 13 عضوًا في 4 مسارات.

> **Mirsad** estimates landslide susceptibility across southwest Saudi Arabia, maps it as an interactive sector map, and proposes alerts that only go out after a human approves them.

<table>
<tr>
<td align="center"><b>126,467</b><br><sub>خلية تنبؤ بحجم 1 كم</sub></td>
<td align="center"><b>1,166</b><br><sub>قطاعًا بحجم 11 كم</sub></td>
<td align="center"><b>195</b><br><sub>قطاعًا مرتفعًا أو حرجًا</sub></td>
<td align="center"><b>12 / 12</b><br><sub>اختبار ناجح</sub></td>
<td align="center"><b>5 / 5</b><br><sub>معايير القبول</sub></td>
</tr>
</table>

## لقطات من النظام

<table>
<tr>
<td width="50%"><img src="docs/screenshots/02_map_dark_ar.jpg" alt="الخريطة"><p align="center"><sub>خريطة القطاعات بمستويات الخطر</sub></p></td>
<td width="50%"><img src="docs/screenshots/18_drawer_shap_ar.jpg" alt="تفاصيل القطاع"><p align="center"><sub>تفاصيل القطاع وأهم العوامل (Shapley)</sub></p></td>
</tr>
<tr>
<td width="50%"><img src="docs/screenshots/07_alert_approved_ar.jpg" alt="الإنذارات"><p align="center"><sub>اعتماد إنذار بموافقة بشرية</sub></p></td>
<td width="50%"><img src="docs/screenshots/09_transparency_light_en.jpg" alt="الشفافية"><p align="center"><sub>صفحة الشفافية · الوضع النهاري بالإنجليزية</sub></p></td>
</tr>
</table>

## كيف يعمل

```mermaid
flowchart LR
  A[ملفات الفريق<br/>تضاريس · غطاء أرضي · انهيارات] --> B[التنظيف والجودة<br/>pipeline/02 · 04]
  B --> C[النموذج<br/>Random Forest · تحقق مكاني]
  C --> D[التفسير والمعايرة<br/>Shapley · Isotonic]
  D --> E[(Supabase<br/>PostgreSQL + PostGIS)]
  E --> F[الخادم<br/>Starlette على Vercel]
  F --> G[الموقع<br/>خريطة · تقارير · إنذارات]
  G --> H{موافقة بشرية}
  H -->|معتمد| I[سجل التدقيق + ختم التقرير]
```

## حالة المشروع

نسبة الإنجاز الفعلية **83%** من متطلبات الـPRD الوظيفية (26 متطلبًا، كل واحد مقيس بدليل)، و**85%** من متطلبات Must. التفصيل الكامل في [التقرير الشامل](docs/Mirsad_Project_Report.pdf).

| المجال | الإنجاز | المتبقي |
|---|:---:|---|
| البيانات | 63% | سجل انهيارات أكبر، أمطار بإحداثيات، جيولوجيا وتربة، انحناء |
| قاعدة البيانات المكانية | 95% | قرار دقة الشبكة |
| الذكاء الاصطناعي | 92% | مميزات v2 بعد وصول البيانات، اعتماد بديل TensorFlow |
| الواجهة والتوثيق | 86% | التنبؤ 72 ساعة، طبقات الأمطار والتربة، مراجعة الفريق |

## النموذج بصراحة

| المقياس | تحقق مكاني | تقسيم عشوائي |
|---|:---:|:---:|
| ROC-AUC | **0.545** | 0.709 |
| PR-AUC | 0.011 | 0.022 |

> ⚠️ أداء النموذج في التحقق المكاني قريب من العشوائي لأن سجل التدريب فيه **12 نقطة انهيار فقط**. النظام مكتمل تقنيًا من البيانات إلى الإنذار، لكن الخريطة أداة دعم قرار أكاديمية وليست أساسًا لقرار ميداني. الأمطار والزلازل لم تدخل النموذج، والتنبؤ الزمني غير متاح (الخادم يرجع 501 بدل أرقام وهمية).

## التقنيات

| الطبقة | التقنية |
|---|---|
| البيانات | Copernicus DEM 30 م · ESA WorldCover 2021 · NASA Global Landslide Catalog · USGS |
| خط المعالجة | Python · pandas · scikit-learn |
| قاعدة البيانات | PostgreSQL + PostGIS على Supabase · SQLite محليًا |
| الخادم | Starlette على Vercel · أدوار مشاهد/مشغّل/مسؤول · سجل تدقيق |
| الواجهة | HTML/CSS/JS · MapLibre GL · خرائط Esri · عربي/إنجليزي · ليلي/نهاري |
| الأتمتة | GitHub Actions: اختبارات على SQLite وPostGIS · تحميل القاعدة · تشغيل أسبوعي |

## التشغيل

```bash
git clone https://github.com/4-u1/Mirsad.git && cd Mirsad
pip install -r requirements-pipeline.txt
export MIRSAD_ADMIN_PASSWORD='…' MIRSAD_OPERATOR_PASSWORD='…'
python pipeline/run_all.py              # تنظيف ← جودة ← تدريب ← تفسير ← Google Earth ← قاعدة البيانات
uvicorn backend.app:app --port 8000     # http://localhost:8000
pytest -q                               # 12 اختبارًا: AC-1..AC-5 والصلاحيات
```

**الإنتاج:** الموقع والخادم على Vercel، والقاعدة على Supabase. تُحمَّل القاعدة من سير العمل `load-supabase.yml` بأسرار المستودع، ويُعاد خط المعالجة كاملًا كل أسبوع عبر `scheduled-run.yml`.

## هيكل المستودع

```
data/raw/          ملفات الفريق كما أُرسلت (بعد حذف 4 نسخ مكررة)
data/processed/    البيانات المنظفة + درجات الخطر + تقارير التنظيف والجودة
pipeline/          01 التضاريس (Colab) · 02 التنظيف · 03 التدريب · 04 الجودة · 05 التفسير · 06 Google Earth
model/             النموذج المدرّب، المعايرة، بطاقة النموذج
backend/           الخادم، مخطط PostGIS، تحميل البيانات، قواعد الإنذار
api/               مدخل الخادم على Vercel
web/               الموقع: الخريطة، الإنذارات، الشفافية، تقرير القطاع، الدليل التفاعلي
tests/             اختبارات القبول والصلاحيات
docs/              التقرير الشامل، الدليل التعريفي، دليل المستخدم، التقرير الفني، شيت الفريق
docs/reference/    وثيقة المتطلبات PRD وهوية المشروع
docs/maps/         مشاريع QGIS والخرائط المصدّرة
```

## الفريق

**القروب الثالث** · 13 عضوًا · 4 مسارات: البيانات الجيولوجية والمناخية · قاعدة البيانات المكانية (GIS) · نمذجة الذكاء الاصطناعي · واجهة الويب والتوثيق.
يسجّل كل عضو ما أنجزه في [شيت الفريق](docs/team/Mirsad_Team_Sheet.xlsx)، ويعتمده القائد أو نائبته.

## المصادر والتراخيص

الكود تحت رخصة [MIT](LICENSE). البيانات: Copernicus DEM (رخصة Copernicus) · ESA WorldCover 2021 (CC BY 4.0) · USGS (ملكية عامة) · NASA Global Landslide Catalog · تقارير إخبارية مذكورة في `data/processed/landslide_inventory.csv`. الخرائط الأساسية وصور الأقمار الصناعية: Esri (HERE, Garmin, © OpenStreetMap contributors, Maxar).

<p align="center"><img src="web/emblem.png" width="64" alt=""><br><sub>مِرصاد · 2026</sub></p>
