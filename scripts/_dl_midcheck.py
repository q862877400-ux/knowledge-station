# -*- coding: utf-8 -*-
"""对 middle.json 原文做子串取证：判断 MinerU 层是否已丢数字/字母。"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
data = Path(os.environ["APPDATA"]) / "KnowledgeStation"
doc = sys.argv[1] if len(sys.argv) > 1 else "doc_01M1FS1P5YZ3SR9TCWBR0T8NCY"
midfiles = list((data / "parse_out" / doc).rglob("*_middle.json"))
if not midfiles:
    print("no middle.json under", data / "parse_out" / doc)
    sys.exit(0)
path = midfiles[0]
raw = path.read_text(encoding="utf-8")
print("middle.json size:", len(raw), "path:", path)
for probe in ["10kV", "kV", "高压线路", "1000m", "GB/T197", "GB/T 197", "—2003", "普通螺纹"]:
    idx = raw.find(probe)
    print(f"[{probe}] found={idx >= 0}", ("ctx=" + repr(raw[max(0, idx - 40):idx + 60])) if idx >= 0 else "")
