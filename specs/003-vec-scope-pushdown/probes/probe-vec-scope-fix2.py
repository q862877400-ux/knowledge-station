# -*- coding: utf-8 -*-
"""第 18 轮 · 续：把修法的**边界**验干净（纯内存库，不碰真库）。

probe-vec-scope-fix.py 已确定：给 vec0 加元数据列 `doc_id TEXT`，
用 `doc_id IN (SELECT value FROM json_each(?))` 能被下推；字面量列表 / OR 不行。

本探针回答**能不能真上线**的四个问题：
  Q5 范围里有 100 篇文档时，还能下推吗？
  Q6 不加范围时（历史路径）行为一字不变吗？（不许有回归）
  Q7 从旧表**纯 SQL 拷贝**到新表（不重算向量），逐字节相同吗？
  Q8 范围指向的文档**没有向量**时，返回空还是报错？
  Q9 元数据列会不会拖慢"不带范围"的 KNN？
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time

import sqlite_vec

DIM = 512
DDL_OLD = f"CREATE VIRTUAL TABLE {{t}} USING vec0(clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[{DIM}])"
DDL_NEW = (f"CREATE VIRTUAL TABLE {{t}} USING vec0(clause_revision_id TEXT PRIMARY KEY,"
           f" doc_id TEXT, embedding FLOAT[{DIM}])")


def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.enable_load_extension(True)
    sqlite_vec.load(c)
    c.enable_load_extension(False)
    return c


def _blob(v):
    return sqlite_vec.serialize_float32(v)


def main() -> int:
    conn = _conn()
    Q = [1.0] + [0.0] * (DIM - 1)
    FAR = [0.0] * (DIM - 1) + [1.0]

    print("=" * 100)
    print("【Q5】范围 = 100 篇文档，其中只有 1 篇有向量（in_weak，且是全局最远）")
    conn.execute(DDL_NEW.format(t="v"))
    conn.execute("INSERT INTO v(clause_revision_id, doc_id, embedding) VALUES (?,?,?)",
                 ("in_weak", "doc000", _blob(FAR)))
    for i in range(25):   # 范围外近邻
        conn.execute("INSERT INTO v(clause_revision_id, doc_id, embedding) VALUES (?,?,?)",
                     (f"out_bulk{i}", "out_doc", _blob(Q)))
    conn.commit()
    docs = [f"doc{i:03d}" for i in range(100)]      # doc000 在范围内
    rows = conn.execute(
        "SELECT clause_revision_id FROM v WHERE doc_id IN (SELECT value FROM json_each(?))"
        " AND embedding MATCH ? AND k = 20 ORDER BY distance",
        (json.dumps(docs), _blob(Q))).fetchall()
    ids = [r[0] for r in rows]
    print(f"    → {len(ids)} 行 {ids[:4]}  {'✅ 下推成功' if ids == ['in_weak'] else '❌ 有问题'}")

    print()
    print("【Q6】不加范围时（历史路径）与旧表逐条对照")
    conn.execute("DROP TABLE IF EXISTS v")
    conn.execute(DDL_NEW.format(t="v"))          # 清掉 Q5 的 25 条近邻，两边数据才可比
    conn.execute(DDL_OLD.format(t="o"))
    for i in range(30):
        conn.execute("INSERT INTO o(clause_revision_id, embedding) VALUES (?,?)",
                     (f"c{i:02d}", _blob([1.0 - i * 0.01] + [0.0] * (DIM - 1))))
        conn.execute("INSERT INTO v(clause_revision_id, doc_id, embedding) VALUES (?,?,?)",
                     (f"c{i:02d}", f"d{i % 3}", _blob([1.0 - i * 0.01] + [0.0] * (DIM - 1))))
    conn.commit()
    a = [r[0] for r in conn.execute(
        "SELECT clause_revision_id FROM o WHERE embedding MATCH ? AND k = 20 ORDER BY distance", (_blob(Q),))]
    b = [r[0] for r in conn.execute(
        "SELECT clause_revision_id FROM v WHERE embedding MATCH ? AND k = 20 ORDER BY distance", (_blob(Q),))]
    print(f"    旧表 top20 = {a[:5]}…")
    print(f"    新表 top20 = {b[:5]}…")
    print(f"    {'✅ 名单逐条相同' if a == b else '❌ 名单不同（回归！）'}")

    print()
    print("【Q7】纯 SQL 拷贝（不重算向量）后，向量字节是否相同")
    conn.execute(DDL_NEW.format(t="copy"))
    conn.execute("INSERT INTO copy(clause_revision_id, doc_id, embedding)"
                 " SELECT clause_revision_id, doc_id, embedding FROM v")
    conn.commit()
    diff = 0
    for r in conn.execute("SELECT clause_revision_id, doc_id, embedding FROM v"):
        r2 = conn.execute("SELECT doc_id, embedding FROM copy WHERE clause_revision_id=?",
                          (r["clause_revision_id"],)).fetchone()
        if r2 is None or bytes(r2["embedding"]) != bytes(r["embedding"]) or r2["doc_id"] != r["doc_id"]:
            diff += 1
    n = conn.execute("SELECT count(*) FROM v").fetchone()[0]
    print(f"    拷贝 {n} 行，逐字节不同的 = {diff}  {'✅ 字节级一致' if diff == 0 else '❌ 有差异'}")

    print()
    print("【Q8】范围指向的文档没有任何向量")
    rows = conn.execute(
        "SELECT clause_revision_id FROM v WHERE doc_id IN (SELECT value FROM json_each(?))"
        " AND embedding MATCH ? AND k = 20 ORDER BY distance",
        (json.dumps(["no_such_doc"]), _blob(Q))).fetchall()
    print(f"    → {len(rows)} 行  {'✅ 返回空、不报错' if len(rows) == 0 else '❌ 异常'}")

    print()
    print("【Q9】元数据列对『不带范围』的 KNN 有没有拖慢（同数据量对照）")
    for tag, ddl in (("旧表", DDL_OLD), ("新表", DDL_NEW)):
        conn.execute(f"DROP TABLE IF EXISTS perf_{tag}")
        conn.execute(ddl.format(t=f"perf_{tag}"))
        for i in range(2000):
            v = [1.0 - (i % 100) * 0.001] + [0.0] * (DIM - 1)
            if tag == "旧表":
                conn.execute(f"INSERT INTO perf_{tag}(clause_revision_id, embedding) VALUES (?,?)",
                             (f"x{i}", _blob(v)))
            else:
                conn.execute(f"INSERT INTO perf_{tag}(clause_revision_id, doc_id, embedding) VALUES (?,?,?)",
                             (f"x{i}", f"d{i % 50}", _blob(v)))
        conn.commit()
        t0 = time.perf_counter()
        for _ in range(50):
            conn.execute(f"SELECT clause_revision_id FROM perf_{tag}"
                         f" WHERE embedding MATCH ? AND k = 20 ORDER BY distance", (_blob(Q),)).fetchall()
        dt = (time.perf_counter() - t0) / 50 * 1000
        print(f"    {tag}：50 次 KNN 平均 {dt:.2f} ms/次")

    print()
    print("=" * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
