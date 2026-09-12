# -*- coding: utf-8 -*-
"""更新 C-扫描件图呈现空白的根因与结论。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ki = json.loads((camp / "known_issues.json").read_text(encoding="utf-8"))
now = datetime.now().isoformat(timespec="seconds")
for x in ki["issues"]:
    if x["type"] == "C-扫描件图呈现空白":
        x["detail"] = ("扫描件附录图 A.3-A.5 呈空白，但逐项核验：middle.json 有 25 个 image 资产、"
                       "figure_html 已注入 19 个 asset、图文件已落盘 parse_out/.../auto/images/*.jpg"
                       "——图链路(识别+注入+落盘)齐全，空白发生在【渲染/端点层】(/assets 拉取或前端填充)，"
                       "属 renderer/api 契约级专项(不同于 ingestion)，非本次 ingestion 修复范畴。")
        x["updated_at"] = now
(camp / "known_issues.json").write_text(
    json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated C-扫描件图呈现空白 root cause")
