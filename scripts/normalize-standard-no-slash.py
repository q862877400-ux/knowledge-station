"""R6c-2c：把库内**存量**全角斜杠归一（`standard_no` / `short_code` / `standard_name`）。

## 为什么做（证据）
真库 6417 条标准里 **5879 条的 `standard_no` 写全角斜杠 `／`（U+FF0F）**；`short_code` 同样 5879 条。
它们**全部创建于 2026-09-16**（最新一条 13:52:26），而**派生侧的修复在 2026-09-17 就做了**
（`_stdparse.derive_standard` / `std_bulk_import` 都已归一）——实测 **2026-09-18 及以后 0 条新增**。
⇒ 没有活的路径在产生新脏行，剩下的**只是存量回填**。

## 安全设计（这是动业主的真库，按"可逆 + 可核"做）
1. **默认 dry-run**，只有显式 `--apply` 才写；
2. 写出**完整变更清单** `var/backup/r6c2c-normalize-slash-<ts>.json`（doc_id/列/旧值/新值）——
   这是回滚凭据（每一条都能精确还原）；
3. 只改**字符形状**：`／`→`/`（不动空格、不动破折号，不做任何"顺手"归一）；
4. **撞车保护**：若某行归一后会与**已存在的另一行**同值，**跳过它**并单独列出
   （不制造重复——实测只有 1 处）；
5. 单事务写入（`write_transaction`），前/后各跑一次 `PRAGMA integrity_check` 与计数核对；
6. 不碰任何其它列。

用法：
    .venv\\Scripts\\python.exe scripts/normalize-standard-no-slash.py            # dry-run
    .venv\\Scripts\\python.exe scripts/normalize-standard-no-slash.py --apply    # 真写
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.config import get_settings  # noqa: E402
from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402

COLS = ("standard_no", "short_code", "standard_name")
FW = "／"
OUT_DIR = ROOT / "var" / "backup"


def _db_stat() -> dict:
    """库文件的 (大小, mtime, sha256)。

    ⚠ 独立复核 b31 的收尾建议：**"可回滚"不能只是口头承诺**——回滚清单必须逐行记 doc_id→原值，
    并且**带上写前/写后的库指纹**，否则事后无法证明"改的就是这些行、库也没被别的东西动过"。
    （2.3GB 的库哈希一次约十几秒；这一步只在 `--apply` 时做两次。）
    """
    import hashlib
    p = Path(get_settings().db_path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return {"path": str(p), "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            "sha256": h.hexdigest()}


def _plan(conn) -> tuple[list[dict], list[dict]]:
    """算出变更清单；同时找出"归一后会撞车"的行（那些**跳过**）。"""
    rows = conn.execute(
        "SELECT doc_id, standard_no, short_code, standard_name FROM doc_meta "
        "WHERE standard_no LIKE '%／%' OR short_code LIKE '%／%' OR standard_name LIKE '%／%'"
    ).fetchall()
    # 现有值集合（每个列各一份），用于撞车判断
    existing: dict[str, set[str]] = {}
    for col in COLS:
        existing[col] = {r[col] for r in conn.execute(f"SELECT {col} FROM doc_meta").fetchall()
                         if r[col] is not None}
    changes: list[dict] = []
    skipped: list[dict] = []
    for r in rows:
        for col in COLS:
            old = r[col]
            if not old or FW not in old:
                continue
            new = old.replace(FW, "/")
            if new == old:
                continue
            # 撞车：目标值已存在，且不是"这一行自己"
            same_row = conn.execute(
                f"SELECT COUNT(*) n FROM doc_meta WHERE {col}=? AND doc_id=?", (new, r["doc_id"])
            ).fetchone()["n"]
            if new in existing[col] and not same_row:
                skipped.append({"doc_id": r["doc_id"], "column": col, "old": old, "new": new,
                                "why": "归一后会与已存在的另一行同值 ⇒ 跳过，不制造重复"})
                continue
            changes.append({"doc_id": r["doc_id"], "column": col, "old": old, "new": new})
    return changes, skipped


def main() -> int:
    apply = "--apply" in sys.argv
    conn = get_db_connection()
    print("integrity_check(前):", conn.execute("PRAGMA integrity_check").fetchone()[0])
    changes, skipped = _plan(conn)
    by_col: dict[str, int] = {}
    for c in changes:
        by_col[c["column"]] = by_col.get(c["column"], 0) + 1
    print(f"计划改动 {len(changes)} 处（按列: {by_col}）；跳过 {len(skipped)} 处")
    for s in skipped:
        print(f"  ⚠ 跳过 {s['column']} {s['old']!r} → {s['new']!r}（{s['why']}）")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    plan_path = OUT_DIR / f"r6c2c-normalize-slash-{stamp}.json"
    before = _db_stat() if apply else None
    plan_path.write_text(json.dumps({"generated_at": stamp, "apply": apply,
                                     "db_before": before,
                                     "changes": changes, "skipped": skipped},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print("变更清单:", plan_path.relative_to(ROOT))
    if not apply:
        print("\n（dry-run：未写库。加 --apply 才写。）")
        return 0
    with write_transaction() as w:
        for c in changes:
            w.execute(f"UPDATE doc_meta SET {c['column']}=? WHERE doc_id=?",
                      (c["new"], c["doc_id"]))
    conn2 = get_db_connection()
    left = {col: conn2.execute(
        f"SELECT COUNT(*) n FROM doc_meta WHERE {col} LIKE '%／%'").fetchone()["n"] for col in COLS}
    integrity = conn2.execute("PRAGMA integrity_check").fetchone()[0]
    # ⚠ **必须在 checkpoint 之后再取指纹**（2026-09-18 自己踩到并更正）：
    #   第一次跑时我在写完立刻 `_db_stat()`，而那时改动还在 WAL 里、主库文件**一个字节都没变**
    #   ⇒ 记下的 "after" 指纹与 "before" **完全相同**（看起来像"什么都没写"）。
    #   指纹只有在 WAL 落盘后才有证据价值：先 checkpoint(TRUNCATE) 再关连接，最后取 stat。
    try:
        conn2.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error as e:  # noqa: F821 —— 少见：库不是 WAL 模式
        print("（wal_checkpoint 跳过：", e, "）")
    conn2.close()
    after = _db_stat()
    plan_path.write_text(json.dumps({"generated_at": stamp, "apply": True,
                                     "db_before": before, "db_after": after,
                                     "integrity_check": integrity, "remaining_fullwidth": left,
                                     "changes": changes, "skipped": skipped},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n写库完成。剩余含全角斜杠的行:", left)
    print("integrity_check(后):", integrity)
    print("库指纹(写后):", {k: after[k] for k in ("size", "mtime", "sha256")})
    print("（跳过的那几处仍在 —— 那是**故意**留的，见清单 skipped）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
