# -*- coding: utf-8 -*-
"""复现 fitz 文本层切分：blocks→items→clauses，定位条款1/2 为何丢失。"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.ingestion.mineru_adapter import (  # noqa: E402
    _extract_text_blocks, text_layer_pua_mangled, _clean_blocks, _reflow_block)
from src.core.ingestion.pipeline import load_middle_items_from_blocks, split_items_into_clauses  # noqa: E402
from src.core.text_utils import reflow_sqrt_formulas  # noqa: E402

pdf = r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1000-2016 高压线路针式瓷绝缘子尺寸与特性.pdf"
blocks = _extract_text_blocks(Path(pdf))
print("blocks:", len(blocks), "pua_mangled:", text_layer_pua_mangled(blocks))
blocks = _clean_blocks(blocks)
blocks = [_reflow_block(b, reflow_sqrt_formulas) for b in blocks]
items, _ = load_middle_items_from_blocks(blocks)
print("items count:", len(items))
print("---- 含 '范围'/'规范'/'术语' 的 items ----")
for it in items:
    t = str(it.text or "")
    if any(k in t for k in ("范围", "规范性引用", "术语和定义", "结构型式")):
        print("  page=%d kind=%s %r" % (it.page_idx, it.kind, t[:40]))
print("---- 前 12 个 item 文本 ----")
for it in items[:12]:
    print("  page=%d %r" % (it.page_idx, str(it.text)[:40]))
import re as _re
from src.core.ingestion.pipeline import (  # noqa: E402
    _CLAUSE_GB, _CHAPTER_HEAD, _CHAPTER_CLAUSE, _plausible_clause_head, _APPENDIX_HEAD, _TOC_HEAD)
print("---- 触发 in_appendix(_APPENDIX_HEAD) 的 item ----")
for i, it in enumerate(items):
    tt = str(it.text or "").strip()
    if _APPENDIX_HEAD.match(tt):
        print("  idx=%d page=%d %r" % (i, it.page_idx, tt[:26]))
print("---- 触发 in_toc(_TOC_HEAD) 的 item ----")
for i, it in enumerate(items):
    if _TOC_HEAD.match(str(it.text or "").strip()):
        print("  idx=%d page=%d %r" % (i, it.page_idx, str(it.text)[:26]))
_sib = _re.compile(r"^\d{1,2}\s*[\u4e00-\u9fff（）(]")
print("---- 章级 item 判定 ----")
for i, it in enumerate(items):
    t = str(it.text or "").strip()
    if t in ("1范围", "2规范性引用文件", "3术语和定义", "4结构型式和型号"):
        nxt = str(items[i + 1].text or "") if i + 1 < len(items) else ""
        prv = str(items[i - 1].text or "") if i > 0 else ""
        is_chapter = not (_sib.match(nxt) or nxt.isdigit() or (not nxt and _sib.match(prv)))
        no = t.lstrip("0123456789")
        first = t[0]
        print("  item=%r m_gb=%s m_HEAD=%s m_chap=%s is_chapter=%s plaus=%s nxt=%r" % (
            t[:16], bool(_CLAUSE_GB.match(t)), bool(_CHAPTER_HEAD.match(t)),
            bool(_CHAPTER_CLAUSE.match(t)), is_chapter,
            bool(_plausible_clause_head(first, t[len(first):])), nxt[:18]))
clauses = split_items_into_clauses(items)
print("---- 切分后条款 ----")
for c in clauses:
    print("  [%s] %s" % (c.number, (c.texts[0] or "")[:30]))
