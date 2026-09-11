"""R49 影响面分析（Phase 9 完整版）。

换版（新版入库替代旧版）后统计受影响面：收藏/批注/项目清单/审查报告，
并复用 compare_docs 输出条款级变化（含模态变化清单）。
"""
from __future__ import annotations

import json

from src.core.storage.versioning import compare_docs
from src.core.storage.sqlite_db import get_db_connection


def analyze_impact(old_doc_id: str, new_doc_id: str) -> dict:
    """旧版被新版替代时的影响面报告。"""
    conn = get_db_connection()

    # 旧版条款的 clause_key 集合（收藏/批注绑定 clause_key，跨版本平移）
    old_rows = conn.execute(
        "SELECT clause_revision_id, clause_key, clause_number FROM clause_revision"
        " WHERE doc_id=?", (old_doc_id,)).fetchall()
    old_keys = {r["clause_key"] for r in old_rows}
    old_nums = {r["clause_number"] for r in old_rows}
    key_to_num = {r["clause_key"]: r["clause_number"] for r in old_rows}

    bookmarks = conn.execute("SELECT bookmark_id, clause_key FROM user_bookmark").fetchall()
    annotations = conn.execute(
        "SELECT annotation_id, clause_key FROM user_annotation").fetchall()

    affected_bookmarks = [b["bookmark_id"] for b in bookmarks if b["clause_key"] in old_keys]
    affected_annotations = [a["annotation_id"] for a in annotations
                            if a["clause_key"] in old_keys]

    # 项目清单：clause_revision_ids 含旧版条款
    projects = conn.execute("SELECT project_id, project_name, clause_revision_ids"
                            " FROM project_list").fetchall()
    old_rev_ids = {r["clause_revision_id"] for r in old_rows}
    affected_projects = []
    for p in projects:
        ids = json.loads(p["clause_revision_ids"] or "[]")
        hit = [i for i in ids if i in old_rev_ids]
        if hit:
            affected_projects.append({"project_id": p["project_id"],
                                      "project_name": p["project_name"],
                                      "clauses": len(hit)})

    # 条款级变化（复用 compare_docs）
    compare = compare_docs(old_doc_id, new_doc_id)
    modality_changes = [p for p in compare["pairs"] if p["modality_changed"]]

    return {
        "old_doc_id": old_doc_id, "new_doc_id": new_doc_id,
        "stats": {
            "affected_bookmarks": len(affected_bookmarks),
            "affected_annotations": len(affected_annotations),
            "affected_projects": len(affected_projects),
            "changed_clauses": sum(1 for p in compare["pairs"] if p["changed"]),
            "modality_changes": len(modality_changes),
            "added_clauses": compare["stats"]["added"],
            "removed_clauses": compare["stats"]["removed"],
        },
        "affected_bookmarks": affected_bookmarks[:50],
        "affected_annotations": affected_annotations[:50],
        "affected_projects": affected_projects[:20],
        "modality_changes": [{
            "clause_number": p["clause_number"],
            "old": p["modality_changed"]["old"],
            "new": p["modality_changed"]["new"],
            "direction": p["modality_changed"]["direction"],
        } for p in modality_changes[:30]],
        "changed_clause_numbers": [p["clause_number"] for p in compare["pairs"]
                                   if p["changed"]][:50],
    }
