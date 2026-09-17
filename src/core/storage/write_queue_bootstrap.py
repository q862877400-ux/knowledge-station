"""单写者队列消费端接线（2026-08-26，P2-①）：引擎启动时启动 WriteWorker，
分发 write_queue 操作——``ingest_doc`` → run_full_ingest/run_docx_ingest（watcher 闭环，
修复"监听文件夹只入队不消费"）；未知类型记 warning 并标记 done（不再永久 pending）。

背景：WriteWorker 类早已实现（串行消费/崩溃恢复/event_log 审计）但从未被实例化——
v4.3 六条红线之一"单写者队列"名存实亡；watcher 入队的 ingest_doc 永远卡 pending。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.core.storage.write_queue import WriteWorker
from src.core.text_utils import clean_standard_name

log = logging.getLogger(__name__)
_worker: WriteWorker | None = None


def _ingest_doc(payload: dict[str, Any]) -> dict[str, Any]:
    from src.core.ingestion.pipeline import run_full_ingest
    from src.core.ingestion.docx_ingest import run_docx_ingest
    from src.core.knowledge.auto_tag import auto_tag

    path = Path(str(payload.get("path", "")))
    if not path.exists():
        raise FileNotFoundError(f"watcher 文件不存在: {path}")
    # 标准号/标签从文件名推断（auto_tag 规则层）；内容级标准号在入库后由 auto_tag 落 doc_meta
    tags = auto_tag("", filename=path.name)
    std = tags.standard_no or path.stem
    # ⚠ 2026-09-17 修：原为 `name = path.stem`（**原始 stem**，同时带着标准号前缀与
    # 副本后缀 `(1)`）——这正是库内 :139 行 `standard_name` 变成 `电梯技术条件(1)` 的来源。
    # 监听到的文件名普遍形如 `GB／T 10058-2023 电梯技术条件(1).pdf`（全角斜杠），
    # 故必须走归一派生（剥开头标准号 + 去结尾副本后缀）。
    name = clean_standard_name(path.stem, standard_no=std) or path.stem
    if path.suffix.lower() == ".pdf":
        return run_full_ingest(path, std, name)
    if path.suffix.lower() == ".docx":
        return run_docx_ingest(path, std, name)
    raise ValueError(f"不支持的监听文件类型: {path.suffix}")


def _handle(op_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    if op_type == "ingest_doc":
        return _ingest_doc(payload)
    # 其余类型暂未接线：直写路径已覆盖（bookmark/annotation/feedback 等走 storage 层），
    # 队列中出现的未知类型跳过并标记 done，避免永久 pending
    log.warning("write_queue 未注册 operation_type=%s，跳过（不悬挂）", op_type)
    return {"skipped": op_type}


def start_write_worker() -> None:
    """引擎启动时调用（server.run 内，uvicorn 拉起前）。幂等。"""
    global _worker
    if _worker is not None:
        return
    _worker = WriteWorker(_handle)
    _worker.start()
    log.info("write_queue 消费端已启动（ingest_doc → run_full_ingest / run_docx_ingest）")


def stop_write_worker() -> None:
    """引擎退出时调用。"""
    global _worker
    if _worker is not None:
        _worker.stop(drain=False)
        _worker = None
