"""对照实验：同一套两段式重排，在 **A 档**（说法与定义条款**有**实词重合）上是什么结果？

为什么必须有这一刀（2026-09-25）：
`probe-rerank-two-stage.py` 量出重排**无效且略负**（非 A 档 200 条：粗排前5 5.5% →
重排 4.0%；池内挪上去 12 / 挪下去 18）。我给的**解释**是：
非 A 档按定义就是"说法与正确术语的定义**零实词重合**"⇒ 正确答案在"判相关性"的重排器眼里
天生像不相关的那一类。**但那只是解释，没有对照**——不知道是"任务形态不匹配"还是"模型不行"。

判据（先写下，再看结果，免得事后编）：
* 若 A 档上重排**有效**（前5 升、池内挪上去 > 挪下去）而非 A 档无效
  ⇒ **支持"任务形态不匹配"**：重排器吃的是词面相关性，而困难集恰恰没有词面。
* 若 A 档上重排**也无效**（与粗排持平或更差）
  ⇒ **"模型在这个语料/这对长短文本上不管用"**才是主因，跟零重合无关。

⚠ 本脚本**不改** `probe-rerank-two-stage.py`（那是已被复核任务书引用的取证件），
只把它的逻辑复制一份、加一个"取哪一档说法"的开关。两边的非 A 数应当逐格相同 ——
**这一条本身就是自检**（若不同，说明我复制时改了东西）。

用法：python var/tmp/probe-rerank-control.py --subset A --limit 200
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
from src.core.retrieval.term_bridge import (                  # noqa: E402
    TERM_ENTRY_RE, TermIndex, merge_round_robin,
)
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")
N_CAND = 50
K_TERMS = 5
PER_TERM = 20


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    subset = "A"
    limit = 200
    if "--subset" in sys.argv:
        subset = sys.argv[sys.argv.index("--subset") + 1]
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    assert subset in ("A", "nonA", "defA", "defA_nonname"), subset

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    idx = TermIndex.load(CACHE)
    terms = [e.term for e in idx.entries]
    pos_of = {t: i for i, t in enumerate(terms)}
    defs = [e.definition for e in idx.entries]

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    wanted = {r["term"] for r in rows}
    by_term: dict[str, set[str]] = {}
    # ⚠ **两个口径分开存**（2026-09-25 自查发现）：判"非 A"究竟该比**术语名**还是
    #   **定义条款正文**？复算脚本用的是**术语名**（非 A = 1,651）；而文档 §二 的 A 档
    #   用的是**定义条款正文**（A = 754 ⇒ 非 A = 1,078）。两者不是一回事：
    #   实测 573 条"定义正文有重合、术语名没有"。这里两个都算，档位用开关选。
    def_words: dict[str, set[str]] = {}
    for (cid, txt) in conn.execute(
            "SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_ENTRY_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in wanted:
            by_term.setdefault(t, set()).add(cid)          # 靶子＝条款 id
            def_words.setdefault(t, set()).update(words(txt))

    tw = {r["term"]: words(r["term"]) for r in rows}
    cases: list[tuple[str, str]] = []
    for r in rows:
        t = r["term"]
        if t not in by_term:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            wq = words(tx)
            name_hit = bool(wq & tw[t])
            def_hit = bool(wq & def_words[t])
            keep = {"A": name_hit,
                    "nonA": not name_hit,
                    "defA": def_hit,
                    "defA_nonname": def_hit and not name_hit}[subset]
            if keep:
                cases.append((t, tx))
    cases = cases[:limit]
    n = len(cases)
    print(f"档={subset}  抽样 {n} 条（全库术语 {len(terms)} 条作候选）", flush=True)

    def fts_ids(text: str, k: int) -> list[str]:
        expr = fts_match_expr(text)
        if not expr.strip():
            return []
        try:
            return [r[0] for r in conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()]
        except sqlite3.OperationalError:
            return []

    Q = np.asarray([embedder.embed_query(tx) for _t, tx in cases], dtype=np.float64)
    Q /= np.maximum(np.linalg.norm(Q, axis=1, keepdims=True), 1e-12)
    R = Q @ idx._matrix().T
    top_n = np.argsort(-R, axis=1)[:, :N_CAND]
    emb_rank = np.asarray([int((R[c] > R[c, pos_of[t]]).sum()) + 1
                           for c, (t, _tx) in enumerate(cases)])

    from src.core.retrieval import reranker
    model = reranker._get_model()
    print("重排模型已加载", flush=True)

    hit = {"A5": 0, "A20": 0, "B5": 0, "B20": 0, "C5": 0, "C20": 0}
    sel = {"pool": 0, "emb1": 0, "emb5": 0, "rr1": 0, "rr5": 0,
           "up": 0, "down": 0}
    t0 = time.time()
    for c, (t, tx) in enumerate(cases):
        tgt = by_term[t]
        gold = pos_of[t]
        a = fts_ids(tx, PER_TERM)
        b = merge_round_robin([fts_ids(x, PER_TERM)
                               for x in [terms[i] for i in top_n[c][:K_TERMS]]])
        cand = top_n[c]
        cand_list = cand.tolist()
        scores = list(model.rerank(tx, [defs[i] for i in cand]))
        order = sorted(range(len(cand)), key=lambda j: -scores[j])
        in_pool = gold in set(cand_list)
        rr_rank = (order.index(cand_list.index(gold)) + 1) if in_pool else 0
        cc = merge_round_robin([fts_ids(x, PER_TERM)
                                for x in [terms[cand[j]] for j in order[:K_TERMS]]])

        hit["A5"] += int(bool(set(a[:5]) & tgt))
        hit["A20"] += int(bool(set(a[:20]) & tgt))
        hit["B5"] += int(bool(set(b[:5]) & tgt))
        hit["B20"] += int(bool(set(b[:20]) & tgt))
        hit["C5"] += int(bool(set(cc[:5]) & tgt))
        hit["C20"] += int(bool(set(cc[:20]) & tgt))
        sel["pool"] += int(in_pool)
        sel["emb1"] += int(emb_rank[c] <= 1)
        sel["emb5"] += int(emb_rank[c] <= 5)
        if in_pool:
            sel["rr1"] += int(rr_rank <= 1)
            sel["rr5"] += int(rr_rank <= 5)
            emb_pool_rank = int((R[c, cand] > R[c, gold]).sum()) + 1
            if rr_rank < emb_pool_rank:
                sel["up"] += 1
            elif rr_rank > emb_pool_rank:
                sel["down"] += 1
        if c == 19:
            el = time.time() - t0
            print(f"  探路 20 条 {el:.0f}s ⇒ 总共约 {el/20*n/60:.1f} 分钟", flush=True)
        if c % 50 == 49:
            print(f"  {c+1}/{n}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"对照：档={subset}，前 {N_CAND} 个候选术语 → 交叉编码器 → 前 {K_TERMS}（{n} 条）")
    print("=" * 78)
    print(f"  ── 术语级")
    print(f"     天花板（真术语在池子里）：{sel['pool']}/{n} = {sel['pool']/n:.1%}")
    print(f"     粗排（向量）：前1 {sel['emb1']/n:.1%}  前5 {sel['emb5']/n:.1%}")
    print(f"     重排（交叉编码器）：前1 {sel['rr1']/n:.1%}  前5 {sel['rr5']/n:.1%}")
    print(f"     池内相对粗排：挪上去 {sel['up']} / 挪下去 {sel['down']}")
    print(f"  ── 条款级")
    print(f"     {'A 基线（大白话直接搜）':<30}{hit['A5']/n:>9.1%}{hit['A20']/n:>9.1%}")
    print(f"     {'B 桥·向量选术语':<30}{hit['B5']/n:>9.1%}{hit['B20']/n:>9.1%}")
    print(f"     {'C 桥·重排后选术语':<30}{hit['C5']/n:>9.1%}{hit['C20']/n:>9.1%}")
    print()
    print("  判据（预先写下，别事后编）：A 档上重排若有效 ⇒ 支持「任务形态不匹配」；")
    print("  若 A 档上也无效 ⇒ 「模型在这对长短文本上不管用」才是主因，与零重合无关。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
