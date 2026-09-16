# -*- coding: utf-8 -*-
"""OCR 数字回填（R58 补丁机制）：MinerU 对部分 PDF 的文本层数字提取失败
（嵌入字体编码不标准），pypdf 能正确还原。入库后比对条款数字密度，
MinerU 明显缺失时以 pypdf 文本打纠错补丁（可撤销、原始快照零侵入）。

CLI: python -m src.core.ingestion.pypdf_backfill [--doc <doc_id>]
     不传 --doc 时扫描全部 PDF 文档。
"""
from __future__ import annotations

import logging
import os
import re
import sys

from src.core.storage.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)

_CLAUSE = re.compile(r"^(\d+(?:\.\d+)+)\s*(.*)$")

#: 条款正文的**终止锚**：命中即认为本条款已结束、停止归并（2026-09-16 新增）。
#
# 缺陷证据（生产库实测）：旧实现只在下一条**数字条款号**处切分，于是
# `表3` / `附录A` / `第5章` / 页眉 `'5 GB/T 10029—2010'` / 工具水印
# `'Evaluation Only. Created with Aspose.PDF…'` 都不被认作边界 → buf 一路吃到
# **页尾**，把页眉、页脚水印、后续表格与附录全并进该条款。实测：
# 19,981 条 content_text 补丁里 **14,906 条（74.6%）** 含盗版站页脚/页眉，
# 而原文 **0 条** —— 污染 100% 由本函数引入，再经 `fetch_full_clause` 透明覆写
# 进入检索、引用与 LLM 提示词。
#
# 判据取"结构标记"而非"任意行"，避免把正文里的普通句子当边界：
#   ① 数字条款号（原判据，保留）；
#   ② 表/图/附录的编号行（`表3 …` / `图 4 …` / `附录A …` / `附录 B.2 …`）；
#   ③ 页眉（页码 + 标准号前缀族 + 年份）；
#   ④ 已知工具/站点水印。
_ANCHOR_TABLE_FIG = re.compile(
    r"^\s*(?:表|图)\s*[A-Za-z]?(?:\.\d+)*\s*\d*(?:\.\d+)*\s*\S")
_ANCHOR_APPENDIX = re.compile(r"^\s*附\s*录\s*[A-Za-z]?\s*\d*(?:\.\d+)*\s*\S?")
_ANCHOR_HEADER = re.compile(
    r"^\s*\d{1,4}\s+(?:GB|DB|JGJ|JG|CJJ|CJ|HG|SH|SY|NB|DL|YB|TB|JT|MT|AQ|TSG)"
    r"\s*/?\s*[A-Z]?\s*\d{3,5}(?:\.\d+)?\s*[—\-–]\s*\d{2,4}\s*$", re.I)
_ANCHOR_WM = re.compile(r"Aspose\.PDF|Evaluation Only|Created with Aspose", re.I)


def _is_terminator(s: str) -> bool:
    """该行是否终止当前条款的归并（结构标记/页眉/水印）。"""
    return bool(_ANCHOR_TABLE_FIG.match(s) or _ANCHOR_APPENDIX.match(s)
                or _ANCHOR_HEADER.match(s) or _ANCHOR_WM.search(s))


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
            # 双包回退：pypdf 优先，PyPDF2 老环境兜底（二者同源 API）。
            from pypdf import PdfReader
        else:
            # PyPDF2 与上一分支同名 import（no-redef 是主要诉求；import-untyped
            # 由全局 ignore_missing_imports 兜住，此处不重复声明——verifier 反证）。
            from PyPDF2 import PdfReader  # type: ignore[no-redef]
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
            # **终止锚**（2026-09-16 新增）：表/图/附录编号、页眉、工具水印
            # 出现即认为本条款已结束 —— 旧实现继续归并，把页尾一切并进条款
            # （见 `_ANCHOR_*` 的缺陷证据）。命中即封闭本条款并清空 cur_no，
            # 使后续内容不再挂到它名下。
            if _is_terminator(s):
                out[cur_no] = " ".join(buf)
                cur_no, buf = None, []
                continue
            buf.append(s)
    if cur_no:
        out[cur_no] = " ".join(buf)
    return out


def _digits(t: str | None) -> int:
    return sum(ch.isdigit() for ch in (t or ""))


def _reindex_fts(conn, clause_revision_id: str, content_text: str,
                 title: str | None, modality: str | None,
                 subject: str | None, behavior_scope: str | None) -> None:
    """把补丁后的正文同步进 `clause_fts`（**只 FTS，不碰向量**）。

    为什么本函数存在而不直接调 `clause_repo._reindex_clause_indexes`：
      ① 那个函数**同时**重算向量（`embed_query` + fastembed），在 `backfill_all`
         逐文档扫全库的路径上会把一次回填从分钟级推到小时级；
      ② 本模块是 ingestion 层，`clause_repo` 是 storage 层，函数级 import 只为
         一个索引同步引入跨层依赖不划算。
    两者的 FTS 口径**必须一致**：`content_segmented = _seg(content_text)`，
    且 modality/subject/behavior_scope 走同一列的原文（本函数不改它们）。
    """
    from src.core.storage.clause_repo import _seg  # noqa: PLC0415（函数级，避免跨层顶层依赖）
    conn.execute(
        "UPDATE clause_fts SET title=?, content_segmented=?, modality=?, subject=?,"
        " behavior_scope_segmented=? WHERE clause_revision_id=?",
        (title or "", _seg(content_text), modality or "", subject or "",
         _seg(behavior_scope or ""), clause_revision_id))


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
            "SELECT clause_revision_id, clause_number, page_start, page_end, content_text,"
            " title, modality, subject, behavior_scope"
            " FROM clause_revision WHERE doc_id=? AND content_type='normal'", (doc_id,)).fetchall()
        cache: dict[int, dict[str, str]] = {}
        patched = 0
        for rid, num, ps, pe, content, title, modality, subject, bscope in rows:
            if not num or "." not in num:
                continue
            for page in {ps, pe}:
                if page not in cache:
                    cache[page] = pypdf_page_clauses(pdf_path, page)
            ptxt = (cache.get(ps) or {}).get(num) or (cache.get(pe) or {}).get(num)
            if not ptxt:
                continue
            # **回填不得严重改变文本量级**（2026-09-16 新增护栏）。
            #
            # 为什么用"长度量级"而不是"相似度阈值"：实测补丁与原文的相似度
            # **中位仅 0.54**（去空白后 SequenceMatcher），任何合理阈值都会拒掉
            # 一半以上——而"低相似度补丁是坏的"这一点**没有被证明**（数字回填天然
            # 会插入空格与符号，相似度本就偏低）。在无证据的情况下硬设相似度阈值，
            # 会打掉真实修复，违反本仓库"证据先于放宽"的纪律。
            #
            # 而"长度量级"有**直接证据**：越界抽取把"条款号 → 页尾"整体并入，
            # 实测 69.5% 的污染补丁比原文长 50% 以上，最长者达原文的数倍；
            # 同时回填**不会**明显缩短正文（它只是补数字），故下限取得宽松。
            #
            # 口径：上限 3×，但留 400 字绝对余量（短条款的 3× 太小，会误杀
            # 真实回填——本用例 `test_backfill_accepts_reasonable_text` 抓出过）；
            # 下限 0.5×（回填只会加字符，缩短说明抽取不完整）。
            _n = len(content or "")
            _hi = max(_n * 3.0, _n + 400)
            if not (_n * 0.5 <= len(ptxt) <= _hi):
                logger.warning(
                    "pypdf 回填越界（长度 %d 不在原文 %d 的 [0.5×, 3×+400] 内）→ 拒绝：%s %s",
                    len(ptxt), _n, doc_id, num)
                continue
            if _digits(ptxt) > _digits(content) * 1.5 and _digits(ptxt) >= 3:
                exists = conn.execute(
                    "SELECT 1 FROM clause_patch WHERE clause_revision_id=? AND field_name='content_text'",
                    (rid,)).fetchone()
                if exists:
                    continue
                patched_value = ptxt[:2000]
                conn.execute(
                    "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
                    " patched_value, patch_reason, created_at)"
                    " VALUES (?,?,?,?,?, datetime('now'))",
                    ("bp_" + rid[-12:], rid, "content_text", patched_value, "OCR数字回填(pypdf)"))
                # **同步 FTS 索引**（2026-09-16 新增；本函数是一个孤立缺陷点）。
                #
                # 缺陷：本函数用**裸 INSERT** 写 `clause_patch`，绕过了
                # `clause_repo.upsert_patch` 里的 `_reindex_clause_indexes` —— 而
                # `fetch_full_clause` 读的是**补丁正文**，`clause_fts` 却仍存补丁前原文。
                # 后果：这些条款的**全文检索命中的是旧文本**（用户按新正文里的词搜不到）。
                # 实测口径：全库 19,981 条 content_text 补丁全部由本函数产生
                # （`patch_reason` 100% 为 `OCR数字回填(pypdf)`），故这批条款的 FTS
                # 从未按补丁正文同步过。
                #
                # 为什么只补 FTS、**不补向量**（诚实标注）：`_reindex_clause_indexes` 还会
                # 用 `embed_query(f"{title}\\n{content[:512]}")` 重算向量，而本函数在
                # **逐文档批量**路径上（`backfill_all` 扫全库），逐条加载 fastembed 会
                # 把一次回填从分钟级推到小时级。且回填只改**尾部**（补数字/去水印），
                # 而向量只看前 512 字 —— 影响远小于对全文检索的影响。
                # 取舍：FTS 必补（用户直接可感），向量留待有需要时按文档批量重算。
                _reindex_fts(conn, rid, patched_value, title, modality, subject, bscope)
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
