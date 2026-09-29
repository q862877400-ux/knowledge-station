"""独立复现另一个 AI 的"P1 端到端：翻译臂前20 3.6% → 16.2%（4.53×）"。

它的说法（fdd37ca，**只改了文档、没提交实现**）：
  A 基线（大白话直接搜）        前5 1.6%(26) / 前20 3.6%(59)
  B 翻译（语义选中文术语→拿术语搜） 前5 12.3%(203) / 前20 16.2%(267)
  C 混合                        前5 8.7% / 前20 14.6%
  样本：1651 条非 A 说法；靶子：术语的定义条款；只用按字找。

本脚本**从零重建三臂**（不用它的脚本——它在 var/tmp，且未入库），并同时给出：
  · 非 A 子集上的三臂（与它可比）
  · **全部 1832 条**上的三臂（防"只挑最难的子集"造成倍数虚高）
  · 术语级（任一说法命中即算）的数，与我此前 21.7% 的口径对齐
只读真库。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.retrieval import embedder  # noqa: E402
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
KS = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(t: str) -> set[str]:
    return {w for w in segment_for_fts(t or "").split() if CJK.match(w)}


def cos(a, b) -> float:
    s = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return s / (na * nb) if na and nb else 0.0


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}

    conn = sqlite3.connect(f"file:{KS}?mode=ro", uri=True)
    define: dict[str, set[str]] = defaultdict(set)
    deftext: dict[str, str] = {}
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in tw:
            define[t].add(cid)
            deftext.setdefault(t, re.sub(r"\s+", " ", txt or "").strip())
    print(f"术语 {len(terms)}；有定义条款 {len(define)}", flush=True)

    def hit(expr_text: str, tgt: set[str], k: int) -> bool:
        expr = fts_match_expr(expr_text)
        if not expr.strip():
            return False
        try:
            got = {r[0] for r in conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()}
        except sqlite3.OperationalError:
            return False
        return bool(tgt & got)

    # 语义选择：术语用"定义正文"表示（我实测最好那一档）
    tvec = embedder.embed_batch([deftext.get(t, t) for t in terms])

    # 建批次：非 A 子集 + 全部
    cases = []          # (term, text, is_nonA)
    for r in rows:
        t = r["term"]
        if t not in define:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            cases.append((t, tx, not (words(tx) & tw[t])))
    nonA = [c for c in cases if c[2]]
    print(f"说法 {len(cases)} 条，其中非 A {len(nonA)} 条", flush=True)

    t0 = time.time()
    qvecs = embedder.embed_batch([tx for _t, tx, _n in cases])
    print(f"说法嵌入 {len(qvecs)} 条 {time.time()-t0:.0f}s", flush=True)

    # 每条说法预先算好：语义 top-1 术语
    top1 = []
    for qv in qvecs:
        best = max(range(len(terms)), key=lambda i: cos(qv, tvec[i]))
        top1.append(terms[best])

    res = {("nonA", a, k): 0 for a in "ABC" for k in (5, 20)}
    res.update({("all", a, k): 0 for a in "ABC" for k in (5, 20)})
    term_hit = {("nonA", a, k): defaultdict(bool) for a in "BC" for k in (5, 20)}
    t1 = time.time()
    for (t, tx, isn), sel in zip(cases, top1):
        grp = "nonA" if isn else "all"
        groups = [grp] if isn else ["all"]
        tgt = define[t]
        for k in (5, 20):
            a = hit(tx, tgt, k)
            b = hit(sel, tgt, k)
            c = hit(tx + " " + sel, tgt, k)
            for g in groups:
                res[(g, "A", k)] += int(a)
                res[(g, "B", k)] += int(b)
                res[(g, "C", k)] += int(c)
            if isn:
                term_hit[("nonA", "B", k)][t] |= b
                term_hit[("nonA", "C", k)][t] |= c
    print(f"检索 {time.time()-t1:.0f}s", flush=True)

    for g, label, n in (("nonA", "非 A 子集（按说法）", len(nonA)),
                        ("all", "全部 1832 条（按说法）", len(cases))):
        print()
        print("=" * 78)
        print(f"{label}  n={n}")
        print("=" * 78)
        for k in (5, 20):
            a = res[(g, "A", k)]; b = res[(g, "B", k)]; c = res[(g, "C", k)]
            print(f"  前{k:>2}： A 基线 {a/n:>6.1%}   B 翻译 {b/n:>6.1%}（{b/max(a,1):.2f}×）"
                  f"   C 混合 {c/n:>6.1%}")
    print()
    print("  术语级（非 A 子集里，任一说法命中即算该术语命中）：")
    n_term = len({t for _t, _x, isn in nonA if isn for t in [ _t ]}) if False else len(
        {t for t, _x, isn in nonA if isn})
    for k in (5, 20):
        for a in "BC":
            v = sum(1 for t in term_hit[("nonA", a, k)] if term_hit[("nonA", a, k)][t])
            print(f"    前{k:>2} {a}：{v}/{n_term} = {v/max(n_term,1):.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
