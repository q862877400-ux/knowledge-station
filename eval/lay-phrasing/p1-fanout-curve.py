"""P1：扇出宽度的曲线（质量 vs 延迟），并试一种更合理的合并顺序。

背景：`p1-selection-strategies.py` 测到 top-5 扇出把"正确答案在返回集合里"
从 12.3% 拉到 28.5%。但扇出**不是免费的**——每多选 1 个术语 = 多 1 次 FTS 查询。
本脚本量 k=1,3,5,10,20 的**质量与实测延迟**，并试一个便宜的改进：
  · 拼接顺序：现在按"选中次序"拼（top-1 术语的 5 条全排在 top-2 术语前面）——
    这对"正确答案落在第几条"是任意的。**轮转交错**（1,1,1,1,1,2,2,2…）可能更合理。

实现：每个 case 只查它 top-20 术语各一次（缓存 top-20 条），所有 k 与两种顺序
都从这份缓存里派生 ⇒ 不会重复查。
⚠ 抽样 400 条（固定种子）——k=20 时全量要 3 万多次查询，太慢。
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.retrieval.embedder import embed_batch  # noqa: E402
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
KS_DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")
KS = (1, 3, 5, 10, 20)


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def interleave(groups: list[list[str]]) -> list[str]:
    """轮转交错合并 + 去重。"""
    out, seen = [], set()
    for row in range(20):
        for g in groups:
            if row < len(g) and g[row] not in seen:
                seen.add(g[row])
                out.append(g[row])
    return out


def main() -> int:
    import numpy as np

    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}

    ks = sqlite3.connect(f"file:{KS_DB}?mode=ro", uri=True)
    print("扫定义条款…", flush=True)
    define: dict[str, set[str]] = {t: set() for t in terms}
    for cid, txt in ks.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in define:
            define[t].add(cid)

    cases = []
    for r in rows:
        t = r["term"]
        if not define.get(t):
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx or (words(tx) & tw[t]):
                continue
            cases.append((t, tx))
    random.seed(20260925)
    sample = random.sample(cases, min(400, len(cases)))
    n = len(sample)
    print(f"非 A 档 {len(cases)} 条；**抽样 {n} 条**（seed=20260925）", flush=True)

    T = np.asarray(embed_batch(terms), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    Q = np.asarray(embed_batch([c[1] for c in sample]), dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
    order = np.argsort(-(Q @ T.T), axis=1)
    print("  嵌入完成", flush=True)

    def fts(q: str, k: int) -> list[str]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return []
        try:
            return [r[0] for r in ks.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()]
        except sqlite3.OperationalError:
            return []

    print(f"逐条查 top-{max(KS)} 个术语（每词一次，后续全从缓存派生）…", flush=True)
    cache, secs = [], 0.0
    t0 = time.time()
    for i, (gold, _ph) in enumerate(sample):
        picked = [terms[j] for j in order[i][:max(KS)]]
        groups = []
        for t in picked:
            t1 = time.time()
            groups.append(fts(t, 20))
            secs += time.time() - t1
        cache.append(groups)
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{n}  {time.time()-t0:.0f}s", flush=True)
    per_query = secs / max(sum(len(g) for g in cache), 1)

    res = {}
    for k in KS:
        for mode in ("顺序拼接", "轮转交错"):
            h5 = h20 = hall = 0
            for i, (gold, _ph) in enumerate(sample):
                tgt = define[gold]
                gs = cache[i][:k]
                if mode == "顺序拼接":
                    merged, seen = [], set()
                    for g in gs:
                        for x in g:
                            if x not in seen:
                                seen.add(x)
                                merged.append(x)
                else:
                    merged = interleave(gs)
                h5 += int(bool(tgt & set(merged[:5])))
                h20 += int(bool(tgt & set(merged[:20])))
                hall += int(bool(tgt & set(merged)))
            res[(k, mode)] = (h5, h20, hall)

    print()
    print("=" * 78)
    print(f"扇出宽度曲线（{n} 条抽样；每词 FTS 实测 {per_query*1000:.0f} ms）")
    print("=" * 78)
    print(f"{'k':<5}{'合并顺序':<12}{'前5':>8}{'前20':>8}{'命中集合':>10}{'单条提问新增查询':>18}{'新增延迟':>12}")
    for k in KS:
        for mode in ("顺序拼接", "轮转交错"):
            a, b, c = res[(k, mode)]
            print(f"{k:<5}{mode:<12}{a/n:>8.1%}{b/n:>8.1%}{c/n:>10.1%}"
                  f"{k:>18}{k*per_query*1000:>10.0f}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
