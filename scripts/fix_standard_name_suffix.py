# -*- coding: utf-8 -*-
"""一次性维护：清理 `doc_meta.standard_name` 结尾的**副本后缀**（`…(1)`）。

## 为什么需要
生产库里 :139 行（2026-09-17 实测，随灌库在涨）`standard_name` 形如 `电梯技术条件(1)`
——那不是从文档内容读出来的，而是**入库时从文件名派生**的（文件名普遍形如
`GB／T 10058-2023 电梯技术条件(1).pdf`）。**派生侧已于同轮修好**
（`text_utils.clean_standard_name` + 三个调用方），本脚本负责**回填已有数据**。

## 只做最小改动（重要）
本脚本**只用 `strip_duplicate_suffix`**，即**只去掉结尾**的 `(数字)`。
**不用** `clean_standard_name`——后者会顺带把表意空格 `U+3000` 与全角斜杠归一，
那会让库内 :312 行**合法**括号名（`聚丙烯(PP)树脂`、`湿式(非金属类)摩擦材料` …）
里的一部分"被顺带改动"，超出本脚本的声明范围。

## 行为
- **默认 dry-run**：只统计与抽样打印，不写库；
- `--apply`：先 `backup.create_snapshot("manual")`（VACUUM INTO + 校验和，手动快照**永不被
  自动清理**，所以随时可回滚），再在**单个事务**里逐行 UPDATE，并为每行写一条
  `operation_log`（operation=`fix_standard_name_suffix`，detail 记 旧值→新值）；
- **幂等**：第二次运行应报 0 行。

## 用法
    .venv\\Scripts\\python scripts\\fix_standard_name_suffix.py            # 预览
    .venv\\Scripts\\python scripts\\fix_standard_name_suffix.py --apply     # 执行（先备份）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402
from src.core.text_utils import strip_duplicate_suffix  # noqa: E402

OPERATION = "fix_standard_name_suffix"


def find_candidates(conn) -> list[tuple[str, str, str]]:
    """返回 [(doc_id, old_name, new_name)]，只有 new != old 的才算候选。

    先在 SQL 里粗筛（含括号）再在 Python 里精确判定——**判据只有一个所有者**
    （`strip_duplicate_suffix`），不在 SQL 里再写一份正则（那会分叉）。
    """
    rows = conn.execute(
        "SELECT doc_id, standard_name FROM doc_meta "
        "WHERE standard_name LIKE '%(%' OR standard_name LIKE '%（%'"
    ).fetchall()
    out: list[tuple[str, str, str]] = []
    for doc_id, name in rows:
        new = strip_duplicate_suffix(name)
        if new != (name or ""):
            out.append((str(doc_id), name, new))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="清理 standard_name 结尾的副本后缀 (N)")
    ap.add_argument("--apply", action="store_true", help="真正写入（默认只预览）")
    ap.add_argument("--no-backup", action="store_true", help="跳过写前快照（不推荐）")
    ap.add_argument("--out", default="", help="报告 JSON 输出路径")
    ap.add_argument("--show", type=int, default=15, help="预览时打印多少条样例")
    args = ap.parse_args()

    conn = get_db_connection()
    total_docs = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    cands = find_candidates(conn)

    print(f"doc_meta 总行数      : {total_docs}")
    print(f"待清理（结尾副本后缀）: {len(cands)}")
    for doc_id, old, new in cands[: args.show]:
        print(f"  [{doc_id}]")
        print(f"     旧: {old}")
        print(f"     新: {new}")

    report = {
        "total_docs": total_docs,
        "candidates": len(cands),
        "applied": False,
        "snapshot_id": None,
        "sample": [{"doc_id": d, "old": o, "new": n} for d, o, n in cands[:50]],
    }

    if not args.apply:
        print("\n（dry-run：未写库。加 --apply 执行）")
    elif not cands:
        print("\n无候选，未做任何写入（幂等 OK）。")
    else:
        if not args.no_backup:
            from src.core.storage.backup import create_snapshot
            snap = create_snapshot("manual")
            report["snapshot_id"] = snap["snapshot_id"]
            print(f"\n写前快照: {snap['snapshot_id']}  checksum={snap['db_checksum'][:16]}…")
            print(f"          路径 {snap['path']}（手动快照不会被自动清理）")
        with write_transaction() as txn:
            for doc_id, old, new in cands:
                txn.execute(
                    "UPDATE doc_meta SET standard_name=?, updated_at=datetime('now') "
                    "WHERE doc_id=?", (new, doc_id))
                txn.execute(
                    "INSERT INTO operation_log(operation, target_type, target_id, detail) "
                    "VALUES (?,?,?,?)",
                    (OPERATION, "doc_meta", doc_id,
                     json.dumps({"old": old, "new": new}, ensure_ascii=False)))
        report["applied"] = True
        print(f"\n已更新 {len(cands)} 行；每行在 operation_log 留痕（operation={OPERATION}）。")

        # 写后复验：同一判据再跑一次，应当为 0
        left = find_candidates(conn)
        report["remaining_after"] = len(left)
        print(f"写后复验：仍带副本后缀 {len(left)} 行（应为 0）")

    if args.out:
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        print(f"报告: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
