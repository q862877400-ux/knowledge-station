"""P1 端到端：把"语义选出术语"接进检索，到底涨不涨。

三臂，同一批 1,651 条非 A 说法，同一套生产口径查询（`fts_match_expr` + `clause_fts`）：
  A 基线   ：直接拿大白话去搜
  B 翻译   ：语义有界选择 → 拿**选中的术语**去搜
  C 混合   ：大白话 + 选中的术语，一起搜

⚠ 只测**按字找这一路**（FTS），不测向量/完整流水线：
  · 快（1,651 × 3 次查询，约 5 分钟），能把"选中术语这一步值多少"**单独隔离出来**；
  · 三臂用的是同一套查询构造器 ⇒ **互相可比**。
  · 端到端上向量那一路还有增益，那是**另一层**，不混进这个对比。
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.retrieval.embedder import embed_batch  # noqa: E402
from src.core.text_utils import fts_match_expr, segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
KS_DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
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
    import numpy as np

    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}

    ks = sqlite3.connect(f"file:{KS_DB}?mode=ro", uri=True)
    print("扫定义条款…", flush=True)
    define: dict[str, set[str]] = {t: set() for t in terms}
    for cid, txt in ks.execute("SELECT clause_revision_id, content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in define:
            define[t].add(cid)
    print(f"  有定义条款的术语 {sum(1 for v in define.values() if v)}", flush=True)

    cases = []
    for r in rows:
        t = r["term"]
        if not define.get(t):
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx or (words(tx) & tw[t]):
                continue
            cases.append((t, tx))
    n = len(cases)
    print(f"非 A 档 {n} 条", flush=True)

    t0 = time.time()
    T = np.asarray(embed_batch(terms), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    Q = np.asarray(embed_batch([c[1] for c in cases]), dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
    pick = [terms[i] for i in np.argmax(Q @ T.T, axis=1)]
    print(f"  嵌入+选择 {time.time()-t0:.0f}s", flush=True)

    def fts(q: str, k: int) -> set[str]:
        expr = fts_match_expr(q)
        if not expr.strip():
            return set()
        try:
            return {r[0] for r in ks.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()}
        except sqlite3.OperationalError:
            return set()

    arms = {"A 基线(大白话直接搜)": [0, 0], "B 翻译(拿选中术语搜)": [0, 0], "C 混合(大白话+术语)": [0, 0]}
    t0 = time.time()
    for i, (gold, phrase) in enumerate(cases, 1):
        tgt = define[gold]
        sel = pick[i - 1]
        for name, q in (("A 基线(大白话直接搜)", phrase),
                        ("B 翻译(拿选中术语搜)", sel),
                        ("C 混合(大白话+术语)", f"{phrase} {sel}")):
            ids5 = fts(q, 5)
            ids20 = fts(q, 20)
            arms[name][0] += int(bool(tgt & ids5))
            arms[name][1] += int(bool(tgt & ids20))
        if i % 300 == 0:
            print(f"  {i}/{n}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"端到端（{n} 条非 A 说法，按字找这一路，靶子=术语的定义条款）")
    print("=" * 78)
    for name, (h5, h20) in arms.items():
        print(f"  {name:<24} 前5 {h5/n:>6.1%} ({h5:>4})    前20 {h20/n:>6.1%} ({h20:>4})")
    a5, a20 = arms["A 基线(大白话直接搜)"]
    b5, b20 = arms["B 翻译(拿选中术语搜)"]
    c5, c20 = arms["C 混合(大白话+术语)"]
    print()
    print(f"  B vs A：前5 {a5/n:.1%} → {b5/n:.1%}（{b5/max(a5,1):.2f}×）；"
          f"前20 {a20/n:.1%} → {b20/n:.1%}（{b20/max(a20,1):.2f}×）")
    print(f"  C vs A：前5 {a5/n:.1%} → {c5/n:.1%}（{c5/max(a5,1):.2f}×）；"
          f"前20 {a20/n:.1%} → {c20/n:.1%}（{c20/max(a20,1):.2f}×）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
