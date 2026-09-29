"""探针：给**查询**加上 bge 官方建议的检索指令前缀，全库候选下的"选术语"能涨多少？

为什么是这一刀：
* `probe-select-rank.py` 量出语义选术语在全库 42,181 候选上 top-1 **2.5%** / top-5 **8.6%**
  ——这是当前唯一的大瓶颈（端到端因此只有 7.0% 前 20）。改候选集那几条（先选文档）已实测无效。
* `src/core/retrieval/embedder.py::embed_query` **什么都没加**（直接把原句喂模型）。
  而 bge 中文系列对**检索型查询**有官方建议的指令前缀（文档侧不加）。
* **改这一处的代价极小**：文档侧向量**一个字节都不用动**（离线那 531s 不用重跑），
  只重嵌查询。所以先量它，性价比最高。

口径：与 `probe-select-rank.py` 逐字一致（同一批 1,651 条非 A 说法、同一套术语向量、
同一份靶子），只换查询侧的写法。
"""
from __future__ import annotations

import json
import re
import sys
import time
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

#: bge 中文系列的官方检索指令（查询侧）。**出处**：BAAI/bge-small-zh-v1.5 模型卡
#: 的 "Instruction" 段（英文版为 "Represent this sentence for searching relevant passages: "）。
INSTR = "为这个句子生成表示以用于检索相关文章："


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
    pos_of = {t: i for i, t in enumerate(terms)}
    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}
    narrow = np.asarray([i for i, t in enumerate(terms) if t in wanted])

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
    print(f"非 A 说法 {len(cases)} 条；候选：500 / {len(terms)}", flush=True)

    T = idx._matrix()
    gold = np.asarray([pos_of[t] for t, _tx in cases])
    gs = None

    for label, mk in (("① 原句（现状）", lambda t: t),
                      ("② 加官方指令前缀", lambda t: INSTR + t)):
        t0 = time.time()
        Q = np.asarray([embedder.embed_query(mk(tx)) for _t, tx in cases], dtype=np.float64)
        Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
        R = Q @ T.T
        g = R[np.arange(len(cases)), gold]
        print()
        print(f"── {label}（嵌入 {time.time()-t0:.0f}s）")
        for name, cols in (("500 候选", narrow), ("全库 %d 候选" % len(terms), None)):
            sub = R if cols is None else R[:, cols]
            rank = (sub > g[:, None]).sum(axis=1) + 1
            n_c = len(terms) if cols is None else len(cols)
            print(f"   {name:<16} 前1 {np.mean(rank<=1):6.1%}  前5 {np.mean(rank<=5):6.1%}"
                  f"  前10 {np.mean(rank<=10):6.1%}  前20 {np.mean(rank<=20):6.1%}"
                  f"  中位 {int(np.median(rank))}/{n_c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
