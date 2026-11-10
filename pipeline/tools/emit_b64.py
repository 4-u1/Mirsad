"""يطبع مجلد المخرجات مضغوطًا بـbase64 في سجل التشغيل، لاسترجاعه بـ pipeline/tools/collect_b64.py."""
import base64, io, sys, tarfile
from pathlib import Path
tag, folder = sys.argv[1], Path(sys.argv[2])
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz") as tf:
    for f in sorted(folder.iterdir()): tf.add(f, arcname=f.name)
s = base64.b64encode(buf.getvalue()).decode()
n = 60000
for i in range(0, len(s), n): print(f"MIRSAD_B64 {tag} {i // n:05d} {s[i:i + n]}")
print(f"MIRSAD_B64_END {tag} {len(buf.getvalue())} bytes")
