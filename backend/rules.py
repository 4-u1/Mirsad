"""مِرصاد · قواعد الخطر والإنذار (PRD 13) — بدون اعتماديات ثقيلة ليعمل الخادم على Vercel."""
import json
from db import now, audit

LEVELS = ["low", "medium", "high", "critical"]


def level_of(s, th):
    return "critical" if s >= th["critical"] else "high" if s >= th["high"] else "medium" if s >= th["medium"] else "low"


# تنبؤ 72 ساعة (FR-U6) — قاعدة شفافة لا نموذج مُعايَر بأحداث:
# النسبة = الأمطار المتوقعة حتى الأفق ÷ المئين 99 لمجموع 3 أيام في القطاع (CHIRPS 2016–2025).
FORECAST_STEPS = ((1.0, 2), (0.5, 1))  # (حد النسبة، عدد درجات الرفع)


def forecast_level(base, ratio):
    """المستوى المتوقع = مستوى القابلية مرفوعًا درجة عند نسبة ≥ 0.5، ودرجتين عند ≥ 1، ولا ينخفض أبدًا."""
    i = LEVELS.index(base)
    if ratio is not None:
        for lim, up in FORECAST_STEPS:
            if ratio >= lim:
                i = min(i + up, len(LEVELS) - 1); break
    return LEVELS[i]


# مؤشر الأقمار الصناعية (ق-6) — للمراجعة البشرية لا لكشف الانهيار آليًا:
# تغيّر NDVI = متوسط آخر 30 يومًا (Sentinel-2) − نفس النافذة قبل سنة. يُعلَّم القطاع إذا كان مغطى نباتيًا
# (NDVI الأساس ≥ 0.15) وانخفض بمقدار ≥ 0.08، وبشرط أن 30% على الأقل من القطاع صافٍ من الغيوم في الفترتين.
NDVI_RULE = {"min_base": 0.15, "drop": -0.08, "min_valid": 0.3}


def ndvi_flag(base, change, valid_now, valid_base):
    """يرجع 'drop' أو 'stable' أو None (بيانات غير كافية)."""
    r = NDVI_RULE
    if base is None or change is None or valid_now is None or valid_base is None: return None
    if valid_now < r["min_valid"] or valid_base < r["min_valid"]: return None
    return "drop" if base >= r["min_base"] and change <= r["drop"] else "stable"


def reasons_for(p, lc):
    r = []
    if p.get("events"):
        r.append({"key": "events", "value": p["events"]})
    r += [{"key": "slope_max", "value": p["slope_max"]}, {"key": "elevation", "value": p["peak_vals"]["elevation"]},
          {"key": "landcover", "value": lc}]
    return r


def propose_alerts(con, run_id, by="system"):
    """يقترح إنذارًا لكل قطاع «مرتفع» فأعلى ليس له إنذار معلّق (PRD 13.2)."""
    rows = con.execute("""SELECT r.sector_id, r.level, r.score, r.details FROM risk_scores r
        WHERE r.model_run_id=? AND r.level IN ('high','critical')
        AND NOT EXISTS (SELECT 1 FROM alerts a WHERE a.sector_id=r.sector_id AND a.status='pending')""", (run_id,)).fetchall()
    batch = []
    for r in rows:
        d = json.loads(r["details"])
        batch.append((r["sector_id"], r["level"], r["score"], json.dumps(reasons_for(d, d["peak_vals"]["landcover"]), ensure_ascii=False),
                      "pending", now(), run_id))
    if batch:
        con.executemany("INSERT INTO alerts(sector_id, level, score, reasons, status, created_at, model_run_id) VALUES (?,?,?,?,?,?,?)", batch)
        con.commit()
        audit(con, by, "alerts.proposed", {"count": len(batch), "model_run_id": run_id})
    return len(batch)
