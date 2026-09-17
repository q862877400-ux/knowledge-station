# -*- coding: utf-8 -*-
"""材料平面仓库（2026-09-17 定位转移 Phase A）：项目 / 材料 / 切片 的读写。

## 与法条链的关系（**零耦合**，别越界）
本模块只碰 `material_project` / `material` / `material_chunk` 三张**新表**；
**不读写** `doc_meta` / `clause_revision` / `source_span` / `clause_patch`。
Track L（采到库内没有的法规标准）评审通过后仍走既有 ingest 管线入 `doc_meta`，
再由 `material.doc_id` **从材料侧回指**——法条链一个字段都不改。

为什么另立平面：`doc_meta.standard_no TEXT NOT NULL UNIQUE` **结构上装不下**财报/新闻。

## 权威性是两个正交轴（业主 2026-09-17 裁定的"公司制度"例）
- **轴 A 来源可信度** `source_tier`（T0~T4）：这份材料本身可不可信 → 决定**怎么标注、能否承重**；
- **轴 B 任务内效力** `task_role`（criterion/reference）：**本次任务以什么为准绳** → 决定**谁说话**。
制度来源层级低于国标，但对"我们公司报销怎么走"它才是准绳 —— 单轴排序必然错一个，
故这里**不提供**任何"按一个分数排序材料"的函数。

## 评审是**硬门**，不是提示——但要说准"硬"到什么程度
检索/分析必须走 `approved_materials()` / `search_materials()`：前者的 SQL 只返回
`review_status='approved'`，后者把该条件**写死在 JOIN 里**（所以批准/撤销**立即**生效，
不给调用方"记得过滤"的机会）。

⚠ **精确边界（2026-09-17 verifier 复核后改正，原先的 docstring 说过头了）**：
1. 硬门是**函数内**保证，**不是数据库强制**——没有 view、没有 trigger。**任何手写 SQL
   或直接查 `material_fts` 都能绕过它**（`schema.sql` 里也写了这条警告）。
2. 本模块**故意**另有三处**不设门**的读函数，**只准评审流程用**（评审人必须先读到正文
   才能判断，盲签等于没评审）：
   `material_chunks()`（第 330 行）、`list_materials()`、`get_material()`。
   ⇒ **任何要产出结论/答案的路径都不得使用它们**；用了就是绕过评审，且**不会有任何报错**。
   今天生产代码里还没有这样的消费方——Phase B 接答案链时，这是最容易悄悄出错的接缝。
3. 因此"唯一入口"指的是**给分析用的那对函数**，不是"本模块所有函数都设了门"。
"""
from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from ulid import ULID

from src.core.config import get_settings
from src.core.storage.sqlite_db import get_db_connection, write_transaction

logger = logging.getLogger(__name__)

#: 轴 A 的层（顺序即"来源可信度"由高到低；**不等于**任务内效力）
TIERS = ("T0", "T1", "T2", "T3", "T4")
#: 层含义（给 UI / 文档复用，避免多处各写一份措辞）
TIER_LABELS: dict[str, str] = {
    "T0": "法定/官方原文",
    "T1": "用户自有原始件",
    "T2": "权威第三方（监管/交易所/审计/标准发布机构/署名研究机构）",
    "T3": "二手转述（媒体/自媒体）——只能当线索，需≥2 个独立来源互证",
    "T4": "不可回溯（无出处/匿名/内容农场）——禁止用于结论",
}


def materials_root() -> Path:
    """材料原件存放根：`<data_dir>/materials/<project_id>/`。

    遵守 §13.0「代码树零运行产物」——运行产物一律写数据区（`data_dir`），不进仓库树。
    """
    return get_settings().data_dir / "materials"


def materials_dir(project_id: str) -> Path:
    """某个项目的参考资料文件夹（**独立目录**：材料与法规语料分开放，便于各自备份/清理）。"""
    d = materials_root() / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------- 项目
def create_project(name: str, *, authority_policy: dict[str, Any] | None = None,
                   note: str | None = None,
                   project_id: str | None = None) -> dict[str, Any]:
    """建项目。`authority_policy` 是**轴 B** 的项目级声明（JSON 序列化后存）。"""
    pid = project_id or f"prj_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO material_project(project_id, name, authority_policy, note) "
            "VALUES (?,?,?,?)",
            (pid, name,
             json.dumps(authority_policy, ensure_ascii=False) if authority_policy else None,
             note))
    return get_project(pid) or {}


def get_project(project_id: str) -> dict[str, Any] | None:
    conn = get_db_connection()
    r = conn.execute(
        "SELECT project_id, name, authority_policy, note, created_at, updated_at "
        "FROM material_project WHERE project_id=?", (project_id,)).fetchone()
    return _project_row(r) if r else None


def list_projects() -> list[dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT project_id, name, authority_policy, note, created_at, updated_at "
        "FROM material_project ORDER BY created_at DESC").fetchall()
    return [_project_row(r) for r in rows]


def _project_row(r) -> dict[str, Any]:
    return {"project_id": r[0], "name": r[1],
            "authority_policy": json.loads(r[2]) if r[2] else None,
            "note": r[3], "created_at": r[4], "updated_at": r[5]}


# --------------------------------------------------------------------- 材料
def add_material(project_id: str, title: str, *, origin: str = "user",
                 kind: str = "other", source_tier: str | None = None,
                 tier_evidence: dict[str, Any] | None = None,
                 tier_reason: str | None = None,
                 url: str | None = None, domain: str | None = None,
                 content_hash: str | None = None, raw_path: str | None = None,
                 mime: str | None = None, page: int | None = None,
                 published_at: str | None = None,
                 material_id: str | None = None) -> dict[str, Any]:
    """登记一份材料。**默认 `review_status='pending'`** —— 未经评审不得使用（硬门）。

    层级默认：用户自有原件 T1；自采（collected）由调用方按判据给（不给则 T3 起，
    因为"网上找来的"在没证据前不该默认可信）。**默认不可信、靠证据升级。**
    """
    if origin not in ("user", "collected"):
        raise ValueError(f"origin 只能是 user/collected，收到 {origin!r}")
    if kind not in ("legal", "other"):
        raise ValueError(f"kind 只能是 legal/other，收到 {kind!r}")
    tier = source_tier or ("T1" if origin == "user" else "T3")
    if tier not in TIERS:
        raise ValueError(f"source_tier 只能是 {TIERS}，收到 {tier!r}")
    mid = material_id or f"mat_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO material(material_id, project_id, origin, kind, title, url, domain,"
            " content_hash, raw_path, mime, source_tier, tier_evidence, tier_reason,"
            " published_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (mid, project_id, origin, kind, title, url, domain, content_hash, raw_path,
             mime, tier, json.dumps(tier_evidence, ensure_ascii=False) if tier_evidence else None,
             tier_reason, published_at))
    return get_material(mid) or {}


def get_material(material_id: str) -> dict[str, Any] | None:
    conn = get_db_connection()
    r = conn.execute(f"SELECT {_MAT_COLS} FROM material WHERE material_id=?",
                     (material_id,)).fetchone()
    return _material_row(r) if r else None


_MAT_COLS = ("material_id, project_id, origin, kind, title, url, domain, fetched_at,"
             " published_at, content_hash, raw_path, mime, source_tier, tier_source,"
             " tier_reason, tier_evidence, task_role, review_status, review_note,"
             " reviewed_at, lifecycle, doc_id, created_at, updated_at")


def _material_row(r) -> dict[str, Any]:
    d = dict(zip(
        ("material_id", "project_id", "origin", "kind", "title", "url", "domain",
         "fetched_at", "published_at", "content_hash", "raw_path", "mime",
         "source_tier", "tier_source", "tier_reason", "tier_evidence", "task_role",
         "review_status", "review_note", "reviewed_at", "lifecycle", "doc_id",
         "created_at", "updated_at"), r))
    d["tier_evidence"] = json.loads(d["tier_evidence"]) if d["tier_evidence"] else None
    return d


def list_materials(project_id: str, *, review_status: str | None = None) -> list[dict[str, Any]]:
    """列材料（**管理/评审界面用**，可以含未批准的）。

    ⚠ 要"给分析用的材料"请用 `approved_materials()`——那是硬门。本函数**不设门**，
    因为它还要服务评审列表本身（用户得先看见 pending 才能批准）。
    """
    conn = get_db_connection()
    sql = f"SELECT {_MAT_COLS} FROM material WHERE project_id=?"
    args: list[Any] = [project_id]
    if review_status is not None:
        sql += " AND review_status=?"
        args.append(review_status)
    sql += " ORDER BY created_at DESC"
    return [_material_row(r) for r in conn.execute(sql, args).fetchall()]


def approved_materials(project_id: str) -> list[dict[str, Any]]:
    """**硬门**：只有已批准的材料才允许进入检索/分析/引用。

    这是 Phase A 验收里"未批准材料不得进入分析"的唯一实现点——凡是要拿材料去
    「用」的代码路径都必须经这里，不要自己拼条件（分散判据早晚会分叉）。
    """
    return list_materials(project_id, review_status="approved")


# --------------------------------------------------------------- 评审 / 层级
def set_review(material_id: str, status: str, *, note: str | None = None) -> bool:
    """批准 / 拒绝（用户评审闸门）。`status` ∈ pending|approved|rejected。"""
    if status not in ("pending", "approved", "rejected"):
        raise ValueError(f"review_status 只能是 pending/approved/rejected，收到 {status!r}")
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE material SET review_status=?, review_note=?, reviewed_at=datetime('now'),"
            " updated_at=datetime('now') WHERE material_id=?",
            (status, note, material_id))
    return cur.rowcount > 0


def set_tier(material_id: str, tier: str, *, source: str = "user",
             reason: str | None = None) -> bool:
    """改**来源可信度**（用户可改，留痕）。

    `source='user'` 表示人为裁定——记下来是为了**日后还能看懂当时的判断**，
    不是限制。层级一改，引用时的标注随之变（因为标注读的就是这个字段）。
    """
    if tier not in TIERS:
        raise ValueError(f"source_tier 只能是 {TIERS}，收到 {tier!r}")
    if source not in ("system", "user"):
        raise ValueError(f"tier_source 只能是 system/user，收到 {source!r}")
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE material SET source_tier=?, tier_source=?, tier_reason=?,"
            " updated_at=datetime('now') WHERE material_id=?",
            (tier, source, reason, material_id))
    return cur.rowcount > 0


def set_task_role(material_id: str, role: str | None) -> bool:
    """声明**任务内效力**（轴 B）：`criterion`=本任务准则 / `reference`=参考 / None=未声明。"""
    if role not in ("criterion", "reference", None):
        raise ValueError(f"task_role 只能是 criterion/reference/None，收到 {role!r}")
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE material SET task_role=?, updated_at=datetime('now') WHERE material_id=?",
            (role, material_id))
    return cur.rowcount > 0


def set_lifecycle(material_id: str, lifecycle: str) -> bool:
    """`ephemeral`（默认，仅本次任务）↔ `promoted`（用户提名升为长期参考）。"""
    if lifecycle not in ("ephemeral", "promoted"):
        raise ValueError(f"lifecycle 只能是 ephemeral/promoted，收到 {lifecycle!r}")
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE material SET lifecycle=?, updated_at=datetime('now') WHERE material_id=?",
            (lifecycle, material_id))
    return cur.rowcount > 0


def link_doc(material_id: str, doc_id: str) -> bool:
    """Track L：评审通过并**入法规库**后，从材料侧回指 `doc_meta.doc_id`（法条链零改动）。"""
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE material SET doc_id=?, updated_at=datetime('now') WHERE material_id=?",
            (doc_id, material_id))
    return cur.rowcount > 0


# --------------------------------------------------------------------- 切片
def add_chunks(material_id: str, chunks: list[dict[str, Any]]) -> int:
    """写入切片（并同步 `material_fts`）。每片须含 `text` / `char_start` / `char_end`（可选 `page`）。

    字符区间是**引用可点回原文位置**的基础（与法条链 source_span 同精神）：
    没有区间就没法把结论指回材料的哪个位置，那就不算"按我们的流程引用"。
    """
    from src.core.text_utils import segment_for_fts
    mat = get_material(material_id)
    rows = []
    fts_rows = []
    for i, c in enumerate(chunks):
        text = str(c.get("text") or "")
        # 空白片（含只有空格的）一律不入库：它们没有内容，进了检索只会稀释结果。
        # 注意判据是 strip()——`"  "` 是真值，只用 `not text` 会漏掉（已被测试抓住）。
        if not text.strip():
            continue
        cs = int(c.get("char_start", 0))
        ce = int(c.get("char_end", cs + len(text)))
        cid = f"mch_{ULID()}"
        rows.append((cid, material_id, int(c.get("ord", i)), text, cs, ce, c.get("page")))
        fts_rows.append((cid, material_id, (mat or {}).get("title") or "",
                         segment_for_fts(text)))
    if not rows:
        return 0
    with write_transaction() as conn:
        conn.executemany(
            "INSERT INTO material_chunk(chunk_id, material_id, ord, text, char_start,"
            " char_end, page) VALUES (?,?,?,?,?,?,?)", rows)
        conn.executemany(
            "INSERT INTO material_fts(chunk_id, material_id, title, content_segmented)"
            " VALUES (?,?,?,?)", fts_rows)
    return len(rows)


def search_materials(project_id: str, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """在**已批准**材料里做全文检索，返回带**引用所需字段**的命中。

    **评审硬门写死在 SQL 里**：`JOIN material ... AND review_status='approved'`。
    这样即使调用方忘了过滤，也**拿不到未批准的材料**——硬门不能靠"调用方记得"。

    返回每项含：切片文本与字符区间、页号、材料标题/来源/层级（轴 A）/任务效力（轴 B）。
    这些字段就是产出物里那条引用要显示与"点回原文"的全部依据（可见性硬需求）。
    """
    from src.core.text_utils import segment_for_fts
    if not isinstance(query, str):
        # 显式拒绝而不是让 jieba 深处抛 AttributeError（verifier 2026-09-17 报的：
        # 非 str 会从 segment_for_fts 内部冒 AttributeError，契约很差）。
        raise TypeError(f"query 必须是 str（收到 {type(query).__name__}）")
    # ⚠ `limit` 的归一**必须在 try 之外**：原先 `int(limit)` 在 try 内，于是
    # `limit=None` 的 TypeError 被兜底 except 吃掉、静默返回 [] —— 与本次战役修掉的
    # `allow_deep="false"` 同一类 bug：**坏参数静默变成"什么都没找到"**。
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError(f"limit 必须是 int（收到 {type(limit).__name__}）")
    q = segment_for_fts(query)
    if not q.strip():
        return []
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT c.chunk_id, c.material_id, c.text, c.char_start, c.char_end, c.page,"
            "       m.title, m.url, m.domain, m.source_tier, m.tier_source, m.task_role,"
            "       m.origin, m.kind, m.doc_id,"
            "       bm25(material_fts) AS score"
            " FROM material_fts"
            " JOIN material_chunk c ON c.chunk_id = material_fts.chunk_id"
            " JOIN material m ON m.material_id = c.material_id"
            " WHERE material_fts MATCH ? AND m.project_id = ? AND m.review_status = 'approved'"
            " ORDER BY score LIMIT ?", (q, project_id, limit)).fetchall()
    except sqlite3.OperationalError as e:
        # 与法条侧同款（`hybrid_engine` 的 FTS 通道：`except sqlite3.OperationalError`
        # + warning）：畸形 MATCH 不该把提问打崩，但**必须留痕**——兜住 `Exception`
        # 会把"表没了 / SQL 写错了"伪装成"材料里没有命中"，那是最坏的一种失真。
        logger.warning("材料 FTS 查询失败: %s", e)
        return []
    return [{"chunk_id": r[0], "material_id": r[1], "text": r[2],
             "char_start": r[3], "char_end": r[4], "page": r[5],
             "title": r[6], "url": r[7], "domain": r[8],
             "source_tier": r[9], "tier_source": r[10], "task_role": r[11],
             "origin": r[12], "kind": r[13], "doc_id": r[14],
             "score": r[15],
             # 引用标注（把两个轴**同时**摆出来，别让读者以为只有一个"可信度"）
             "tier_label": TIER_LABELS.get(r[9], r[9]),
             "role_label": ("本任务准则" if r[11] == "criterion"
                            else "参考" if r[11] == "reference" else "未声明效力")}
            for r in rows]


def delete_material(material_id: str) -> bool:
    """删除材料（连同切片与检索索引）。**只动材料平面**，不碰法条链。"""
    with write_transaction() as conn:
        conn.execute("DELETE FROM material_fts WHERE material_id=?", (material_id,))
        conn.execute("DELETE FROM material_chunk WHERE material_id=?", (material_id,))
        cur = conn.execute("DELETE FROM material WHERE material_id=?", (material_id,))
    return cur.rowcount > 0


def material_chunks(material_id: str) -> list[dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT chunk_id, material_id, ord, text, char_start, char_end, page "
        "FROM material_chunk WHERE material_id=? ORDER BY ord", (material_id,)).fetchall()
    return [dict(zip(("chunk_id", "material_id", "ord", "text", "char_start",
                      "char_end", "page"), r)) for r in rows]


def chunk_count(material_id: str) -> int:
    conn = get_db_connection()
    return int(conn.execute("SELECT COUNT(*) FROM material_chunk WHERE material_id=?",
                            (material_id,)).fetchone()[0])
