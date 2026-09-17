# -*- coding: utf-8 -*-
"""材料平面：**Track L —— 采到的法规/标准要怎么进法条库**（Phase C 第二步，2026-09-17）。

## 这一段在整条链里的位置
`collect.collect_text` 会在 `tier_evidence['track_l']` 里记下"这**可能**是一部标准的正文"
（`status: pending_review`）。之后评审通过，才轮到"要不要把它变成法条库里的正式文档"。
本模块就是那个**决策**：库内已有 ⇒ 只回指；库内没有 ⇒ 需要入库（走既有 ingest 管线）。

## 方案 §4.1 的纪律（本模块据此写死）
> Track L（采到库内没有的法规标准）评审通过后仍走**既有 ingest 管线**入 `doc_meta`，
> 再由 `material.doc_id` **从材料侧回指**——**法条链一个字段都不改**。

所以本模块：
- **只读** `doc_meta`（判断"有没有"），**不写**它；
- 唯一会写的动作是 `link_doc`（写 `material.doc_id`，属**材料平面**的列）；
- 真正的入库（写 `doc_meta` / `clause_revision`）**留给下一步**，且必须复用既有管线。

## 三条门（顺序即优先级，写在这里以免别处再判一次）
1. **材料必须存在**；
2. **必须已批准**——这是评审硬门，**没有例外**：未批准的材料**不可能**进法条库
   （否则就出现"绕过评审把东西塞进法规库"的最坏路径）；
3. **必须带 `track_l` 意图**——没认出是标准的普通资料，Track L 不适用（正常跳过）。

## 诚实边界
- 判"库内有没有"只按 `standard_no` 的**比较键**（`text_utils.standard_no_key`）——
  它是 Exact 匹配（含年份与部分号），**不做**"同一标准的不同版本/勘误"的模糊关联。
- 采集件的正文来自网页 ⇒ **不是**官方原件。即使入库，`doc_meta` 的
  `legal_status`/`legal_hierarchy` 等判据仍应由既有管线的规则给，**本模块不代它决定**。
- 本模块**不抓网、不解析 PDF**。
"""
from __future__ import annotations

from typing import Any

from src.core.storage import material_repo as mr
from src.core.storage.sqlite_db import get_db_connection
from src.core.text_utils import standard_no_key

#: 可能的动作（给 UI/日志用；**唯一一处**定义）。
ACTIONS = ("skip", "blocked", "link", "import")


def track_l_intent(material: dict[str, Any] | None) -> dict[str, Any] | None:
    """从材料里取 Track L 意图（`tier_evidence.track_l`）。没有则 `None`。

    `tier_evidence` 在库里是 JSON 文本、经 `_material_row` 解出来是 dict；
    这里对两种形态都容错（旧行可能是字符串）。
    """
    if not material:
        return None
    ev = material.get("tier_evidence")
    if isinstance(ev, str):
        import json
        try:
            ev = json.loads(ev)
        except Exception:  # noqa: BLE001 — 坏 JSON 不该让决策抛错，按"没有意图"处理
            return None
    if not isinstance(ev, dict):
        return None
    intent = ev.get("track_l")
    return intent if isinstance(intent, dict) else None


def find_existing_doc(standard_no: str | None) -> str | None:
    """库内是否已有这部标准（按比较键 Exact 匹配）→ 返回 `doc_id` 或 `None`。

    **只读** `doc_meta`。为什么在 Python 侧比对而不是 SQL `WHERE standard_no=?`：
    库内写法是 `GB 10146-2015`，采集侧是 `GB10146-2015` —— SQL 里等不上，
    而"归一成一个键再比"这件事已经有唯一所有者（`text_utils.standard_no_key`）。
    """
    key = standard_no_key(standard_no)
    if not key:
        return None
    rows = get_db_connection().execute("SELECT doc_id, standard_no FROM doc_meta").fetchall()
    for doc_id, stored in rows:
        if standard_no_key(stored) == key:
            return str(doc_id)
    return None


def plan_import(material_id: str) -> dict[str, Any]:
    """**决策**（不产生任何写入）：这份材料在 Track L 下该做什么。

    Returns:
        `{action, material_id, standard_no?, existing_doc_id?, why}`，
        其中 `action ∈ ACTIONS`：
        - `skip`    —— 不是标准正文（没有 track_l 意图）；
        - `blocked` —— **未批准**（评审硬门，绝不越过）；
        - `link`    —— 库内已有 ⇒ 只需从材料侧回指；
        - `import`  —— 库内没有 ⇒ 需要入库（**本模块不做**，下一步复用既有管线）。
    """
    mat = mr.get_material(material_id)
    if mat is None:
        return {"action": "skip", "material_id": material_id, "why": "材料不存在"}

    intent = track_l_intent(mat)
    if intent is None:
        return {"action": "skip", "material_id": material_id,
                "why": "没有 track_l 意图（不是被认出的标准正文）"}

    if mat.get("review_status") != "approved":
        return {
            "action": "blocked", "material_id": material_id,
            "standard_no": intent.get("standard_no"),
            "why": f"材料未批准（review_status={mat.get('review_status')!r}）——"
                   "评审硬门：未批准的材料不可能进法条库",
        }

    standard_no = intent.get("standard_no")
    existing = find_existing_doc(standard_no)
    if existing is not None:
        return {"action": "link", "material_id": material_id, "standard_no": standard_no,
                "existing_doc_id": existing,
                "why": "库内已有这部标准（按比较键匹配）⇒ 只需从材料侧回指"}
    return {"action": "import", "material_id": material_id, "standard_no": standard_no,
            "why": "库内没有这部标准 ⇒ 需走既有 ingest 管线入库（本模块不做，见模块头注）"}


def apply_link(material_id: str) -> dict[str, Any]:
    """执行 `link` 动作（**唯一会写的操作**，且只写材料平面的 `doc_id` 列）。

    - `link`   → 回指成功，返回 `linked: True`；
    - 其它动作 → **什么都不做**并原样返回决策（调用方据此如实报告，
      尤其 `import` 要能被看到"还没入库"，而不是静默成功）。
    """
    plan = plan_import(material_id)
    if plan["action"] != "link":
        return {**plan, "linked": False}
    ok = mr.link_doc(material_id, str(plan["existing_doc_id"]))
    return {**plan, "linked": bool(ok)}
