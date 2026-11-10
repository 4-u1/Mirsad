"""مِرصاد · نقطة دخول الخادم على Vercel (Python ASGI). يخدم /api/v1/* من backend/app.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import app  # noqa: E402,F401
