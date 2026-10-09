# -*- coding: utf-8 -*-
"""第 18 轮：验证「向量通道范围下推」的修法能不能成立（只读、纯内存库，不碰真库）。

⚠⚠ **2026-10-09 就地更正：本文件的 Q1【作废】，不要引用它的读数。**
   Q1 查的是 `clause_revision_id IN (SELECT value FROM json_each(?))`，而喂进去的是**文档 id**
   （`["in_doc"]`）**不是条款 id** ⇒ 那是个**无意义的查询**，它返回 0 行**不能**当作"复现缺陷"。
   ⇒ **真正的判决性实验在 `probe-mechanism.py`**（直接 SQL 跑两种写法，扫规模 × 有向量比例）：
      失效条件是"**范围里只有一部分条款有向量**"，**与表大小无关**；
      且**真库今天不满足该条件**（0 篇"有条款却没向量"的文档）⇒ 旧写法现在工作正常。
   **Q2a / Q2b / Q2c / Q2d / Q5–Q9 不受影响**（它们喂的是 `doc_id`，是对的）。

背景（第 17 轮实测，见 tests/test_kb_scope_retrieval.py 的 docstring）：
  `clause_vec` = `vec0(clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512])`，
  范围过滤写成 `clause_revision_id IN (SELECT clause_revision_id FROM clause_revision
  WHERE doc_id IN (SELECT value FROM json_each(?)))`
  ⇒ 在"范围里只有一部分条款有向量"时返回 `[]`（见 probe-mechanism.py）。

本探针要回答的问题（决定修法）：
  Q1 现状能复现吗？
  Q2 给 vec0 加一个**元数据列** `doc_id TEXT`，用 `doc_id IN (...)` 过滤，能被下推吗？
  Q3 如果 `IN (子查询)` 不行，`IN (字面量列表)` 行不行？
  Q4 有没有别的可用形态（`rowid IN` / partition key）？

判据：范围内那条必须被返回，且**不许**有 `out_` 前缀的行混进来。
"""
from __future__ import annotations

import json
import sqlite3
import sys

import sqlite_vec

DIM = 512


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)
    return conn


def _blob(v: list[float]) -> bytes:
    return sqlite_vec.serialize_float32(v)


def _mk(conn: sqlite3.Connection, name: str, ddl: str) -> None:
    conn.execute(f"DROP TABLE IF EXISTS {name}")
    conn.execute(ddl)


def _report(tag: str, rows) -> list[str]:
    ids = [r[0] for r in rows]
    bad = [i for i in ids if i.startswith("out_")]
    ok = "✅ 下推成功" if (ids and not bad and "in_weak" in ids) else (
        "❌ 返回空" if not ids else "❌ 混进范围外" if bad else "⚠ 结果异常")
    print(f"    {tag:<46} → {len(ids):>3} 行 {str(ids[:4]):<34} {ok}")
    return ids


def main() -> int:
    print("=" * 100)
    print("sqlite-vec 版本:", getattr(sqlite_vec, "__version__", "?"))
    conn = _conn()
    print("SQLite 版本 :", sqlite3.sqlite_version)
    print("=" * 100)

    QVEC = [1.0] + [0.0] * (DIM - 1)          # 查询向量
    FAR = [0.0] * (DIM - 1) + [1.0]           # 范围内那条：与查询最远
    in_docs = ["in_doc"]                       # 范围：1 篇文档
    scope_json = json.dumps(in_docs)

    # ── 公共数据：范围内 5 条（只有 in_weak 有向量）+ 范围外 25 条近邻 ──────────────
    def seed(conn, table, with_doc: bool):
        cols = "(clause_revision_id, doc_id, embedding)" if with_doc else \
               "(clause_revision_id, embedding)"
        ph = "(?,?,?)" if with_doc else "(?,?)"
        def ins(cid, doc, v):
            args = (cid, doc, _blob(v)) if with_doc else (cid, _blob(v))
            conn.execute(f"INSERT INTO {table} {cols} VALUES {ph}", args)
        ins("in_weak", "in_doc", FAR)          # 范围内、唯一有向量的那条
        for i in range(25):                     # 范围外批量近邻（与查询向量完全一致）
            ins(f"out_bulk{i}", "out_doc", QVEC)
        ins("out_hot1", "out_doc", QVEC)
        ins("out_hot2", "out_doc", [0.9, 0.1] + [0.0] * (DIM - 2))
        conn.commit()

    print()
    print("【Q1】现状复现：vec0(clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512])")
    _mk(conn, "v1", f"CREATE VIRTUAL TABLE v1 USING vec0("
                    f"clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[{DIM}])")
    seed(conn, "v1", with_doc=False)
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v1"
        " WHERE embedding MATCH ? AND k = 20"
        " AND clause_revision_id IN (SELECT value FROM json_each(?))"
        " ORDER BY distance", (_blob(QVEC), scope_json)).fetchall()
    _report("clause_revision_id IN (SELECT … json_each)", rows)

    print()
    print("【Q2】修法候选：vec0(clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[512])")
    _mk(conn, "v2", f"CREATE VIRTUAL TABLE v2 USING vec0("
                    f"clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[{DIM}])")
    seed(conn, "v2", with_doc=True)

    print("  Q2a doc_id IN (SELECT value FROM json_each(?))")
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v2"
        " WHERE doc_id IN (SELECT value FROM json_each(?))"
        " AND embedding MATCH ? AND k = 20 ORDER BY distance",
        (scope_json, _blob(QVEC))).fetchall()
    _report("doc_id IN (SELECT … json_each)", rows)

    print("  Q2b doc_id IN (?, ?) 字面量列表（2 个 doc）")
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v2"
        " WHERE doc_id IN (?, ?) AND embedding MATCH ? AND k = 20 ORDER BY distance",
        ("in_doc", "out_doc", _blob(QVEC))).fetchall()
    _report("doc_id IN (?, ?)  [in_doc, out_doc]", rows)

    print("  Q2c doc_id = ? 单值")
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v2"
        " WHERE doc_id = ? AND embedding MATCH ? AND k = 20 ORDER BY distance",
        ("in_doc", _blob(QVEC))).fetchall()
    _report("doc_id = ?  [in_doc]", rows)

    print("  Q2d 多个 doc_id 用 OR 连接（2 个 doc）")
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v2"
        " WHERE (doc_id = ? OR doc_id = ?) AND embedding MATCH ? AND k = 20 ORDER BY distance",
        ("in_doc", "out_doc", _blob(QVEC))).fetchall()
    _report("(doc_id = ? OR doc_id = ?)", rows)

    print()
    print("【Q3】rowid 路线：vec0 的 rowid 能不能被下推")
    rows = conn.execute(
        "SELECT clause_revision_id, distance FROM v2"
        " WHERE rowid IN (SELECT rowid FROM v2 WHERE doc_id = 'in_doc')"
        " AND embedding MATCH ? AND k = 20 ORDER BY distance",
        (_blob(QVEC),)).fetchall()
    _report("rowid IN (SELECT rowid … doc_id='in_doc')", rows)

    print()
    print("【Q4】partition key 路线：vec0(..., partition key doc_id, ...)")
    try:
        _mk(conn, "v3", f"CREATE VIRTUAL TABLE v3 USING vec0("
                        f"doc_id TEXT partition key, clause_revision_id TEXT PRIMARY KEY,"
                        f" embedding FLOAT[{DIM}])")
        seed(conn, "v3", with_doc=True)
        rows = conn.execute(
            "SELECT clause_revision_id, distance FROM v3"
            " WHERE doc_id IN (?, ?) AND embedding MATCH ? AND k = 20 ORDER BY distance",
            ("in_doc", "out_doc", _blob(QVEC))).fetchall()
        _report("partition key doc_id IN (?, ?)", rows)
    except Exception as e:  # noqa: BLE001
        print("    partition key 建表/查询失败:", type(e).__name__, str(e)[:120])

    print()
    print("=" * 100)
    print("结论要读：只有 Q2a/Q2b 里「范围内那条被返回、且无 out_ 混入」的形态，才能当修法。")
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
