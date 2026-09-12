# -*- coding: utf-8 -*-
"""把已确认的「正常入库识别流程与原件不一致」缺陷登记到 known_issues.json。"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
camp = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "debug_loop"
ki = json.loads((camp / "known_issues.json").read_text(encoding="utf-8"))

now = datetime.now().isoformat(timespec="seconds")
new = [
    {"type": "INGEST-MinerU-数字标准号丢失",
     "count": 1, "first": now, "pdfs": ["GB/T 1000-2016"],
     "level": "ingestion(parse_pdf_with_mineru/_mineru_deep_analyze)",
     "detail": "正常入库识别流程默认 force_deep=True，MinerU 深度模型对文本层重识别丢数字/字母/标准号："
               "GB/T 1000-2016 实测 10kV→空、1000m→空、GB/T 197→/、图号→空、英文空格粘连；"
               "middle.json 已丢（fitz get_text(dict) 原始 span 完整）。文本层完好本可用 fitz 保真。",
     "solution": None, "recurred": False},
    {"type": "INGEST-Fitz-条款号未识别丢条款",
     "count": 1, "first": now, "pdfs": ["GB/T 1000-2016"],
     "level": "ingestion(load_middle_items_from_blocks/split_items_into_clauses)",
     "detail": "fitz 文本层路径 span 保字完整，但条款号'1/2/3'未与标题'范围/规范性引用文件/术语和定义'"
               "合并（b2=范围 无前缀），切分器因此丢条款 1/2/3（GB/T 1000-2016 重导 total_clauses=5）。"
               "文本层保真方向需先修此条款切分缺陷。",
     "solution": None, "recurred": False},
]
ki.setdefault("issues", []).extend(new)
# 去重：同 type 已存在则更新而非重复
seen = {}
for i in ki["issues"]:
    seen[i["type"]] = i
ki["issues"] = list(seen.values())
(camp / "known_issues.json").write_text(
    json.dumps(ki, ensure_ascii=False, indent=2), encoding="utf-8")
print("known_issues.json updated; issues:", [i["type"] for i in ki["issues"]])
