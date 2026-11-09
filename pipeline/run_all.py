"""مِرصاد · تشغيل خط المعالجة كاملًا بالترتيب (PRD · A-FR6: تشغيل دوري).

python pipeline/run_all.py            ← تنظيف ← جودة ← تدريب وتنبؤ ← مقارنات وتفسير ← تحميل قاعدة البيانات
يُشغَّل دوريًا عبر .github/workflows/scheduled-run.yml أو cron:  0 3 * * 0  cd /path/Mirsad && python pipeline/run_all.py
"""
import subprocess, sys, datetime, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STEPS = ["pipeline/02_clean_data.py", "pipeline/04_quality_report.py", "pipeline/03_train_model.py",
         "pipeline/05_evaluate_explain.py", "pipeline/06_export_google_earth.py", "backend/load_db.py"]
log = {"started": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "steps": []}
for s in STEPS:
    r = subprocess.run([sys.executable, str(ROOT / s)], cwd=ROOT, capture_output=True, text=True)
    log["steps"].append({"step": s, "ok": r.returncode == 0})
    print(("OK   " if r.returncode == 0 else "FAIL ") + s)
    if r.returncode:
        print(r.stderr[-2000:]); break
log["finished"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
(ROOT / "model" / "last_run.json").write_text(json.dumps(log, indent=2), encoding="utf-8")
sys.exit(0 if all(x["ok"] for x in log["steps"]) and len(log["steps"]) == len(STEPS) else 1)
