"""法规更新检查（LAW_SOURCE_PLAN §6）：比对库内官方来源文档与官方源现状。

- 时效变更：flk detail.sxx 与入库时 source_status 比对（已修改/已废止）
- 新版本：当前文档已非有效版时，同标题搜索 sxx=3 有效版 → 提示重导
不落库、不删除；纯只读比对。
"""
from __future__ import annotations

from src.core.knowledge.law_source import flk_client as flk
from src.core.storage.sqlite_db import get_db_connection


def check_law_updates() -> dict:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT doc_id, standard_no, standard_name, source, source_id, source_status"
        " FROM doc_meta WHERE source IS NOT NULL AND source != ''").fetchall()
    findings: dict = {"checked": len(rows), "status_changes": [], "new_versions": []}
    for r in rows:
        if r["source"] == "flk":
            _check_flk(findings, r)
    return findings


def _check_flk(findings: dict, r) -> None:
    try:
        d = flk.detail(r["source_id"])
    except Exception:
        return
    base = {"doc_id": r["doc_id"], "standard_no": r["standard_no"],
            "standard_name": r["standard_name"], "bbbs": r["source_id"]}
    # 1) 时效变更（sxx: 3=有效, 2=已修改, 1=已废止/其他）
    if d.sxx is not None:
        stored = r["source_status"]
        if stored is None or str(stored) != str(d.sxx):
            findings["status_changes"].append({
                **base, "old_status": stored, "new_status": str(d.sxx),
                "title": d.title})
    # 2) 当前已非有效版 → 找同标题有效版提示重导
    if d.sxx is not None and d.sxx != 3:
        try:
            data = flk.search(r["standard_name"][:40], search_range=1,
                              search_type=1, sxx=[3], page=1, page_size=10)
            for hit in flk.parse_rows(data):
                if hit["bbbs"] != r["source_id"] and hit["flxz"] in (
                        "法律", "行政法规", "宪法"):
                    findings["new_versions"].append({
                        **base, "new_bbbs": hit["bbbs"], "new_title": hit["title"],
                        "new_gbrq": hit["gbrq"], "current_sxx": d.sxx})
                    break
        except Exception:
            pass
