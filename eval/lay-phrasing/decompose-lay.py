"""说法级分解：把"没东西可对"（零字面重合）与"有东西但对不上/排不上"分开。

对每一条说法算两件事：
  · 与术语的定义条款**有没有任何 ≥2 字重合**（有 = 按字找至少有个钩子）
  · 按字找能不能把定义条款搜进前 5 / 前 20
然后交叉成表。这样才能说清"6.8% 命中"里各占多少。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
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


def subs2(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    want = {r["term"] for r in rows}
    define: dict[str, set[str]] = defaultdict(set)
    dtext: dict[str, list[set[str]]] = defaultdict(list)
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            define[t].add(cid)
            dtext[t].append(subs2(txt or ""))

    def fts_ids(q: str, k: int) -> set[str]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return set()
        try:
            cur = conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k))
            return {r[0] for r in cur.fetchall()}
        except sqlite3.OperationalError:
            return set()

    table = defaultdict(int)
    total = 0
    for r in rows:
        t = r["term"]
        if t not in define:
            continue
        tgt = define[t]
        srcs = dtext[t]
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            total += 1
            ss = subs2(tx)
            hook = any(ss & s for s in srcs)
            h5 = bool(tgt & fts_ids(tx, 5))
            h20 = bool(tgt & fts_ids(tx, 20))
            table[(hook, h5, h20)] += 1

    print(f"V2 说法共 {total} 条")
    print()
    print("| 与定义条款有 ≥2 字重合 | 进前5 | 进前20 | 条数 | 占比 |")
    print("|---|---|---|---|---|")
    for hook in (True, False):
        for h5 in (True, False):
            for h20 in (True, False):
                n = table.get((hook, h5, h20), 0)
                if n:
                    print(f"| {'有' if hook else '**无**'} | {'✅' if h5 else '❌'} | "
                          f"{'✅' if h20 else '❌'} | {n} | {n/total:.1%} |")
    nohook = sum(n for (h, a, b), n in table.items() if not h)
    hook = total - nohook
    print()
    print(f"  零重合（按字找**原理上无解**）：{nohook}/{total} = {nohook/total:.1%}")
    print(f"  有重合（至少有个钩子）：      {hook}/{total} = {hook/total:.1%}")
    h_hit = sum(n for (h, a, b), n in table.items() if h and a)
    print(f"  在「有钩子」里能进前 5 的：   {h_hit}/{hook} = {h_hit/max(hook,1):.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
