# -*- coding: utf-8 -*-
"""临时探针（不入库）：在**真库规模**下量我们三条召回通道的耗时 —— 补一个登记已久的空档。

## 为什么
`docs/research/rag-encyclopedia-study.md` 写着"第 3 章索引优化（ANN/HNSW 取舍）未读；
**我们仍是逐条暴力比对**"，而 `docs/KB-FOLDER-PLAN.md` 明确登记
"**仍未验：向量通道在真库规模下的耗时**"。
业主现在问的是"记忆能不能到百万/千万条" ⇒ **第一手答案得从我们自己的曲线上看**，不在别人的博客里。

## 量什么（全部只读）
* `clause_vec` 的**行数与维度**（这是"逐条暴力比对"的 N）；
* ① 查询嵌入耗时（bge-small-zh-v1.5，512 维）；
* ② **向量 KNN 耗时**（sqlite-vec vec0，k=20）—— 若它是线性扫描，则耗时 ∝ N；
* ③ FTS5/BM25 耗时（对照：倒排索引不随 N 线性涨）；
* ④ 精确条款号（有索引）耗时（对照）。
并给出**线性外推**到 1000 万条的估计（只对②有意义，且要标明是外推）。

⚠ 真库**只读**打开（`mode=ro`）；不写任何东西。
⚠ 单机单次 ⇒ 数字是量级参考。
"""
from __future__ import annotations

import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
N_RUNS = 7
QUERY = "防火间距不足时应该怎么处理"


def _med(fn, n: int = N_RUNS) -> float:
    xs = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        xs.append((time.perf_counter() - t) * 1000)
    return statistics.median(xs)


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    load_vec_extension(conn)

    n_vec = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    n_clause = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    n_doc = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    print(f"真库（只读）：文档 {n_doc:,} / 条款 {n_clause:,} / 向量行 {n_vec:,}")
    print(f"  数据集约 2.2 GB；查询：「{QUERY}」；每项取 {N_RUNS} 次的中位数")
    print()

    t_emb = _med(lambda: embedder.embed_query(QUERY), 5)
    emb = embedder.embed_query(QUERY)
    print(f"① 查询嵌入（512 维）            {t_emb:8.1f} ms")

    def vec_knn():
        conn.execute("SELECT clause_revision_id, distance FROM clause_vec"
                     " WHERE embedding MATCH ? AND k = 20", (json.dumps(emb),)).fetchall()

    t_vec = _med(vec_knn)
    print(f"② 向量 KNN（sqlite-vec, k=20）  {t_vec:8.1f} ms   ← 若线性扫描则 ∝ N")

    # 佐证"逐条暴力"：若是线性扫描，k 取多少几乎不影响耗时；若走了 ANN 索引，k 会有明显影响。
    for k in (1, 500):
        tk = _med(lambda k=k: conn.execute(
            "SELECT clause_revision_id, distance FROM clause_vec"
            " WHERE embedding MATCH ? AND k = ?", (json.dumps(emb), k)).fetchall(), 5)
        print(f"   （佐证）k={k:<4}                {tk:8.1f} ms")

    from src.core.retrieval.hybrid_engine import _fts_query  # noqa: PLC0415

    fq = _fts_query(QUERY) or QUERY

    def fts():
        conn.execute("SELECT clause_revision_id FROM clause_fts"
                     " WHERE clause_fts MATCH ? ORDER BY rank LIMIT 20", (fq,)).fetchall()

    try:
        t_fts = _med(fts)
        print(f"③ FTS5/BM25（倒排，k=20）        {t_fts:8.1f} ms")
    except Exception as e:  # noqa: BLE001
        t_fts = None
        print(f"③ FTS5 查询失败：{type(e).__name__}: {e}")

    def exact():
        conn.execute("SELECT cr.clause_revision_id FROM clause_revision cr"
                     " WHERE cr.clause_number = ? LIMIT 20", ("5.1",)).fetchall()

    try:
        t_ex = _med(exact)
        print(f"④ 精确条款号（有索引）          {t_ex:8.1f} ms")
    except Exception as e:  # noqa: BLE001
        t_ex = None
        print(f"④ 精确条款号查询失败：{type(e).__name__}: {e}")

    print()
    print("=" * 84)
    print("线性外推（**只对②成立**：vec0 是逐条比对、无 ANN 索引）")
    print("=" * 84)
    per_row = t_vec / max(n_vec, 1)
    for n in (1_000_000, 10_000_000):
        print(f"  {n:>12,} 条 ⇒ 向量那一路约 {per_row * n / 1000:8.2f} 秒/次查询"
              f"（按 {per_row * 1000:.4f} ms/千行 推）")
    print()
    print("⚠ 这是**外推**，不是实测；但它给的是「这条路会不会先坏」的量级判断。")
    print("⚠ ③④ 是**倒排/索引**，不随 N 线性涨 ⇒ 规模化的瓶颈**不在它们身上**。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
