"""生产问答路径**实际喂给六路通道的查询串**是什么（只读，产出可核的清单）。

为什么要单独落一份：报告与配置盘点都断言"171 条里有 N 条，生产实际搜的不是用户的原始问法"，
独立复核指出**这个数没有任何产物可核**（本批 16 个文件里搜不到）。这里把它变成可复算的清单。

口径（照 `src/core/llm/ks_answer.py` 的检索前链条）：
    query → parse_declared → detect_theme / classify_intent → refine_search_query
          → expand_with_alias → expand_query_with_history（无历史时是恒等）

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\preprocess-diff.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
V2 = HERE / "benchmark-v2.jsonl"
OUT = HERE / "query-preprocess.json"


def main() -> int:
    from src.core.query import understanding as qu
    from src.core.knowledge.alias_extract import expand_with_alias
    from src.core.retrieval.hybrid_engine import expand_query_with_history

    items = [json.loads(l) for l in V2.read_text(encoding="utf-8").splitlines() if l.strip()]
    per = []
    for it in items:
        q = it["query"]
        declared, clean = qu.parse_declared(q)
        theme = qu.detect_theme(clean)
        intent = qu.classify_intent(clean)
        refined = qu.refine_search_query(clean or q, intent, theme)
        try:
            final = expand_with_alias(expand_query_with_history(refined, []))
            alias_ok = True
        except Exception as e:  # noqa: BLE001
            final, alias_ok = refined, False
            print("别名扩展降级:", e, flush=True)
        per.append({
            "i": it["i"], "raw": q, "search_query": final,
            "changed": final != q,
            "theme": theme, "intent": intent, "alias_ok": alias_ok,
        })

    changed = [p for p in per if p["changed"]]
    result = {
        "meta": {
            "source": str(V2),
            "chain": "parse_declared → detect_theme/classify_intent → refine_search_query"
                     " → expand_with_alias → expand_query_with_history",
            "producer": "src/core/llm/ks_answer.py（检索前那一串）",
            "why": "六路通道实际收到的是 search_query，不是用户原始问法",
        },
        "n": len(per), "n_changed": len(changed),
        "changed": changed,
        "per_query": per,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"n": len(per), "n_changed": len(changed),
                      "samples": [{"i": c["i"], "raw": c["raw"], "search_query": c["search_query"]}
                                  for c in changed[:5]]}, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
