"""常驻看门狗：保证 KnowledgeStation「自动续接」链不停摆。

背景
----
本机 app 的自动化调度器**只对"未来槽位"触发**；一旦某轮的槽位过期，就永远不会补触发。
（实测：+1 / +3 / +15 分钟余量的自链都出现过接不上。）

本脚本是**独立常驻进程**：每 60 秒检查一次 app 的 `workbuddy.db`（表 `automations`），
发现本任务"已过期且交接单长时间没动"就把它重新上弦（`next_run_at` / `scheduled_at` 设到未来）。

顺带修一处不一致：`schedule_type='once'` 却残留 `rrule` —— 自动清空。

安全边界
--------
- 只读写 **一个** 任务行（`TASK_ID`），绝不碰别的任务。
- 只改 `next_run_at` / `scheduled_at` / `status` / `rrule` / `updated_at`，不删行、不改 prompt。
- 全程 try/except，出错只写日志、绝不退出。
- 锁文件防多开。

用法
----
    <python> autochain-watchdog.py            # 常驻
    <python> autochain-watchdog.py --once     # 只跑一轮（调试）
    <python> autochain-watchdog.py --stop     # 删锁
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---------------- 配置 ----------------
DB = Path("C:/Users/Zegel/.workbuddy-ai/workbuddy.db")
TASK_ID = "1b206fd3-357f-47a1-bf5b-e17ec5c419a3"
HANDOFF = Path("D:/AI/work space/zcode/.workbuddy-ai/memory/AUTO-CHAIN-HANDOFF.md")
LOGFILE = Path("D:/AI/work space/zcode/.workbuddy-ai/memory/autochain-watchdog.log")
LOCKFILE = Path("D:/AI/work space/zcode/.workbuddy-ai/memory/autochain-watchdog.lock")

LOOP_S = 60              # 检查间隔（秒）
OVERDUE_MS = 120_000     # 槽位过期超过这个数才算"卡住"（毫秒）
HANDOFF_STALE_S = 300    # 交接单超过这个秒数没动才算"链停了"
REARM_LEAD_S = 120       # 重新上弦时给调度器留的余量（秒）
MAX_LOG_BYTES = 2_000_000


def now_ms() -> int:
    return int(time.time() * 1000)


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%dT%H:%M:%S")


def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    line = f"[{ts()}] {msg}"
    try:
        if LOGFILE.exists() and LOGFILE.stat().st_size > MAX_LOG_BYTES:
            LOGFILE.write_text("", encoding="utf-8")
        with LOGFILE.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass
    print(line, flush=True)


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB), timeout=10)
    con.execute("PRAGMA busy_timeout=10000")
    return con


def tick(verbose: bool) -> None:
    n = now_ms()
    if not DB.exists():
        log("DB 不存在，跳过")
        return
    con = connect()
    try:
        row = con.execute(
            "select schedule_type, rrule, next_run_at, scheduled_at, status "
            "from automations where id = ?",
            (TASK_ID,),
        ).fetchone()
        if row is None:
            log("任务行不存在，跳过")
            return
        stype, rrule, next_run, sched, status = row

        # 1) 修不一致：once 却带 rrule
        if stype == "once" and (rrule or "").strip() != "":
            con.execute("update automations set rrule = '' where id = ?", (TASK_ID,))
            con.commit()
            log(f"修：清空残留 rrule（原 {rrule!r}）")

        # 2) 判定卡住
        nxt = int(next_run) if next_run is not None else None
        overdue = nxt is not None and (n - nxt) > OVERDUE_MS
        status_bad = status != "ACTIVE"
        try:
            stale_s = time.time() - HANDOFF.stat().st_mtime
        except FileNotFoundError:
            stale_s = 10**9
        stale = stale_s > HANDOFF_STALE_S

        if (overdue or status_bad) and stale:
            target = n + REARM_LEAD_S * 1000
            con.execute(
                "update automations set next_run_at = ?, scheduled_at = ?, "
                "status = 'ACTIVE', updated_at = ? where id = ?",
                (target, iso(target), n, TASK_ID),
            )
            con.commit()
            od = f"{(n - nxt) // 1000}s" if nxt else "?"
            log(
                f"★ 重新上弦：status={status} next_run={sched}(过期 {od}) "
                f"handoff落后={stale_s:.0f}s ⇒ {iso(target)}"
            )
        else:
            od = f"{(n - nxt) // 1000}s" if nxt else "?"
            log(
                f"正常：status={status} next_run={sched}(过期 {od}) "
                f"handoff落后={stale_s:.0f}s"
            )
    finally:
        con.close()


def main() -> int:
    if "--stop" in sys.argv:
        try:
            LOCKFILE.unlink()
            print("lock removed")
        except FileNotFoundError:
            print("no lock")
        return 0

    once = "--once" in sys.argv

    if not once:
        if LOCKFILE.exists():
            age = time.time() - LOCKFILE.stat().st_mtime
            if age < 900:
                print(f"另一个看门狗在跑（锁 {age:.0f}s 前），退出")
                return 1
            log(f"锁已陈旧（{age:.0f}s），接管")
        LOCKFILE.write_text(str(os.getpid()), encoding="utf-8")

    log(f"=== 看门狗启动 pid={os.getpid()} once={once} task={TASK_ID} ===")
    try:
        while True:
            try:
                if not once:
                    LOCKFILE.write_text(str(os.getpid()), encoding="utf-8")
                tick(verbose=once)
            except Exception as exc:  # noqa: BLE001
                log(f"本轮异常（已吞）：{type(exc).__name__}: {exc}")
            if once:
                break
            time.sleep(LOOP_S)
    finally:
        if not once:
            try:
                LOCKFILE.unlink()
            except FileNotFoundError:
                pass
            log("=== 看门狗退出 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
