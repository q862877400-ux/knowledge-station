# -*- coding: utf-8 -*-
"""检查扫描件 middle.json 的图像资产，判断附录图 A.3-A.5 是否缺失。"""
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
doc = sys.argv[1]
data = Path(os.environ["APPDATA"]) / "KnowledgeStation"
midfiles = list((data / "parse_out" / doc).rglob("*_middle.json"))
print("middle.json:", len(midfiles), midfiles[0] if midfiles else "NONE")
if not midfiles:
    sys.exit(0)
mj = json.loads(midfiles[0].read_text(encoding="utf-8"))
# 收集所有 image 资产（image_path + caption）
imgs = []
for page in mj.get("pdf_info", []):
    for block in page.get("para_blocks") or []:
        btype = block.get("type")
        if btype not in ("image", "chart"):
            continue
        cap, path = "", None
        for sub in block.get("blocks") or []:
            st = sub.get("type")
            if st in ("image_caption", "image_title"):
                # 题注里的 span 文本
                def spans_text(o):
                    out = []
                    def walk(x):
                        if isinstance(x, dict):
                            if kk("text") and isinstance(x.get("text"), str):
                                out.append(x["text"])
                            for v in list(x.values()):
                                walk(v)
                        elif isinstance(x, list):
                            for v in x:
                                walk(v)
                    def kk(k):
                        return True
                    walk(o)
                    return " ".join(out)
                cap = spans_text(sub) or cap
            elif st == "image_body":
                for line in sub.get("lines") or []:
                    for span in line.get("spans") or []:
                        if span.get("image_path"):
                            path = span["image_path"]
        imgs.append({"type": btype, "page": page.get("page_idx", "?"),
                     "cap": (cap or "")[:40], "path": path})
print("image blocks:", len(imgs))
for im in imgs:
    print("  page=%s type=%s path=%s cap=%r" % (im["page"], im["type"], im["path"], im["cap"]))
