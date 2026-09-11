"""监听文件夹自动入库（Task 11.2）：2 秒轮询（P4 少依赖，不用 watchdog）。

流程：扫描目录 → file_hash 防重（doc_meta + 目录内已处理清单）→ 入 write_queue
（operation_type='ingest_doc'，payload 含路径/格式）→ 由单写者队列串行执行。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.core.storage.sqlite_db import get_db_connection
from src.core.storage.write_queue import enqueue

SUPPORTED = {".pdf", ".docx"}


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _already_ingested(hash_: str) -> bool:
    conn = get_db_connection()
    return conn.execute("SELECT 1 FROM doc_meta WHERE file_hash=?", (hash_,)).fetchone() is not None


def scan_and_enqueue(directory: Path) -> list[dict]:
    """扫描目录中未入库的新文件并入队。返回本次入队清单。"""
    if not directory.exists():
        return []
    conn = get_db_connection()
    # 目录内已入队文件（避免重启后重复入队）
    queued = {json.loads(r["payload"]).get("path") for r in conn.execute(
        "SELECT payload FROM write_queue WHERE operation_type='ingest_doc'").fetchall()}
    enqueued: list[dict] = []
    for p in sorted(directory.iterdir()):
        if not p.is_file() or p.suffix.lower() not in SUPPORTED:
            continue
        if _already_ingested(_file_hash(p)):
            continue
        if str(p) in queued:
            continue
        enqueue("ingest_doc", {"path": str(p), "suffix": p.suffix.lower()})
        enqueued.append({"path": str(p), "status": "queued"})
    return enqueued


def ingest_queue_status() -> dict:
    """入库队列状态（排队/解析中/完成/失败计数 + 明细）。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT operation_type, status, payload, result, created_at, processed_at"
        " FROM write_queue WHERE operation_type='ingest_doc'"
        " ORDER BY queue_id DESC LIMIT 50").fetchall()
    items = []
    for r in rows:
        try:
            payload = json.loads(r["payload"])
        except Exception:
            payload = {}
        items.append({"status": r["status"], "path": payload.get("path", ""),
                      "result": r["result"], "created_at": r["created_at"],
                      "processed_at": r["processed_at"]})
    counts = {"queued": 0, "done": 0, "failed": 0}
    for it in items:
        counts[it["status"] if it["status"] in counts else "queued"] += 1
    return {"counts": counts, "items": items}
