"""探针：用现成的 `bge-reranker-base` 做两段式，能不能救回"候选集太大"这个瓶颈？

链条与已知数（2026-09-25，全库 42,181 候选）：
* 语义选术语：前1 **2.5%** / 前5 **8.6%** / 前50 **25.7%**（中位 386）
  ⇒ 单靠向量，真术语大多**连前 50 都进不去**；
* 端到端（桥·轮转，k=5）：前20 从 500 候选的 32.6% 掉到 **8.4%**。

两段式要问的是：**向量取前 N（N=50）→ 交叉编码器重排 → 取前 5**，
重排能把 8.6% 提到多少？**天花板是"真术语进向量前 N"的 25.7%**（N=50）——
重排再好也不能超过它。所以本探针必须**同时**印出天花板，否则会把"重排有效"和
"上游召回不够"混成一句话。

三臂，**同一批抽样**（配对比较，不是两次独立抽样）：
  A 基线（大白话直接按字找条款）
  B 桥（向量选 top-5 术语 → 各查 FTS → 轮转合并）        —— 现状
  C 桥+重排（向量前 N 个候选术语 → 交叉编码器 → top-5）   —— 候选
另外单列**术语级**：A/B 选择臂下真术语的名次（含天花板"进前 N"）。

⚠ 交叉编码器很慢（CPU）。脚本先跑 20 条探路并**把实测速度印出来**，
按 `--limit` 控制总条数；不看速度就跑满会白等很久。
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
N_CAND = 50          # 向量粗排保留多少个术语给重排
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
    limit = 200
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    idx = TermIndex.load(CACHE)
    terms = [e.term for e in idx.entries]
    pos_of = {t: i for i, t in enumerate(terms)}
    defs = [e.definition for e in idx.entries]
    print(f"全库术语 {len(terms)} 条；本批抽样 {limit} 条说法", flush=True)

    # 靶子 = 该术语的**全部**定义条款（与 measure-term-bridge.py 同一口径）
    wanted = {json.loads(l)["term"] for l in
              CASES.read_text(encoding="utf-8").splitlines() if l.strip()}
    by_term: dict[str, set[str]] = {}
    for cid, txt in conn.execute(
            "SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_ENTRY_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in wanted:
            by_term.setdefault(t, set()).add(cid)

    rows = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    tw = {r["term"]: words(r["term"]) for r in rows}
    cases: list[tuple[str, str]] = []
    for r in rows:
        t = r["term"]
        if t not in by_term:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx and not (words(tx) & tw[t]):
                cases.append((t, tx))
    cases = cases[:limit]
    n = len(cases)
    print(f"非 A 抽样 {n} 条", flush=True)

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
    R = Q @ idx._matrix().T                                   # (n, 42181)
    top_n = np.argsort(-R, axis=1)[:, :N_CAND]                # 向量粗排前 N

    from src.core.retrieval import reranker
    model = reranker._get_model()
    print("重排模型已加载（bge-reranker-base，本机已有）", flush=True)

    # ── 单列：选择臂的名次 ────────────────────────────────────────────────
    emb_rank = np.empty(n, dtype=int)
    for c, (t, _tx) in enumerate(cases):
        emb_rank[c] = int((R[c] > R[c, pos_of[t]]).sum()) + 1

    hit = {"A5": 0, "A20": 0, "B5": 0, "B20": 0, "C5": 0, "C20": 0}
    hit["emb5"] = hit["emb20"] = 0
    sel = {"emb1": 0, "emb5": 0, "rr1": 0, "rr5": 0, "pool": 0, "rr_moved_up": 0,
           "rr_moved_down": 0}
    t0 = time.time()
    for c, (t, tx) in enumerate(cases):
        tgt = by_term[t]
        gold = pos_of[t]

        a = fts_ids(tx, PER_TERM)
        emb_terms = [terms[i] for i in top_n[c][:K_TERMS]]
        b = merge_round_robin([fts_ids(x, PER_TERM) for x in emb_terms])

        cand = top_n[c]
        scores = list(model.rerank(tx, [defs[i] for i in cand]))
        order = sorted(range(len(cand)), key=lambda j: -scores[j])
        # ⚠ `order` 里装的是**池内下标**（0..N-1），不是全局术语下标 ——
        #   第一版直接拿全局 gold 去 `order.index()` ⇒ ValueError（实测踩到，留痕）。
        cand_list = cand.tolist()
        in_pool = gold in set(cand_list)
        rr_rank = (order.index(cand_list.index(gold)) + 1) if in_pool else 0
        rr_terms = [terms[cand[j]] for j in order[:K_TERMS]]
        cc = merge_round_robin([fts_ids(x, PER_TERM) for x in rr_terms])

        hit["A5"] += int(bool(set(a[:5]) & tgt))
        hit["A20"] += int(bool(set(a[:20]) & tgt))
        hit["B5"] += int(bool(set(b[:5]) & tgt))
        hit["B20"] += int(bool(set(b[:20]) & tgt))
        hit["C5"] += int(bool(set(cc[:5]) & tgt))
        hit["C20"] += int(bool(set(cc[:20]) & tgt))
        hit["emb5"] += int(emb_rank[c] <= 5)
        hit["emb20"] += int(emb_rank[c] <= 20)
        # ── 选择臂（术语级）：比条款级灵敏得多，这里才是判"重排有没有用"的地方 ──
        sel["pool"] += int(in_pool)
        sel["emb1"] += int(emb_rank[c] <= 1)
        sel["emb5"] += int(emb_rank[c] <= 5)
        if in_pool:
            sel["rr1"] += int(rr_rank <= 1)
            sel["rr5"] += int(rr_rank <= 5)
            # 重排相对粗排把真术语往上挪了吗？（真术语**在池子里**的那些案例才可判）
            emb_in_pool_rank = int((R[c, cand] > R[c, gold]).sum()) + 1
            if rr_rank < emb_in_pool_rank:
                sel["rr_moved_up"] += 1
            elif rr_rank > emb_in_pool_rank:
                sel["rr_moved_down"] += 1
        if c == 19:
            el = time.time() - t0
            print(f"  探路 {20} 条用了 {el:.0f}s ⇒ 每条约 {el/20*1000:.0f}ms，"
                  f"预计总共 {el/20*n/60:.1f} 分钟", flush=True)
        if c % 25 == 24:
            print(f"  {c+1}/{n}  {time.time()-t0:.0f}s", flush=True)

    ceil_n = float(np.mean(emb_rank <= N_CAND))
    print()
    print("=" * 78)
    print(f"两段式重排（非 A 抽样 {n} 条；向量前 {N_CAND} 个候选术语 → 交叉编码器 → 前 {K_TERMS}）")
    print("=" * 78)
    print("  ── 术语级（判「重排有没有用」看这里，条款级太粗）")
    print(f"     天花板（真术语进向量前 {N_CAND}，即池子里）：{sel['pool']}/{n} = {ceil_n:.1%}")
    print(f"     粗排（向量）：前1 {sel['emb1']/n:.1%}  前5 {sel['emb5']/n:.1%}")
    print(f"     重排（交叉编码器，只在池子里排）：前1 {sel['rr1']/n:.1%}  前5 {sel['rr5']/n:.1%}")
    print(f"     池子内相对粗排：被**挪上去** {sel['rr_moved_up']} 条 / "
          f"被**挪下去** {sel['rr_moved_down']} 条（池子内名次变化）")
    print()
    print(f"  ── 条款级")
    print(f"     {'臂':<30}{'前5':>9}{'前20':>9}")
    print(f"     {'A 基线（大白话直接搜）':<30}{hit['A5']/n:>9.1%}{hit['A20']/n:>9.1%}")
    print(f"     {'B 桥·向量选术语（现状）':<30}{hit['B5']/n:>9.1%}{hit['B20']/n:>9.1%}")
    print(f"     {'C 桥·重排后选术语':<30}{hit['C5']/n:>9.1%}{hit['C20']/n:>9.1%}")
    print()
    print("  ⚠ 这是**非 A 子集**（基线天然接近 0）⇒ 报数必须带这个分母。")
    print("  ⚠ 若 C 明显好于 B 但仍低于天花板 ⇒ 瓶颈在**上游召回**，下一刀该扩 N 或换粗排。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
