"""义务清单与检查表引擎（R-L9，阶段4）。

业务活动描述 → 召回对业务设定义务的"应当/必须"型法条/条款 →
按主题（文档/领域）分组 → 可勾选自查表（勾选状态持久化）。
"""
from __future__ import annotations

from src.core.retrieval.hybrid_engine import perform_hybrid_search
from src.core.storage import user_data
from src.core.storage.sqlite_db import get_db_connection


def generate_obligation_list(business_description: str, top_k: int = 12) -> dict:
    """从本地库召回义务条款，生成义务清单并落库。

    双重校验：modality 为应当型 **且** 正文确实含义务词
    （防御库内 modality 与内容不一致的行，如手工插入/分型漂移）。
    """
    matched = perform_hybrid_search(business_description, top_k=top_k * 2)
    obligations = [
        c for c in matched
        if c.modality in ("应当", "应", "必须") and c.modality_strength == 3
        and any(w in (c.content_text or "") for w in ("应当", "应", "必须"))]

    conn = get_db_connection()
    items: list[dict] = []
    seen = set()
    for c in obligations:
        if c.clause_revision_id in seen:
            continue
        seen.add(c.clause_revision_id)
        doc = conn.execute(
            "SELECT domain_tags FROM doc_meta WHERE doc_id=?", (c.doc_id,)).fetchone()
        items.append({
            "clause_revision_id": c.clause_revision_id,
            "standard_no": c.standard_no,
            "clause_number": c.clause_number,
            "obligation_text": (c.content_text or "")[:300],
            "group": _topic_of(doc["domain_tags"] if doc else None, c.standard_no),
            "checked": False,
        })
        if len(items) >= top_k:
            break

    out = user_data.save_obligation_list(business_description, items, mode="list")
    return {"list_id": out["list_id"], "business_description": business_description,
            "groups": _grouped(items), "count": len(items)}


def to_checklist(list_id: str) -> dict:
    """转换为检查表模式：每条义务 → 是/否自查问句。"""
    data = user_data.get_obligation_list(list_id)
    if data is None:
        from src.core.exceptions import KnowledgeStationError
        raise KnowledgeStationError(f"清单不存在: {list_id}", code="list_not_found")
    items = []
    for it in data["items"]:
        q = it["obligation_text"].strip().rstrip("。；;")
        items.append({**it, "question": f"是否已落实：{q[:120]}？"})
    user_data.update_obligation_list(list_id, items)
    return {"list_id": list_id, "groups": _grouped(items), "count": len(items),
            "mode": "checklist"}


def toggle_check(list_id: str, clause_revision_id: str, checked: bool) -> bool:
    data = user_data.get_obligation_list(list_id)
    if data is None:
        return False
    for it in data["items"]:
        if it["clause_revision_id"] == clause_revision_id:
            it["checked"] = bool(checked)
    return user_data.update_obligation_list(list_id, data["items"])


def _topic_of(domain_tags_json: str | None, standard_no: str) -> str:
    import json as _json
    try:
        tags = _json.loads(domain_tags_json or "[]")
    except Exception:
        tags = []
    if tags:
        return tags[0]
    return standard_no[:12]


def _grouped(items: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for it in items:
        groups.setdefault(it["group"], []).append(it)
    return [{"group": g, "items": its} for g, its in groups.items()]
