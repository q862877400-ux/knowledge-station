"""P1·改后做法的下限：**纯字面**能不能从 500 个术语里挑对那一个？

为什么先量这个：改了做法之后（"从库自己的术语表里有界地选"），
最便宜的实现是字面匹配。若字面就已有明显信号 ⇒ 先别上模型；若接近随机 ⇒ 才必须上。

做法：对每条非 A 说法，用**两种字面判据**给 500 个术语打分，看正确答案排第几。
  · 判据 1：2 字子串重合数
  · 判据 2：jieba 实词重合数
随机基线：500 候选 ⇒ top-1 期望 0.2%。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.text_utils import segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def subs2(s: str) -> set[str]:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def main() -> int:
    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}
    ts = {t: subs2(t) for t in terms}
    print(f"候选术语 {len(terms)} 个（随机 top-1 ≈ {1/len(terms):.2%}）", flush=True)

    # 只取非 A 档（与术语无重合的）——它们才是"要选"的那些
    cases = []
    for r in rows:
        t = r["term"]
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            ws = words(tx)
            if ws & tw[t]:
                continue           # A 档跳过
            cases.append((t, tx, ws, subs2(tx)))
    print(f"非 A 档 {len(cases)} 条", flush=True)

    stat = {("子串", 1): 0, ("子串", 5): 0, ("子串", 50): 0,
            ("实词", 1): 0, ("实词", 5): 0, ("实词", 50): 0}
    mrr = {"子串": 0.0, "实词": 0.0}
    ex = {"子串": [], "实词": []}
    for t, tx, ws, ss in cases:
        for label, q in (("子串", ss), ("实词", ws)):
            if not q:
                continue
            scored = []
            for cand in terms:
                s = len(q & (ts[cand] if label == "子串" else tw[cand]))
                scored.append((s, cand))
            scored.sort(key=lambda x: (-x[0], x[1]))
            rank = next(i for i, (_s, c) in enumerate(scored, 1) if c == t)
            for k in (1, 5, 50):
                stat[(label, k)] += int(rank <= k)
            mrr[label] += 1.0 / rank
            if len(ex[label]) < 5 and rank == 1:
                ex[label].append((t, tx, scored[0][0]))

    n = len(cases)
    print()
    print("=" * 78)
    print(f"纯字面基线（{n} 条非 A 说法 × {len(terms)} 个候选术语）")
    print("=" * 78)
    for label in ("子串", "实词"):
        print(f"  【{label}判据】"
              f"  top1 {stat[(label,1)]/n:>6.1%}"
              f"   top5 {stat[(label,5)]/n:>6.1%}"
              f"   top50 {stat[(label,50)]/n:>6.1%}"
              f"   MRR {mrr[label]/n:.3f}")
    print(f"  （随机基线：top1 {1/len(terms):.2%} / top5 {5/len(terms):.2%}）")
    print()
    for label in ("子串", "实词"):
        print(f"  {label}判据排对第 1 的例子：")
        for t, tx, sc in ex[label]:
            print(f"    [{t}] 重合 {sc} 字 —— {tx[:34]}")
    print()
    best = max(stat[("子串", 1)], stat[("实词", 1)]) / n
    print(f"  ⇒ 纯字面最好 top1 = {best:.1%}（随机 {1/len(terms):.2%}）"
          f" ⇒ {'有信号，可先不上模型' if best > 5/len(terms) else '**接近随机 ⇒ 必须靠语义/模型**'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
