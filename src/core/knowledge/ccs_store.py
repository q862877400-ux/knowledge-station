"""CCS（中国标准分类号）查询台账的读写层（2026-09-22「补全分类号」）。

════════ 它管什么、不管什么 ════════

* **管**：每一次分类号查询的**结论与出处** —— 是哪一层命中的、前几层为什么没命中、
  命中的是哪种关键词形式、站点返回的标准号是什么、失败是哪一类（网络/查无/读不出）。
  表形状见 ``schema.sql`` 的 ``doc_ccs_state``（那里写了"为什么不塞进
  ``doc_filing_state``、也不写 ``doc_meta.ccs_code``"）。
* **不管**：**CCS 标签本身**。标签的唯一所有者是 ``doc_meta.domain_tags`` 里的
  ``CCS:…`` 条目（分类树 ``doc_catalog`` 读的就是它）—— 本模块**只**通过
  :func:`apply_ccs_tag` 往那里写那**一条**（没有就追加、有了就替换），绝不另存一份
  "权威分类号"。

════════ 三条纪律 ════════

1. **一篇只保留一条 ``CCS:`` 标签 + 幂等**（⚠ 2026-09-24 就地更正，留痕）：
   原文写的是「写标签是**追加** + 幂等……本模块只可能**多**一条 ``CCS:…``」。
   "幂等"那半句对（同一个号重复补不写第二条），**"追加"那半句是错的**：
   ``force=True``（刷新）会给同一篇**追加第二条** ``CCS:`` 标签，而读侧
   （``ccs_tag_of`` / ``doc_catalog``）只取**第一条** ⇒ 刷新**静默无效**、
   台账（``doc_ccs_state.ccs_code``）与分类树各说各话（复核 HIGH-1）。
   现在：没有 CCS 标签就追加，**有了就就地替换**（新号与旧号相同则一个字不改），
   历史遗留的多条也顺手收成一条。
2. **绝不改写别的标签**：``domain_tags`` 里已有的 消防/通用/… 全部原样保留、
   **位置也不动**；本模块只可能多第一条 ``CCS:…`` 或换掉那一条。
3. **只在补到的时候才写标签**：``outcome != 'found'`` 一律不动 ``domain_tags``
   （那正是"待分类里那些没有建议的"为什么会没有建议 —— 原因记在本表里，不靠猜）。
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.core.exceptions import KnowledgeStationError
from src.core.storage.sqlite_db import get_db_connection, write_transaction

#: 本表列名（防拼错列名静默写空；与 schema.sql 一字不差）
_COLUMNS: tuple[str, ...] = (
    "doc_id", "outcome", "source", "keyword_form", "matched_no", "ccs_code",
    "ccs_name", "reason", "attempts_json", "checked_at", "applied_at",
)

#: 台账里"还没补到"的四种结论（界面「待分类」用它讲"为什么没有建议"）
UNRESOLVED_OUTCOMES: tuple[str, ...] = ("not_found", "network_failed", "parse_failed",
                                        "not_applicable")


def _err(msg: str, code: str) -> KnowledgeStationError:
    return KnowledgeStationError(msg, code=code)


def ccs_tag_of(domain_tags: Any) -> str | None:
    """``domain_tags``（JSON 串或 list）里已有的 ``CCS:…`` 条目；没有返回 None。"""
    tags = _as_list(domain_tags)
    for t in tags:
        if isinstance(t, str) and t.startswith("CCS:"):
            return t
    return None


def _as_list(domain_tags: Any) -> list[Any]:
    """``domain_tags`` 统一成 list（库里是 JSON 字符串；已是 list 就用它）。"""
    if isinstance(domain_tags, list):
        return list(domain_tags)
    if not domain_tags:
        return []
    try:
        got = json.loads(domain_tags)
    except (TypeError, ValueError):
        return []
    return got if isinstance(got, list) else []


def record_ccs_lookup(doc_id: str, result: dict,
                      db_path: Any = None) -> dict:
    """把一次查询的结论写进台账（幂等 upsert）。**不改** ``doc_meta``、**不改**标签。

    ``result`` = :func:`src.core.knowledge.ccs_fetcher.resolve_ccs` 的返回（命中或未命中
    都行 —— 未命中的 ``outcome`` / ``reason`` / ``attempts`` 正是要留痕的东西）。
    """
    outcome = str(result.get("outcome") or "")
    if outcome not in ("found", "not_found", "network_failed", "parse_failed",
                       "not_applicable"):
        raise _err(f"不认识的 outcome: {outcome!r}", "invalid_ccs_outcome")
    attempts = result.get("attempts") or []
    with write_transaction(db_path) as conn:
        if conn.execute("SELECT 1 FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone() is None:
            raise _err(f"文档不存在: {doc_id}", "doc_not_found")
        conn.execute(
            "INSERT INTO doc_ccs_state(doc_id, outcome, source, keyword_form, matched_no,"
            " ccs_code, ccs_name, reason, attempts_json, checked_at)"
            " VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))"
            " ON CONFLICT(doc_id) DO UPDATE SET"
            "   outcome=excluded.outcome, source=excluded.source,"
            "   keyword_form=excluded.keyword_form, matched_no=excluded.matched_no,"
            "   ccs_code=excluded.ccs_code, ccs_name=excluded.ccs_name,"
            "   reason=excluded.reason, attempts_json=excluded.attempts_json,"
            "   checked_at=excluded.checked_at",
            (doc_id, outcome, result.get("source"), result.get("keyword_form"),
             result.get("matched_no"), result.get("code"), result.get("sub"),
             str(result.get("reason") or "")[:500],
             json.dumps(attempts, ensure_ascii=False)[:20000]))
        row = conn.execute("SELECT * FROM doc_ccs_state WHERE doc_id=?",
                           (doc_id,)).fetchone()
        return dict(row)


def apply_ccs_tag(doc_id: str, tag: str, result: dict | None = None,
                  db_path: Any = None) -> dict:
    """把 ``CCS:…`` 标签写进 ``doc_meta.domain_tags`` 并记台账（**一个事务**）。

    ⚠⚠ **一篇只能有一条 ``CCS:`` 标签 —— "刷新"是替换，不是追加**（复核 HIGH-1，
    2026-09-24 就地更正）：读侧的 ``ccs_tag_of`` / ``doc_catalog`` 取的都是
    **第一条**，所以旧实现那种"append 第二条"会让 ``force=True`` 的刷新**静默无效**
    （读的还是旧码），台账（``doc_ccs_state.ccs_code``）与分类树各说各话。

    规则（按库里的现状算，不靠调用方声明）：

    * 还没有 CCS 标签 ⇒ **追加**（别的位置的标签一个不动）；
    * 已有 CCS 标签、且与新标签**不同** ⇒ **就地替换**（``replaced`` 如实给旧值）；
    * 已有 CCS 标签、与新标签**相同** ⇒ 一个字都不改（幂等，``applied=False``）；
    * 历史遗留的**多余** CCS 条目 ⇒ 顺手收成一条（修既有错数据，不是新写一条）。

    返回 ``{"applied", "tag", "replaced", "tags", "state"}`` —— ``applied`` 的含义是
    "``domain_tags`` 真的变了"；``replaced`` 是换掉的那条旧标签（没换就是 None）。
    """
    text = str(tag or "").strip()
    if not text.startswith("CCS:"):
        raise _err(f"不是 CCS 标签: {tag!r}（必须形如 CCS:P16 工程防火）",
                   "invalid_ccs_tag")
    with write_transaction(db_path) as conn:
        row = conn.execute("SELECT domain_tags FROM doc_meta WHERE doc_id=?",
                           (doc_id,)).fetchone()
        if row is None:
            raise _err(f"文档不存在: {doc_id}", "doc_not_found")
        tags = _as_list(row["domain_tags"])
        replaced: str | None = None
        positions = [i for i, t in enumerate(tags)
                     if isinstance(t, str) and t.startswith("CCS:")]
        if not positions:
            tags = tags + [text]
            applied = True
        else:
            first = positions[0]
            replaced = tags[first]
            # 就地换掉第一条 + 收掉历史遗留的多余条目（`first` 之前的索引不变，
            # 因为被删的都是它之后的）
            new_tags = [t for i, t in enumerate(tags) if i not in positions[1:]]
            new_tags[first] = text
            applied = (new_tags != tags)
            tags = new_tags
        if applied:
            conn.execute(
                "UPDATE doc_meta SET domain_tags=?, updated_at=datetime('now')"
                " WHERE doc_id=?",
                (json.dumps(tags, ensure_ascii=False), doc_id))
        if result is not None:
            conn.execute(
                "INSERT INTO doc_ccs_state(doc_id, outcome, source, keyword_form,"
                " matched_no, ccs_code, ccs_name, reason, attempts_json, checked_at,"
                " applied_at) VALUES (?,?,?,?,?,?,?,?,?, datetime('now'), datetime('now'))"
                " ON CONFLICT(doc_id) DO UPDATE SET"
                "   outcome=excluded.outcome, source=excluded.source,"
                "   keyword_form=excluded.keyword_form, matched_no=excluded.matched_no,"
                "   ccs_code=excluded.ccs_code, ccs_name=excluded.ccs_name,"
                "   reason=excluded.reason, attempts_json=excluded.attempts_json,"
                "   checked_at=excluded.checked_at,"
                "   applied_at=COALESCE(doc_ccs_state.applied_at, excluded.applied_at)",
                (doc_id, str(result.get("outcome") or "found"), result.get("source"),
                 result.get("keyword_form"), result.get("matched_no"),
                 result.get("code"), result.get("sub"),
                 str(result.get("reason") or "")[:500],
                 json.dumps(result.get("attempts") or [], ensure_ascii=False)[:20000]))
        else:
            conn.execute(
                "INSERT INTO doc_ccs_state(doc_id, outcome, checked_at, applied_at)"
                " VALUES (?, 'found', datetime('now'), datetime('now'))"
                " ON CONFLICT(doc_id) DO UPDATE SET"
                "   outcome='found', checked_at=datetime('now'),"
                "   applied_at=COALESCE(doc_ccs_state.applied_at, datetime('now'))",
                (doc_id,))
        state = conn.execute("SELECT * FROM doc_ccs_state WHERE doc_id=?",
                             (doc_id,)).fetchone()
    return {"applied": applied, "tag": text, "replaced": replaced, "tags": tags,
            "state": dict(state) if state is not None else None}


def get_ccs_state(doc_id: str, db_path: Any = None) -> dict | None:
    """某一篇的分类号查询台账（没有这一行 ⇒ None，表示**还没查过**）。"""
    conn = get_db_connection(db_path)
    row = conn.execute("SELECT * FROM doc_ccs_state WHERE doc_id=?", (doc_id,)).fetchone()
    return dict(row) if row is not None else None


def ccs_states_for(doc_ids: list[str], db_path: Any = None) -> dict[str, dict]:
    """批量取台账（`GET /kb/inbox` 一次要几十篇，别一篇一条 SQL）。"""
    ids = [str(d) for d in doc_ids if str(d).strip()]
    if not ids:
        return {}
    conn = get_db_connection(db_path)
    ph = ",".join("?" * len(ids))
    return {r["doc_id"]: dict(r) for r in conn.execute(
        f"SELECT * FROM doc_ccs_state WHERE doc_id IN ({ph})", ids)}


def counts_by_outcome(db_path: Any = None) -> dict[str, int]:
    """台账按结论计数（界面「补全分类号」的结果概览用）。"""
    conn = get_db_connection(db_path)
    out = {k: 0 for k in ("found", "not_found", "network_failed", "parse_failed",
                          "not_applicable")}
    for r in conn.execute("SELECT outcome, COUNT(*) AS n FROM doc_ccs_state"
                          " GROUP BY outcome"):
        out[str(r["outcome"])] = int(r["n"])
    return out


def state_columns() -> tuple[str, ...]:
    """本表列名（给测试与审计对形状用；**唯一所有者**在 schema.sql）。"""
    return _COLUMNS


def table_exists(conn: sqlite3.Connection) -> bool:
    """表在不在（老库没跑过 ``init_schema`` 时给调用方一个判据，不靠猜）。"""
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='doc_ccs_state'"
    ).fetchone() is not None
