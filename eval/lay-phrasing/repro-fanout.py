"""复核另一个 AI 的扇出结论（它没提交、卡在"等第五批复核"上）。

它的主张（var/tmp/NOTES-p1-fanout.md，400 抽样）：
  · 顺序拼接：不管扇出多宽，**前 20 永远卡在 15.8%**（top-1 术语的 20 条占满返回位）
  · 轮转交错：k=5 时前 20 → 28.0%、命中集合 37.0%，**同样的查询数、零额外成本**
  · k=5 是性价比拐点

本脚本**用更强的术语表示**（定义正文，我实测 top-1 22.2% 优于术语名的 16.4%）重做，
并同时报"顺序拼接 / 轮转交错"两种合并顺序，看它的结论是否复现。
非 A 子集 1651 条；靶子=术语的定义条款；只读真库。
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

    cases = []
    for r in rows:
        t = r["term"]
        if t not in define:
            continue
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx and not (words(tx) & tw[t]):
                cases.append((t, tx))
    print(f"非 A 说法 {len(cases)} 条", flush=True)

    tvec = embedder.embed_batch([deftext.get(t, t) for t in terms])
    qvec = embedder.embed_batch([tx for _t, tx in cases])
    print("  嵌入完成", flush=True)

    def fts_ids(term: str, k: int) -> list[str]:
        expr = fts_match_expr(term)
        if not expr.strip():
            return []
        try:
            return [r[0] for r in conn.execute(
                "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH ? "
                "ORDER BY bm25(clause_fts) LIMIT ?", (expr, k)).fetchall()]
        except sqlite3.OperationalError:
            return []

    WIDTH = 5
    PER = 20
    seq = {"5": 0, "20": 0}
    rr = {"5": 0, "20": 0}
    recall = 0
    n = 0
    t0 = time.time()
    for i, ((t, tx), qv) in enumerate(zip(cases, qvec), 1):
        tgt = define[t]
        sel = sorted(range(len(terms)), key=lambda j: -cos(qv, tvec[j]))[:WIDTH]
        lists = [fts_ids(terms[j], PER) for j in sel]
        # 顺序拼接
        s = [c for L in lists for c in L]
        # 轮转交错
        r = []
        for pos in range(PER):
            for L in lists:
                if pos < len(L):
                    r.append(L[pos])
        n += 1
        recall += int(bool(set(s) & tgt))
        seq["5"] += int(bool(set(s[:5]) & tgt))
        seq["20"] += int(bool(set(s[:20]) & tgt))
        rr["5"] += int(bool(set(r[:5]) & tgt))
        rr["20"] += int(bool(set(r[:20]) & tgt))
        if i % 400 == 0:
            print(f"  {i}/{len(cases)}  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"扇出 k={WIDTH}，每术语取 FTS 前 {PER}（{n} 条非 A 说法，术语表示=定义正文）")
    print("=" * 78)
    print(f"{'合并顺序':<14}{'前5':>10}{'前20':>10}{'命中集合':>12}")
    print(f"{'顺序拼接':<14}{seq['5']/n:>10.1%}{seq['20']/n:>10.1%}{recall/n:>12.1%}")
    print(f"{'轮转交错':<14}{rr['5']/n:>10.1%}{rr['20']/n:>10.1%}{recall/n:>12.1%}")
    print()
    print(f"  它的主张（400 抽样，术语表示较弱）：顺序前20 15.8% / 轮转前20 28.0% / 命中集合 37.0%")
    print(f"  ⇒ 本复现：{'结论方向复现' if rr['20'] > seq['20'] else '**未复现**'}"
          f"（轮转 {rr['20']/n:.1%} vs 顺序 {seq['20']/n:.1%}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
