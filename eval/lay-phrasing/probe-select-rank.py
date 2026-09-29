"""探针：把"选术语"这一步**单独**量出来，候选集 500 vs 42,181 各一次。

为什么必须有这一刀：`measure-term-bridge.py --all` 量出端到端**塌了**
（前 20：500 候选 29.7% → 全库候选 **7.0%**）。但端到端把"选术语"和"拿术语去搜"
两件事混在一起，看不出损失落在哪一步。这里只问一句：

    真术语，在语义排序里排第几？（候选集分别取 500 / 42,181）

口径：
* 说法集、非 A 判定、靶子（该术语的全部定义条款）与 `measure-term-bridge.py` 完全一致；
* "500" = 说法文件里出现过的那些术语（**每个用例的正确答案都在候选集里**），
  "全库" = 库内全部术语 —— 两次都是"答案在候选集内"，差别只有干扰项数量（84×）；
* 术语表示 = 定义正文（实测优于术语名），生产同款 `bge-small-zh-v1.5`。

一个矩阵乘算完：`R = Q @ Tᵀ`，真术语的名次 = "比它分高的候选个数 + 1"。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import numpy as np                                          # noqa: E402

from src.core.retrieval import embedder                      # noqa: E402
from src.core.retrieval.term_bridge import TERM_ENTRY_RE, TermIndex  # noqa: E402
from src.core.text_utils import segment_for_fts               # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass

    idx = TermIndex.load(CACHE)
    print(f"全库术语 {len(idx)} 条", flush=True)
    terms = [e.term for e in idx.entries]
    pos_of = {t: i for i, t in enumerate(terms)}

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}
    narrow = [i for i, t in enumerate(terms) if t in wanted]
    print(f"500 候选口径 = 说法文件里出现过的 {len(narrow)} 条", flush=True)

    tw = {t: words(t) for t in wanted}
    cases: list[tuple[str, str]] = []
    for r in rows:
        t = r["term"]
        if t not in pos_of or t not in tw:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx and not (words(tx) & tw[t]):        # 非 A：与术语**词级**不重合
                cases.append((t, tx))
    print(f"非 A 说法 {len(cases)} 条", flush=True)

    t0 = time.time()
    Q = np.asarray([embedder.embed_query(tx) for _t, tx in cases], dtype=np.float64)
    Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
    T = idx._matrix()                                  # 已归一化（float64）
    print(f"嵌入 {time.time()-t0:.0f}s，开始算 {Q.shape[0]}×{T.shape[0]} 相似度", flush=True)

    R = Q @ T.T                                        # (n_cases, n_terms)
    gold = np.asarray([pos_of[t] for t, _tx in cases])
    gold_score = R[np.arange(len(cases)), gold]

    for label, cols in (("500 候选", np.asarray(narrow)),
                        ("全库 42,181 候选", np.arange(len(terms)))):
        sub = R[:, cols]
        gs = R[np.arange(len(cases)), gold]            # 真术语的分（与子集无关）
        rank = (sub > gs[:, None]).sum(axis=1) + 1     # 名次（同分算前）
        print()
        print(f"── {label}（{len(cols)} 条）")
        for k in (1, 5, 10, 20, 50):
            print(f"   真术语进前 {k:<3}: {(rank <= k).mean():6.1%}")
        print(f"   中位名次 {int(np.median(rank))} / {len(cols)}"
              f"（随机中位 {len(cols)//2}）")
        if label.startswith("500"):
            r500 = rank
        else:
            rfull = rank
    both = np.asarray([pos_of[t] for t, _tx in cases])
    in_narrow = np.isin(both, np.asarray(narrow))
    print()
    print(f"── 只在 500 候选里排名靠前、换全库就掉的（前 5 → 跌出前 5）："
          f"{int(((r500 <= 5) & (rfull > 5)).sum())} 条")
    print(f"   任何口径下真术语都在候选集内：500 {in_narrow.mean():.0%}，全库 100%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
