# -*- coding: utf-8 -*-
"""OCR 数字回填（R58 补丁机制）：MinerU 对部分 PDF 的文本层数字提取失败
（嵌入字体编码不标准），pypdf 能正确还原。入库后比对条款数字密度，
MinerU 明显缺失时以 pypdf 文本打纠错补丁（可撤销、原始快照零侵入）。

CLI: python -m src.core.ingestion.pypdf_backfill [--doc <doc_id>]
     不传 --doc 时扫描全部 PDF 文档。
"""
from __future__ import annotations

import os
import re
import sys

from src.core.storage.sqlite_db import get_db_connection

_CLAUSE = re.compile(r"^(\d+(?:\.\d+)+)\s*(.*)$")


def _pypdf_available() -> bool:
    try:
        import pypdf  # noqa: F401
        return True
    except ImportError:
        try:
            import PyPDF2  # noqa: F401
            return True
        except ImportError:
            return False


def pypdf_page_clauses(pdf_path: str, page_no: int) -> dict[str, str]:
    """pypdf 提取指定页文本 → 按行首条款号切分 {number: text}。"""
    if not _pypdf_available():
        return {}
    try:
        if sys.modules.get("pypdf"):
            from pypdf import PdfReader
        else:
            from PyPDF2 import PdfReader
    except Exception:
        return {}
    try:
        r = PdfReader(pdf_path)
        if page_no < 1 or page_no > len(r.pages):
            return {}
        t = (r.pages[page_no - 1].extract_text() or "").replace("\u3000", " ").replace("\xa0", " ")
    except Exception:
        return {}
    out: dict[str, str] = {}
    cur_no, buf = None, []
    for ln in t.splitlines():
        s = ln.strip()
        if not s:
            continue
        m = _CLAUSE.match(s)
        if m and (len(m.group(1)) >= 3 or m.group(1).count(".") >= 1):
            if cur_no:
                out[cur_no] = " ".join(buf)
            cur_no = m.group(1)
            buf = [s]
        elif cur_no:
            buf.append(s)
    if cur_no:
        out[cur_no] = " ".join(buf)
    return out


def _digits(t: str | None) -> int:
    return sum(ch.isdigit() for ch in (t or ""))


def backfill_document(doc_id: str, pdf_path: str | None, conn=None) -> int:
    """对单个文档执行回填，返回打补丁条数。
    注意：get_db_connection 返回线程局部共享连接——绝不 close（关闭会导致
    后续同线程 init_schema/查询报 "Cannot operate on a closed database"）。"""
    if not pdf_path or not os.path.exists(pdf_path):
        return 0
    if not _pypdf_available():
        return 0
    own = conn is None
    if own:
        conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT clause_revision_id, clause_number, page_start, page_end, content_text"
            " FROM clause_revision WHERE doc_id=? AND content_type='normal'", (doc_id,)).fetchall()
        cache: dict[int, dict[str, str]] = {}
        patched = 0
        for rid, num, ps, pe, content in rows:
            if not num or "." not in num:
                continue
            for page in {ps, pe}:
                if page not in cache:
                    cache[page] = pypdf_page_clauses(pdf_path, page)
            ptxt = (cache.get(ps) or {}).get(num) or (cache.get(pe) or {}).get(num)
            if not ptxt:
                continue
            if _digits(ptxt) > _digits(content) * 1.5 and _digits(ptxt) >= 3:
                exists = conn.execute(
                    "SELECT 1 FROM clause_patch WHERE clause_revision_id=? AND field_name='content_text'",
                    (rid,)).fetchone()
                if exists:
                    continue
                conn.execute(
                    "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
                    " patched_value, patch_reason, created_at)"
                    " VALUES (?,?,?,?,?, datetime('now'))",
                    ("bp_" + rid[-12:], rid, "content_text", ptxt[:2000], "OCR数字回填(pypdf)"))
                # 联动：回填即复核确认，存疑转可信
                conn.execute(
                    "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
                    " patched_value, patch_reason, created_at)"
                    " VALUES (?,?,?,?,?, datetime('now'))",
                    ("bpv_" + rid[-12:], rid, "is_suspicious", "false", "OCR回填联动"))
                patched += 1
        if own:
            conn.commit()
        return patched
    finally:
        pass  # 共享线程局部连接绝不 close（关闭会让后续同线程操作全部报 closed）


def backfill_all(conn=None) -> int:
    """扫描全部含 PDF 原件的文档执行回填。"""
    own = conn is None
    if own:
        conn = get_db_connection()
    try:
        docs = conn.execute(
            "SELECT doc_id, file_path FROM doc_meta WHERE file_path LIKE '%.pdf'").fetchall()
        total = 0
        for did, fpath in docs:
            total += backfill_document(did, fpath, conn)
        if own:
            conn.commit()
        return total
    finally:
        pass  # 共享线程局部连接绝不 close


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default=None, help="只处理指定 doc_id")
    args = ap.parse_args()
    n = backfill_document(args.doc, None) if args.doc else backfill_all()
    print(f"pypdf 回填补丁: {n} 条")
