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
- **落库的 `standard_no` 写法与库内既有行不一致**（这是一个**已知的观感问题**，不是判据问题）：
  新入库的行用的是 `auto_tag` 的归一形 **`GB88888-2088`**（无空格），
  而库内既有 6417 行是 **`GB 10146-2015`**（带空格）。
  判重/比较走 `standard_no_key`，**不受影响**；但拼写不统一，将来若做"按标准号列目录"
  会看到两种写法。⇒ 需要写一个**canonicalizer**，而它必须正确处理 `DB11/T 1234` 这类
  "前缀里带数字"的号段——所以**没有**用一行正则糊上去（那会把 `DB11/T` 变成 `DB 11/T`，
  比不统一更糟）。这是留给后续的一个明确待办。
- 采集件的正文来自网页 ⇒ **不是**官方原件。即使入库，`doc_meta` 的
  `legal_status`/`legal_hierarchy` 等判据仍应由既有管线的规则给，**本模块不代它决定**。
- 本模块**不抓网、不解析 PDF**。
"""
from __future__ import annotations

import re
from typing import Any

from src.core.storage import material_repo as mr
from src.core.storage.sqlite_db import get_db_connection
from src.core.text_utils import law_name_key, standard_no_key

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


def find_existing_law(law_name: str | None) -> str | None:
    """库内是否已有这部**法规**（按 `law_name_key` 比对 `standard_no`/`standard_name`）。

    为什么法规的"身份"在 `standard_no` 列里：既有法规管线 `law_source.ingest` 就是这么存的
    （`standard_no=standard_no or d.title`——法规没有号，**用名称当号**）。所以主判据是
    `standard_no`；`standard_name` 只在**法规类**文档上兜底（防同一部法两处写法不一致）。
    ⚠ **不**拿 `standard_name` 去匹配 `doc_type='standard'` 的行：那会把一部法规
    误判成"库内有"（标准名与法规名偶合），于是**该入库的法规被跳过**。
    """
    key = law_name_key(law_name)
    if not key:
        return None
    rows = get_db_connection().execute(
        "SELECT doc_id, standard_no, standard_name, doc_type FROM doc_meta").fetchall()
    for doc_id, std_no, name, doc_type in rows:
        if law_name_key(std_no) == key:
            return str(doc_id)
        if str(doc_type or "") != "standard" and law_name_key(name) == key:
            return str(doc_id)
    return None


def plan_import(material_id: str) -> dict[str, Any]:
    """**决策**（不产生任何写入）：这份材料在 Track L 下该做什么。

    两种意图（`doc_kind`）走**两条身份判据**，互不混用：
    - `standard`：按 `standard_no` 的**比较键**（`standard_no_key`，含年份/部分号）；
    - `law`：按**法规名的比较键**（`law_name_key`，**保留修正年份**——见那个函数的说明）。
    ⚠ 旧行可能没有 `doc_kind`（本字段是 2026-09-17 加的）：那时按"有 `standard_no`
    就当标准"回退，**不猜**法规。

    Returns:
        `{action, material_id, doc_kind, standard_no?|law_name?, existing_doc_id?, why}`，
        其中 `action ∈ ACTIONS`：
        - `skip`    —— 不是标准/法规正文（没有 track_l 意图）；
        - `blocked` —— **未批准**（评审硬门，绝不越过）；
        - `link`    —— 库内已有 ⇒ 只需从材料侧回指；
        - `import`  —— 库内没有 ⇒ 需要入库（`import_to_library` 走既有 ingest 管线）。
    """
    mat = mr.get_material(material_id)
    if mat is None:
        return {"action": "skip", "material_id": material_id, "why": "材料不存在"}

    intent = track_l_intent(mat)
    if intent is None:
        return {"action": "skip", "material_id": material_id,
                "why": "没有 track_l 意图（不是被认出的标准/法规正文）"}

    kind = str(intent.get("doc_kind") or ("standard" if intent.get("standard_no") else "law"))
    standard_no = intent.get("standard_no")
    law_name = intent.get("law_name")
    identity: dict[str, Any] = {"doc_kind": kind, "standard_no": standard_no,
                                "law_name": law_name}

    if mat.get("review_status") != "approved":
        return {
            "action": "blocked", "material_id": material_id, **identity,
            "why": f"材料未批准（review_status={mat.get('review_status')!r}）——"
                   "评审硬门：未批准的材料不可能进法条库",
        }

    if kind == "law":
        existing = find_existing_law(law_name)
        if existing is not None:
            return {"action": "link", "material_id": material_id, **identity,
                    "existing_doc_id": existing,
                    "why": "库内已有这部法规（按名称比较键匹配）⇒ 只需从材料侧回指"}
        return {"action": "import", "material_id": material_id, **identity,
                "why": "库内没有这部法规 ⇒ 需走既有 ingest 管线入库（按法规口径）"}

    existing = find_existing_doc(standard_no)
    if existing is not None:
        return {"action": "link", "material_id": material_id, **identity,
                "existing_doc_id": existing,
                "why": "库内已有这部标准（按比较键匹配）⇒ 只需从材料侧回指"}
    return {"action": "import", "material_id": material_id, **identity,
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


def _material_text(material_id: str) -> str:
    """把材料的切片拼回正文（**切片就是存档副本**——采集件没有源文件）。

    拼接用 `"\\n"` 而不是原分隔符：这里只要"能切出条款"的正文，不需要保真
    （法条侧会重新切分；保真不变量只在**材料侧引用**那条链上要求）。
    """
    chunks = mr.material_chunks(material_id)
    return "\n".join(str(c.get("text") or "") for c in chunks)


#: 法规名的**安全**层级推断（**只用不会错的规则**）。
#:
#: ⚠ 为什么这么保守：判效力层级（法律 / 行政法规 / 部门规章 / 地方性法规…）要看
#: **发行机关**，而采网页拿不到（`条例` 既可能是国务院行政法规、也可能是省人大地方性法规）。
#: 猜错等于把一个错误的位阶写进法规库——P1 上比"不写"坏得多。
#: ⇒ 只有"以 `法` 结尾 ⇒ 法律（狭义）"与"含司法解释字样 ⇒ 司法解释"两条是安全的，
#: 其余一律 **`未定`**（`doc_catalog._law_tier` 对未知值会自己按名称关键词再兜一层，
#: 兜不到就显示"未定级"——**不假装知道**）。
_LAW_HIER_SAFE = ("司法解释", "最高人民法院", "最高人民检察院")


def _law_hierarchy(name: str) -> str:
    """法规名 → `legal_hierarchy` 存储值（**保守**；不确定返回 `未定`）。"""
    base = re.sub(r"[（(][^）)]*[）)]\s*$", "", str(name or "").strip()).strip()
    if any(k in base for k in _LAW_HIER_SAFE):
        return "司法解释"
    # ⚠ **endswith("法") 会误吃"办法/方法/做法"**（实测踩到：`行政处罚办法` 被判成"法律"）——
    # 那正是"猜错位阶"的典型。排除掉这些才算"以法结尾"。
    if base.endswith("法典") or (base.endswith("法") and not base.endswith(("办法", "方法", "做法"))):
        return "法律"
    return "未定"


def import_to_library(material_id: str) -> dict[str, Any]:
    """**Track L 入库**：把已批准、库内没有的标准/法规正文灌进法条库。

    **必须已批准**（复用 `plan_import` 的门，不另判一次）。
    入库走**既有** `ingestion.law_text.ingest_law_text`（切分/分型/建边/事务都在那里，
    本函数不重写任何一段），成功后再回到材料侧 `link_doc` 回指。

    两个 `doc_type` 口径（**别混**，生产库 6417 行全是 `standard`）：
    - **标准**（`GB 88888-2088` 这类）→ `doc_type='standard'` +
      `legal_hierarchy` 用既有的 `pipeline._hier_from_no`（复用，不新写一份前缀判断）；
    - **法规**（`第X条` 形态，2026-09-17 起可识别）→ `doc_type='法律法规'`，
      `standard_no` **用法规名**（既有法规管线就是这个口径：
      `law_source.ingest._ingest(standard_no=standard_no or d.title)`），
      `legal_hierarchy` 由 `_law_hierarchy` 保守推断（不确定就是 `未定`，
      见那里的说明——**不假装知道位阶**）。

    ⚠ 采集件正文**来自网页、不是官方原件**：这里只负责"灌进去，
    使它能被检索/引用"，不替既有管线决定效力判据（那是 `doc_meta` 规则的事）。
    """
    plan = plan_import(material_id)
    if plan["action"] != "import":
        # blocked / skip / link 一律**不动法条链**（blocked 尤其重要：未批准不得入库）
        return {**plan, "imported": False}

    mat = mr.get_material(material_id) or {}
    body = _material_text(material_id)
    if not body.strip():
        return {**plan, "imported": False,
                "why": "材料没有切片（没有正文）——入库会造出一部空标准"}

    from src.core.ingestion.law_text import ingest_law_text
    from src.core.ingestion.pipeline import _hier_from_no

    if plan.get("doc_kind") == "law":
        law_name = str(plan.get("law_name") or "").strip()
        if not law_name:
            return {**plan, "imported": False,
                    "why": "track_l 意图里没有 law_name（法规名没取到）——"
                           "没有名字就没法在库里认它，宁可不入库"}
        result = ingest_law_text(
            body, law_name, str(mat.get("title") or law_name),
            legal_hierarchy=_law_hierarchy(law_name),
            domain_tags=None,
            doc_type="法律法规",
            short_code=None,                      # 法规口径（既有管线的默认截断规则）
            source_marker="material-collected://track-l",
            source_url=mat.get("url"),
        )
    else:
        standard_no = str(plan.get("standard_no") or "").strip()
        if not standard_no:
            return {**plan, "imported": False, "why": "track_l 意图里没有 standard_no"}
        result = ingest_law_text(
            body, standard_no, str(mat.get("title") or standard_no),
            legal_hierarchy=_hier_from_no(standard_no, fallback="GB"),
            domain_tags=None,
            doc_type="standard",
            # 短码口径与 `docx_ingest` 一致（去空格去连字符）
            short_code=standard_no.replace(" ", "").replace("-", ""),
            source_marker="material-collected://track-l",
            source_url=mat.get("url"),
        )
    status = result.get("status")
    # `standard_exists` 说明库内其实已有（归一化判据与既有查重口径不同导致的边界），
    # 那就退回"只回指"——**不要**把既有文档覆盖掉。
    if status == "standard_exists":
        doc_id = str(result.get("existing_doc_id") or "")
        linked = mr.link_doc(material_id, doc_id) if doc_id else False
        return {**plan, "action": "link", "existing_doc_id": doc_id,
                "imported": False, "linked": bool(linked),
                "why": "库内已有这部标准（既有管线的原样查重命中）⇒ 只回指"}
    if status != "ok":
        return {**plan, "imported": False, "import_status": status,
                "why": f"入库未成功（{status}）：{result.get('message') or '见引擎返回'}"}

    doc_id = str(result.get("doc_id") or "")
    linked = mr.link_doc(material_id, doc_id) if doc_id else False
    return {**plan, "imported": True, "doc_id": doc_id, "linked": bool(linked),
            "total_clauses": result.get("total_clauses"),
            "why": "已走既有 ingest 管线入库并回指"}


def reconcile(material_id: str) -> dict[str, Any]:
    """**Track L 的单一入口**：评审之后调用它，由它按决策分派。

    - `link`   → `apply_link`（只回指）；
    - `import` → `import_to_library`（走既有管线入库 + 回指）；
    - `skip` / `blocked` → **什么都不做**，原样返回决策。

    为什么要这个函数：调用方（评审后的钩子/工具）不该自己去判"这次该 link 还是 import"
    ——那是本模块的判据，分散出去早晚分叉。返回体里恒有 `imported`/`linked` 两个布尔，
    让"没做任何事"与"做了但没成功"**看得出来**。
    """
    plan = plan_import(material_id)
    if plan["action"] == "link":
        return {**apply_link(material_id), "imported": False}
    if plan["action"] == "import":
        return import_to_library(material_id)
    return {**plan, "imported": False, "linked": False}
