# -*- coding: utf-8 -*-
"""spec 003 · 真库端到端：走**生产的 `perform_hybrid_search`**（不是手写 SQL）验范围通道。

为什么还要这一步：前面的探针/实测都是**手写 SQL**。手写容易漏掉调用链上的东西
（本轮已经因为手写 SQL 写错一次）。这一步走**真代码路径**、对**真库**（663,634 行）。

做法：把嵌入器打成"固定向量"（模型下不下来），其余一律走生产逻辑。
⚠ 只跑 SELECT，不写库。
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")

from src.core.retrieval import embedder as emb
from src.core.retrieval.hybrid_engine import perform_hybrid_search
from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

DIM = 512
QV = [1.0] + [0.0] * (DIM - 1)


def main() -> int:
    conn = get_db_connection()
    load_vec_extension(conn)
    print("库 =", conn.execute("SELECT file FROM pragma_database_list").fetchone()[0])
    print("clause_vec 行数 =", conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0])

    emb.is_available = lambda: True          # type: ignore[assignment]
    emb.embed_query = lambda q: QV           # type: ignore[assignment]

    print()
    print("=== 走生产路径：范围提问（channels=['vec']）===")
    docs = [r[0] for r in conn.execute(
        "SELECT doc_id FROM clause_revision GROUP BY doc_id ORDER BY COUNT(*) DESC LIMIT 5")]
    print("范围 =", len(docs), "篇文档（取条款最多的 5 篇）")

    rows = perform_hybrid_search("随便问点什么", top_k=10, channels=["vec"],
                                 rerank=False, doc_ids=docs)
    got = [r.clause_revision_id if hasattr(r, "clause_revision_id") else r[0] for r in rows]
    print("  返回 =", len(got), "条")

    # 每条结果的真实 doc_id 必须在范围内
    scope = set(docs)
    outside = []
    for cid in got:
        d = conn.execute("SELECT doc_id FROM clause_revision WHERE clause_revision_id=?",
                         (cid,)).fetchone()
        if not d or d[0] not in scope:
            outside.append((cid, d[0] if d else None))
    print("  越界（不在范围内）= %d  %s" % (len(outside), outside[:3]))
    print("  判定 =", "✅ 范围内有结果且零越界" if (got and not outside) else "❌")

    print()
    print("=== 对照：不限定范围（历史路径）应能返回 ===")
    rows2 = perform_hybrid_search("随便问点什么", top_k=10, channels=["vec"], rerank=False)
    got2 = [r.clause_revision_id if hasattr(r, "clause_revision_id") else r[0] for r in rows2]
    print("  返回 =", len(got2), "条  ", "✅" if got2 else "❌")

    print()
    print("=== 对照：空范围必须一条都不返回（不许退化成全库）===")
    rows3 = perform_hybrid_search("随便问点什么", top_k=10, channels=["vec"],
                                  rerank=False, doc_ids=[])
    print("  返回 =", len(rows3), "条  ", "✅" if not rows3 else "❌ 退化成全库了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
