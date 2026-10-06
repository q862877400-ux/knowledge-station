"""字面重叠率（"按字找"的先天天花板）——用本批考卷自己的数字，不引用任何历史数字。

对每条问法：把提问按 **通道 B 实际使用的同一条分词口径**（`text_utils.segment_for_fts`
+ `fts_match_expr` 的过滤规则）切成词，再看这些词在 **gold 条文的 `content_segmented`** 里
出现几个。一个都不出现 ⇒ **通道 B（FTS5）结构上不可能召回这条 gold**，
与"bm25 排得不好"无关 —— 这是两件不同的事，必须分开报。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\lexical-overlap.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
V2 = HERE / "benchmark-v2.jsonl"
OUT = HERE / "lexical-overlap.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def main() -> int:
    from src.core.text_utils import segment_for_fts

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    items = [json.loads(l) for l in V2.read_text(encoding="utf-8").splitlines() if l.strip()]

    def tokens(q: str) -> list[str]:
        """与 `fts_match_expr` 同一条口径：分词 → 只留字母数字/下划线/中文 → 丢单字符词。"""
        out = []
        for w in segment_for_fts(q).split():
            for tok in re.sub(r"[^\w\u4e00-\u9fff]", " ", w).split():
                if len(tok) > 1:
                    out.append(tok)
        return out

    per = []
    for it in items:
        cr = it["v2"]["gold_cr_id"]
        seg = conn.execute("SELECT content_segmented FROM clause_fts"
                           " WHERE clause_revision_id=?", (cr,)).fetchone()
        seg = (seg[0] if seg else "") or ""
        seg_set = set(seg.split())
        tk = tokens(it["query"])
        hit = [t for t in tk if t in seg_set]
        per.append({
            "i": it["i"], "kind": it["kind"],
            "n_tokens": len(tk), "n_hit": len(hit),
            "coverage": round(len(hit) / len(tk), 3) if tk else None,
            "zero_overlap": len(hit) == 0,
            "hit_tokens": hit[:12],
            "query": it["query"],
        })

    def rate(rows):
        n = len(rows)
        return {
            "n": n,
            "zero_overlap": sum(1 for r in rows if r["zero_overlap"]),
            "zero_overlap_pct": round(sum(1 for r in rows if r["zero_overlap"]) / n, 4) if n else None,
            "coverage_mean": round(sum(r["coverage"] or 0 for r in rows) / n, 4) if n else None,
            "coverage_median": sorted(r["coverage"] or 0 for r in rows)[n // 2] if n else None,
        }

    result = {
        "meta": {
            "source": str(V2), "db": str(DB),
            "tokenizer": "text_utils.segment_for_fts + fts_match_expr 的过滤规则（与通道 B 同口径）",
            "compare_against": "gold 条款在 clause_fts.content_segmented 里的词集合",
            "why": "一个共同词都没有 ⇒ 通道 B 结构上召不回这条 gold（是表示/词汇问题，不是排序问题）",
        },
        "all": rate(per),
        "by_kind": {k: rate([r for r in per if r["kind"] == k]) for k in ("定义", "要求")},
        "examples_zero": [r for r in per if r["zero_overlap"]][:8],
        "per_query": per,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_query"},
                     ensure_ascii=False, indent=1)[:3000])
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
