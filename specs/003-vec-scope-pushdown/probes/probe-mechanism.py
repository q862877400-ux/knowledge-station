# -*- coding: utf-8 -*-
"""spec 003 · 判决性实验（修正版）：**直接 SQL** 跑两种写法，找旧写法的失效条件。

⚠ 上一版（probe-scale-flip.py）踩坑：它调 `perform_hybrid_search`，而那是**新代码** ⇒
标着"旧写法"的那一列其实是新写法，**不可比**。本版改成直接 SQL。

变量：
  N   = clause_vec 里"范围外近邻"的条数（与查询向量完全一致 ⇒ 全局 top-k 全是它们）
  m   = 范围内 5 条里**有向量**的条数（夹具=1；真库≈全部）
判据：范围内那条（与查询最远）必须被返回，且**不许**出现 `out_`。
"""
from __future__ import annotations

import json
import sqlite3
import sys

import sqlite_vec

DIM = 512
OLD_SQL = ("SELECT clause_revision_id FROM clause_vec WHERE embedding MATCH ? AND k = 20"
           " AND clause_revision_id IN (SELECT clause_revision_id FROM clause_revision"
           " WHERE doc_id IN (SELECT value FROM json_each(?))) ORDER BY distance")
NEW_SQL = ("SELECT clause_revision_id FROM clause_vec"
           " WHERE doc_id IN (SELECT value FROM json_each(?))"
           " AND embedding MATCH ? AND k = 20 ORDER BY distance")


def main() -> int:
    c = sqlite3.connect(":memory:")
    c.enable_load_extension(True); sqlite_vec.load(c); c.enable_load_extension(False)
    c.execute("CREATE TABLE clause_revision(clause_revision_id TEXT PRIMARY KEY, doc_id TEXT)")
    c.execute(f"CREATE VIRTUAL TABLE clause_vec USING vec0("
              f"clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[{DIM}])")
    for i in range(5):
        c.execute("INSERT INTO clause_revision VALUES (?,?)", (f"in_c{i}", "in_doc"))
    c.execute("INSERT INTO clause_revision VALUES ('out_x','out_doc')")
    c.commit()

    FAR = sqlite_vec.serialize_float32([0.0] * (DIM - 1) + [1.0])
    NEAR = sqlite_vec.serialize_float32([1.0] + [0.0] * (DIM - 1))
    scope = json.dumps(["in_doc"])

    print("=" * 92)
    print("%-8s %-10s | %-22s | %-22s" % ("近邻数N", "范围内有向量m", "旧写法 clause_revision_id IN", "新写法 doc_id IN"))
    print("-" * 92)
    for n in (25, 200, 2000, 20000, 100000):
        for m in (1, 5):
            c.execute("DELETE FROM clause_vec")
            for i in range(n):
                c.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                          " VALUES (?,?,?)", (f"out_{i}", "out_doc", NEAR))
            for i in range(m):
                c.execute("INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
                          " VALUES (?,?,?)", (f"in_c{i}", "in_doc", FAR))
            c.commit()
            res = []
            for sql, args in ((OLD_SQL, (NEAR, scope)), (NEW_SQL, (scope, NEAR))):
                rows = [r[0] for r in c.execute(sql, args)]
                bad = [r for r in rows if r.startswith("out_")]
                ok = bool(rows) and not bad
                res.append("%-3d 行 %s" % (len(rows), "✅" if ok else ("❌空" if not rows else "❌越界")))
            print("%-8d %-10d | %-22s | %-22s" % (n, m, res[0], res[1]))
    print("-" * 92)
    print("读法：旧写法哪一档开始 ❌ ⇒ 那是翻转点。新写法应**全档 ✅**。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
