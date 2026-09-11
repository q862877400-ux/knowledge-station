# -*- coding: utf-8 -*-
"""国标体检结果回流知识库（2026-08-27）。

读 scripts/std_status_check.py 产出的 results.jsonl → 按归一号匹配 doc_meta →
更新已入库标准的 legal_status/effective_from(生效)/published_at(发布)/ccs_code/
ccs_name/ics；值变化时记 event_log 审计（对齐 change_repo.mark_ack 的闭环纪律）。

数据/代码分离：--jsonl 指向体检结果文件（数据区）；--db 指向引擎库（默认托管路径）。
只更新**已入库**的 doc（未入库的标准跳过——doc_meta 不存在该号）。

用法：
  python scripts/std_status_import.py --jsonl "<体检结果>/results.jsonl" [--db PATH] [--dry-run]

反爬不适用（本脚本为本地写库，无网络）。写库走 write_transaction（单写者）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.update.channels.base import norm_no  # noqa: E402


def _norm(no: str | None) -> str:
    return norm_no(no or "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="国标体检结果回流知识库 doc_meta")
    ap.add_argument("--jsonl", required=True, help="results.jsonl 路径")
    ap.add_argument("--db", default=None, help="引擎库路径（默认 get_db_connection 托管路径）")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写库")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条（冒烟）")
    args = ap.parse_args(argv)

    from src.core.storage.sqlite_db import get_db_connection, write_transaction
    from ulid import ULID

    # 读体检结果（多轮续查同号保留最后一条）
    by_std: dict[str, dict] = {}
    for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if "error" in d or not d.get("found"):
            continue   # 失败/查无不导入
        by_std[_norm(d.get("standard_no"))] = d
    if args.limit:
        by_std = dict(list(by_std.items())[: args.limit])
    print(f"[load] 有效体检结果 {len(by_std)} 条（失败/查无已跳过）", flush=True)

    db_target = Path(args.db) if args.db else None
    conn = get_db_connection(db_target)
    # 库内标准号（归一）→ doc_id, 现状态
    docs = {_norm(r["standard_no"]): dict(r)
            for r in conn.execute(
                "SELECT doc_id, standard_no, legal_status, effective_from, published_at,"
                " ccs_code, ccs_name, ics, withdrawn_date FROM doc_meta").fetchall()}
    print(f"[db] 库内标准 {len(docs)} 个", flush=True)

    updated = skipped_not_in_db = unchanged = 0
    changes_rows = []
    for no_norm, d in by_std.items():
        doc = docs.get(no_norm)
        if doc is None:
            skipped_not_in_db += 1
            continue
        new = {
            "legal_status": d.get("legal_status"),
            "effective_from": d.get("effective_date") or None,
            "published_at": d.get("publish_date") or None,
            "ccs_code": d.get("ccs_code") or None,
            "ccs_name": d.get("ccs_name") or None,
            "ics": d.get("ics") or None,
            "withdrawn_date": d.get("withdrawn_date") or None,
        }
        # 字段是否有变化（仅 compare 非空差异，避免把 None 覆盖成空字符串）
        diff = {k: v for k, v in new.items()
                if v and v != (doc.get(k) or None)}
        if not diff or diff.get("legal_status") == doc.get("legal_status"):
            # legal_status 相同也算无变化；其他字段可能仍补断点
            if not diff:
                unchanged += 1
                continue
        changes_rows.append((doc["doc_id"], doc, new, diff))

    if args.dry_run:
        print(f"[dry-run] 待更新 {len(changes_rows)} 条 / 未入库跳过 {skipped_not_in_db} / 无变化 {unchanged}")
        return 0

    with write_transaction(db_target) as txn:
        for doc_id, doc, new, diff in changes_rows:
            sets = {k: v for k, v in new.items()
                    if k in ("legal_status", "effective_from", "published_at",
                             "ccs_code", "ccs_name", "ics", "withdrawn_date")}
            if not sets:
                continue
            sets["updated_at"] = "datetime('now')"
            set_clause = ", ".join(f"{k} = ?" for k in sets if k != "updated_at") + \
                (", updated_at = datetime('now')" if "updated_at" in sets else "")
            vals = [sets[k] for k in sets if k != "updated_at"]
            txn.execute(f"UPDATE doc_meta SET {set_clause} WHERE doc_id=?", (*vals, doc_id))
            # 审计日志（对齐 mark_ack 闭环纪律）
            before = json.dumps({"legal_status": doc["legal_status"],
                                 "effective_from": doc["effective_from"]}, ensure_ascii=False)
            after = json.dumps({k: v for k, v in new.items() if v}, ensure_ascii=False)
            txn.execute(
                "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                " target_id, before_state, after_state) VALUES (?,?,?,?,?,?,?)",
                (str(ULID()), "update/status_refreshed", "check", "doc_meta", doc_id,
                 before, after))
            updated += 1

    print(f"[done] 已更新 {updated} 条 / 未入库跳过 {skipped_not_in_db} / 无变化 {unchanged}", flush=True)
    print(f"[out] 知识库 doc_meta 状态/发布/生效/CCS 已刷新", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
