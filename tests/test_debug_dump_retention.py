# -*- coding: utf-8 -*-
"""`debug_dump` 的**保留策略**：外发审计的量**不许**把提问证据挤掉（2026-09-25 真缺陷回归）。

## 这一组在守什么

`debug_dump` 一张表承载两类东西：**外发审计**（`trigger_type='egress'`，量大，
实测约 110 条/天）与**提问证据**（`trigger_type='user_export'`，带 `retrieval_result`，
**不可再生**）。原先两处写入都**把整张表裁到最新 1000 行** ⇒ 谁写得多谁说话：
**审计把提问证据挤出去**（实测当时 1,000 行里只剩 8 行带检索结果、提问最多活约 9 天）。

修法是**按 `trigger_type` 各自清理**（`src/core/storage/debug_dump_retention.py`）。

## 判据（两条，互为对照）

1. **正向**：先放少量提问证据、再灌满 1000 条审计 ⇒ 提问证据**一条都不许少**。
2. **反向**（这条是防"空闸门"的）：同样数据下，用**旧的"全表裁"** SQL ⇒
   提问证据**必须被挤掉**。没有这条，测试可能只是"什么都没做也通过"。

⚠ `db` 夹具是**会话级**库（见 `tests/conftest.py`：测试数据 id 必须唯一化）⇒
本文件的 `dump_id` 一律用模块级自增序号生成，**不许写死名字**。
"""
from __future__ import annotations

import itertools

from src.core.storage.debug_dump_retention import (
    KEEP_EGRESS, KEEP_QUESTION_EVIDENCE, TYPE_EGRESS, TYPE_QUESTION, prune,
)
from src.core.storage.sqlite_db import get_db_connection

_SEQ = itertools.count()


def _new_id() -> str:
    return f"dump_{next(_SEQ):06d}"


def _insert(conn, trigger_type: str, query: str = "q") -> str:
    dump_id = _new_id()
    conn.execute(
        "INSERT INTO debug_dump (dump_id, trigger_type, query) VALUES (?,?,?)",
        (dump_id, trigger_type, query))
    conn.commit()
    return dump_id


def _fill_egress(conn, n: int) -> list[str]:
    """灌 n 条外发审计（模拟每天 ~110 条写满窗口）。**不清理**，由调用方决定怎么清。"""
    ids = [_new_id() for _ in range(n)]
    conn.executemany(
        "INSERT INTO debug_dump (dump_id, trigger_type, query) VALUES (?,?,?)",
        [(i, TYPE_EGRESS, f"cloud call {i}") for i in ids])
    conn.commit()
    return ids


def _count(conn, trigger_type: str) -> int:
    return int(conn.execute(
        "SELECT COUNT(*) FROM debug_dump WHERE trigger_type = ?",
        (trigger_type,)).fetchone()[0])


def _reset(conn) -> None:
    """清空这张表。

    ⚠ **必须**：`db` 夹具是**会话级**库，而本文件的判据是"按类型计数" ——
    不清的话上一个测试灌的行会累进来（实测出现过 `assert 2010 == 6`）。
    ⚠ 只清 `debug_dump`；别的测试不依赖它的存量。
    """
    conn.execute("DELETE FROM debug_dump")
    conn.commit()


def _prune_whole_table(conn, keep: int) -> None:
    """**旧行为**（缺陷本体），只在本测试里当"反向"对照用——生产代码里已不存在。

    它与生产实现的关键差别就在**没有 `WHERE trigger_type = ?`**（于是两类互相挤占）。
    """
    conn.execute(
        "DELETE FROM debug_dump WHERE dump_id NOT IN ("
        " SELECT dump_id FROM debug_dump ORDER BY created_at DESC, rowid DESC LIMIT ?)",
        (keep,))
    conn.commit()


def test_egress_volume_cannot_evict_question_evidence(db):
    """**正向**：灌满审计窗口之后，提问证据必须一条不少。"""
    conn = get_db_connection()
    _reset(conn)
    for i in range(3):
        _insert(conn, TYPE_QUESTION, f"真实提问 {i}")
    assert _count(conn, TYPE_QUESTION) == 3

    _fill_egress(conn, KEEP_EGRESS)          # 审计刚好写满自己的窗口
    prune(conn, TYPE_EGRESS, KEEP_EGRESS)    # 它清理自己

    assert _count(conn, TYPE_QUESTION) == 3, (
        "外发审计把提问证据挤掉了 —— 而提问证据（命中哪些标准号+条款号）**不可再生**，"
        "P1 的盈亏平衡点与 P5 的真实提问分布都要用它")


def test_the_whole_table_prune_would_evict_them(db):
    """**反向**：同一批数据喂给旧的"全表裁"，提问证据**必须**被挤掉。

    没有这一条，上面那条可能只是"什么都没做也通过"（空闸门）。
    """
    conn = get_db_connection()
    _reset(conn)
    for i in range(3):
        _insert(conn, TYPE_QUESTION, f"真实提问 {i}")
    _fill_egress(conn, KEEP_EGRESS)          # 总行数 = 1003 > 1000
    assert _count(conn, TYPE_QUESTION) == 3

    _prune_whole_table(conn, 1000)           # 旧行为：只留最新 1000 行

    assert _count(conn, TYPE_QUESTION) == 0, (
        "旧的全表清理**没有**挤掉提问证据 —— 那说明这条反向对照失效了（数据构造有问题），"
        "正向那条也就证明不了什么")


def test_pruning_one_type_leaves_the_other_alone(db):
    """按类型清理**只裁自己那一类**（这条是修复的全部要点）。"""
    conn = get_db_connection()
    _reset(conn)
    for i in range(4):
        _insert(conn, TYPE_QUESTION)
    _fill_egress(conn, 4)

    gone = prune(conn, TYPE_QUESTION, 2)

    assert gone == 2 and _count(conn, TYPE_QUESTION) == 2
    assert _count(conn, TYPE_EGRESS) == 4, "裁提问证据时动了审计记录"


def test_keep_bound_is_respected_and_returns_the_count(db):
    """`keep` 生效、且返回删掉的条数（调用方可据此观测）。"""
    conn = get_db_connection()
    _reset(conn)
    _fill_egress(conn, 10)
    assert prune(conn, TYPE_EGRESS, 4) == 6
    assert _count(conn, TYPE_EGRESS) == 4
    assert prune(conn, TYPE_EGRESS, 4) == 0, "已经裁到位了，再裁不该再删"


def test_the_newest_are_the_ones_kept(db):
    """留下的是**最新**的（同一秒内插入时靠 rowid 兜底成全序）。"""
    conn = get_db_connection()
    _reset(conn)
    ids = _fill_egress(conn, 10)
    prune(conn, TYPE_EGRESS, 3)
    kept = {r[0] for r in conn.execute(
        "SELECT dump_id FROM debug_dump WHERE trigger_type = ?", (TYPE_EGRESS,))}
    assert kept == set(ids[-3:]), kept


def test_question_evidence_outlives_the_audit_window():
    """**意图**要写进断言：提问证据的保留上限必须**大于**审计的——
    否则"提问活得比审计久"这个修复意图会在有人调小它时静默消失。"""
    assert KEEP_QUESTION_EVIDENCE > KEEP_EGRESS, (
        "提问证据的保留上限不该小于/等于审计的：它不可再生，而审计每天上百条")


# ── 调用点（2026-09-26 复核 MED-1：上面那些只测了 prune 助手，**没测接线**）────────
# 复核实测：三处**语法合法**的调用点变异（把 server 改成裁 egress、把 record_egress
# 改成裁提问、上限抄成另一个常量）**全部 0 红灯存活** —— 而"哪个写入者裁哪一类"
# 正是本批改的东西。本条把**真实调用点**钉住。
# ⚠ 不跑 1200 次真实写入：`KEEP_*` 是 `from … import` 绑进**调用点所在模块**的名字
#   ⇒ monkeypatch 它 = 改调用点用的上限，几次写入就能看出裁剪对不对。
def test_record_egress_call_site_prunes_its_own_type_with_its_own_cap(db, monkeypatch):
    """`record_egress` 必须裁 **egress**、且用**它自己的上限**。"""
    from src.core.llm import egress_audit

    monkeypatch.setattr(egress_audit, "KEEP_EGRESS", 3)     # 免跑上千次真实写入
    conn = get_db_connection()
    _reset(conn)
    _insert(conn, TYPE_QUESTION, "真实提问（不可再生）")

    for i in range(6):
        egress_audit.record_egress(service="s", endpoint="e", payload={"i": i},
                                   query=f"cloud call {i}")

    assert _count(conn, TYPE_QUESTION) == 1, (
        "调用点裁错了类型：它把**提问证据**裁了（复核 MED-1 的变异之一）")
    assert _count(conn, TYPE_EGRESS) == 3, (
        "调用点没用它自己的上限（KEEP_EGRESS）——审计会无界增长，或上限静默失效")
