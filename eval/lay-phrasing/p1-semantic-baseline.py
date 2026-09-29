"""P1 语义基线：把大白话和 500 个术语用**生产同款嵌入模型**比，选得对不对。

上一刀（`p1-literal-baseline.py`）结论：**纯字面在随机水平**（top1 0.7% vs 随机 0.20%），
所以 P1 必须靠语义。这个脚本量"语义能做到哪"——**它是 P1 的上限参考**，
决定"有界选择 + 语义"这条路值不值得往下走。

口径与生产一致：`src.core.retrieval.embedder.embed_batch`（BAAI/bge-small-zh-v1.5，
**未加查询指令前缀**，与生产完全相同），余弦相似度。
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO = Path(r"D:\AI\work space\zcode")
sys.path.insert(0, str(REPO))
from src.core.retrieval.embedder import embed_batch  # noqa: E402
from src.core.text_utils import segment_for_fts  # noqa: E402

D = REPO / "var" / "tmp"
CJK = re.compile(r"^[\u4e00-\u9fff]{2,}$")


def words(text: str) -> set[str]:
    return {w for w in segment_for_fts(text or "").split() if CJK.match(w)}


def main() -> int:
    try:
        import numpy as np
    except ImportError:
        print("没有 numpy，量不了（4 亿次点积，纯 Python 太慢）")
        return 2

    rows = [json.loads(l) for l in (D / "gen-V2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    terms = sorted({r["term"] for r in rows})
    tw = {t: words(t) for t in terms}

    cases = []
    for r in rows:
        t = r["term"]
        for x in (r.get("lay") or []):
            tx = x.get("text") if isinstance(x, dict) else x
            if not tx:
                continue
            ws = words(tx)
            if ws & tw[t]:
                continue          # A 档跳过
            cases.append((t, tx))
    print(f"候选术语 {len(terms)}；非 A 档 {len(cases)} 条", flush=True)

    t0 = time.time()
    print("嵌入术语…", flush=True)
    T = np.asarray(embed_batch(terms), dtype=np.float32)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-9
    print(f"  {time.time()-t0:.0f}s  shape={T.shape}", flush=True)

    print("嵌入大白话…", flush=True)
    Q = np.asarray(embed_batch([c[1] for c in cases]), dtype=np.float32)
    Q /= np.linalg.norm(Q, axis=1, keepdims=True) + 1e-9
    print(f"  {time.time()-t0:.0f}s", flush=True)

    print("算相似度并排序…", flush=True)
    S = Q @ T.T                       # (n_cases, n_terms)
    gold_idx = np.asarray([terms.index(c[0]) for c in cases])
    # 正确答案的排名（0-based）
    gold_score = S[np.arange(len(cases)), gold_idx]
    rank = (S > gold_score[:, None]).sum(axis=1) + 1
    n = len(cases)
    print()
    print("=" * 78)
    print(f"语义基线（{n} 条非 A 说法 × {len(terms)} 个候选术语，生产同款嵌入）")
    print("=" * 78)
    for k in (1, 3, 5, 10, 50):
        print(f"  top{k:<3} {(rank <= k).mean():>7.1%}")
    print(f"  MRR  {(1.0 / rank).mean():.3f}")
    print(f"  中位排名 {int(np.median(rank))} / {len(terms)}")
    print(f"  （随机：top1 {1/len(terms):.2%} / top5 {5/len(terms):.2%}，中位排名 {len(terms)//2}）")
    print()
    print("  排第 1 的例子：")
    order = np.argsort(rank)
    for i in order[:8]:
        print(f"    rank={rank[i]:<4} [{cases[i][0]}]  {cases[i][1][:40]}")
    print()
    print("  排最后的例子（看看难成什么样）：")
    for i in order[-4:]:
        print(f"    rank={rank[i]:<4} [{cases[i][0]}]  {cases[i][1][:40]}")
    print()
    top1 = (rank <= 1).mean()
    top5 = (rank <= 5).mean()
    print(f"  ⇒ 语义 top1 {top1:.1%}（随机 {1/len(terms):.2%}）"
          f"、top5 {top5:.1%}（随机 {5/len(terms):.2%}）")
    verdict = ("**明显有信号，这条路成立**" if top1 > 5 / len(terms)
               else "有信号但很弱 ⇒ 需要更好的语义手段（换模型/多次投票/先选短名单）")
    print(f"  ⇒ {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
