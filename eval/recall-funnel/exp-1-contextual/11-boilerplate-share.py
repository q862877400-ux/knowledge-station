"""样板占比（可复算版）：上下文占了送进模型的文本多大比例？

## ⚠ 本脚本替代了一份定义说不清的旧产物（`boilerplate-share.json` 的 v1）

旧版三个问题（独立复核 F7 指出，已自查确认）：
 1. **没写定义** ⇒ 复核用"样板/(样板+正文)"复算，我原来是"样板**字符**/整段"，
    还**漏算了 `> ` 前缀与换行** ⇒ 同一批数据能算出 0.29 / 0.31 / 0.34 三种"中位"。
 2. **样本是前 20000 行**（按 rowid 取，等于最早的几篇文档），
    正文长度中位 **63**，而全库中位是 **55** ⇒ **系统性偏长**。
 3. 标了"全库"，实际不是。

## 本版的定义（**唯一、无歧义**）

    retrieval_text = 样板 + 正文        （正文恒在最后一段）
    → 样板字符数 = len(retrieval_text) − len(body)
    → 占比       = 样板字符数 / len(retrieval_text)

样板 = 标准名 + `> ` + 章节路径 + `> ` + 条款号 + 换行 —— **只统计送进模型的文本**，
不含 `clause_revision` 里没进向量的任何字段。范围 = **全表 521,978 条**（不是抽样）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\11-boilerplate-share.py
"""
from __future__ import annotations

import json
import sqlite3
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
OUT = HERE / "boilerplate-share.json"


def main() -> int:
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    n = c.execute("SELECT COUNT(*) FROM retrieval_text_ctx").fetchone()[0]

    # SQL 里直接算，避免把 52 万条文本都拉进内存
    rows = c.execute(
        "SELECT length(retrieval_text) - length(body) AS boiler,"
        "       length(body) AS body_len,"
        "       length(retrieval_text) AS total"
        " FROM retrieval_text_ctx WHERE length(retrieval_text) > 0").fetchall()
    boiler = [r[0] for r in rows]
    body = [r[1] for r in rows]
    total = [r[2] for r in rows]
    share = [b / t for b, t in zip(boiler, total) if t]
    share.sort()

    # 考卷那 171 条 gold 的同一个量（解释"稀释"假设时对比定义/要求用）
    v2 = [json.loads(l) for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]
    by_kind = {}
    for kind in ("定义", "要求"):
        sub = [it["v2"]["gold_cr_id"] for it in v2 if it["kind"] == kind]
        ph = ",".join("?" * len(sub))
        rr = c.execute(
            f"SELECT length(retrieval_text) - length(body), length(retrieval_text)"
            f" FROM retrieval_text_ctx WHERE clause_revision_id IN ({ph})", sub).fetchall()
        ss = sorted(b / t for b, t in rr if t)
        if ss:
            by_kind[kind] = {"n": len(ss), "share_median": round(st.median(ss), 4),
                             "share_mean": round(st.mean(ss), 4)}

    result = {
        "definition": ("样板字符数 / 整段字符数；"
                       "样板 = 标准名 + '> ' + 章节路径 + '> ' + 条款号 + 换行；"
                       "样板字符数 = len(retrieval_text) − len(body)"),
        "scope": f"全表 {len(rows)} / {n} 条（不是抽样，不是前缀）",
        "why_v2": "v1 没写定义、且只取前 20000 行（正文中位 63 vs 全库 55，偏长）—— 独立复核 F7 指出后重做",
        "library": {
            "n": len(rows),
            "boiler_chars_median": st.median(boiler),
            "body_chars_median": st.median(body),
            "total_chars_median": st.median(total),
            "share_median": round(st.median(share), 4),
            "share_mean": round(st.mean(share), 4),
            "share_p90": round(share[int(len(share) * 0.9)], 4),
            "share_p99": round(share[int(len(share) * 0.99)], 4),
        },
        "benchmark_171_gold_by_kind": by_kind,
        "note_for_the_dilution_hypothesis": (
            "定义/要求两类的样板占比几乎相同 ⇒ 占比本身**解释不了**要求类表现更差；"
            "那半个问题在 ab-analysis.json 的逐条翻转里（要求类翻出多于翻进），"
            "但那是**观测**，机制**未单验**"),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
