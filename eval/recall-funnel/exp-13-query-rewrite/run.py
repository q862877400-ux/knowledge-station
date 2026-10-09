"""exp-13：**查询侧改写** A/B/C/D —— 只改查询串，索引一个字不动。

## 为什么做这个
`exp-8` 已答：向量对 120/120 **全召回**、中位名次 **4,322** ⇒ 是**名次**问题、不是"嵌入空间没形成语义邻域"。
三条路已被量过并堵死：**列先验**（E9 上界 3.04× < 门槛 4.32×）、**重排器**（exp-11 只 +1.67pt）、
**放大上限**（exp-6 没用）⇒ 剩下的是 **查询改写 / 语料内统计关系**。本批做它的**最便宜形式**：
只改查询串、不重建索引、不换模型、不改生产代码。

## 冻结口径（跑前写死，见同目录 `stop-loss.json`）
 · 考卷 = `benchmark-v2.jsonl` 的 **headline 120 条**（`v2.bucket=="keep"` 且 flags 不含
   `gold_multi_def`/`gold_dup_text`）—— 与 `exp-8` **同一口径**；
 · 模型 = 生产 `bge-small-zh-v1.5`（fastembed，CPU/ONNX），走 `src.core.retrieval.embedder`；
 · 向量 = 全库**精确**名次（暴力扫，非 ANN）；
 · **唯一变量 = 送进 `embed_query` 的查询串**；索引/条文/向量表**一个字不动**；
 · **四臂**：
   - `A0_raw`              原样提问（生产口径，基线）
   - `B1_bge_instruction`  BGE 官方中文检索指令前缀 + 提问
   - `C1_domain_prefix`    领域前缀 + 提问
   - `D1_prf_expand`       **语料内 PRF 扩展**：A0 的向量 Top-20 条款文本 → 取在 >=3 篇里出现、
                           且提问里没有的中文内容词（<=8 个）→ 追加到提问后面
 · **仪器对照**：`A0` 的逐条 `vector_rank` 必须与 `exp-8/fullrank.json` **0 处不同**。

## 报什么
每臂：`Vector@20/@100/@1000`、向量全库**中位名次**、`by_subset`（字面零重合档 / 普通档）；
A0 与 D1 另报 `FTS@1000`（只有这两臂的查询串是"内容"，B1/C1 是指令前缀，喂 FTS 无意义）；
各改写臂 vs A0 的**配对翻转**与 **McNemar 精确 p**。

用法： `.venv\\Scripts\\python.exe eval\\recall-funnel\\exp-13-query-rewrite\\run.py`
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from math import comb
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
OUT = HERE / "result.json"
OUT_Q = HERE / "per-query.jsonl"

BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
DOMAIN_PREFIX = "检索相关法规与标准条文："

PRF_TOP_DOCS = 20      # PRF 取 A0 向量前多少条条款当"伪相关集"
PRF_TOP_TERMS = 8      # 最多追加几个词
PRF_MIN_DF = 3         # 至少出现在伪相关集的几篇里才算
PRF_MIN_LEN = 2        # 词长下限（单字不要）

ARMS = ("A0_raw", "B1_bge_instruction", "C1_domain_prefix", "D1_prf_expand")
THRESHOLDS_PT = (20, 100, 1000)


# ── 纯函数（单测直接变异这些）────────────────────────────────────────────────

def _default_tokenize(text: str) -> list[str]:
    """生产同款分词器（jieba）。测试注入替身即可脱离 jieba。"""
    import jieba
    return [t.strip() for t in jieba.lcut(text) if t.strip()]


def _is_cjk_word(tok: str) -> bool:
    """只保留含中文的词（纯数字/标点/英文串不进扩展）。"""
    return any("\u4e00" <= ch <= "\u9fff" for ch in tok)


def arm_queries(query: str, prf_terms: Sequence[str] | None = None) -> dict[str, str]:
    """★ 纯函数：四臂各自的查询串。**唯一变量就是这里返回的串**。

    `D1_prf_expand` 没有扩展词时**退回原样**（不追加空串），这样"没扩到词"与"基线"逐字相同，
    不会把一次空扩展当成一次改写。
    """
    base = (query or "").strip()
    terms = [t for t in (prf_terms or []) if t]
    return {
        "A0_raw": base,
        "B1_bge_instruction": BGE_QUERY_INSTRUCTION + base,
        "C1_domain_prefix": DOMAIN_PREFIX + base,
        "D1_prf_expand": (base + " " + " ".join(terms)).strip() if terms else base,
    }


def pick_prf_terms(
    query: str,
    docs: Sequence[str],
    tokenize: Callable[[str], list[str]] = _default_tokenize,
    top_m: int = PRF_TOP_TERMS,
    min_df: int = PRF_MIN_DF,
) -> list[str]:
    """★ 纯函数（分词器可注入）：从"伪相关集"文档里挑扩展词。

    规则（跑前写死）：候选 = 出现在 **>= min_df 篇**、**含中文**、**长度 >= 2**、
    **提问里没有**的词；排序 = 出现篇数降序 → 词长降序 → 字典序（确定性）。
    同一篇里重复出现的词**只计一次**（df 是"文档频率"，不是词频）。
    """
    q_terms = set(tokenize(query))
    df: dict[str, int] = {}
    for d in docs:
        seen: set[str] = set()
        for t in tokenize(d):
            if len(t) < PRF_MIN_LEN or not _is_cjk_word(t):
                continue
            if t in q_terms or t in seen:
                continue
            seen.add(t)
        for t in seen:
            df[t] = df.get(t, 0) + 1
    cand = [(t, c) for t, c in df.items() if c >= min_df]
    cand.sort(key=lambda x: (-x[1], -len(x[0]), x[0]))
    return [t for t, _ in cand[:top_m]]


def rank_of(scores: np.ndarray, idx: int) -> int:
    """名次 = **严格更优**的条数 + 1（分数越大越好）。"""
    return int((scores > scores[idx]).sum()) + 1


def top_k_indices(scores: np.ndarray, k: int) -> list[int]:
    """取分数最高的 k 个下标（降序）。"""
    k = min(k, len(scores))
    part = np.argpartition(-scores, k - 1)[:k]
    return [int(i) for i in part[np.argsort(-scores[part])]]


def mcnemar_exact(b: int, c: int) -> float:
    """★ 配对"翻进 b / 翻出 c"的双侧精确二项 p（exp-11 同法）。"""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * p)


def hit_rate(ranks: Sequence[int | None], thr: int) -> float:
    """ranks 里 <= thr 的比例（None = 未召回，算不中）。"""
    if not ranks:
        return 0.0
    return round(sum(1 for r in ranks if r is not None and r <= thr) / len(ranks) * 100, 2)


def median_rank(ranks: Sequence[int | None]) -> int | None:
    vals = sorted(r for r in ranks if r is not None)
    return vals[len(vals) // 2] if vals else None


def flip_counts(base: Sequence[bool], arm: Sequence[bool]) -> tuple[int, int]:
    """(翻进, 翻出)：base=False→arm=True 的条数 / base=True→arm=False 的条数。"""
    b = sum(1 for x, y in zip(base, arm) if (not x) and y)
    c = sum(1 for x, y in zip(base, arm) if x and (not y))
    return b, c


# ── 驱动器（要真库，几十秒；不写库）──────────────────────────────────────────

def _headline(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if (r.get("v2") or {}).get("bucket") == "keep"
        and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))
    ]


def _fts_rank(conn: sqlite3.Connection, query: str, gold: str):
    from src.core.retrieval.hybrid_engine import _fts_query
    fq = _fts_query(query)
    if not fq:
        return None, None
    try:
        cnt = conn.execute(
            "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ?", (fq,)).fetchone()[0]
        grow = conn.execute(
            "SELECT rank FROM clause_fts WHERE clause_fts MATCH ? AND clause_revision_id = ?",
            (fq, gold)).fetchone()
        if grow is not None and cnt:
            better = conn.execute(
                "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ? AND rank < ?",
                (fq, grow[0])).fetchone()[0]
            return int(better) + 1, int(cnt)
        return None, int(cnt)
    except sqlite3.OperationalError as e:  # noqa: BLE001
        print(f"[exp-13] ⚠ FTS 失败: {e}", flush=True)
        return None, None


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension  # noqa: F401
    from src.core.retrieval import embedder
    import funnel

    conn = funnel.ro_conn(DB)
    print(f"[exp-13] 库 = {DB}（mode=ro）", flush=True)

    rows = [json.loads(l) for l in
            (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]
    items = _headline(rows)
    print(f"[exp-13] headline 考卷 = {len(items)} 条", flush=True)

    t0 = time.perf_counter()
    vr = conn.execute("SELECT clause_revision_id, embedding FROM clause_vec").fetchall()
    ids = [r[0] for r in vr]
    M = np.frombuffer(b"".join(r[1] for r in vr), dtype=np.float32).reshape(len(vr), -1)
    total = len(ids)
    id_pos = {cid: i for i, cid in enumerate(ids)}
    print(f"[exp-13] 全库矩阵 {M.shape} 载入 {time.perf_counter()-t0:.0f}s "
          f"内存 {M.nbytes/1e9:.2f} GB  向量总数 {total}", flush=True)

    def vec_scores(qvec: np.ndarray) -> np.ndarray:
        # ★ 与 exp-8 **逐字同一算式**：`np.linalg.norm(M - qe, axis=1)`。
        #   首跑曾用等价但更快的 `-(||M||²-2M·q+||q||²)`，结果 3/120 条名次差 ±1
        #   —— 那 3 处是 **float32 并列**（最近非零距离差 6e-8~6e-7 ≈ 1 ULP），
        #   两式舍入不同就把并列掰向另一边。仪器对照要求"0 处不同" ⇒ 换回同算式。
        return -np.linalg.norm(M - qvec, axis=1)

    # ── ① A0：原样（生产口径）+ 取 Top-20 供 PRF ─────────────────────────────
    print("[exp-13] 臂 A0_raw …", flush=True)
    t0 = time.perf_counter()
    a0_scores = []
    a0_ranks: list[int | None] = []
    a0_top20: list[list[int]] = []
    for it in items:
        qv = np.asarray(embedder.embed_query(it["query"]), dtype=np.float32)
        s = vec_scores(qv)
        a0_scores.append(s)
        gi = id_pos.get(it["v2"]["gold_cr_id"])
        a0_ranks.append(rank_of(s, gi) if gi is not None else None)
        a0_top20.append(top_k_indices(s, PRF_TOP_DOCS))
    print(f"[exp-13] A0 完成 {time.perf_counter()-t0:.0f}s", flush=True)

    # ── ② D1：语料内 PRF 扩展（用 A0 的 Top-20 文本）─────────────────────────
    print("[exp-13] 臂 D1_prf_expand …", flush=True)
    t0 = time.perf_counter()
    d1_queries: list[str] = []
    d1_terms: list[list[str]] = []
    for it, top in zip(items, a0_top20):
        cids = [ids[i] for i in top]
        qmarks = ",".join("?" * len(cids))
        txt = {r[0]: r[1] for r in conn.execute(
            f"SELECT clause_revision_id, COALESCE(content_text,'') FROM clause_revision "
            f"WHERE clause_revision_id IN ({qmarks})", cids)}
        docs = [txt.get(c, "") for c in cids]
        terms = pick_prf_terms(it["query"], docs)
        d1_terms.append(terms)
        d1_queries.append(arm_queries(it["query"], terms)["D1_prf_expand"])
    print(f"[exp-13] D1 扩展词就绪 {time.perf_counter()-t0:.0f}s "
          f"（有扩展词的题 {sum(1 for t in d1_terms if t)}/{len(d1_terms)}）", flush=True)

    # ── ③ 四臂统一算名次 ────────────────────────────────────────────────────
    arm_ranks: dict[str, list[int | None]] = {"A0_raw": a0_ranks}
    for arm in ARMS:
        if arm == "A0_raw":
            continue
        print(f"[exp-13] 臂 {arm} …", flush=True)
        t0 = time.perf_counter()
        ranks: list[int | None] = []
        for n, it in enumerate(items):
            q = d1_queries[n] if arm == "D1_prf_expand" else arm_queries(it["query"])[arm]
            qv = np.asarray(embedder.embed_query(q), dtype=np.float32)
            s = vec_scores(qv)
            gi = id_pos.get(it["v2"]["gold_cr_id"])
            ranks.append(rank_of(s, gi) if gi is not None else None)
        arm_ranks[arm] = ranks
        print(f"[exp-13] {arm} 完成 {time.perf_counter()-t0:.0f}s", flush=True)

    # ── ④ FTS（只有 A0 与 D1 的查询串是"内容"）──────────────────────────────
    fts: dict[str, list[int | None]] = {}
    for arm in ("A0_raw", "D1_prf_expand"):
        ranks = []
        for n, it in enumerate(items):
            q = it["query"] if arm == "A0_raw" else d1_queries[n]
            r, _cnt = _fts_rank(conn, q, it["v2"]["gold_cr_id"])
            ranks.append(r)
        fts[arm] = ranks
        print(f"[exp-13] FTS {arm}：@1000 = {hit_rate(ranks, 1000)}%", flush=True)

    # ── ⑤ 聚合 ─────────────────────────────────────────────────────────────
    labels = [(it.get("v2") or {}).get("subset", {}).get("label") for it in items]
    subset_names = sorted({x for x in labels if x})

    def by_subset(ranks, thr):
        out = {}
        for nm in subset_names:
            sub = [r for r, lb in zip(ranks, labels) if lb == nm]
            out[nm] = {"n": len(sub), "hit": hit_rate(sub, thr)}
        return out

    agg: dict = {"n": len(items), "total_clauses": total, "arms": {}}
    for arm in ARMS:
        r = arm_ranks[arm]
        rec = {f"vector_top{t}": hit_rate(r, t) for t in THRESHOLDS_PT}
        rec["vector_median_rank"] = median_rank(r)
        rec["by_subset_top1000"] = by_subset(r, 1000)
        if arm != "A0_raw":
            base_hit = [x is not None and x <= 1000 for x in arm_ranks["A0_raw"]]
            arm_hit = [x is not None and x <= 1000 for x in r]
            b, c = flip_counts(base_hit, arm_hit)
            rec["vs_A0_top1000"] = {
                "delta_pt": round(rec["vector_top1000"] - agg["arms"]["A0_raw"]["vector_top1000"], 2),
                "flip_in": b, "flip_out": c, "mcnemar_p": round(mcnemar_exact(b, c), 4),
            }
        agg["arms"][arm] = rec
    agg["fts"] = {arm: {f"top{t}": hit_rate(fts[arm], t) for t in THRESHOLDS_PT}
                  for arm in fts}

    # ── ⑥ 仪器对照：A0 必须逐条复现 exp-8 ───────────────────────────────────
    fr = json.loads((ROOT / "eval" / "recall-funnel" / "exp-8-fullrank"
                     / "fullrank.json").read_text(encoding="utf-8"))
    e8 = {r["i"]: r["vector_rank"] for r in fr["per_query"]}
    mism = [(it["i"], e8.get(it["i"]), a0_ranks[n])
            for n, it in enumerate(items) if e8.get(it["i"]) != a0_ranks[n]]
    agg["instrument_check"] = {
        "exp8_median_vector_rank": fr["agg"]["vector"].get("median"),
        "mismatch_count": len(mism),
        "mismatch_samples": mism[:5],
        "note": "A0 逐条 vector_rank 必须与 exp-8/fullrank.json 0 处不同",
    }

    print("\n[exp-13] ==== 结果 ====")
    for arm in ARMS:
        a = agg["arms"][arm]
        extra = ""
        if arm != "A0_raw":
            v = a["vs_A0_top1000"]
            extra = f"  Δ={v['delta_pt']:+.2f}pt 进{v['flip_in']}/出{v['flip_out']} p={v['mcnemar_p']}"
        print(f"  {arm:20s} @20={a['vector_top20']:5.2f}%  @100={a['vector_top100']:5.2f}%  "
              f"@1000={a['vector_top1000']:5.2f}%  中位={a['vector_median_rank']}{extra}")
    print(f"  FTS @1000  A0={agg['fts']['A0_raw']['top1000']}%  D1={agg['fts']['D1_prf_expand']['top1000']}%")
    print(f"  仪器对照：与 exp-8 不同 = {len(mism)} 处"
          f"（exp-8 中位 {fr['agg']['vector'].get('median')}）")

    OUT.write_text(json.dumps({"note": "exp-13 查询侧改写 A/B/C/D；口径见 run.py docstring 与 stop-loss.json",
                               "agg": agg}, ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT_Q.open("w", encoding="utf-8") as f:
        for n, it in enumerate(items):
            f.write(json.dumps({
                "i": it["i"], "query": it["query"], "gold_cr_id": it["v2"]["gold_cr_id"],
                "subset": labels[n],
                "prf_terms": d1_terms[n], "d1_query": d1_queries[n],
                "vector_rank": {arm: arm_ranks[arm][n] for arm in ARMS},
                "fts_rank": {arm: fts[arm][n] for arm in fts},
            }, ensure_ascii=False) + "\n")
    print(f"\n[exp-13] 已写 {OUT} 与 {OUT_Q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
