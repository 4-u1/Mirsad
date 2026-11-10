"""مِرصاد · قواعد الخطر والإنذار (PRD 13) — بدون اعتماديات ثقيلة ليعمل الخادم على Vercel."""
import json
from db import now, audit

LEVELS = ["low", "medium", "high", "critical"]


def level_of(s, th):
    return "critical" if s >= th["critical"] else "high" if s >= th["high"] else "medium" if s >= th["medium"] else "low"


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
