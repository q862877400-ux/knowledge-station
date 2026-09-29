"""P1 keystone：**语义**能不能从 500 个术语里挑对那一个？

纯字面基线已实测 ≈ 随机（top1 0.7% vs 0.20%，且排对的那些是**0 字重合靠字母序**）。
所以问题变成：**语义行不行**。用库里**现成**的嵌入模型（bge-small-zh-v1.5，生产同款）。

对照三种"术语侧"的表示：
  a) 只用**术语名**本身
  b) 用**定义条款的正文**（术语名 + 定义，库里现成）
  c) 用**术语名 + 英文名**（从术语条目的双语形态里取）

判据：对每条非 A 说法，按余弦相似度给 500 个术语排序，看正确答案排第几。
随机基线 top1 = 0.20%。
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
import sqlite3  # noqa: E402
from src.core.retrieval import embedder  # noqa: E402
from src.core.text_utils import segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
KS_DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
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

    # 术语的定义正文 + 英文名（从真库的定义条款里取）
    ks = sqlite3.connect(f"file:{KS_DB}?mode=ro", uri=True)
    deftext: dict[str, str] = {}
    enname: dict[str, str] = {}
    for (txt,) in ks.execute("SELECT content_text FROM clause_revision"):
        m = TERM_RE.match(txt or "")
        if not m:
            continue
        t = m.group(1).strip().strip("（）()·、-—")
        if t in tw and t not in deftext:
            deftext[t] = re.sub(r"\s+", " ", txt or "").strip()
            enname[t] = m.group(2).strip()
    print(f"术语 {len(terms)}；取到定义正文 {len(deftext)}", flush=True)

    # 非 A 档说法
    cases = []
    for r in rows:
        t = r["term"]
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if tx and not (words(tx) & tw[t]):
                cases.append((t, tx))
    print(f"非 A 档 {len(cases)} 条", flush=True)

    arms = {
        "a) 只用术语名": {t: t for t in terms},
        "b) 定义正文": {t: deftext.get(t, t) for t in terms},
        "c) 术语名+英文名": {t: (t + " " + enname.get(t, "")).strip() for t in terms},
    }
    qtexts = [tx for _t, tx in cases]
    t0 = time.time()
    qvecs = embedder.embed_batch(qtexts)
    print(f"  说法向量 {len(qvecs)} 条  {time.time()-t0:.0f}s", flush=True)

    print()
    print("=" * 78)
    print(f"语义选术语（{len(cases)} 条非 A 说法 × {len(terms)} 个候选，bge-small-zh-v1.5）")
    print("=" * 78)
    for name, side in arms.items():
        t0 = time.time()
        tvecs = embedder.embed_batch([side[t] for t in terms])
        top1 = top5 = top50 = 0
        mrr = 0.0
        ex = []
        for (t, tx), qv in zip(cases, qvecs):
            scored = sorted(((cos(qv, tv), c) for tv, c in zip(tvecs, terms)),
                            key=lambda x: (-x[0], x[1]))
            rank = next(i for i, (_s, c) in enumerate(scored, 1) if c == t)
            top1 += rank <= 1
            top5 += rank <= 5
            top50 += rank <= 50
            mrr += 1.0 / rank
            if rank == 1 and len(ex) < 4:
                ex.append((t, tx, scored[0][0]))
        n = len(cases)
        print(f"  【{name}】top1 {top1/n:>6.1%}  top5 {top5/n:>6.1%}"
              f"  top50 {top50/n:>6.1%}  MRR {mrr/n:.3f}   （{time.time()-t0:.0f}s）")
        for t, tx, sc in ex:
            print(f"      排对例：[{t}] 相似度 {sc:.3f} —— {tx[:32]}")
    print(f"  （随机基线 top1 {1/len(terms):.2%} / top5 {5/len(terms):.2%}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
