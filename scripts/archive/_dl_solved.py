# -*- coding: utf-8 -*-
"""标记已根因修复的缺陷为 solved。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ki = json.loads((camp / "known_issues.json").read_text(encoding="utf-8"))
now = datetime.now().isoformat(timespec="seconds")
SOLVED = {
    "INGEST-MinerU-数字标准号丢失": "文本层完好→fitz 保真（parse 不跑深度 + run_full_ingest 优先 fitz blocks）；根治 MinerU 深度丢字。GB/T 1000-2016 验证 10kV/GB/T197/图号/括号全对。",
    "INGEST-Fitz-条款号未识别丢条款": "修 `_CHAPTER_HEAD`(章头空格\\s+) + `_DIR_ENTRY_RE`(目录页附录条目误设 in_appendix)；章级条款 1-6 恢复。",
}
for x in ki["issues"]:
    if x["type"] in SOLVED:
        x["solution"] = SOLVED[x["type"]]
        x["solved_at"] = now
(camp / "known_issues.json").write_text(
    json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")
print("updated solutions for:", [i["type"] for i in ki["issues"] if i.get("solved_at")])
# 追加 debug_log
with open(camp / "debug_log.txt", "a", encoding="utf-8") as f:
    f.write("[%s] Round1: 修复4个通用ingestion bug（_CHAPTER_HEAD/PUA判据二/PUA长跑/_APPENDIX目录条目）+ 文本层→fitz切换；GB/T 1000-2016 正常流程保字+条款全；pipeline/retrieval/dryrun/docx/phase 32 passed\n" % now)
