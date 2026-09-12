"""变更仓储：update_check_batch / update_change_event 读写（阶段六·批次1）。

数据契约：pipeline/02 §2（schema.sql 29/30 号表，CHECK 枚举冻结）。
- 写路径一律经 ``sqlite_db.write_transaction`` 短事务（单写者语义，禁止裸写）；
- 读路径走普通线程局部连接（WAL 读不阻塞写）；
- ULID 用 python-ulid：批次前缀 ``upd_``、事件前缀 ``chg_``；
- 审计：变更检出/去重重放/确认/人工维护均落 event_log（pipeline/05 §4 铁律 4）；
- captcha 结果禁止落库（04a INS-C-01：只返回标记，不误记 gray/failed）。

幂等契约（04a INS-A-04 / INS-D-07）：同一 ``(batch_id, standard_no)`` 重放判定
不新增 chg_ 行——已存在则原位更新并留 dedup 审计。
"""
from __future__ import annotations

import json
from typing import Any

from ulid import ULID

from src.core.storage.sqlite_db import get_db_connection, write_transaction
from src.core.update.channels.base import (
    UPD_BAD_PAYLOAD,
    UPD_BATCH_NOT_FOUND,
    UPD_CAPTCHA_BLOCKED,
    UPD_CHANGE_NOT_FOUND,
    UPD_ILLEGAL_BATCH_STATUS,
    UPD_ILLEGAL_CHANGE_TYPE,
    UPD_ILLEGAL_LEGAL_STATUS,
    UPD_ILLEGAL_TRIGGER,
    CHANGE_TYPES,
    LEGAL_STATUSES,
    UpdateError,
    upd_log,
)

#: update_check_batch.status CHECK 枚举（schema 冻结）
BATCH_STATUSES = ("pending", "running", "paused", "done", "failed")
#: trigger_type CHECK 枚举
TRIGGER_TYPES = ("manual", "scheduled")


# ================================================================ 批次
def create_batch(trigger: str = "manual", total: int = 0) -> dict:
    """新建巡检批次（status=pending），返回批次行 dict。"""
    if trigger not in TRIGGER_TYPES:
        raise UpdateError(f"非法 trigger_type: {trigger}", code=UPD_ILLEGAL_TRIGGER)
    batch_id = f"upd_{ULID()}"
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO update_check_batch (batch_id, trigger_type, status, total)"
            " VALUES (?,?, 'pending', ?)",
            (batch_id, trigger, int(total)))
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "update/batch_created",
             "user" if trigger == "manual" else "system",
             "update_check_batch", batch_id,
             json.dumps({"trigger": trigger, "total": int(total)}, ensure_ascii=False)))
    upd_log(batch_id, "inspector", "INFO", "batch_created", trigger=trigger, total=int(total))
    fresh = get_batch(batch_id)
    assert fresh is not None  # 刚 INSERT 完必存在
    return fresh


def get_batch(batch_id: str) -> dict | None:
    """读单个批次；不存在返回 None。"""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM update_check_batch WHERE batch_id=?",
                       (batch_id,)).fetchone()
    return _batch_dict(row) if row is not None else None


def list_batches(limit: int = 50) -> list[dict]:
    """历史批次（created_at 倒序）。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM update_check_batch ORDER BY created_at DESC, batch_id DESC LIMIT ?",
        (int(limit),)).fetchall()
    return [_batch_dict(r) for r in rows]


def update_progress(batch_id: str, checked: int = 1,
                    red: int = 0, yellow: int = 0, green: int = 0, gray: int = 0) -> dict:
    """原子累加进度计数（首查自动盖 started_at）；四色恒等式由调用方保证。"""
    with write_transaction() as txn:
        cur = txn.execute(
            """UPDATE update_check_batch SET
                 checked = checked + ?, red_count = red_count + ?,
                 yellow_count = yellow_count + ?, green_count = green_count + ?,
                 gray_count = gray_count + ?,
                 started_at = COALESCE(started_at, datetime('now'))
               WHERE batch_id = ?""",
            (int(checked), int(red), int(yellow), int(green), int(gray), batch_id))
        if cur.rowcount == 0:
            raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)
    updated = get_batch(batch_id)
    assert updated is not None  # UPDATE 刚命中，必然存在
    return updated


# ================================================================ 变更事件
def append_change(change: dict[str, Any]) -> str:
    """写入一条标准变更事件，返回 change_id（``chg_<ULID>``）。

    change 字段字典（其余键忽略）：batch_id*/standard_no*/change_type*/source_channel*
    为必填；可选 doc_id/standard_name/current_legal_status/latest_info(dict|str)/
    evidence_url/archived_pdf_path/captcha。

    - ``captcha=True`` → 抛 UPD-1002（仓储层硬闸，captcha 永不入库）；
    - 非法枚举 → UPD-3004 / UPD-3001，事务回滚零脏行（INS-D-06）；
    - 同批同号已存在 → 原位更新复用 change_id（幂等去重，INS-D-07），审计标 dedup。
    """
    # captcha 硬闸最先判：任何携带 captcha 标记的结果都不得触达数据层
    if change.get("captcha"):
        raise UpdateError("captcha 结果只返回标记，禁止写入变更表（INS-C-01）",
                          code=UPD_CAPTCHA_BLOCKED)
    batch_id = change.get("batch_id")
    standard_no = change.get("standard_no")
    change_type = change.get("change_type")
    source_channel = change.get("source_channel")
    missing = [name for name, val in (
        ("batch_id", batch_id), ("standard_no", standard_no),
        ("change_type", change_type), ("source_channel", source_channel)) if not val]
    if missing:
        raise UpdateError(f"append_change 缺少必填字段: {missing}", code=UPD_BAD_PAYLOAD)
    # missing 检查通过 ⇒ 四字段均为真值 str（下方 SQL/日志以 str 使用）
    assert isinstance(batch_id, str) and isinstance(standard_no, str)
    assert isinstance(change_type, str) and isinstance(source_channel, str)
    if change_type not in CHANGE_TYPES:
        raise UpdateError(f"非法 change_type: {change_type}", code=UPD_ILLEGAL_CHANGE_TYPE)
    legal_status = change.get("current_legal_status")
    if legal_status is not None and legal_status not in LEGAL_STATUSES:
        raise UpdateError(f"非法 legal_status: {legal_status}", code=UPD_ILLEGAL_LEGAL_STATUS)

    info = change.get("latest_info")
    info_json = json.dumps(info, ensure_ascii=False) if isinstance(info, dict) else info

    with write_transaction() as txn:
        if txn.execute("SELECT 1 FROM update_check_batch WHERE batch_id=?",
                       (batch_id,)).fetchone() is None:
            raise UpdateError(f"批次不存在: {batch_id}", code=UPD_BATCH_NOT_FOUND)

        existing = txn.execute(
            "SELECT change_id FROM update_change_event WHERE batch_id=? AND standard_no=?",
            (batch_id, standard_no)).fetchone()
        dedup = existing is not None
        if dedup:
            change_id = existing["change_id"]
            txn.execute(
                """UPDATE update_change_event SET
                     doc_id=?, standard_name=?, change_type=?, current_legal_status=?,
                     latest_info_json=?, source_channel=?, evidence_url=?,
                     archived_pdf_path=?, detected_at=datetime('now')
                   WHERE change_id=?""",
                (change.get("doc_id"), change.get("standard_name"), change_type,
                 legal_status, info_json, source_channel, change.get("evidence_url"),
                 change.get("archived_pdf_path"), change_id))
        else:
            change_id = f"chg_{ULID()}"
            txn.execute(
                """INSERT INTO update_change_event
                   (change_id, batch_id, doc_id, standard_no, standard_name, change_type,
                    current_legal_status, latest_info_json, source_channel, evidence_url,
                    archived_pdf_path, user_ack)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,0)""",
                (change_id, batch_id, change.get("doc_id"), standard_no,
                 change.get("standard_name"), change_type, legal_status, info_json,
                 source_channel, change.get("evidence_url"),
                 change.get("archived_pdf_path")))

        metadata = {"batch_id": batch_id, "standard_no": standard_no,
                    "change_type": change_type, "source_channel": source_channel,
                    "dedup": dedup}
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state, metadata) VALUES (?,?,?,?,?,?,?)",
            (str(ULID()), "update/change_detected", "system", "update_change_event",
             change_id,
             json.dumps({"change_type": change_type, "legal_status": legal_status},
                        ensure_ascii=False),
             json.dumps(metadata, ensure_ascii=False)))

    upd_log(batch_id, "inspector", "INFO",
            "change_dedup_replayed" if dedup else "change_detected",
            standard_no=standard_no, change_type=change_type,
            source_channel=source_channel, change_id=change_id)
    return change_id


def mark_ack(change_id: str, ack: bool = True) -> dict:
    """用户确认变更事件（user_ack=0/1），留审计；不存在抛 UPD-2002。

    2026-08-26（巡检确认闭环修复）：确认"废止/被替代"类变更时**同步写回
    doc_meta.legal_status**——此前只标记 user_ack，库状态永不更新，
    已废止标准（如 AQ 3028-2008，2024-07-01 废止）继续被检索当现行引用（用户实测反馈）。
    """
    applied = None
    with write_transaction() as txn:
        cur = txn.execute("UPDATE update_change_event SET user_ack=? WHERE change_id=?",
                          (int(bool(ack)), change_id))
        if cur.rowcount == 0:
            raise UpdateError(f"变更事件不存在: {change_id}", code=UPD_CHANGE_NOT_FOUND)
        if ack:
            row = txn.execute(
                "SELECT doc_id, change_type, current_legal_status FROM update_change_event"
                " WHERE change_id=?", (change_id,)).fetchone()
            if row and row["doc_id"]:
                new_status = row["current_legal_status"]
                if (new_status in ("withdrawn", "superseded")
                        and row["change_type"] in ("withdrawn", "superseded")):
                    dm = txn.execute(
                        "SELECT legal_status FROM doc_meta WHERE doc_id=?",
                        (row["doc_id"],)).fetchone()
                    if dm and dm["legal_status"] != new_status:
                        txn.execute(
                            "UPDATE doc_meta SET legal_status=?, updated_at=datetime('now')"
                            " WHERE doc_id=?", (new_status, row["doc_id"]))
                        txn.execute(
                            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                            " target_id, before_state, after_state) VALUES (?,?,?,?,?,?,?)",
                            (str(ULID()), "update/status_applied_to_doc", "user", "doc_meta",
                             row["doc_id"],
                             json.dumps({"legal_status": dm["legal_status"]},
                                        ensure_ascii=False),
                             json.dumps({"legal_status": new_status}, ensure_ascii=False)))
                        applied = {"doc_id": row["doc_id"], "legal_status": new_status}
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, after_state) VALUES (?,?,?,?,?,?)",
            (str(ULID()), "update/change_ack", "user", "update_change_event", change_id,
             json.dumps({"user_ack": int(bool(ack))}, ensure_ascii=False)))
    upd_log("-", "inspector", "INFO", "change_ack", change_id=change_id,
            user_ack=int(bool(ack)),
            applied=json.dumps(applied or {}, ensure_ascii=False))
    return {"change_id": change_id, "user_ack": bool(ack), "applied": applied}


def manual_status(change_id: str, legal_status: str,
                  note: str | None = None) -> dict:
    """人工维护法律状态（manual 渠道语义）：校验枚举、原值入审计 before_state。"""
    if legal_status not in LEGAL_STATUSES:
        raise UpdateError(f"非法 legal_status: {legal_status}", code=UPD_ILLEGAL_LEGAL_STATUS)
    with write_transaction() as txn:
        row = txn.execute(
            "SELECT current_legal_status, latest_info_json FROM update_change_event"
            " WHERE change_id=?", (change_id,)).fetchone()
        if row is None:
            raise UpdateError(f"变更事件不存在: {change_id}", code=UPD_CHANGE_NOT_FOUND)
        old_status = row["current_legal_status"]
        try:
            info: dict[str, Any] = json.loads(row["latest_info_json"] or "{}")
            if not isinstance(info, dict):
                info = {}
        except (TypeError, ValueError):
            info = {}
        info["manual_note"] = note
        txn.execute(
            "UPDATE update_change_event SET current_legal_status=?, latest_info_json=?"
            " WHERE change_id=?",
            (legal_status, json.dumps(info, ensure_ascii=False), change_id))
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, before_state, after_state, metadata) VALUES (?,?,?,?,?,?,?,?)",
            (str(ULID()), "update/manual_status", "user", "update_change_event", change_id,
             json.dumps({"legal_status": old_status}, ensure_ascii=False),
             json.dumps({"legal_status": legal_status}, ensure_ascii=False),
             json.dumps({"note": note}, ensure_ascii=False)))
    upd_log("-", "inspector", "INFO", "manual_status_applied",
            change_id=change_id, from_status=old_status, to_status=legal_status)
    return {"change_id": change_id, "current_legal_status": legal_status}


# ================================================================ 内部工具
def _batch_dict(row) -> dict:  # noqa: ANN001 — sqlite3.Row
    d = dict(row)
    for key in ("total", "checked", "red_count", "yellow_count", "green_count",
                "gray_count"):
        d[key] = int(d.get(key) or 0)
    return d
