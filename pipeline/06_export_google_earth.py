"""مِرصاد · تصدير خريطة الخطر إلى Google Earth (KMZ).

يُنتج web/data/mirsad_google_earth.kmz: القطاعات ملوّنة بمستوى الخطر (مجلد لكل مستوى)، الانهيارات التاريخية،
وحدود منطقة الدراسة، مع بطاقة معلومات لكل قطاع. يُفتح في Google Earth Pro أو Google Earth Web (Projects ← Import KML).
التشغيل بعد 05:  python pipeline/06_export_google_earth.py
"""
from pathlib import Path
from xml.sax.saxutils import escape
import json, zipfile

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web" / "data"
sectors = json.loads((WEB / "sectors.geojson").read_text(encoding="utf-8"))
events = json.loads((WEB / "landslides.json").read_text(encoding="utf-8"))
card = json.loads((ROOT / "model" / "model_card.json").read_text(encoding="utf-8"))
LV = {"critical": ("حرج", "D9412B", "cc"), "high": ("مرتفع", "AC573A", "b3"), "medium": ("متوسط", "D59A4D", "8c"), "low": ("منخفض", "6F8E9A", "40")}
FEAT = {"elevation": "الارتفاع", "slope": "الانحدار", "aspect": "اتجاه المنحدر", "landcover": "الغطاء الأرضي"}

def kml_color(hex_rgb, alpha):  # KML: aabbggrr
    return alpha + hex_rgb[4:6] + hex_rgb[2:4] + hex_rgb[0:2]

styles = "".join(f"""<Style id="lv-{k}"><LineStyle><color>{kml_color(c, 'ff')}</color><width>{2 if k in ('high','critical') else 0.6}</width></LineStyle>
<PolyStyle><color>{kml_color(c, a)}</color></PolyStyle></Style>""" for k, (_, c, a) in LV.items())
styles += """<Style id="ev-exact"><IconStyle><color>ff2a2ad9</color><scale>1.1</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/caution.png</href></Icon></IconStyle></Style>
<Style id="ev-approx"><IconStyle><color>ff4d9ad5</color><scale>0.9</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/open-diamond.png</href></Icon></IconStyle></Style>
<Style id="extent"><LineStyle><color>ffb8c738</color><width>3</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>"""

def sector_pm(f):
    p = f["properties"]; name, _, _ = LV[p["level"]]
    ring = " ".join(f"{lo},{la},0" for lo, la in f["geometry"]["coordinates"][0])
    shap = "".join(f"<tr><td>{FEAT[k]}</td><td dir='ltr'>{v:+.3f}</td></tr>" for k, v in list(p.get("shap", {}).items())[:3])
    desc = (f"<div dir='rtl' style='font-family:Tahoma'><b>مستوى الخطر: {name}</b><br>الدرجة: {p['score']:.2f} (أعلى خلية {p['max']:.2f})<br>"
            f"متوسط الارتفاع: {p['elev']} م · أقصى انحدار: {p['slope_max']}°<br>انهيارات مسجّلة داخله: {p['events']}<br>"
            f"<br><b>أكبر العوامل أثرًا (Shapley)</b><table>{shap}</table><br><small>مرصاد · نموذج {card['version']}</small></div>")
    return (f"<Placemark><name>{p['id']} · {name}</name><styleUrl>#lv-{p['level']}</styleUrl>"
            f"<description><![CDATA[{desc}]]></description><Polygon><tessellate>1</tessellate><altitudeMode>clampToGround</altitudeMode>"
            f"<outerBoundaryIs><LinearRing><coordinates>{ring}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>")

folders = ""
for k in ("critical", "high", "medium", "low"):
    fs = [f for f in sectors["features"] if f["properties"]["level"] == k]
    folders += f"<Folder><name>{LV[k][0]} ({len(fs)})</name><visibility>{0 if k == 'low' else 1}</visibility>{''.join(sector_pm(f) for f in fs)}</Folder>"
ev = "".join(f"""<Placemark><name>{escape(e['point_id'])}</name><styleUrl>#{'ev-exact' if e['usable_for_terrain'] is True else 'ev-approx'}</styleUrl>
<description><![CDATA[<div dir='rtl'>{escape(str(e['place']))}<br>التاريخ: {e['event_date'] or 'غير معروف'}<br>دقة الموقع: {escape(str(e['location_precision']))}</div>]]></description>
<Point><coordinates>{e['lon']},{e['lat']},0</coordinates></Point></Placemark>""" for e in events)
st = card["cleaning"]["study_area"]
box = f"{st['lon_min']},{st['lat_min']},0 {st['lon_max']},{st['lat_min']},0 {st['lon_max']},{st['lat_max']},0 {st['lon_min']},{st['lat_max']},0 {st['lon_min']},{st['lat_min']},0"
kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>مرصاد · خريطة مخاطر الانهيارات الأرضية</name>
<description>قطاعات 0.1° ملوّنة بمستوى الخطر حسب عتبات وثيقة المتطلبات، والانهيارات التاريخية. نموذج {card['version']} · {card['trained_at']}.</description>
<LookAt><longitude>42.35</longitude><latitude>18.35</latitude><altitude>0</altitude><range>750000</range><tilt>35</tilt><heading>0</heading></LookAt>
{styles}<Folder><name>القطاعات حسب المستوى</name>{folders}</Folder>
<Folder><name>الانهيارات التاريخية ({len(events)})</name>{ev}</Folder>
<Placemark><name>حدود منطقة الدراسة</name><styleUrl>#extent</styleUrl><Polygon><outerBoundaryIs><LinearRing><coordinates>{box}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</Document></kml>"""
out = WEB / "mirsad_google_earth.kmz"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("doc.kml", kml)
print(out, round(out.stat().st_size / 1024), "KB")
