"""引用边批量重算（**只读诊断版**）—— 2026-10-09 真缺陷的批量修法研究。

## 背景

`src/core/ingestion/law_text.py` 建边时误用循环残留变量 `m`（详见该处注释），
导致**每条文档的最后一条条款吸走整份文档的引用边**，其余条款的引用边全丢。
真库（2026-10-09 只读实测）：出度最高的那条（正文 106 字、自身 `cross_refs` 为 `[]`）
挂 **204 条出边**；全库 **845 条**条款呈同一形状、99.9% 是各文档最后一条。

## 为什么能批量修（本脚本的结论）

建边只依赖两样**都已经在库里**的东西：每条的 `clause_number` 与 `cross_refs`。
正确逻辑就是：

    number_to_id = {clause_number: clause_revision_id}   # 每份文档一份
    edges = [(src_id, dst_id)
             for 每条条款的每个 ref
             if src 与 ref 都在 number_to_id 里 and src_id != dst_id]

⇒ **不需要原文、不需要重跑分类器、不需要重新入库。**

## 本脚本做什么

对**全库每份文档**按上式重算，与现有 `evidence_edge` 对照，打印：

* 现有边数 / 重算边数；
* 有多少份文档不一致、按来源分组；
* 抽几份看差异形状（只多 / 只少）。

**只读**（`mode=ro`），**不写任何东西**。把 `--db` 指向副本可安全复算。

## 复跑

    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py
    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py --db <副本路径> --sample 5

## ⚠ 落地（`--apply`）**故意没实现**

改边属**必验类别**、且动生产库。落地前必须先：① 备份库；② 定回滚方式；
③ 走单写者/离线迁移的既有姿势（参考 `scripts/apply-folder-filing.py` 的「回滚 SQL 写在 docstring 里」）；
④ 派独立复核。**在那之前本脚本只诊断、不改。**
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys

DEFAULT_DB = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")


def analyze(db: str, sample: int) -> int:
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    cur: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for r in con.execute(
        """SELECT src.doc_id d, e.source_clause_id s, e.target_clause_id t
           FROM evidence_edge e
           JOIN clause_revision src ON src.clause_revision_id = e.source_clause_id"""
    ):
        cur[r["d"]].add((r["s"], r["t"]))

    by_doc: dict[str, list[sqlite3.Row]] = collections.defaultdict(list)
    for r in con.execute(
        "SELECT doc_id, clause_revision_id, clause_number, cross_refs FROM clause_revision"
    ):
        by_doc[r["doc_id"]].append(r)

    want: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    selfloops = 0
    for doc, rows in by_doc.items():
        n2id = {r["clause_number"]: r["clause_revision_id"] for r in rows}
        for r in rows:
            src_id = r["clause_revision_id"]
            for ref in json.loads(r["cross_refs"] or "[]"):
                dst_id = n2id.get(ref)
                if dst_id is None:
                    continue
                if dst_id == src_id:
                    selfloops += 1
                    continue
                want[doc].add((src_id, dst_id))

    cur_total = sum(len(v) for v in cur.values())
    want_total = sum(len(v) for v in want.values())
    diff = [d for d in (set(cur) | set(want)) if cur.get(d, set()) != want.get(d, set())]

    kind: dict[str, str] = {}
    for r in con.execute("SELECT doc_id, file_path FROM doc_meta"):
        kind[r["doc_id"]] = "lawrefbook" if (r["file_path"] or "").startswith("lawrefbook://") else "其它"

    print("库                    =", db)
    print("有条款的文档数        =", len(by_doc))
    print("现有边总数            =", cur_total)
    print("重算边总数            =", want_total)
    print("重算撞出的自环（跳过）=", selfloops)
    print("不一致的文档数        =", len(diff))
    print("  按来源分组          =", dict(collections.Counter(kind.get(d, "?") for d in diff)))
    print()
    print("=== 抽样看差异形状 ===")
    for d in diff[:sample]:
        nm = con.execute("SELECT standard_name FROM doc_meta WHERE doc_id=?", (d,)).fetchone()
        c, w = cur.get(d, set()), want.get(d, set())
        print("  %s" % (nm["standard_name"] if nm else d)[:56])
        print("    现有 %d / 重算 %d | 只多(假边) %d 只少(丢边) %d"
              % (len(c), len(w), len(c - w), len(w - c)))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="引用边批量重算（只读诊断）")
    ap.add_argument("--db", default=DEFAULT_DB, help="库路径（默认真库，只读打开）")
    ap.add_argument("--sample", type=int, default=3, help="抽样展示几份不一致文档")
    args = ap.parse_args(argv)
    if not os.path.exists(args.db):
        print("库不存在：", args.db)
        return 1
    return analyze(args.db, args.sample)


if __name__ == "__main__":
    sys.exit(main())
