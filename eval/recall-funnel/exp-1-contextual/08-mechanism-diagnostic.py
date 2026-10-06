"""E1 机制诊断（可复跑）：换文本后，**同一篇文档内的条文是不是被推得更像了**？

先行指标（Δmargin = −0.0060）最自然的解释是：上下文里"同一篇文档每条都一样"的样板
（标准名 + 章号）把同篇条文往一个共同重心上推 ⇒ **条文之间的可区分度下降** ⇒ 名次变差。

本脚本直接量这件事（两个向量表都在副本里，不需要重算 embedding）：
 · **篇内相似度**：同一文档内条文两两余弦的均值；
 · **篇间相似度**：随机跨文档条文对的两两余弦均值；
 · 两个臂各算一遍，比差值。
判据：实验臂的**篇内**升幅明显大于**篇间** ⇒ 机制成立。

⚠ 依赖 `clause_vec_ctx` 已算完（或至少覆盖取样文档）。中途跑只覆盖已算部分。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\08-mechanism-diagnostic.py
"""
from __future__ import annotations

import array
import json
import random
import sqlite3
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
OUT = HERE / "mechanism-diagnostic.json"


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)

    docs = c.execute(
        "SELECT cr.doc_id, COUNT(*) n FROM clause_revision cr"
        " WHERE EXISTS (SELECT 1 FROM clause_vec_ctx v"
        "               WHERE v.clause_revision_id = cr.clause_revision_id)"
        " GROUP BY cr.doc_id HAVING n >= 10 ORDER BY n DESC LIMIT 40").fetchall()
    print(f"[diag] 取 {len(docs)} 篇文档（每篇 ≥10 条且两个臂都已算）")

    def load(doc_id: str, table: str, limit: int = 40):
        rows = c.execute(
            f"SELECT v.embedding FROM {table} v JOIN clause_revision cr"
            "   ON cr.clause_revision_id = v.clause_revision_id"
            " WHERE cr.doc_id = ? LIMIT ?", (doc_id, limit)).fetchall()
        return [list(array.array("f", bytes(r[0]))) for r in rows]

    def cos(a, b):
        return sum(x * y for x, y in zip(a, b))

    def mean_pairwise(vs):
        s, n = 0.0, 0
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                s += cos(vs[i], vs[j])
                n += 1
        return s / n if n else None

    within = {"base": [], "ctx": []}
    for doc_id, _n in docs:
        for arm, table in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            m = mean_pairwise(load(doc_id, table))
            if m is not None:
                within[arm].append(m)

    rnd = random.Random(20261006)
    ids = [r[0] for r in c.execute("SELECT clause_revision_id FROM clause_vec_ctx LIMIT 20000")]
    doc_of = {r[0]: r[1] for r in c.execute(
        "SELECT clause_revision_id, doc_id FROM clause_revision"
        " WHERE clause_revision_id IN (SELECT clause_revision_id FROM clause_vec_ctx LIMIT 20000)")}
    cross = {"base": [], "ctx": []}
    for _ in range(4000):
        a, b = rnd.sample(ids, 2)
        if doc_of.get(a) == doc_of.get(b):
            continue
        vs = {}
        for arm, table in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            ra = c.execute(f"SELECT embedding FROM {table} WHERE clause_revision_id=?", (a,)).fetchone()
            rb = c.execute(f"SELECT embedding FROM {table} WHERE clause_revision_id=?", (b,)).fetchone()
            vs[arm] = (ra, rb)
        if not all(all(v) for v in vs.values()):
            continue
        cross["base"].append(cos(list(array.array("f", bytes(vs["base"][0][0]))),
                                 list(array.array("f", bytes(vs["base"][1][0])))))
        cross["ctx"].append(cos(list(array.array("f", bytes(vs["ctx"][0][0]))),
                                list(array.array("f", bytes(vs["ctx"][1][0])))))

    d_within = st.mean(within["ctx"]) - st.mean(within["base"])
    d_cross = st.mean(cross["ctx"]) - st.mean(cross["base"])
    result = {
        "question": "换文本后，同一篇文档内的条文是不是被推得更像了？（解释先行指标的负号）",
        "n_docs": len(within["base"]), "n_cross_pairs": len(cross["base"]),
        "within_doc": {"base_mean": st.mean(within["base"]), "ctx_mean": st.mean(within["ctx"]),
                       "base_median": st.median(within["base"]), "ctx_median": st.median(within["ctx"]),
                       "delta": d_within},
        "cross_doc": {"base_mean": st.mean(cross["base"]), "ctx_mean": st.mean(cross["ctx"]),
                      "delta": d_cross},
        "verdict": ("机制成立：篇内升幅远大于篇间 ⇒ 模型更多在认「哪篇文档」而不是「哪条条文」"
                    if d_within > 0.005 and d_within > 3 * max(d_cross, 0.001)
                    else "机制不成立或不足以解释"),
        "implication": [
            "篇内相似度大幅上升 ⇒ 同一篇文档内部的条文更难区分。",
            "而我们的任务恰恰是：在一篇（通常几十条）里挑出正确那一条。",
            "所以对 @20/@100 这类「要精确排前面」的指标，风险大于收益；@1000 取决于文档级信号能否补回来。",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "implication"},
                     ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
