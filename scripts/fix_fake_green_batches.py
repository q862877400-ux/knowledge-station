"""订正 ANOM-001 修复前产生的历史"假绿"巡检批次（done 但四色合计 0/异常）。

幂等：目标批次已非 done 或已写过同批审计则跳过。只改数据 + 审计，不改代码。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402
from ulid import ULID  # noqa: E402

#: 已知假绿批次（冒烟取证：done 但四色合计 0 或渠道全失败）
FAKE_GREEN_BATCHES = (
    "bul_01M0SGMKA5522MTQZ3H5MPVZ67",   # 首轮冒烟 done 假绿（19 号全 0）
    "bul_01M0SHQ83E9B70J9P1GVYAKHKT",   # 旧引擎进程重跑 done 假绿
)


def main() -> int:
    conn = get_db_connection()
    fixed = skipped = 0
    for bid in FAKE_GREEN_BATCHES:
        row = conn.execute(
            "SELECT status, total, checked FROM bulk_import_batch WHERE batch_id=?",
            (bid,)).fetchone()
        if row is None:
            print(f"[skip] {bid} 不存在")
            skipped += 1
            continue
        if row["status"] != "done":
            print(f"[skip] {bid} 当前 status={row['status']}（非 done，无需订正）")
            skipped += 1
            continue
        audited = conn.execute(
            "SELECT 1 FROM event_log WHERE event_type='update/batch_corrected'"
            " AND target_id=? LIMIT 1", (bid,)).fetchone()
        if audited:
            print(f"[skip] {bid} 已订正过（审计存在）")
            skipped += 1
            continue
        with write_transaction() as txn:
            txn.execute("UPDATE bulk_import_batch SET status='failed' WHERE batch_id=?",
                        (bid,))
            txn.execute(
                "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                " target_id, before_state, after_state) VALUES (?,?,?,?,?,?,?)",
                (str(ULID()), "update/batch_corrected", "system", "bulk_import_batch",
                 bid,
                 json.dumps({"status": "done", "total": row["total"],
                             "checked": row["checked"]}, ensure_ascii=False),
                 json.dumps({"status": "failed",
                             "reason": "anom001_legacy_fake_green",
                             "script": "fix_fake_green_batches.py"},
                            ensure_ascii=False)))
        fixed += 1
        print(f"[fix] {bid}: done -> failed（审计已写）")
    print(f"完成：订正 {fixed}，跳过 {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
