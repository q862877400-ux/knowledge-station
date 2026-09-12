# -*- coding: utf-8 -*-
"""列出 12 本对比目录里的预览不同屏(按内容哈希去重)，便于逐本全屏核。"""
import hashlib
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
base = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop" / "pagecmp"
books = ["GBT1000-2016", "GBT9278-2008", "GBT11-2020", "GBT12-2020", "GBT10-2013",
         "GBT10000-2023", "GBT1003-2016", "GBT1008-2008", "GBT1019-2008",
         "GBT1028-2018", "GBT1029-2021", "GBT1031-2009"]
for b in books:
    d = base / b
    if not d.exists():
        print(b, "MISSING")
        continue
    seen, distinct = {}, []
    for f in sorted(d.glob("prev_p*")):
        try:
            h = hashlib.sha256(f.read_bytes()).hexdigest()[:10]
        except Exception:
            h = f.stat().st_size
        if h not in seen:
            seen[h] = f.name
            distinct.append(f.name)
    print("%-14s distinct_prev_screens=%d  -> %s" % (b, len(distinct),
          ",".join(distinct)))
