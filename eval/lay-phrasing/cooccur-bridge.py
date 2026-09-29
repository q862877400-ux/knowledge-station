"""P1 第一刀 · 可行性：**只用库内共现**能不能把大白话接到术语上？

背景（本会话实测）：
  * 41.2% 的大白话与定义条款本身有词重合（A 档，本来就能对上）；
  * 47.4% 只在"那篇文档"里有词、定义条款里没有（B 档）——**而文档级可达不等于条款可达**
    （两段式实测：全局 21.7% → 文档内 26.7%，只多 5 个点）；
  * 11.5% 连那篇文档都没有（C 档）。

⇒ 出路必须是"把大白话里的词**接到术语/定义**上"，而不是接到文档上。
本脚本量这条路的**非循环**可行性：**不看生成数据里的配对**，
只问"这个词与该术语在真库里**同现过没有**"（FTS AND）。

判据：非 A 档里，**有多少条含至少一个"与术语同现过"的词**。
若高 ⇒ 库内可自建桥（不需要外部百科）；若低 ⇒ 必须外部资源。
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
from src.core.text_utils import segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
TERM_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*)?\s*"
    r"([\u4e00-\u9fff][\u4e00-\u9fff（）()·、\-]{2,15}?)\s*"
    r"([A-Za-z][A-Za-z \-/(),]{2,60}?)\s*"
    r"(?=[\u4e00-\u9fff（])"
)
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    want = {r["term"] for r in rows}
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

    define: dict[str, set[str]] = defaultdict(set)
    id_words: dict[str, set[str]] = {}
    print("扫定义条款…", flush=True)
    for cid, txt in conn.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in want:
            define[t].add(cid)
            id_words[cid] = words(txt)

    # 收集"非 A 档"的说法 + 它们的候选词（不在定义条款里的词）
    cases: list[tuple[str, str, list[str]]] = []
    a_n = 0
    for r in rows:
        t = r["term"]
        if t not in define:
            continue
        cw: set[str] = set()
        for c in define[t]:
            cw |= id_words.get(c, set())
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            ws = words(tx)
            if ws & cw:
                a_n += 1
                continue
            # 候选桥接词：phrasing 里的实词，按长度降序（长的更像专业词）
            cand = sorted(ws - cw, key=lambda w: (-len(w), w))[:4]
            if cand:
                cases.append((t, tx, cand))
    print(f"A 档 {a_n} 条；非 A 档待测 {len(cases)} 条", flush=True)

    # 术语的 FTS 短语形式（缓存）
    term_expr: dict[str, str] = {}
    for t in want:
        seg = segment_for_fts(t)
        term_expr[t] = f'"{seg}"' if seg.strip() else ""

    cache: dict[tuple[str, str], bool] = {}

    def cooccur(t: str, w: str) -> bool:
        key = (t, w)
        if key in cache:
            return cache[key]
        te = term_expr.get(t, "")
        we = f'"{segment_for_fts(w)}"'
        ok = False
        if te:
            try:
                n = conn.execute(
                    "SELECT count(*) FROM clause_fts WHERE clause_fts MATCH ?",
                    (f"{te} AND {we}",)).fetchone()[0]
                ok = n > 0
            except sqlite3.OperationalError:
                ok = False
        cache[key] = ok
        return ok

    print("逐条测库内共现（缓存去重）…", flush=True)
    t0 = time.time()
    hit = 0
    examples: list[tuple[str, str, str]] = []
    for i, (t, tx, cand) in enumerate(cases, 1):
        found = None
        for w in cand:
            if cooccur(t, w):
                found = w
                break
        if found:
            hit += 1
            if len(examples) < 8:
                examples.append((t, tx, found))
        if i % 200 == 0:
            print(f"  {i}/{len(cases)}  {time.time()-t0:.0f}s  缓存 {len(cache)}", flush=True)

    n = len(cases)
    print()
    print("=" * 78)
    print(f"非 A 档 {n} 条：**含至少一个「与术语在库里同现过」的词**的有多少？")
    print("=" * 78)
    print(f"  有：**{hit}/{n} = {hit/max(n,1):.1%}**")
    print(f"  无：{n-hit}/{n} = {(n-hit)/max(n,1):.1%}  ⇒ 这部分只能靠**外部**词典/百科")
    print(f"  （去重后实际问过的 (术语,词) 对：{len(cache)}；耗时 {time.time()-t0:.0f}s）")
    print()
    print("  例（术语 ← 大白话里的哪个词与它同现过）：")
    for t, tx, w in examples:
        print(f"    [{t}] ← 「{w}」   原话：{tx[:32]}")
    print()
    print("  ⚠ 口径：这是**可行性上界**——'同现过'只说明库里存在把这两者连起来的证据，")
    print("     不等于'拿它当桥就能把定义条款搜出来'。后者要另测（扩展查询后跑一遍）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
