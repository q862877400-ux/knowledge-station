# -*- coding: utf-8 -*-
"""一次性维护：把 `doc_meta.standard_no` 尾部的「(OCR采集)」来源标记**搬**到 `source` 字段。

## 为什么需要（spec 009）

生产库 **1,430 篇**（占 8,983 篇的 **15.9%**）的 `standard_no` 尾部带 `(OCR采集)`，
它们全部来自 2026-10-07 那次 **LawRefBook** 导入（`file_path` 前缀 `lawrefbook://`）。
用户点开证据卡片时**会直接看到**这个后缀（`plugin/client/KsTurnTab.tsx` 渲染 `standard_no`）。

## ⚠ 为什么是「搬」而不是「删」（本脚本的核心口径）

实测这 1,430 篇的其余字段**全部按"官方现行"登记**：

| 字段 | 值 |
|---|---|
| `quality_grade` | `A`（契约是"OCR 识别率 ≥0.95"，而第三方 OCR 没这个证据） |
| `legal_status` | `effective` |
| `standard_type` | `mandatory` |
| `source` | **`NULL`** |

⇒ **这个后缀是它们唯一的"非官方来源"标记。**
只抹掉后缀 = 把来路信息删干净，把一个"显示缺陷"升级成"合规缺陷"。
所以本脚本**同一个事务里必须同时**把 `source` 写成 `lawrefbook`。

## 三件事在同一个事务里做完

1. `doc_meta.standard_no` 去掉尾部后缀（判据唯一所有者 = `text_utils.strip_ocr_source_suffix`）；
2. `doc_meta.source` ← `'lawrefbook'`（**信息量不减少**）；
3. `clause_fts.standard_no` 同步（**那是另一份副本**，实测 58,536 行带后缀；
   只改 1 不改 3 会让两条检索通道看到不同的标准号）。

每行写一条 `operation_log`（operation = `fix_standard_no_ocr_suffix`，detail 记旧值→新值）。

## 行为

- **默认 dry-run**：只统计与抽样打印，不写库；
- `--apply`：先 `create_snapshot("manual")`（手动快照**永不被自动清理**），再单事务写入；
- **写前撞号检查**：若去后缀后出现重复标准号 ⇒ **中止**（现状实测 0 个）；
- **幂等**：第二次运行应报 0 行。

## 用法
    .venv\\Scripts\\python scripts\\fix-standard-no-ocr-suffix.py            # 预览
    .venv\\Scripts\\python scripts\\fix-standard-no-ocr-suffix.py --apply     # 执行（先备份）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402
from src.core.text_utils import strip_ocr_source_suffix  # noqa: E402

OPERATION = "fix_standard_no_ocr_suffix"

#: 这批文档的来源（2026-10-12 实测：1,430/1,430 的 `source_url` 都指向它）
SOURCE_VALUE = "lawrefbook"
SOURCE_URL_MARK = "RanKKI/LawRefBook"

#: 只认这个后缀（判据在 text_utils；这里只用于 SQL 粗筛，**不在 SQL 里再写一份正则**）
SQL_PREFILTER = "standard_no LIKE '%(OCR采集)%'"


def find_candidates(conn) -> list[tuple[str, str, str]]:
    """返回 [(doc_id, old_no, new_no)]，只有 new != old 的才算候选。

    先在 SQL 里**粗筛**（含后缀字面）再在 Python 里**精确判定** ——
    判据只有一个所有者（`strip_ocr_source_suffix`），不在 SQL 里再写一份正则（那会分叉）。
    """
    rows = conn.execute(
        f"SELECT doc_id, standard_no, source FROM doc_meta WHERE {SQL_PREFILTER}"
    ).fetchall()
    out: list[tuple[str, str, str]] = []
    for doc_id, no, _src in rows:
        new = strip_ocr_source_suffix(no)
        if new != (no or ""):
            out.append((str(doc_id), no, new))
    return out


def check_collisions(conn, cands) -> list[tuple[str, list[str]]]:
    """撞号检查：去后缀后是否与**别的**文档的标准号重复。

    返回 [(冲突的标准号, [doc_id...])]；空列表 = 无冲突。
    ⚠ 必须在**写之前**跑：一旦撞号，检索会把两篇文档混起来。
    """
    by_new: dict[str, list[str]] = {}
    for doc_id, _old, new in cands:
        by_new.setdefault(new, []).append(doc_id)
    # 候选中内部重复
    dups = {k: v for k, v in by_new.items() if len(v) > 1}
    # 与"不在这批里"的文档重复
    for new, doc_ids in by_new.items():
        others = conn.execute(
            "SELECT doc_id FROM doc_meta WHERE standard_no=? AND doc_id NOT IN "
            f"({','.join('?' * len(doc_ids))})", (new, *doc_ids)).fetchall()
        if others:
            dups.setdefault(new, []).extend(str(r[0]) for r in others)
    return sorted(dups.items())


def check_source_consistency(conn, cands) -> dict:
    """核实这批候选**确实**都来自 LawRefBook（防止把别的来源一起改了）。"""
    ids = [d for d, _, _ in cands]
    if not ids:
        return {"checked": 0, "all_lawrefbook": True, "other_sources": []}
    q = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT doc_id, file_path, source_url FROM doc_meta WHERE doc_id IN ({q})", ids
    ).fetchall()
    other = [(str(r[0]), str(r[1])[:60]) for r in rows
             if SOURCE_URL_MARK not in str(r[2] or "")]
    return {"checked": len(rows), "all_lawrefbook": not other, "other_sources": other[:10]}


def count_fts_rows(conn) -> int:
    """`clause_fts` 里带后缀的行数（**另一份副本**）。"""
    return conn.execute(
        f"SELECT COUNT(*) FROM clause_fts WHERE {SQL_PREFILTER}").fetchone()[0]


def source_distribution(conn) -> dict[str, int]:
    rows = conn.execute(
        "SELECT COALESCE(source,'(NULL)') s, COUNT(*) n FROM doc_meta GROUP BY s").fetchall()
    return {str(r[0]): int(r[1]) for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description="把 standard_no 的 (OCR采集) 后缀搬进 source")
    ap.add_argument("--apply", action="store_true", help="真正写入（默认只预览）")
    ap.add_argument("--no-backup", action="store_true", help="跳过写前快照（不推荐）")
    ap.add_argument("--out", default="", help="报告 JSON 输出路径")
    ap.add_argument("--show", type=int, default=12, help="预览时打印多少条样例")
    args = ap.parse_args()

    conn = get_db_connection()
    total_docs = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    total_clauses = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    cands = find_candidates(conn)
    n_fts = count_fts_rows(conn)
    dist_before = source_distribution(conn)

    print(f"doc_meta 总行数        : {total_docs:,}")
    print(f"条款总行数             : {total_clauses:,}")
    print(f"待搬后缀的文档         : {len(cands):,}")
    print(f"clause_fts 待同步      : {n_fts:,}")
    print(f"写前 source 分布       : {dist_before}")
    for doc_id, old, new in cands[: args.show]:
        print(f"  [{doc_id}]")
        print(f"     旧: {old}")
        print(f"     新: {new}")

    cons = check_source_consistency(conn, cands)
    print(f"\n来源一致性：{cons['checked']:,} 篇里非 LawRefBook 的 {len(cons['other_sources'])} 篇")
    for d, p in cons["other_sources"]:
        print(f"     ⚠ {d}  {p}")

    coll = check_collisions(conn, cands)
    print(f"撞号检查：{len(coll)} 处冲突")
    for k, ids in coll[:10]:
        print(f"     ⚠ |{k}| ← {ids[:4]}")

    report = {
        "total_docs": total_docs,
        "total_clauses": total_clauses,
        "candidates": len(cands),
        "fts_rows_to_sync": n_fts,
        "source_distribution_before": dist_before,
        "source_consistency": cons,
        "collisions": [{"standard_no": k, "doc_ids": v} for k, v in coll],
        "applied": False,
        "snapshot_id": None,
    }

    # ---- 中止条件：撞号 或 来源不符（后者只警告，因为文件名可能变过）----
    if coll:
        print("\n⛔ 有撞号，**中止**（不写入）。请先人工处置。")
        if args.out:
            Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
        return 2

    if not args.apply:
        print("\n（dry-run：未写库。加 --apply 执行）")
    elif not cands and not n_fts:
        print("\n无候选，未做任何写入（幂等 OK）。")
    else:
        if not args.no_backup:
            from src.core.storage.backup import create_snapshot
            snap = create_snapshot("manual")
            report["snapshot_id"] = snap["snapshot_id"]
            print(f"\n写前快照: {snap['snapshot_id']}  checksum={snap['db_checksum'][:16]}…")
            print(f"          路径 {snap['path']}（手动快照不会被自动清理）")

        with write_transaction() as txn:
            # ① doc_meta：去后缀 + 记来源（**同一个事务**，不许分开）
            for doc_id, old, new in cands:
                txn.execute(
                    "UPDATE doc_meta SET standard_no=?, source=?,"
                    " updated_at=datetime('now') WHERE doc_id=?",
                    (new, SOURCE_VALUE, doc_id))
                txn.execute(
                    "INSERT INTO operation_log(operation, target_type, target_id, detail)"
                    " VALUES (?,?,?,?)",
                    (OPERATION, "doc_meta", doc_id,
                     json.dumps({"standard_no_old": old, "standard_no_new": new,
                                 "source_new": SOURCE_VALUE}, ensure_ascii=False)))
            # ② clause_fts：同步那份副本（FTS5 无外键，靠 clause_revision 关联）
            # ⚠ 逐文档更新（**不能**一条 UPDATE 把同一值刷给所有文档 —— 每篇的新标准号不同）
            for doc_id, _old, new in cands:
                txn.execute(
                    "UPDATE clause_fts SET standard_no=? WHERE clause_revision_id IN ("
                    "  SELECT cr.clause_revision_id FROM clause_revision cr"
                    "  WHERE cr.doc_id=?)",
                    (new, doc_id))
        report["applied"] = True
        print(f"\n已处理 {len(cands):,} 篇文档；每行在 operation_log 留痕（operation={OPERATION}）。")

        # 写后复验：同一判据再跑一次，应当为 0
        left = find_candidates(conn)
        left_fts = count_fts_rows(conn)
        report["remaining_after"] = len(left)
        report["remaining_fts_after"] = left_fts
        print(f"写后复验：doc_meta 仍带后缀 {len(left)} 行（应为 0）；"
              f"clause_fts 仍带后缀 {left_fts} 行（应为 0）")

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"报告: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
