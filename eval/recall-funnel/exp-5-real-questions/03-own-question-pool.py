"""查「真实提问」在本机攒了多少 —— 这是比爬部委更省的来源。

## 背景（本仓计划 §「真实提问分布」那条）
计划记着：系统本来在攒真实提问，**但被保留策略销毁过** ——
实测"1000 行里 egress 998 行、user_export 2 行，而那 2 条是同一句测试提问问了两次 ⇒ **真实使用语料为零**"。
根因：两处硬编码 `LIMIT 1000` 共用一个滚动窗。
**2026-09-26 已修（`0718979`）**：改成按 `trigger_type` 各自清理，**提问证据保留 5000 条**。

本脚本只读，数三件事：
 ① `debug_dump` 表里各 `trigger_type` 各有多少行、时间跨度多少；
 ② 其中"**真的像用户提问**"的有多少（去重后）；
 ③ 这些提问**能不能当考卷**（要看它有没有带检索结果/命中信息）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\03-own-question-pool.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT = HERE / "own-question-pool.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def main() -> int:
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    if "debug_dump" not in tables:
        print("⛔ 真库里没有 debug_dump 表 —— 说明这份库不是应用在用的那份，或表名变了")
        print("   现有表：", tables)
        return 0

    cols = [d[1] for d in conn.execute("PRAGMA table_info(debug_dump)")]
    print(f"[q] debug_dump 列 = {cols}")
    total = conn.execute("SELECT COUNT(*) FROM debug_dump").fetchone()[0]
    by_type = conn.execute(
        "SELECT trigger_type, COUNT(*), MIN(created_at), MAX(created_at)"
        " FROM debug_dump GROUP BY trigger_type").fetchall()
    print(f"[q] 总行数 = {total}")
    for t, n, mn, mx in by_type:
        print(f"     trigger_type={t!r:18s} {n:5d} 行   时间 {mn} ~ {mx}")

    # 问题类
    from src.core.storage.debug_dump_retention import KEEP_QUESTION_EVIDENCE, TYPE_QUESTION
    qs = conn.execute(
        "SELECT query, created_at, llm_output FROM debug_dump WHERE trigger_type=?",
        (TYPE_QUESTION,)).fetchall()
    uniq = {q for q, _, _ in qs if q}
    with_ans = sum(1 for _, _, o in qs if (o or "").strip())
    print(f"\n[q] 提问证据：保留上限 {KEEP_QUESTION_EVIDENCE}；现有 {len(qs)} 行，去重后 {len(uniq)} 条不同提问")
    print(f"[q] 其中带 LLM 回答的 {with_ans} 行")
    if qs:
        print("[q] 最早/最新 =", qs[0][1], "/", qs[-1][1])
        print("[q] 抽样（前 5 条，截断）：")
        for q, t, _ in qs[:5]:
            print(f"     [{t}] {(q or '')[:70]}")

    result = {
        "why": "计划记录：真实提问曾被保留策略销毁、2026-09-26 已修（提问证据保留 5000）。本脚本查现状。",
        "db": str(DB),
        "debug_dump_columns": cols,
        "total_rows": total,
        "by_trigger_type": [{"trigger_type": t, "n": n, "first": mn, "last": mx}
                            for t, n, mn, mx in by_type],
        "question_evidence": {
            "keep_limit": KEEP_QUESTION_EVIDENCE,
            "rows": len(qs), "unique_queries": len(uniq),
            "rows_with_llm_output": with_ans,
            "samples": [{"query": (q or "")[:120], "at": t} for q, t, _ in qs[:20]],
        },
        "can_it_be_a_benchmark": ("还不能直接当考卷：考卷需要**每条问法对应到具体条文**（gold）。"
                                  "提问证据里只有问法与回答，**没有检索命中的条文 id** ⇒ "
                                  "要做成考卷，仍需对每条问题单独定 gold。"),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
