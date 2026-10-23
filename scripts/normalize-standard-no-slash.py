"""R6c-2c：把库内**存量**全角斜杠归一（`standard_no` / `short_code` / `standard_name`）。

## 为什么做（证据）
真库 6417 条标准里 **5879 条的 `standard_no` 写全角斜杠 `／`（U+FF0F）**；`short_code` 同样 5879 条。
它们**全部创建于 2026-09-16**（最新一条 13:52:26），而**派生侧的修复在 2026-09-17 就做了**
（`_stdparse.derive_standard` / `std_bulk_import` 都已归一）。

⚠ **2026-09-18 更正（本文件原先写的是"没有活的路径在产生新脏行，剩下的只是存量回填"——那是错的）**：
独立复核 b32 **证伪**了它。至少两条**活的**路径仍会产出全角：
监听到的 `GB／T 10058-2023 电梯技术条件(1).pdf`（`write_queue_bootstrap._ingest_doc` 用 `path.stem`）
与 `var/ocr-loop/ingest_from_manifest.py`（manifest 里 **8205 条带全角**，其中约 2322 条 PDF 尚未入库；
真库现存 `standard_no='GBZ/T'` 那一行就是它 `split_std` 的指纹）。
我当时的"日期论证"也不成立：`created_at >= 2026-09-17` 的行数 = **0**，
"之后 0 条新增"只是因为**这两天压根没入库**。
⇒ 存量回填**必须在入库侧收口之后**才有意义；收口已落在
`text_utils.store_standard_no` + `clause_repo.insert_document`（§11.0 R6c-2d）。
本脚本只负责**存量**，不代替那一步。

## 安全设计（这是动业主的真库，按"可逆 + 可核"做）
1. **默认 dry-run**，只有显式 `--apply` 才写；
2. 写出**完整变更清单** `var/backup/r6c2c-normalize-slash-<ts>.json`（doc_id/列/旧值/新值）——
   这是回滚凭据（每一条都能精确还原）；
3. 只改**字符形状**：`／`→`/`（不动空格、不动破折号，不做任何"顺手"归一）；
4. **撞车保护**：若某行归一后会与**已存在的另一行**同值，**跳过它**并单独列出
   （不制造重复——实测只有 1 处）；⚠ 2026-09-18 复核 b32 之后**补了第二种撞车**
   （"本次计划内自撞"：两行都全角、归一到同一个**尚不存在**的值）——真库 `short_code`
   只有非唯一索引，旧写法会在它上面**静默写重复**（复核已复现）；
5. 单事务写入（`write_transaction`），前/后各跑一次 `PRAGMA integrity_check` 与计数核对；
   ⚠ 每条 UPDATE **带 CAS**（`AND {col}=?`）+ rowcount 校验，任何一条对不上就**整批回滚**
   （防"计划与写入之间被人改过 ⇒ 静默覆盖"）；
6. 不碰任何其它列。**只加一条汇总 `event_log`**（审计痕迹，与写同事务）；
   `updated_at` 刻意**不 bump**（那会让"内容被改过"的 UI 信号说谎）。

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

# ⚠ 让 `_measure_common` 能被导入：**必须把本文件所在的 scripts/ 放进搜索路径**。
#   只在 cwd=仓根、以 `python scripts/xxx.py` 方式跑时才能直接 import；
#   而 `tests/test_classical_segmentation_ruler.py` 是用 `spec_from_file_location`
#   **按文件路径**加载本脚本的 —— 那时 cwd 与 sys.path 都不是 scripts/，
#   直接 import 会 ModuleNotFoundError（2026-10-23 被门禁的 pytest 步当场抓到）。
#   全仓另 10 个脚本用同样的写法处理 `src`，这里照抄同一模式。
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _measure_common import db_stat as _db_stat  # noqa: E402
from ulid import ULID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.storage.sqlite_db import get_db_connection, write_transaction  # noqa: E402

COLS = ("standard_no", "short_code", "standard_name")
FW = "／"
OUT_DIR = ROOT / "var" / "backup"



def _plan(conn) -> tuple[list[dict], list[dict]]:
    """算出变更清单；同时找出"归一后会撞车"的行（那些**跳过**）。

    ⚠ **两种撞车都要看**（独立复核 b32 的 4.4 实测：只防第一种会**静默造重复**）：
      1. 目标值与**库里已存在**的某行相同（下面的 `existing`）；
      2. 目标值与**本次计划里前面某行**相同（`planned`）——两行都写全角、归一到**同一个尚不存在**的值，
         只查 `existing` 是看不见的。真库 `short_code` **只有非唯一索引**（`standard_no` 才有 UNIQUE），
         所以第 2 种在 `short_code` 上会真的写进两行一样的值**并报"写库完成 integrity ok"**。
         复核在一次性库上用真脚本复现过（`('GB/T33332003', 2)`）。
    """
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
    planned: dict[tuple[str, str], str] = {}   # (列, 目标值) → 第一条占位的 doc_id
    for r in rows:
        for col in COLS:
            old = r[col]
            if not old or FW not in old:
                continue
            new = old.replace(FW, "/")
            if new == old:
                continue
            # 撞车（1）：目标值已存在，且不是"这一行自己"
            same_row = conn.execute(
                f"SELECT COUNT(*) n FROM doc_meta WHERE {col}=? AND doc_id=?", (new, r["doc_id"])
            ).fetchone()["n"]
            if new in existing[col] and not same_row:
                skipped.append({"doc_id": r["doc_id"], "column": col, "old": old, "new": new,
                                "why": "归一后会与已存在的另一行同值 ⇒ 跳过，不制造重复"})
                continue
            # 撞车（2）：本次计划内自撞（复核 b32 的 4.4）
            key = (col, new)
            if key in planned:
                skipped.append({"doc_id": r["doc_id"], "column": col, "old": old, "new": new,
                                "why": f"归一后会与**本次计划内** {planned[key]} 同值 ⇒ 跳过，"
                                       "不制造重复（快照式判重看不见这种）"})
                continue
            planned[key] = r["doc_id"]
            changes.append({"doc_id": r["doc_id"], "column": col, "old": old, "new": new})
    # 自检：清单里 (列, 目标值) 不许有重复（防以后改坏上面的判重）
    seen: set[tuple[str, str]] = set()
    for c in changes:
        k = (c["column"], c["new"])
        assert k not in seen, f"计划内自撞漏网: {k}"
        seen.add(k)
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
    # ⚠ 写之前先确认清单仍与库一致（**CAS**，独立复核 b32 的"lost update"那条）：
    #   `WHERE doc_id=?` 不校验现值 ⇒ 计划与写入之间若有人改过这一行，会被**静默覆盖**；
    #   `doc_id` 被并发删掉时 UPDATE 影响 0 行，脚本照样报"写库完成"。
    #   所以：UPDATE 带上 `AND {col}=?`，逐条看 rowcount；**任何一条对不上就整批回滚**（fail-closed），
    #   而不是"写一半再说"——清单是可回滚的凭据，凭据失效时停下来才是对的。
    with write_transaction() as w:
        for c in changes:
            cur = w.execute(f"UPDATE doc_meta SET {c['column']}=? WHERE doc_id=? AND {c['column']}=?",
                            (c["new"], c["doc_id"], c["old"]))
            if cur.rowcount != 1:
                raise RuntimeError(
                    f"现值与计划不一致（doc_id={c['doc_id']} {c['column']}: "
                    f"期望 {c['old']!r}）⇒ 整批回滚，请重跑 dry-run 重新出计划")
        # 审计痕迹（复核 b32 指出：这次动真库在应用自身的审计轨迹里**没有任何痕迹**）。
        # 只加一条**汇总**事件（不逐行 11758 条），同事务落库；`updated_at` 刻意**不 bump**
        # ——那会让"内容被改过"的 UI 信号说谎，而本次只换字符形状。
        w.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type, target_id, metadata)"
            " VALUES (?,?,?,?,?,?)",
            (f"evt_{ULID()}", "standard_no_shape_fix", "script:normalize-standard-no-slash",
             "doc_meta", stamp, json.dumps(
                 {"changes": len(changes), "skipped": len(skipped), "by_column": by_col,
                  "plan": plan_path.name}, ensure_ascii=False)))
    # ⚠ 写后核对用**同一个连接**：`get_db_connection()` 是**线程局部且按线程缓存**的，
    #   再取一次拿到的是同一个对象，`conn2.close()` 会把共享连接关掉
    #   ⇒ 同进程第二次调用直接 `ProgrammingError`（复核 b32 实测复现）。
    left = {col: conn.execute(
        f"SELECT COUNT(*) n FROM doc_meta WHERE {col} LIKE '%／%'").fetchone()["n"] for col in COLS}
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    # ⚠ **必须在 checkpoint 之后再取指纹**（2026-09-18 自己踩到并更正）：
    #   第一次跑时我在写完立刻 `_db_stat()`，而那时改动还在 WAL 里、主库文件**一个字节都没变**
    #   ⇒ 记下的 "after" 指纹与 "before" **完全相同**（看起来像"什么都没写"）。
    #   指纹只有在 WAL 落盘后才有证据价值：先 checkpoint(TRUNCATE) 再取 stat。
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except sqlite3.Error as e:  # noqa: F821 —— 少见：库不是 WAL 模式
        print("（wal_checkpoint 跳过：", e, "）")
    after = _db_stat()
    plan_path.write_text(json.dumps({"generated_at": stamp, "apply": True,
                                     "db_before": before, "db_after": after,
                                     "integrity_check": integrity, "remaining_fullwidth": left,
                                     "audit_event": "standard_no_shape_fix",
                                     "changes": changes, "skipped": skipped},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n写库完成。剩余含全角斜杠的行:", left)
    print("integrity_check(后):", integrity)
    print("库指纹(写后):", {k: after[k] for k in ("size", "mtime", "sha256")})
    print("（跳过的那几处仍在 —— 那是**故意**留的，见清单 skipped）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
