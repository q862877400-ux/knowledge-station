"""统一外发记录助手（Task 10.0：零外发 → 外发可审计）。

D1/D2 落地：所有云端调用（LLM / 未来 rerank / 多模态 / 云解析）的完整 payload 必须落库可审计。
现阶段 LLM 问答链路已由 server.py `_write_debug_dump` 全量落库（query/retrieval_result/prompt/
llm_output/verification_result）；本模块提供：
  1. `record_egress()` —— 非 chat 云调用（rerank/VLM/云解析）的统一登记入口，
     写 debug_dump（trigger_type='egress'），返回 dump_id 即 Trace ID；
  2. `query_egress()` / `export_egress()` —— 审计 API 的只读聚合与导出。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ulid import ULID

from src.core.config import get_settings
from src.core.storage.debug_dump_retention import (
    KEEP_EGRESS, TYPE_EGRESS, prune as prune_debug_dump,
)
from src.core.storage.sqlite_db import get_db_connection

# 审计聚合时视为"外发记录"的 trigger_type 集合
_AUDIT_TRIGGER_TYPES = ("user_export", "egress")

_SERVICE_HINT = re.compile(r"https?://[^/\s]+")


def record_egress(service: str, endpoint: str, payload: Any,
                  response_meta: dict | None = None,
                  query: str | None = None,
                  prompt_preview: str | None = None) -> str:
    """登记一次云端调用。返回 dump_id（即 Trace ID）。

    payload 建议传可 JSON 序列化对象（或原始字符串）；审计 API 会展示摘要而非全文外发。
    """
    conn = get_db_connection()
    dump_id = f"dump_{ULID()}"
    try:
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
    except TypeError:
        payload_json = str(payload)
    logs = json.dumps({
        "service": service,
        "endpoint": endpoint,
        "response_meta": response_meta or {},
        "payload_bytes": len(payload_json.encode("utf-8")),
    }, ensure_ascii=False)
    conn.execute(
        "INSERT INTO debug_dump (dump_id, trigger_type, query, prompt, llm_output, logs)"
        " VALUES (?,?,?,?,?,?)",
        (dump_id, "egress", (query or "")[:500], prompt_preview or payload_json[:4000],
         "", logs))
    # ⚠ **按类型清理**（2026-09-25 修真缺陷）：原先这里是**全表**裁到 1000 行，
    #   而外发审计量大（实测 992/1000、约 110 条/天）⇒ **把"提问证据"挤出去**
    #   （实测：1,000 行里只剩 8 行带检索结果，提问最多活约 9 天）。
    #   详见 `src/core/storage/debug_dump_retention.py` 的模块说明。
    prune_debug_dump(conn, TYPE_EGRESS, KEEP_EGRESS)
    conn.commit()
    return dump_id


def _row_to_audit(row) -> dict:
    """debug_dump 行 → 审计条目（脱敏：只给摘要，不给完整 prompt 外发细节）。"""
    try:
        logs = json.loads(row["logs"] or "{}")
    except Exception:
        logs = {}
    service = logs.get("service") or ("deepseek-chat" if row["trigger_type"] == "user_export"
                                      else row["trigger_type"])
    endpoint = logs.get("endpoint") or ""
    prompt = row["prompt"] or ""
    out = row["llm_output"] or ""
    return {
        "dump_id": row["dump_id"],
        "created_at": row["created_at"],
        "service": service,
        "endpoint": endpoint,
        "query": (row["query"] or "")[:120],
        "payload_bytes": logs.get("payload_bytes", len(prompt.encode("utf-8"))),
        "prompt_preview": re.sub(r"\s+", " ", prompt)[:200],
        "response_preview": re.sub(r"\s+", " ", out)[:200],
        "verification_status": _verification_brief(row["verification_result"]),
        "trace": logs.get("trace") or {},
    }


def _verification_brief(vjson: str | None) -> dict | None:
    if not vjson:
        return None
    try:
        v = json.loads(vjson)
    except Exception:
        return None
    return {"is_valid": v.get("is_valid"),
            "answer_confidence": v.get("answer_confidence")}


def query_egress(limit: int = 50, offset: int = 0,
                 cursor: str | None = None) -> dict:
    """审计聚合（只读）。按时间倒序返回外发记录。

    - ``cursor``：keyset 深翻页（"created_at|dump_id"，取上一页末条的 dump_id/created_at），
      提供时按 (created_at, dump_id) 键集翻页，避免 OFFSET 深翻页扫描（百万级审计日志）；
    - 兼容旧调用：cursor=None 时维持 limit/offset 语义。
    """
    conn = get_db_connection()
    ph = ",".join("?" * len(_AUDIT_TRIGGER_TYPES))
    total = conn.execute(
        f"SELECT COUNT(*) FROM debug_dump WHERE trigger_type IN ({ph})",
        _AUDIT_TRIGGER_TYPES).fetchone()[0]
    order = " ORDER BY created_at DESC, dump_id DESC"
    if cursor:
        c, d = cursor.split("|", 1)
        rows = conn.execute(
            f"SELECT * FROM debug_dump WHERE trigger_type IN ({ph})"
            " AND (created_at < ? OR (created_at = ? AND dump_id < ?))"
            f"{order} LIMIT ?",
            (*_AUDIT_TRIGGER_TYPES, c, c, d, max(1, int(limit)))).fetchall()
    else:
        rows = conn.execute(
            f"SELECT * FROM debug_dump WHERE trigger_type IN ({ph})"
            f"{order} LIMIT ? OFFSET ?",
            (*_AUDIT_TRIGGER_TYPES, max(0, int(limit)), max(0, int(offset)))).fetchall()
    return {"total": total, "items": [_row_to_audit(r) for r in rows]}


def export_egress() -> Path:
    """导出全部外发记录为 JSON 文件（exports 目录，供 /export/download 下载）。"""
    data = query_egress(limit=10000)
    out = get_settings().data_dir / "exports" / \
        f"egress-audit-{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return out
