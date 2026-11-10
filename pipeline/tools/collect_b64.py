"""يسترجع مخرجات سير عمل من سجله: gh run view <id> --log | python pipeline/tools/collect_b64.py <مجلد>"""
import base64, io, re, sys, tarfile
from collections import defaultdict
from pathlib import Path
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
parts = defaultdict(dict)
for line in sys.stdin:
    m = re.search(r"MIRSAD_B64 (\S+) (\d{5}) (\S+)", line)
    if m: parts[m.group(1)][int(m.group(2))] = m.group(3)
for tag, ch in parts.items():
    data = base64.b64decode("".join(ch[i] for i in sorted(ch)))
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        tf.extractall(out, filter="data")
    print(tag, len(data), "bytes ->", sorted(m.name for m in tarfile.open(fileobj=io.BytesIO(data)).getmembers()))
