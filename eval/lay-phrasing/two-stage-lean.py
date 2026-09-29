"""两段式策略的**轻量版**：抽样 200 个术语，只测 D ∈ {1,3}。

问题：大白话"先找对文档、再在文档内定位"这条策略成不成立？
（上一轮已量出：前 5 名里，条款级命中 7.4%，而**文档级** 42.6% ⇒ 通常找得对文档、找不到那一条。）

做法（两段都用生产口径 FTS，不用向量）：
  第一段：大白话 → FTS 前 100 → 按名次取前 D 个**不同文档**
  第二段：在这 D 个文档**各自内部**再搜一次 → 各取前 5 条 → 并起来
对照：不分段的全局条款级命中。

⚠ 这是**抽样**（200/458），不是全量；结论要写明这一点。
只读真库。
"""
from __future__ import annotations

import json
import random
import re
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import fts_match_expr  # noqa: E402

D = REPO / "var" / "tmp"
DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
import os
SAMPLE = int(os.environ.get('TS_SAMPLE', '60'))
DOCS = (1, 3)


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    # 只取有说法的（42 个写空的没东西可搜），再**固定种子**抽样（可复现）
    have = [r for r in rows if [x["text"] for x in (r.get("lay") or []) if x.get("text")]]
    random.seed(20260925)
    sample = random.sample(have, min(SAMPLE, len(have)))
    print(f"有说法的术语 {len(have)} 个；**固定种子抽样 {len(sample)} 个**（seed=20260925）")

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    want = {r["term"] for r in sample}
    define: dict[str, set[str]] = defaultdict(set)
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if m and m.group(1).strip().strip("（）()·、-—") in want:
            define[m.group(1).strip().strip("（）()·、-—")].add(cid)

    def top(q: str, k: int, doc: str | None = None) -> list[tuple[str, str]]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return []
        sql = ("SELECT cr.clause_revision_id, cr.doc_id FROM clause_fts "
               "JOIN clause_revision cr ON cr.clause_revision_id = clause_fts.clause_revision_id "
               "WHERE clause_fts MATCH ?")
        params: list = [expr]
        if doc:
            sql += " AND cr.doc_id = ?"
            params.append(doc)
        sql += " ORDER BY bm25(clause_fts) LIMIT ?"
        params.append(k)
        try:
            return conn.execute(sql, tuple(params)).fetchall()
        except sqlite3.OperationalError:
            return []

    base = {5: 0, 20: 0}
    staged = {d: 0 for d in DOCS}
    n = 0
    t0 = time.time()
    for i, r in enumerate(sample, 1):
        t = r["term"]
        tgt = define.get(t)
        if not tgt:
            continue
        texts = [x["text"] for x in (r.get("lay") or []) if x.get("text")]
        n += 1
        for k in (5, 20):
            for tx in texts:
                if tgt & {c for c, _d in top(tx, k)}:
                    base[k] += 1
                    break
        cand: dict[int, list[str]] = {d: [] for d in DOCS}
        for tx in texts:
            seen: list[str] = []
            for _c, doc in top(tx, 100):
                if doc not in seen:
                    seen.append(doc)
                if len(seen) >= max(DOCS):
                    break
            for d in DOCS:
                for doc in seen[:d]:
                    if doc not in cand[d]:
                        cand[d].append(doc)
        for d in DOCS:
            hit = False
            for doc in cand[d]:
                for tx in texts:
                    if tgt & {c for c, _dd in top(tx, 5, doc=doc)}:
                        hit = True
                        break
                if hit:
                    break
            staged[d] += int(hit)
        if i % 50 == 0:
            print(f"  {i}/{len(sample)}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"抽样 {n} 个术语（每条 4 条大白话，任一命中即算）")
    print("=" * 78)
    print(f"{'做法':<40}{'条款级命中':>16}")
    print(f"{'对照·全局一次取前 5':<40}{base[5]:>8} ({base[5]/n:>5.1%})")
    print(f"{'对照·全局一次取前 20':<40}{base[20]:>8} ({base[20]/n:>5.1%})")
    for d in DOCS:
        label = f"两段式·先取前 {d} 篇文档，再文档内取 5"
        print(f"{label:<40}{staged[d]:>8} ({staged[d]/n:>5.1%})")
    print()
    best_d = max(staged, key=lambda x: staged[x])
    print(f"  两段式最好 {staged[best_d]/n:.1%}（前 {best_d} 篇） vs 全局前 20 {base[20]/n:.1%}")
    print(f"  ⇒ 相对提升 {staged[best_d]/max(base[20],1):.2f}×"
          f" ⇒ {'策略成立' if staged[best_d] > base[20] else '**策略不成立**'}")
    Path(D / "two-stage-lean.json").write_text(json.dumps(
        {"n": n, "base5": base[5], "base20": base[20],
         "staged": {str(k): v for k, v in staged.items()}}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
