"""针对性测试：**挑一条真带连接的条款，用大白话问它，看扩边有没有把它该带的东西带进来**。

## 为什么重做

exp-16 的 `run.py` 用 **hit@20** 当尺子 —— 那是"**gold 在不在候选集里**"。
但扩边的职责是「**防例外/但书/引用遗漏**」：它要带进来的是**被引用的那一条**，
而那一条**通常不是 gold**（gold 是用户问的那条）。⇒ **hit@20 看不见扩边的价值**，尺子用错了。

## 本脚本测什么

1. **正确性**：给定源条款，扩 1 跳 = 它的出边目标集合（机械核对）。
2. **价值（逐案）**：用一句**大白话**问"源条款管的事"，跑生产检索 ⇒ 看
   ① 源条款在不在 top-20；② 扩边把目标带进来没有；③ 目标是不是"不看就答不全"的那条。

## 只读

`mode=ro`；不改生产代码、不写库。
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DB = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db"))

#: 逐案：源条款（标准名, 条款号）+ 一句大白话问法
CASES = [
    ("中华人民共和国民法典", "第三百三十八条",
     "承包地被征收了，土地承包经营权人能拿到什么补偿？"),
    ("中华人民共和国民法典", "第四百六十六条",
     "合同条款有争议的时候，按什么规则确定它的意思？"),
    ("中华人民共和国民法典", "第四百一十一条",
     "企业用生产设备抵押，抵押财产什么时候算确定？"),
    ("商品农药验收规则", "3.3",
     "收货单位按什么规定验收进货的农药产品？"),
]


def main() -> int:
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

    con = get_db_connection()
    try:
        load_vec_extension(con)
    except Exception as exc:  # noqa: BLE001
        print("（向量扩展加载失败，向量路缺席）：", exc)

    out = []
    for std, num, query in CASES:
        print("=" * 78)
        print("【%s %s】" % (std, num))
        print("  大白话问法：", query)
        src = con.execute(
            """SELECT cr.clause_revision_id, cr.content_text FROM clause_revision cr
               JOIN doc_meta dm ON dm.doc_id = cr.doc_id
               WHERE dm.standard_name=? AND cr.clause_number=?""", (std, num)).fetchone()
        if not src:
            print("  ⚠ 找不到源条款")
            continue
        sid = src["clause_revision_id"]

        # ---- ① 正确性：扩 1 跳 == 出边目标集合 ----
        targets = [r[0] for r in con.execute(
            "SELECT target_clause_id FROM evidence_edge WHERE status='active'"
            " AND source_clause_id=?", (sid,))]
        print("  ① 该条的出边目标 %d 条 ⇒ 扩 1 跳应当恰好带回这 %d 条" % (len(targets), len(targets)))

        # ---- ② 价值：跑生产检索 ----
        res = perform_hybrid_search(query, top_k=20, rerank=False)
        base = [c.clause_revision_id for c in res]
        print("  ② 检索 top-20 里有没有这条源条款：%s" % ("有 ✓" if sid in base else "没有 ✗"))
        # 扩 1 跳
        added: list[str] = []
        if base:
            q = ("SELECT target_clause_id FROM evidence_edge WHERE status='active'"
                 " AND source_clause_id IN (%s)" % ",".join("?" * len(base)))
            seen = set(base)
            for (t,) in con.execute(q, base):
                if t not in seen:
                    seen.add(t)
                    added.append(t)
        hit_t = [t for t in targets if t in set(added)]
        in_base = [t for t in targets if t in set(base)]
        final = set(base) | set(added)
        present = [t for t in targets if t in final]
        print("  ③ 扩 1 跳新带进 %d 条；**它引用的那几条**：在最终集合里 %d/%d"
              % (len(added), len(present), len(targets)))
        if in_base:
            print("      （其中 %d 条本来就在 top-20 里）" % len(in_base))
        for t in present:
            tx = con.execute("SELECT clause_number, content_text FROM clause_revision"
                             " WHERE clause_revision_id=?", (t,)).fetchone()
            tag = "扩边带进" if t in set(added) else "本来就在池里"
            print("      → [%s] %s | %s" % (tag, tx["clause_number"],
                                          (tx["content_text"] or "").replace("\n", " ")[:84]))
        out.append({"case": f"{std} {num}", "query": query,
                    "src_in_top20": sid in base, "n_targets": len(targets),
                    "n_added": len(added), "target_in_base": len(in_base),
                    "target_present_final": len(present)})

    print()
    print("=== 汇总 ===")
    print("  判据 = 源条款引用的那几条，在【最终集合(top-20 ∪ 扩1跳)】里在不在")
    for r in out:
        print("  %-28s 源在池=%s 出边=%d 扩边新带进=%d → 目标在最终集合 %d/%d"
              % (r["case"], r["src_in_top20"], r["n_targets"], r["n_added"],
                 r["target_present_final"], r["n_targets"]))
    (Path(__file__).resolve().parent / "targeted.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
