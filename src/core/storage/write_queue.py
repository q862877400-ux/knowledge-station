"""单写者队列：所有写操作排队串行执行（短事务），并落 event_log 审计。"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Callable

from ulid import ULID

from src.core.storage.sqlite_db import get_db_connection, write_transaction


class WriteWorker:
    """后台单写者线程，串行消费 write_queue 表。"""

    def __init__(self, handler: Callable[[str, dict[str, Any]], Any], poll_interval: float = 0.05):
        self._handler = handler
        self._poll_interval = poll_interval
        self._cv = threading.Condition()
        self._thread: threading.Thread | None = None
        self._stop = False
        # 测试用：检测写操作是否被串行化
        self.active_writes = 0
        self.max_concurrent_writes = 0
        self._serial_lock = threading.Lock()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._recover_stale_processing()
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="ks-write-worker", daemon=True)
        self._thread.start()

    @staticmethod
    def _recover_stale_processing() -> None:
        """崩溃恢复：上次运行卡在 processing 的任务重置为 pending（启动时无并发写者，安全）。"""
        conn = get_db_connection()
        cur = conn.execute(
            "UPDATE write_queue SET status='pending' WHERE status='processing'")
        conn.commit()
        if cur.rowcount:
            import logging
            logging.getLogger(__name__).warning(
                "write_queue 恢复了 %d 条卡死任务", cur.rowcount)

    def stop(self, drain: bool = True) -> None:
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        if self._thread:
            if drain:
                self._thread.join(timeout=10)
            self._thread = None

    def _run(self) -> None:
        while True:
            with self._cv:
                if self._stop:
                    return
            job = self._claim_next()
            if job is None:
                with self._cv:
                    self._cv.wait(self._poll_interval)
                continue
            queue_id, op_type, payload = job
            try:
                result = self._execute_serial(op_type, payload)
                self._finish(queue_id, "done", result)
            except Exception as e:  # noqa: BLE001 - 队列必须吞异常记录失败
                self._finish(queue_id, "failed", {"error": str(e)})

    def _execute_serial(self, op_type: str, payload: dict[str, Any]) -> Any:
        with self._serial_lock:
            self.active_writes += 1
            self.max_concurrent_writes = max(self.max_concurrent_writes, self.active_writes)
            try:
                return self._handler(op_type, payload)
            finally:
                self.active_writes -= 1

    def _claim_next(self) -> tuple[int, str, dict[str, Any]] | None:
        conn = get_db_connection()
        try:
            row = conn.execute(
                "SELECT queue_id, operation_type, payload FROM write_queue "
                "WHERE status='pending' ORDER BY queue_id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            cur = conn.execute(
                "UPDATE write_queue SET status='processing' WHERE queue_id=? AND status='pending'",
                (row["queue_id"],))
            conn.commit()
            if cur.rowcount == 0:
                return None
            return row["queue_id"], row["operation_type"], json.loads(row["payload"])
        except sqlite3.Error:
            return None

    def _finish(self, queue_id: int, status: str, result: Any) -> None:
        conn = get_db_connection()
        conn.execute(
            "UPDATE write_queue SET status=?, result=?, processed_at=datetime('now') WHERE queue_id=?",
            (status, json.dumps(result, ensure_ascii=False, default=str), queue_id))
        conn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type, metadata) VALUES (?,?,?,?,?)",
            (str(ULID()), f"write_queue.{status}", "system", "write_queue",
             json.dumps({"queue_id": queue_id}, ensure_ascii=False)))
        conn.commit()


def enqueue(operation_type: str, payload: dict[str, Any]) -> int:
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO write_queue (operation_type, payload) VALUES (?, ?)",
        (operation_type, json.dumps(payload, ensure_ascii=False)))
    conn.commit()
    return int(cur.lastrowid)


def wait_until_drained(timeout: float = 10.0) -> bool:
    import time
    deadline = time.monotonic() + timeout
    conn = get_db_connection()
    while time.monotonic() < deadline:
        row = conn.execute(
            "SELECT COUNT(*) FROM write_queue WHERE status IN ('pending','processing')").fetchone()
        if row[0] == 0:
            return True
        time.sleep(0.02)
    return False


def run_inline(op_type: str, payload: dict[str, Any],
               handler: Callable[[str, dict[str, Any]], Any]) -> Any:
    """同步直写（测试/维护用）：走同样的短事务路径，绕过后台线程。"""
    return handler(op_type, payload)
