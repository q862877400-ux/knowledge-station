"""版本替代链与条款对比（Phase 6：R29 替代链 / R42 版本对照 / R49 模态变化清单）。

对照规则：
- 版本链沿 doc_meta.superseded_by 追踪（旧→新）；
- 条款匹配优先 clause_key（跨修订平移），回退 clause_number 精确匹配；
- 变化判定：文本相似度 + 模态词变化（R49：旧版"宜"→新版"应"等）。
"""
from __future__ import annotations

import difflib
import json
from typing import Any

from src.core.domain.models import MODALITY_STRENGTH
from src.core.storage.sqlite_db import get_db_connection


def version_chain(doc_id: str) -> list[dict]:
    """沿 superseded_by 双向展开版本链（旧→新，含自己）。"""
    conn = get_db_connection()
    # 全量索引（库内文档数有限）：链尾（superseded_by 为 NULL 的现行版）
    # 也必须可见，否则链条在最后一段断掉
    rows = conn.execute(
        "SELECT doc_id, standard_no, standard_name, legal_status, effective_from,"
        " superseded_by FROM doc_meta").fetchall()
    index = {r["doc_id"]: dict(r) for r in rows}
    # 从给定 doc 出发找链头（最旧）
    chain: list[dict] = []
    cur = doc_id
    for _ in range(20):
        r = index.get(cur)
        if r is None:
            break
        chain.append(r)
        nxt = r.get("superseded_by")
        if not nxt or nxt == cur:
            break
        cur = nxt
    return chain


def _clause_index(conn, doc_id: str) -> dict[str, dict]:
    rows = conn.execute(
        "SELECT clause_revision_id, clause_key, clause_number, content_text, modality,"
        " modality_strength, page_start FROM clause_revision WHERE doc_id=? "
        " AND content_type='normal'", (doc_id,)).fetchall()
    idx: dict[str, dict] = {}
    for r in rows:
        d = dict(r)
        d["similar"] = 1.0
        idx[d["clause_key"]] = d            # 优先 key 匹配
        idx.setdefault(f"no:{d['clause_number']}", d)  # 回退条款号匹配
    return idx


def compare_docs(doc_a: str, doc_b: str) -> dict[str, Any]:
    """两文档条款对照（R42 版本对照 / R16 跨标准对比共用）。

    返回 {a, b: meta, pairs, stats}；pairs 含 modality_changed（R49 模态变化清单）。
    """
    conn = get_db_connection()
    meta_a = conn.execute(
        "SELECT doc_id, standard_no, standard_name, legal_status, effective_from"
        " FROM doc_meta WHERE doc_id=?", (doc_a,)).fetchone()
    meta_b = conn.execute(
        "SELECT doc_id, standard_no, standard_name, legal_status, effective_from"
        " FROM doc_meta WHERE doc_id=?", (doc_b,)).fetchone()
    if meta_a is None or meta_b is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError("对比文档不存在", code="doc_not_found")

    idx_a, idx_b = _clause_index(conn, doc_a), _clause_index(conn, doc_b)
    pairs = []
    seen_b: set[str] = set()
    paired_a: set[str] = set()   # 已配对的旧版 revision（removed 判据，见文件末注释）
    for key, ca in idx_a.items():
        cb = idx_b.get(key)
        if cb is None:
            continue
        if key.startswith("no:") and (ca["clause_key"] in idx_b):
            continue  # key 已配对，跳过条款号回退项
        seen_b.add(cb["clause_revision_id"])
        paired_a.add(ca["clause_revision_id"])
        old_text, new_text = ca["content_text"] or "", cb["content_text"] or ""
        sim = difflib.SequenceMatcher(None, old_text[:500], new_text[:500]).ratio()
        modality_changed = None
        if ca.get("modality") and cb.get("modality") and ca["modality"] != cb["modality"]:
            strength_a = MODALITY_STRENGTH.get(ca["modality"], -1)
            strength_b = MODALITY_STRENGTH.get(cb["modality"], -1)
            if strength_a != strength_b:
                modality_changed = {
                    "old": ca["modality"], "new": cb["modality"],
                    "old_strength": strength_a, "new_strength": strength_b,
                    "direction": "strengthened" if strength_b > strength_a else "weakened",
                }
        pairs.append({
            "clause_number": cb["clause_number"],
            "old": {"content": old_text[:800], "modality": ca.get("modality"),
                    "page_start": ca.get("page_start")},
            "new": {"content": new_text[:800], "modality": cb.get("modality"),
                    "page_start": cb.get("page_start")},
            "changed": sim < 0.999,
            "similarity": round(sim, 3),
            "modality_changed": modality_changed,
        })

    # 仅存在于其中一方的条款（新增/删除）
    # ⚠ 2026-09-16 修复（iteration-6 自查 §7）：旧实现把 doc_a 的 revision_id 与
    # `idx_b.values()` 的全部 revision_id 比对——而 `_clause_index` 按 `WHERE doc_id=?`
    # 建索引，两个不同文档的 revision_id **必然互不相同**，故该判据**恒真**，
    # `removed` 恒等于「旧版全部条款号」（连两版完全相同时也报全删）。
    # 该值经 storage/impact.py:60 进入 `POST /api/v1/documents/impact` 的影响面报告，
    # 属用户可见输出。现改为按「该条款**是否配对成功**」判定。
    added = [v["clause_number"] for k, v in idx_b.items()
             if k.startswith("no:") and v["clause_revision_id"] not in seen_b]
    removed = [v["clause_number"] for k, v in idx_a.items()
               if k.startswith("no:") and v["clause_revision_id"] not in paired_a]

    return {
        "a": dict(meta_a), "b": dict(meta_b),
        "pairs": pairs,
        "stats": {"paired": len(pairs), "added": len(added), "removed": len(removed),
                  "modality_changes": sum(1 for p in pairs if p["modality_changed"])},
        "added_clause_numbers": added[:30],
        "removed_clause_numbers": removed[:30],
    }
