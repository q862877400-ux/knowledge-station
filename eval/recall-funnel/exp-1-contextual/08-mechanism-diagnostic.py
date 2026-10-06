"""E1 机制诊断 v2（可复跑）：换文本后，模型是不是更"认文档"、更不"认条文"？

## v1 的两个问题（独立复核 F8 指出，已自查确认）

1. **样本有偏**：v1 取的是 `ORDER BY n DESC LIMIT 40`，即**全库最大的 40 篇文档**
   （条文数 962~1494，中位 674；而全库文档条文数中位只有 53）。极端长文档不代表全库。
2. **量错了对象**：v1 量的是"篇内/篇间相似度的**水平**"。相似度水平升高，
   **不等于**"可区分度下降"。要证"模型更认文档"，得看**最近邻里同篇的比例**。

## v2 改成三件事

| 量 | 怎么算 | 它回答什么 |
|---|---|---|
| A 篇内相似度 | 同文档条文两两余弦的均值/中位 | 照旧（参考值） |
| B 篇间相似度 | 随机跨文档对的两两余弦 | 照旧（参考值） |
| **C 最近邻同篇率** | 随机抽 N 条，各跑 KNN top-k（**两个臂从同一批查询**），数 top-k 里有多少条与该条**同属一篇文档** | **直接回答"模型是不是更在认文档"** |

样本规则（**写死，可复算**）：文档按 `doc_id` 排序后**等距抽样**（不是取最大的），
只要求该文档在本进程抽样时两臂都已算完；C 的条文样本用固定种子随机抽。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\08-mechanism-diagnostic.py
"""
from __future__ import annotations

import array
import json
import random
import sqlite3
import statistics as st
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
OUT = HERE / "mechanism-diagnostic.json"
N_DOCS = 40
N_CROSS = 4000
N_CLAUSES = 300
TOPK = 20


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)

    def vec(table: str, cid: str):
        r = c.execute(f"SELECT embedding FROM {table} WHERE clause_revision_id=?", (cid,)).fetchone()
        return None if r is None else list(array.array("f", bytes(r[0])))

    cos = lambda a, b: sum(x * y for x, y in zip(a, b))       # noqa: E731 单位向量 ⇒ 内积即余弦

    # ── A/B：篇内、篇间 ───────────────────────────────────────────────────
    # 等距抽样（按 doc_id 排序），不是"取最大的"
    docs = [r[0] for r in c.execute(
        "SELECT doc_id FROM clause_revision GROUP BY doc_id HAVING COUNT(*) >= 10 ORDER BY doc_id")]
    step = max(1, len(docs) // N_DOCS)
    picked = docs[::step][:N_DOCS]
    print(f"[diag] 满足 ≥10 条的文档共 {len(docs)} 篇，等距抽 {len(picked)} 篇"
          f"（不是按条文数降序）", flush=True)

    def load(doc_id, table, limit=40):
        return [list(array.array("f", bytes(r[0]))) for r in c.execute(
            f"SELECT v.embedding FROM {table} v JOIN clause_revision cr"
            "   ON cr.clause_revision_id = v.clause_revision_id"
            " WHERE cr.doc_id = ? LIMIT ?", (doc_id, limit))]

    def pairwise(vs):
        s, n = 0.0, 0
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                s += cos(vs[i], vs[j]); n += 1
        return s / n if n else None

    within = {"base": [], "ctx": []}
    for d in picked:
        for arm, tbl in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            vs = load(d, tbl)
            m = pairwise(vs)
            if m is not None:
                within[arm].append(m)
    print(f"[diag] 篇内算完（{len(within['base'])} 篇）", flush=True)

    rnd = random.Random(20261006)
    ids = [r[0] for r in c.execute("SELECT clause_revision_id FROM clause_vec_ctx LIMIT 30000")]
    doc_of = dict(c.execute(
        "SELECT clause_revision_id, doc_id FROM clause_revision"
        " WHERE clause_revision_id IN (SELECT clause_revision_id FROM clause_vec_ctx LIMIT 30000)"))
    cross = {"base": [], "ctx": []}
    for _ in range(N_CROSS):
        a, b = rnd.sample(ids, 2)
        if doc_of.get(a) == doc_of.get(b):
            continue
        va, vb = vec("clause_vec", a), vec("clause_vec", b)
        wa, wb = vec("clause_vec_ctx", a), vec("clause_vec_ctx", b)
        if not all((va, vb, wa, wb)):
            continue
        cross["base"].append(cos(va, vb)); cross["ctx"].append(cos(wa, wb))
    print(f"[diag] 篇间算完（{len(cross['base'])} 对）", flush=True)

    # ── C：最近邻同篇率（**这才是"认不认文档"的直接证据**）─────────────────
    probe = rnd.sample(ids, min(N_CLAUSES, len(ids)))
    same = {"base": 0, "ctx": 0}
    tot = 0
    t0 = time.perf_counter()
    for i, cid in enumerate(probe, 1):
        qv = vec("clause_vec_ctx", cid)          # 用该条自己的向量当查询（两臂同一个查询）
        if qv is None:
            continue
        d = doc_of.get(cid)
        for arm, tbl in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            rows = c.execute(
                f"SELECT v.clause_revision_id FROM {tbl} v"
                " WHERE v.embedding MATCH ? AND k = ? ORDER BY v.distance",
                (array.array("f", qv).tobytes(), TOPK)).fetchall()
            same[arm] += sum(1 for r in rows if doc_of.get(r[0]) == d)
        tot += 1
        if i % 50 == 0:
            print(f"[diag] 最近邻 {i}/{len(probe)}  {time.perf_counter()-t0:.0f}s", flush=True)

    nn = {arm: round(same[arm] / (tot * TOPK), 4) for arm in ("base", "ctx")} if tot else {}
    d_within = st.mean(within["ctx"]) - st.mean(within["base"])
    d_cross = st.mean(cross["ctx"]) - st.mean(cross["base"])
    d_nn = (nn.get("ctx", 0) - nn.get("base", 0)) if nn else None

    result = {
        "question": "换文本后，模型是不是更'认文档'、更不'认条文'？",
        "v1_problems_fixed": [
            "v1 取的是全库最大的 40 篇（条文数 962~1494，全库中位 53）⇒ 样本有偏；"
            "v2 改为按 doc_id 等距抽样。",
            "v1 只量了相似度水平 ⇒ 不等于可区分度；v2 补上 C：最近邻同篇率。",
        ],
        "sample_rule": (f"文档：满足 ≥10 条的 {len(docs)} 篇按 doc_id 等距抽 {len(picked)} 篇；"
                        f"最近邻：固定种子随机抽 {tot} 条，每臂 KNN top-{TOPK}；"
                        f"篇间：固定种子随机跨文档对 {len(cross['base'])} 对"),
        "A_within_doc_similarity": {
            "base_mean": round(st.mean(within["base"]), 4), "ctx_mean": round(st.mean(within["ctx"]), 4),
            "base_median": round(st.median(within["base"]), 4), "ctx_median": round(st.median(within["ctx"]), 4),
            "delta": round(d_within, 4),
        },
        "B_cross_doc_similarity": {
            "base_mean": round(st.mean(cross["base"]), 4), "ctx_mean": round(st.mean(cross["ctx"]), 4),
            "delta": round(d_cross, 4),
        },
        "C_nearest_neighbour_same_doc_rate": {
            "k": TOPK, "n_queries": tot,
            "base": nn.get("base"), "ctx": nn.get("ctx"), "delta": d_nn,
            "reading": "top-k 邻居里有多大比例与该条同属一篇文档 —— 越高说明模型越在'认文档'",
        },
        "verdict": (
            "**机制成立**：最近邻同篇率明显上升 ⇒ 模型确实更在'认文档'"
            if d_nn is not None and d_nn > 0.02 else
            "**机制未获支持**：最近邻同篇率没有明显变化 ⇒ '模型更认文档'这个说法**不成立**（尽管相似度水平变了）"),
        "boundary": ("A/B/C 都是**观测**；由它们推出机制属于**解释**，本实验没有为解释单独做干预实验。"
                     "C 是本轮新增的直接证据，A/B 只作参考。"),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
