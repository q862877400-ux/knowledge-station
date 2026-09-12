"""双向溯源（Task 12.2）：条款 → 被谁引用。

聚合 debug_dump（提问证据）、user_bookmark、project_list、obligation_list.items、
review_point.matched_clause_ids——按 clause_key / clause_revision_id 匹配。
"""
from __future__ import annotations

import json

from src.core.exceptions import KnowledgeStationError
from src.core.storage.sqlite_db import get_db_connection


def query_backlinks(clause_revision_id: str) -> dict:
    conn = get_db_connection()
    cr = conn.execute(
        "SELECT clause_key, clause_number FROM clause_revision WHERE clause_revision_id=?",
        (clause_revision_id,)).fetchone()
    if cr is None:
        raise KnowledgeStationError(f"条款不存在: {clause_revision_id}",
                                    code="clause_not_found")
    key, number = cr["clause_key"], cr["clause_number"]

    backlinks: dict[str, list[dict]] = {
        "qa": [], "bookmarks": [], "projects": [], "obligations": [], "reviews": []}

    # 1. 问答引用（debug_dump.retrieval_result 中的证据）
    for r in conn.execute(
            "SELECT query, created_at FROM debug_dump WHERE retrieval_result LIKE ?"
            " ORDER BY created_at DESC LIMIT 20", (f"%{clause_revision_id}%",)).fetchall():
        backlinks["qa"].append({"query": r["query"], "created_at": r["created_at"]})

    # 2. 收藏（clause_key）
    for r in conn.execute(
            "SELECT bookmark_id, remark, created_at FROM user_bookmark WHERE clause_key=?",
            (key,)).fetchall():
        backlinks["bookmarks"].append(dict(r))

    # 3. 项目清单（clause_revision_id 在 JSON 数组）
    for r in conn.execute("SELECT project_id, project_name, clause_revision_ids FROM project_list").fetchall():
        ids = json.loads(r["clause_revision_ids"] or "[]")
        if clause_revision_id in ids:
            backlinks["projects"].append({"project_id": r["project_id"],
                                          "project_name": r["project_name"]})

    # 4. 义务清单/检查表（items JSON 内 clause_revision_id）
    for r in conn.execute("SELECT list_id, business_description, items FROM obligation_list").fetchall():
        items = json.loads(r["items"] or "[]")
        if any(it.get("clause_revision_id") == clause_revision_id for it in items):
            backlinks["obligations"].append({"list_id": r["list_id"],
                                             "business_description": r["business_description"]})

    # 5. 审查报告点（matched_clause_ids JSON）
    for r in conn.execute(
            "SELECT point_id, point_type, verdict FROM review_point"
            " WHERE matched_clause_ids LIKE ?", (f"%{clause_revision_id}%",)).fetchall():
        backlinks["reviews"].append(dict(r))

    total = sum(len(v) for v in backlinks.values())
    return {"clause_revision_id": clause_revision_id, "clause_key": key,
            "clause_number": number, "total": total, "backlinks": backlinks}
