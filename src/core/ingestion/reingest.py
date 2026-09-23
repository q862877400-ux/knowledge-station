"""「重来一次」——把**已经在库里的**文件重新解析一遍（KB-FOLDER-PLAN 第 4 步）。

## 为什么需要它（三条都走不通的回头路）

真库里有 2 篇 ``catalog_hidden=1`` 的真标准（``GB/T 12668.8-2017``、``GB 9706.222-2022``）：
页面上看不到（所有目录读取都带 ``catalog_hidden = 0``）、拿**同一个文件**重传被判
``duplicate``、换**一份扫描件**重传被判 ``standard_exists``、而"明知重复也重来"的开关以前
只挂在法律法规那条路上（``/api/v1/laws/ingest``）⇒ **没有一条走得通的回头路**。
本模块就是那条路。

## 纪律（写在这里，免得下一个人改歪）

* **不另写一套解析**：全程只有 ``run_full_ingest(..., reingest=True)`` —— 那条路径
  ``run_full_ingest`` 里本来就有（新开一个 ``doc_id``、删掉同标准号的旧文档）。
* **用户的整理成果必须跟着走**（2026-09-24 审计 A1）：重导会换 ``doc_id``，而"这一篇在
  哪些目录里"（``folder_member``，多对多）与它的归位记录（``doc_filing_state``）都不是
  文档表的附庸（**没有表级 FK**）⇒ 换 id 时**必须原样搬过去**。搬的那一半在
  ``run_full_ingest`` 的 reingest 块里（删旧文档**前**拍快照、入库**成功后**落到新 id），
  本模块只把结果如实带出来（``filing_assets_carried``）。
* **不猜**：源文件路径取 ``doc_meta.file_path``。它不是一个真实存在的文件时**如实跳过**
  并把原因返回给调用方（批量导入的快扫占位行、文件被移走的行都属于这一类），
  **不许**拿标准号去磁盘上瞎找。
* **真解析要几十秒到几十分钟**（扫描件要 OCR）⇒ 起后台线程、端点**立刻**返回；
  进度由 ``doc_filing_state.stage`` 表达（``recognizing`` → ``confirming`` / ``failed``），
  界面靠它如实显示，**不编一个假进度条**。
* **同一时刻只跑一批**（进程内锁）：拿不到锁回 ``reingest_busy``（409），
  **不排队** —— 用户点了按钮该看到"已经在跑了"，不是"排在后面"。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("ks.ingestion.reingest")

#: 一次最多接几篇（后台线程串行解析；防"手一抖选 379 篇"把机器占死一整天）。
MAX_REINGEST_DOCS = 50

#: 进程内的"正在跑"标志（拿不到 = 已经有一批在跑）与最近一次的进度快照。
_LOCK = threading.Lock()
_PROGRESS: dict[str, Any] = {"running": False, "total": 0, "done": 0, "results": [],
                             "started_at": None, "finished_at": None, "last_error": None}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def plan_reingest(doc_ids: list[str]) -> dict:
    """**只读**：这一批里哪些能重来、哪些不能（各自为什么）。不写库、不起线程。"""
    from src.core.storage.sqlite_db import get_db_connection

    ids = [str(d) for d in doc_ids if str(d).strip()]
    if not ids:
        raise ValueError("doc_ids 不能为空")
    if len(ids) > MAX_REINGEST_DOCS:
        raise ValueError(f"一次最多 {MAX_REINGEST_DOCS} 篇，收到 {len(ids)} 篇")
    conn = get_db_connection()
    ph = ",".join("?" * len(ids))
    rows = {r["doc_id"]: dict(r) for r in conn.execute(
        f"SELECT doc_id, file_path, standard_no, standard_name, doc_type"
        f" FROM doc_meta WHERE doc_id IN ({ph})", ids)}
    ready: list[dict] = []
    skipped: list[dict] = []
    for doc_id in ids:
        row = rows.get(doc_id)
        if row is None:
            skipped.append({"doc_id": doc_id, "reason": "库里没有这一篇（doc_not_found）"})
            continue
        raw = str(row.get("file_path") or "").strip()
        # 快扫占位行的 file_path 是**真实路径**，但有些行（历史/异常）存的是标记 JSON
        # 或是空串 ⇒ 只认"磁盘上真的存在那个文件"。
        if raw == "" or raw.startswith("{"):
            skipped.append({"doc_id": doc_id,
                            "reason": "这一篇没有可用的源文件路径（没法重新解析）"})
            continue
        p = Path(raw)
        if not p.is_file():
            skipped.append({"doc_id": doc_id,
                            "reason": f"源文件不在磁盘上：{raw}"})
            continue
        ready.append({"doc_id": doc_id, "path": str(p),
                      "standard_no": str(row.get("standard_no") or ""),
                      "standard_name": str(row.get("standard_name") or ""),
                      "doc_type": str(row.get("doc_type") or "standard")})
    return {"ready": ready, "skipped": skipped}


def _run(items: list[dict]) -> None:
    """后台线程：串行重导每一篇。状态由 pipeline 写（见模块头）。"""
    from src.core.ingestion.pipeline import run_full_ingest

    for it in items:
        result: dict[str, Any] = {"doc_id": it["doc_id"], "standard_no": it["standard_no"]}
        try:
            out = run_full_ingest(Path(it["path"]), it["standard_no"], it["standard_name"],
                                  doc_type=it["doc_type"], reingest=True)
            result["status"] = str(out.get("status"))
            result["new_doc_id"] = out.get("doc_id")
            result["total_clauses"] = out.get("total_clauses")
            result["filing_stage"] = out.get("filing_stage")
            result["filing_failure_kind"] = out.get("filing_failure_kind")
            result["catalog_hidden"] = out.get("catalog_hidden")
            # 归属与归位记录的搬运结果（审计 A1 的修法）：None = 没有旧文档要替换；
            # 否则 = {moved_members, stage, carried_fields, …}（搬了几条、最终 stage）。
            result["filing_assets_carried"] = out.get("filing_assets_carried")
            if out.get("status") != "ok":
                # 没成功 ⇒ 旧行还在（reingest 的删除只发生在解析成功之后）：写"识别失败"，
                # 别让它永远停在「识别中」。
                _write_failed(it["doc_id"], str(out.get("message") or out.get("status")))
        except Exception as exc:                            # noqa: BLE001
            logger.warning("重导失败 doc=%s", it["doc_id"], exc_info=True)
            result["status"] = "error"
            result["error"] = f"{type(exc).__name__}: {exc}"
            _write_failed(it["doc_id"], f"解析中断（{type(exc).__name__}）")
        _PROGRESS["results"].append(result)
        _PROGRESS["done"] = len(_PROGRESS["results"])
    _PROGRESS["running"] = False
    _PROGRESS["finished_at"] = _now()
    try:
        _LOCK.release()
    except RuntimeError:                                    # 理论上到不了；宁可记日志也不炸线程
        logger.warning("reingest 锁释放异常（可能已被释放）")


def _write_failed(doc_id: str, reason: str) -> None:
    from src.core.ingestion.pipeline import _write_filing_state
    _write_filing_state(doc_id, "failed", failure_kind=reason[:200])


def start_reingest(doc_ids: list[str]) -> dict:
    """起一批「重来一次」：写 ``recognizing`` + 起后台线程，**立刻**返回。

    ``{queued, started:[{doc_id,…}], skipped:[{doc_id,reason}]}``；已有批次在跑 ⇒
    ``RuntimeError("reingest_busy")``（路由映射成 409）。
    """
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError("reingest_busy")
    try:
        plan = plan_reingest(doc_ids)
        from src.core.ingestion.pipeline import _write_filing_state
        marked: list[dict] = []
        for it in plan["ready"]:
            _write_filing_state(it["doc_id"], "recognizing", failure_kind=None)
            marked.append(it)
        _PROGRESS.update({"running": bool(marked), "total": len(marked), "done": 0,
                          "results": [], "started_at": _now(), "finished_at": None,
                          "last_error": None})
        if not marked:
            _LOCK.release()
            return {"queued": 0, "started": [], "skipped": plan["skipped"]}
        threading.Thread(target=_run, args=(marked,), daemon=True,
                         name="ks-reingest").start()
        return {"queued": len(marked), "started": marked, "skipped": plan["skipped"]}
    except Exception:
        # 起不来（参数错/写库错）⇒ 释放锁，别把"重来一次"永久锁死。
        if _LOCK.locked():
            try:
                _LOCK.release()
            except RuntimeError:
                pass
        raise


def reingest_status() -> dict:
    """最近一批「重来一次」的进度（**如实**：running/total/done + 逐篇结果）。"""
    return dict(_PROGRESS, results=list(_PROGRESS.get("results", [])))
