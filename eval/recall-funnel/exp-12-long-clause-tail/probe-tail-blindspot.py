"""P0·0.10 决定性探针：尾巴上的字面信号，向量路够不着、FTS 路够得着。

只读真库、只读 `clause_vec`（既有、head-only 的向量）、**不写任何向量**、不改生产代码。

做法（口径跑前写死）
====================
对每条"长条款"（content_text 长度 > 700，保证尾巴够长），造两条查询：
  · `q_head` = 从 head（content_text[:512]）里挑一段**在 tail 里不出现**的中文串（10 字）
  · `q_tail` = 从 tail（content_text[512:]）里挑一段**在 head 里不出现**的中文串（10 字）
两条查询走**生产同款**的两条路：
  · FTS：`SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? ORDER BY rank LIMIT 20`
         （表达式用 `text_utils.fts_match_expr`，与生产同源）
  · 向量：`SELECT clause_revision_id, distance FROM clause_vec WHERE embedding MATCH ? AND k = 20`
         （查询向量用 `embedder.embed_query`，与生产同源）
判据：目标条款**在不在前 20**，在的话名次是多少。

预期（若 P0·0.10 成立）：`q_head` 两条路都能找到；`q_tail` **FTS 找得到、向量找不到**
（因为 `clause_vec` 是 head-only 嵌出来的）。

边界：抽样（不是全部）；单机单时点；query 是机械从原文挖的（不是真实提问）。
"""

from __future__ import annotations

import json
import os
import random
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

DB_PATH = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")
OUT = Path(__file__).resolve().parent / "probe-tail-blindspot.json"

HEAD_CHARS = 512
MIN_LEN = 800
SAMPLE_N = 30
PHRASE_LEN = 14          # v1 用 10 字 ⇒ 常被 jieba 切成常用词、OR 后目标挤不进前 20；v2 加长到 14 字
FTS_LIMIT = 100          # v1 用生产上限 20 ⇒ 分不清"FTS 找不到"与"FTS 找到但排 >20"；v2 放宽到 100
VEC_K = 1000             # v1 用生产上限 20；v2 用深读上限，看向量名次差多少
CJK_RUN = re.compile(r"[\u4e00-\u9fff]{6,}")


def pick_phrase(region: str, other: str, take: int = PHRASE_LEN) -> str | None:
    """从 region 里挑一段 take 字中文串，要求它在 other 里**不出现**。"""
    for m in CJK_RUN.finditer(region):
        s = m.group(0)
        for start in range(0, max(1, len(s) - take + 1)):
            cand = s[start:start + take]
            if len(cand) >= take and cand not in other:
                return cand
    return None


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    from src.core.text_utils import fts_match_expr
    from src.core.retrieval import embedder

    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    load_vec_extension(con)

    rows = con.execute(
        "SELECT clause_revision_id, title, content_text FROM clause_revision "
        "WHERE LENGTH(content_text) > ? ORDER BY clause_revision_id", (MIN_LEN,)).fetchall()
    rng = random.Random(20261009)
    rng.shuffle(rows)
    sample = rows[:SAMPLE_N]

    if not embedder.is_available():
        print("向量引擎不可用，探针无法进行", file=sys.stderr)
        return 2

    recs = []
    for r in sample:
        text = r["content_text"] or ""
        head, tail = text[:HEAD_CHARS], text[HEAD_CHARS:]
        qh = pick_phrase(head, tail)
        qt = pick_phrase(tail, head)
        if not qh or not qt:
            continue
        rec = {"crid": r["clause_revision_id"], "len": len(text), "q_head": qh, "q_tail": qt}
        for tag, q in (("head", qh), ("tail", qt)):
            # FTS（放宽到 FTS_LIMIT，分开"找不到"与"排 >20"）
            fq = fts_match_expr(q)
            try:
                fr = con.execute(
                    "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                    "ORDER BY rank LIMIT ?", (fq, FTS_LIMIT)).fetchall()
            except sqlite3.OperationalError:
                fr = []
            ids = [x[0] for x in fr]
            rec[f"fts_{tag}_rank"] = (ids.index(r["clause_revision_id"]) + 1
                                      if r["clause_revision_id"] in ids else None)
            # 向量（深读 k=VEC_K）
            emb = embedder.embed_query(q)
            vr = con.execute(
                "SELECT clause_revision_id, distance FROM clause_vec "
                "WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                (json.dumps(emb), VEC_K)).fetchall()
            vids = [x[0] for x in vr]
            rec[f"vec_{tag}_rank"] = (vids.index(r["clause_revision_id"]) + 1
                                      if r["clause_revision_id"] in vids else None)
        recs.append(rec)

    def hit_rate(key: str, cap: int | None = None) -> dict:
        n = len(recs)
        vals = [x.get(key) for x in recs]
        h = sum(1 for v in vals if v is not None and (cap is None or v <= cap))
        med = None
        present = sorted(v for v in vals if v is not None)
        if present:
            med = present[len(present) // 2]
        return {"n": n, "hits": h, "rate_pct": round(100.0 * h / max(n, 1), 2),
                "median_rank_when_found": med}

    out = {
        "sample_n": len(recs),
        "min_len": MIN_LEN,
        "head_chars": HEAD_CHARS,
        "phrase_len": PHRASE_LEN,
        "fts_limit": FTS_LIMIT,
        "vec_k": VEC_K,
        "fts_head": hit_rate("fts_head_rank"),
        "fts_tail": hit_rate("fts_tail_rank"),
        "fts_head_at20": hit_rate("fts_head_rank", 20),
        "fts_tail_at20": hit_rate("fts_tail_rank", 20),
        "vec_head": hit_rate("vec_head_rank"),
        "vec_tail": hit_rate("vec_tail_rank"),
        "vec_head_at20": hit_rate("vec_head_rank", 20),
        "vec_tail_at20": hit_rate("vec_tail_rank", 20),
        "rows": recs,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, ensure_ascii=False, indent=2))
    # 逐条打印对照
    for x in recs:
        print(f"{x['crid'][:26]} len={x['len']:4d} "
              f"| head: fts={x['fts_head_rank']} vec={x['vec_head_rank']} "
              f"| tail: fts={x['fts_tail_rank']} vec={x['vec_tail_rank']}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
