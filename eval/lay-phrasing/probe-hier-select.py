"""探针：**先选文档、再在文档内选术语**能不能把"选术语"从 8.6% 救回来？

背景（同批实测）：语义选术语在 **500 候选**上 top-1 22.2% / top-5 47.3%，
换到**全库 42,181 候选**塌成 **2.5% / 8.6%**（中位名次 386）。端到端因此从
前20 29.7% 掉到 7.0%。⇒ 瓶颈全在"候选集太大"。

这一刀问：**先按文档粗筛**（术语天然属于某一篇），候选集能缩到多小、真术语还找不找得到？
三层量：
  1. **文档级**：真术语所在文档，在文档排序里进前 D 的准确率（文档数比术语数少得多）；
  2. **文档内**：已知正确文档时，真术语在该文档自己的术语里进前 K 的比例（**上界**）；
  3. **级联**（真正要看的）：取文档前 D ⇒ 候选集 = 这些文档里**全部**术语
     ⇒ 在缩小后的候选集里重排名次。D 越大候选集越大。

口径与 `probe-select-rank.py` 完全一致（说法集、非 A 判定、术语表示=定义正文）。
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import numpy as np                                          # noqa: E402

from src.core.retrieval import embedder                      # noqa: E402
from src.core.retrieval.term_bridge import TermIndex          # noqa: E402
from src.core.text_utils import segment_for_fts               # noqa: E402

CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")
DS = (1, 3, 5, 10, 20)


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    idx = TermIndex.load(CACHE)
    terms = [e.term for e in idx.entries]
    docs = [e.doc_id for e in idx.entries]
    pos_of = {t: i for i, t in enumerate(terms)}
    doc_of_term = {t: d for t, d in zip(terms, docs)}

    by_doc: dict[str, list[int]] = defaultdict(list)
    for i, d in enumerate(docs):
        by_doc[d].append(i)
    doc_list = sorted(by_doc)
    doc_idx = {d: j for j, d in enumerate(doc_list)}
    print(f"全库术语 {len(terms)} 条，分布在 {len(doc_list)} 篇文档里"
          f"（平均每篇 {len(terms)/len(doc_list):.1f} 条术语）", flush=True)

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    tw = {r["term"]: words(r["term"]) for r in rows}
    cases: list[tuple[str, str]] = []
    for r in rows:
        t = r["term"]
        if t not in pos_of:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx and not (words(tx) & tw[t]):
                cases.append((t, tx))
    print(f"非 A 说法 {len(cases)} 条", flush=True)

    t0 = time.time()
    Q = np.asarray([embedder.embed_query(tx) for _t, tx in cases], dtype=np.float64)
    Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
    T = idx._matrix()
    R = Q @ T.T
    gold = np.asarray([pos_of[t] for t, _tx in cases])
    print(f"相似度算完 {time.time()-t0:.0f}s", flush=True)

    # ── 层 1：文档级（按该文档内术语的最高分）─────────────────────────────
    n_doc = len(doc_list)
    D = np.full((len(cases), n_doc), -2.0)
    for j, d in enumerate(doc_list):
        D[:, j] = R[:, by_doc[d]].max(axis=1)
    gold_doc = np.asarray([doc_idx[doc_of_term[t]] for t, _tx in cases])
    gd = D[np.arange(len(cases)), gold_doc]
    doc_rank = (D > gd[:, None]).sum(axis=1) + 1

    print()
    print("── 层 1：真术语所在**文档**的名次（候选文档 %d 篇）" % n_doc)
    for k in DS:
        print(f"   进前 {k:<3}: {(doc_rank <= k).mean():6.1%}")
    print(f"   中位名次 {int(np.median(doc_rank))}（随机中位 {n_doc//2}）")

    # ── 层 2：已知正确文档时，文档内排名（上界）───────────────────────────
    inner = []
    for c, (t, _tx) in enumerate(cases):
        cols = by_doc[doc_of_term[t]]
        mine = R[c, pos_of[t]]
        inner.append(int((R[c, cols] > mine).sum()) + 1)
    inner = np.asarray(inner)
    print()
    print("── 层 2：**已知正确文档**时，真术语在文档内术语里的名次（上界）")
    for k in (1, 3, 5, 10):
        print(f"   进前 {k:<3}: {(inner <= k).mean():6.1%}")

    # ── 层 3：级联（取文档前 D ⇒ 候选集 = 这些文档的全部术语 ⇒ 重排名次）──
    order = np.argsort(-D, axis=1)
    print()
    print("── 层 3：级联 · 取文档前 D 后再在候选集内排名")
    print(f"   {'D':>3}{'候选术语数(中位)':>18}{'前1':>9}{'前5':>9}{'前20':>9}")
    for d in DS:
        picked_docs = order[:, :d]
        cand_cols = [np.concatenate([by_doc[doc_list[j]] for j in row]) for row in picked_docs]
        top1 = top5 = top20 = 0
        sizes = []
        for c in range(len(cases)):
            cols = cand_cols[c]
            sizes.append(len(cols))
            g = pos_of[cases[c][0]]
            if g not in set(cols.tolist()):        # 正确文档没进前 D ⇒ 无从谈起
                continue
            rank = int((R[c, cols] > R[c, g]).sum()) + 1
            top1 += int(rank <= 1)
            top5 += int(rank <= 5)
            top20 += int(rank <= 20)
        m = len(cases)
        print(f"   {d:>3}{int(np.median(sizes)):>18}{top1/m:>9.1%}{top5/m:>9.1%}{top20/m:>9.1%}")
    print()
    print("  ⚠ 层 3 的候选集是**这些文档里的全部术语**（不是全部术语），")
    print("     与单层全库口径的可比性在于：**真术语必须在候选集内**才可能命中，")
    print("     正确文档漏在 D 之外的那些案例直接算未命中（不偷偷剔除）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
