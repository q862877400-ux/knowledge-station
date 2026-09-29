"""探针：`topk_by_cos` 的 numpy 路径与纯 Python 参照实现，**在真数据上**是否给同一个答案。

为什么单独量：`topk_by_cos(use_numpy=True)` 只是参照实现的**加速等价物**。如果它在真实
42,181 条候选上换掉了个别名次，那么"用加速路径重跑能复现纯 Python 那批数字"这句话就是假的
—— 那是**结论级**的差异，不是性能问题。
单元判据（`tests/test_term_bridge.py`）只在合成向量上比，这里在真嵌入上比。

用法：python var/tmp/probe-topk-equivalence.py [查询条数]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from src.core.retrieval import embedder                    # noqa: E402
from src.core.retrieval.term_bridge import TermIndex, topk_by_cos  # noqa: E402

CACHE = REPO / "var" / "tmp" / "term-index-full.json"
CASES = REPO / "var" / "tmp" / "gen-V2.jsonl"


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    idx = TermIndex.load(CACHE)
    print(f"候选 {len(idx)} 条，取前 {n} 条说法各比一次 top-5 / top-20")

    texts: list[str] = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        for x in (json.loads(line).get("lay") or []):
            t = x.get("text") if isinstance(x, dict) else x
            if t:
                texts.append(t)
            if len(texts) >= n:
                break
        if len(texts) >= n:
            break

    qs = [embedder.embed_query(t) for t in texts]
    diff5 = diff20 = order_diff = 0
    for q in qs:
        # 参照实现只跑一次 k=20（它给出的是一条**全序**，前 5 就是它的前缀），
        # 否则纯 Python 那条要扫两遍 42,181 条，白等一倍时间。
        ref20 = topk_by_cos(q, idx.vectors, 20, use_numpy=False)
        ref5 = ref20[:5]
        fast5 = topk_by_cos(q, idx.vectors, 5, use_numpy=True)
        fast20 = topk_by_cos(q, idx.vectors, 20, use_numpy=True)
        if set(fast20) != set(ref20):
            diff20 += 1
        if set(fast5) != set(ref5):
            diff5 += 1
        elif fast5 != ref5:
            order_diff += 1
    print(f"top-5  集合不同：{diff5}/{len(qs)}")
    print(f"top-20 集合不同：{diff20}/{len(qs)}")
    print(f"top-5  同集合但名次不同：{order_diff}/{len(qs)}")
    print("（全 0 ⇒ 加速路径在真数据上与参照实现同答，纯 Python 那批数字可用加速路径复现）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
