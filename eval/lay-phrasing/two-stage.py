"""验证「先找对文档、再在文档内定位」这条策略到底成不成。

两段式（都用生产口径的 FTS，不用向量，快）：
  第一段：大白话 → FTS 前 100 → 按名次取前 D 个**不同文档**
  第二段：在这 D 个文档**各自内部**再搜一次 → 各取前 5 条 → 并起来
判据：并起来里面有没有**定义该术语的那条条款**。

对照：不分段（全局一次）的条款级命中率，即 P1/P2 一直用的那个数。
若两段式明显更高 ⇒ 这条策略成立，而且**不需要任何同义词资源**。
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
from src.core.text_utils import fts_match_expr  # noqa: E402

D = REPO / "var" / "tmp"
DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
DOCS = (1, 3, 5)


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    want = {r["term"] for r in rows}
    define: dict[str, set[str]] = defaultdict(set)
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if m and m.group(1).strip().strip("（）()·、-—") in want:
            define[m.group(1).strip().strip("（）()·、-—")].add(cid)

    def top(q: str, k: int, doc: str | None = None) -> list[tuple[str, str]]:
        """返回 [(clause_id, doc_id), ...]"""
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
    for i, r in enumerate(rows, 1):
        t = r["term"]
        tgt = define.get(t)
        if not tgt:
            continue
        texts = [x["text"] for x in (r.get("lay") or []) if x.get("text")]
        if not texts:
            continue
        n += 1
        # 对照：全局一次
        for k in (5, 20):
            hit = False
            for tx in texts:
                if tgt & {c for c, _d in top(tx, k)}:
                    hit = True
                    break
            base[k] += int(hit)
        # 两段式：第一段取候选文档，第二段在文档内定位
        cand_docs: dict[int, list[str]] = {d: [] for d in DOCS}
        for tx in texts:
            seen = []
            for _c, doc in top(tx, 100):
                if doc not in seen:
                    seen.append(doc)
                if len(seen) >= max(DOCS):
                    break
            for d in DOCS:
                for doc in seen[:d]:
                    if doc not in cand_docs[d]:
                        cand_docs[d].append(doc)
        for d in DOCS:
            hit = False
            for doc in cand_docs[d]:
                for tx in texts:
                    if tgt & {c for c, _dd in top(tx, 5, doc=doc)}:
                        hit = True
                        break
                if hit:
                    break
            staged[d] += int(hit)
        if i % 100 == 0:
            print(f"  {i}/{len(rows)}  {time.time()-t0:.0f}s")

    print()
    print("=" * 78)
    print(f"有定义的术语 {n} 个（每条 4 条大白话，任一命中即算）")
    print("=" * 78)
    print(f"{'做法':<34}{'条款级命中':>16}")
    print(f"{'对照·全局一次 前5':<34}{base[5]:>8} ({base[5]/n:>5.1%})")
    print(f"{'对照·全局一次 前20':<34}{base[20]:>8} ({base[20]/n:>5.1%})")
    for d in DOCS:
        print(f"{'两段式·先取前 ' + str(d) + ' 篇文档再文档内取5':<34}"
              f"{staged[d]:>8} ({staged[d]/n:>5.1%})")
    print()
    best = max(staged.values())
    print(f"  两段式最好 {best/n:.1%} vs 全局前20 {base[20]/n:.1%}"
          f" ⇒ {'策略成立' if best > base[20] else '策略不成立'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
