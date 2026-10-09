"""引用边批量重算（诊断 + 修复）—— 2026-10-09 真缺陷的批量修法。

## 背景

`src/core/ingestion/law_text.py` 建边时误用循环残留变量 `m`（详见该处注释），
导致**每条文档的最后一条条款吸走整份文档的引用边**，其余条款的引用边全丢。
真库（2026-10-09 只读实测）：出度最高的那条（正文 106 字、自身 `cross_refs` 为 `[]`）
挂 **204 条出边**；全库 **845 条**条款呈同一形状、99.9% 是各文档最后一条、
99.6% 属于 `lawrefbook://` 文档（该来源共 1,430 份）。

代码已修（`b9d9d3b`）。**本脚本负责把已有文档的边重算回来。**

## 为什么能批量修

建边只依赖两样**都已经在库里**的东西：每条的 `clause_number` 与 `cross_refs`。正确逻辑：

    number_to_id = {clause_number: clause_revision_id}   # 每份文档一份
    edges = [(src_id, dst_id)
             for 每条条款的每个 ref
             if src 与 ref 都在 number_to_id 里 and src_id != dst_id]

⇒ **不需要原文、不需要重跑分类器、不需要重新入库。**

## 用法

    # 只读诊断（默认）
    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py
    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py --db <副本> --sample 5

    # 实际修复（先备份，再在**一个事务**里逐文档 delete + insert）
    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py --apply
    .venv/Scripts/python.exe scripts/rebuild-reference-edges.py --apply --db-copy

`--apply` 会先写两份备份：
* **边级备份**（JSONL，执行前这 862 份文档的**全部**边）⇒ `--backup-dir`（默认 `var/tmp/`）
* **全库副本**（可选，`--db-copy`）⇒ 与库同目录的 `backup/`

## 回滚（把边恢复成执行前的样子）

边级备份里就是**执行前那批文档的全部边**。回滚 = 先清空这批文档的边，再逐条插回：

    .venv/Scripts/python.exe - <<'PY'
    import json, sqlite3
    DB  = r'<库路径>'
    BAK = r'<备份 jsonl>'
    rows = [json.loads(l) for l in open(BAK, encoding='utf-8')]
    docs = sorted({r['doc_id'] for r in rows})
    con = sqlite3.connect(DB); con.execute('PRAGMA busy_timeout=60000')
    with con:                                     # 单事务
        con.executemany(
            'DELETE FROM evidence_edge WHERE source_clause_id IN '
            '(SELECT clause_revision_id FROM clause_revision WHERE doc_id=?)',
            [(d,) for d in docs])
        con.executemany(
            'INSERT INTO evidence_edge (edge_id, edge_type, source_clause_id,'
            ' target_clause_id, confidence, status, created_at) VALUES (?,?,?,?,?,?,?)',
            [(r['edge_id'], r['edge_type'], r['source_clause_id'], r['target_clause_id'],
              r['confidence'], r['status'], r['created_at']) for r in rows])
    print('回滚完成：', len(rows), '条边')
    PY

## 判据（修完必须成立）

1. **"零引用却有边"的条款数 = 0**；
2. 每条的**出边数 == 该条 `cross_refs` 解析出的目标数**（逐条吻合）；
3. 全库边数 == 重算边数。
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

from ulid import ULID

DEFAULT_DB = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")
#: 与 `law_text.py` 落库时一致（`[(t, s, d, 0.9, "active") ...]`）
EDGE_CONF = 0.9


def _plan(db: str):
    """只读：算出「现有边 / 重算边 / 不一致文档」。返回 (con, by_doc, cur, want, diff)。"""
    con = sqlite3.connect("file:" + db.replace("\\", "/") + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row

    by_doc: dict[str, list[sqlite3.Row]] = collections.defaultdict(list)
    for r in con.execute(
        "SELECT doc_id, clause_revision_id, clause_number, cross_refs FROM clause_revision"
    ):
        by_doc[r["doc_id"]].append(r)

    cur: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for r in con.execute(
        """SELECT src.doc_id d, e.source_clause_id s, e.target_clause_id t
           FROM evidence_edge e
           JOIN clause_revision src ON src.clause_revision_id = e.source_clause_id"""
    ):
        cur[r["d"]].add((r["s"], r["t"]))

    want: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for doc, rows in by_doc.items():
        n2id = {r["clause_number"]: r["clause_revision_id"] for r in rows}
        for r in rows:
            src_id = r["clause_revision_id"]
            for ref in json.loads(r["cross_refs"] or "[]"):
                dst_id = n2id.get(ref)
                if dst_id is None or dst_id == src_id:
                    continue
                want[doc].add((src_id, dst_id))

    diff = [d for d in (set(cur) | set(want)) if cur.get(d, set()) != want.get(d, set())]
    return con, by_doc, cur, want, diff


def analyze(db: str, sample: int) -> int:
    con, by_doc, cur, want, diff = _plan(db)
    kind: dict[str, str] = {}
    for r in con.execute("SELECT doc_id, file_path FROM doc_meta"):
        kind[r["doc_id"]] = "lawrefbook" if (r["file_path"] or "").startswith("lawrefbook://") else "其它"

    print("库                    =", db)
    print("有条款的文档数        =", len(by_doc))
    print("现有边总数            =", sum(len(v) for v in cur.values()))
    print("重算边总数            =", sum(len(v) for v in want.values()))
    print("不一致的文档数        =", len(diff))
    print("  按来源分组          =", dict(collections.Counter(kind.get(d, "?") for d in diff)))
    print("  这些文档现有边      =", sum(len(cur.get(d, set())) for d in diff))
    print("  这些文档重算后      =", sum(len(want.get(d, set())) for d in diff))
    print()
    print("=== 抽样看差异形状 ===")
    for d in diff[:sample]:
        nm = con.execute("SELECT standard_name FROM doc_meta WHERE doc_id=?", (d,)).fetchone()
        c, w = cur.get(d, set()), want.get(d, set())
        print("  %s" % (nm["standard_name"] if nm else d)[:56])
        print("    现有 %d / 重算 %d | 只多(假边) %d 只少(丢边) %d"
              % (len(c), len(w), len(c - w), len(w - c)))
    return 0


def apply(db: str, backup_dir: str, db_copy: bool) -> int:
    con_ro, by_doc, cur, want, diff = _plan(db)
    con_ro.close()
    if not diff:
        print("没有需要修的文档（现有边已与重算一致）")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    Path(backup_dir).mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=60000")

    # ---- ① 备份：边级（执行前这批文档的全部边）----
    docs = sorted(diff)
    clause_ids_by_doc = {d: [r["clause_revision_id"] for r in by_doc[d]] for d in docs}
    bak_path = str(Path(backup_dir) / f"edges-backup-{stamp}.jsonl")
    n_bak = 0
    with open(bak_path, "w", encoding="utf-8") as fh:
        for d in docs:
            ids = clause_ids_by_doc[d]
            for i in range(0, len(ids), 400):
                chunk = ids[i:i + 400]
                q = ("SELECT * FROM evidence_edge WHERE source_clause_id IN (%s)"
                     % ",".join("?" * len(chunk)))
                for r in con.execute(q, chunk):
                    fh.write(json.dumps({
                        "doc_id": d, "edge_id": r["edge_id"], "edge_type": r["edge_type"],
                        "source_clause_id": r["source_clause_id"],
                        "target_clause_id": r["target_clause_id"],
                        "confidence": r["confidence"], "status": r["status"],
                        "created_at": r["created_at"]}, ensure_ascii=False) + "\n")
                    n_bak += 1
    print("① 边级备份 →", bak_path, "|", n_bak, "条")

    # ---- ② 备份：全库副本（可选）----
    if db_copy:
        dst = str(Path(db).parent / "backup" / f"knowledge.db.bak-{stamp}")
        Path(dst).parent.mkdir(parents=True, exist_ok=True)
        dst_con = sqlite3.connect(dst)
        with dst_con:
            con.backup(dst_con)          # SQLite 在线备份 API（一致快照）
        dst_con.close()
        print("② 全库副本 →", dst, "|", os.path.getsize(dst) // 1048576, "MB")

    # ---- ③ 应用：单事务，逐文档 delete + insert ----
    n_del = n_ins = 0
    with con:                                 # 事务：要么全成，要么全不成
        for d in docs:
            ids = clause_ids_by_doc[d]
            for i in range(0, len(ids), 400):
                chunk = ids[i:i + 400]
                q = ("DELETE FROM evidence_edge WHERE source_clause_id IN (%s)"
                     % ",".join("?" * len(chunk)))
                n_del += con.execute(q, chunk).rowcount
            rows = [(f"edge_{ULID()}", "reference_relation", s, t, EDGE_CONF, "active")
                    for s, t in sorted(want.get(d, set()))]
            con.executemany(
                "INSERT INTO evidence_edge (edge_id, edge_type, source_clause_id,"
                " target_clause_id, confidence, status) VALUES (?,?,?,?,?,?)", rows)
            n_ins += len(rows)
    print("③ 已应用：删", n_del, "条 / 插", n_ins, "条（文档", len(docs), "份）")
    con.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="引用边批量重算（诊断 / 修复）")
    ap.add_argument("--db", default=DEFAULT_DB, help="库路径（默认真库）")
    ap.add_argument("--sample", type=int, default=3, help="诊断模式抽样展示几份")
    ap.add_argument("--apply", action="store_true", help="真的写库（默认只读诊断）")
    ap.add_argument("--backup-dir", default="var/tmp", help="边级备份目录")
    ap.add_argument("--db-copy", action="store_true", help="额外做一份全库副本")
    args = ap.parse_args(argv)
    if not os.path.exists(args.db):
        print("库不存在：", args.db)
        return 1
    if args.apply:
        return apply(args.db, args.backup_dir, args.db_copy)
    return analyze(args.db, args.sample)


if __name__ == "__main__":
    sys.exit(main())
