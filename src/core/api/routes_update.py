"""更新模块 API 路由（2026-08-26，P3-②）：从 server.py create_app 闭包抽出。

- /api/v1/update/*（巡检/变更/报告）、/discover/*（找标）、/ingest/bulk/*（万级批量）、
  /data/package/*（打包）与领域订阅；
- ``_upd_runs`` 进程内登记由闭包移到模块级（语义不变：与 DB status='running' 构成双闸）。
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from fastapi import Request

from src.core.storage.sqlite_db import get_db_connection

logger = logging.getLogger(__name__)

# 运行中巡检批次的进程内登记（与 DB status='running' 构成双闸，防并发巡检）
_upd_runs_lock = threading.Lock()
_upd_runs: set[str] = set()


def _upd_error(e: Exception, json_error):
    """UpdateError/KnowledgeStationError → 业务错误响应：
    not_found 族（UPD-2003 批次 / UPD-2002 变更 / UPD-2005 公告源）→ 404，
    其余校验/冲突 → 422。"""
    from src.core.update.channels.base import (
        UPD_ANNOUNCE_SOURCE_NOT_FOUND, UPD_BATCH_NOT_FOUND, UPD_CHANGE_NOT_FOUND)
    code = getattr(e, "code", "internal_error")
    status = 404 if code in (UPD_BATCH_NOT_FOUND, UPD_CHANGE_NOT_FOUND,
                             UPD_ANNOUNCE_SOURCE_NOT_FOUND) else 422
    return json_error(status, code, str(e))


def register(app, json_error):
    @app.post("/api/v1/update/check")
    async def update_check(request: Request):
        """一键检查更新（F-01）：建 manual 巡检批次 → 后台线程执行，响应立即返回。

        - 已有运行中的巡检批次（DB running 或本进程在跑）→ 409/UPD-2001 拒绝，
          绝不并发巡检；
        - ``tier`` 可选：tier0（默认，特别关注 ∪ 未首检）/ tier1（全库滚动）；
        - 后台执行沿用 fire-and-forget daemon 线程模式（同 office_roundtrip /
          watcher 的轻量线程口径），前端经 GET /update/batch/{id} 1s 轮询进度。
        """
        import threading
        from src.core.update import inspector
        from src.core.update.channels.base import UPD_BATCH_ALREADY_RUNNING
        try:
            body = await request.json()
        except Exception:
            body = {}
        tier = body.get("tier") or "tier0"
        with _upd_runs_lock:
            conn = get_db_connection()
            row = conn.execute(
                "SELECT batch_id FROM bulk_import_batch"
                " WHERE batch_kind='inspect' AND status='running'"
                " ORDER BY created_at DESC LIMIT 1").fetchone()
            running_id = next(iter(_upd_runs), None) or \
                (row["batch_id"] if row else None)
            if running_id:
                return json_error(409, UPD_BATCH_ALREADY_RUNNING,
                                   f"已有运行中的巡检批次: {running_id}")
            try:
                batch = inspector.create_inspect_batch(tier=tier, trigger="manual")
            except Exception as e:  # noqa: BLE001 — 非法 tier 等 → 校验层错误
                return json_error(422, getattr(e, "code", "UPD-3005"), str(e))
            _upd_runs.add(batch["batch_id"])   # 先登记再起线程，闭合竞态窗口

        def _run():
            try:
                inspector.run_batch(batch["batch_id"])
            except Exception as exc:  # noqa: BLE001 — 后台线程必须吞异常存活
                logger.warning("update batch %s 执行失败: %s",
                               batch["batch_id"], exc)
            finally:
                with _upd_runs_lock:
                    _upd_runs.discard(batch["batch_id"])

        threading.Thread(target=_run, name=f"ks-update-run-{batch['batch_id']}",
                         daemon=True).start()
        return {"code": 200, "status": "success",
                "data": {"batch_id": batch["batch_id"],
                         "status": batch["status"], "total": batch["total"]}}

    @app.get("/api/v1/update/batch/{batch_id}")
    async def update_batch_progress(batch_id: str):
        """进度+统计（前端任务小卡片 1s 轮询，契约明确不走 SSE）。"""
        from src.core.update import inspector
        batch = inspector.get_inspect_batch(batch_id)
        if batch is None:
            return json_error(404, "UPD-2003", f"批次不存在: {batch_id}")
        out = {k: v for k, v in batch.items() if k != "checkpoint_json"}
        try:
            ckpt = json.loads(batch.get("checkpoint_json") or "{}")
            if not isinstance(ckpt, dict):
                ckpt = {}
        except (TypeError, ValueError):
            ckpt = {}
        out["pause_reason"] = ckpt.get("pause_reason")
        out["pending"] = len(ckpt.get("queue") or [])
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/batch/{batch_id}/pause")
    async def update_batch_pause(batch_id: str):
        """断点暂停：运行中在块边界落 checkpoint 后转 paused；幂等；不存在 → 404。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import inspector
        try:
            out = inspector.pause_batch(batch_id)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/batch/{batch_id}/resume")
    async def update_batch_resume(batch_id: str):
        """断点恢复：仅 paused 可续跑（后台线程执行，不阻塞响应）；
        不存在 → 404/UPD-2003；终态 → 422/UPD-3005；running/pending 原样返回。"""
        import threading
        from src.core.update import inspector
        batch = inspector.get_inspect_batch(batch_id)
        if batch is None:
            return json_error(404, "UPD-2003", f"批次不存在: {batch_id}")
        if batch["status"] in ("done", "failed"):
            return json_error(422, "UPD-3005",
                               f"批次已终态({batch['status']})，拒绝重启: {batch_id}")

        def _run():
            try:
                inspector.resume_batch(batch_id)
            except Exception as exc:  # noqa: BLE001 — 后台线程吞异常存活
                logger.warning("update batch %s 恢复失败: %s", batch_id, exc)

        if batch["status"] == "paused":
            threading.Thread(target=_run, name=f"ks-update-resume-{batch_id}",
                             daemon=True).start()
        return {"code": 200, "status": "success", "data": batch}

    @app.get("/api/v1/update/batches")
    async def update_batches(limit: int = 20):
        """历史批次（created_at 倒序）。"""
        from src.core.update import change_repo
        return {"code": 200, "status": "success",
                "data": change_repo.list_batches(limit)}

    @app.get("/api/v1/update/changes")
    async def update_changes(batch_id: str | None = None,
                             change_type: str | None = None, limit: int = 200):
        """变更明细（三色列表数据源）；可按批次 / change_type 过滤。"""
        conn = get_db_connection()
        where: list[str] = []
        args: list[object] = []
        if batch_id:
            where.append("batch_id=?")
            args.append(batch_id)
        if change_type:
            where.append("change_type=?")
            args.append(change_type)
        sql = "SELECT * FROM update_change_event"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY detected_at DESC, change_id DESC LIMIT ?"
        args.append(int(limit))
        rows = conn.execute(sql, args).fetchall()
        return {"code": 200, "status": "success",
                "data": [dict(r) for r in rows], "total": len(rows)}

    @app.post("/api/v1/update/changes/{change_id}/ack")
    async def update_change_ack(change_id: str, request: Request):
        """用户确认变更事件（body 可选 {"ack": bool}，缺省确认）。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import change_repo
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            out = change_repo.mark_ack(change_id, bool(body.get("ack", True)))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/changes/{change_id}/manual")
    async def update_change_manual(change_id: str, request: Request):
        """人工维护法律状态 ``{legal_status,note}``（manual 渠道语义）。

        非法枚举 → 422/UPD-3001（base.py 冻结错误码表：3001=illegal_legal_status；
        3003 为 batch_not_found，故此处按模块实现抛出的校验层码透传）。
        """
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import change_repo
        try:
            body = await request.json()
        except Exception:
            body = {}
        legal_status = body.get("legal_status")
        if not legal_status:
            return json_error(422, "UPD-3001", "缺少 legal_status")
        try:
            out = change_repo.manual_status(change_id, str(legal_status),
                                            body.get("note"))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/report/{batch_id}")
    async def update_report(batch_id: str):
        """生成《更新检查报告》docx 到 exports 目录，返回下载文件名
        （配合既有 GET /export/download 下载）；批次不存在 → 404/UPD-2003。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import report as upd_report
        try:
            path = upd_report.export_batch_report(batch_id)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success",
                "data": {"path": str(path), "name": Path(path).name}}

    @app.post("/api/v1/update/report-xlsx/{batch_id}")
    async def update_report_xlsx(batch_id: str):
        """生成《更新检查结果》Excel(.xlsx) 到 exports 目录，返回下载文件名
        （配合既有 GET /export/download 下载）；批次不存在 → 404/UPD-2003。
        与 docx 版共用聚合：巡检汇总/变更明细全量/月度趋势三 sheet。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import report as upd_report
        try:
            path = upd_report.export_batch_report_xlsx(batch_id)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success",
                "data": {"path": str(path), "name": Path(path).name}}

    # ---- 公告发现（自定义公告源；契约增量见 pipeline/03「公告发现」节）----

    @app.post("/api/v1/update/announce-scan")
    async def announce_scan(request: Request):
        """公告源扫描（F-公告发现）：fire-and-forget daemon 线程执行，响应立即返回。

        - ``force``（默认 false）：false 走时间闸（announce.min_interval_hours 默认 6h
          内扫过 → 200 {status:'skipped'} 不重扫）；true 无视时间闸（手动按钮）；
        - 运行中 → 409/UPD-2006；僵尸扫描（DB running 但进程内无登记）→ 自愈开新扫；
        - 进度经 GET /update/announce-scan/last 轮询（host 1.2s）。
        """
        from src.core.update import announce
        try:
            body = await request.json()
        except Exception:
            body = {}
        force = bool(body.get("force"))
        from src.core.exceptions import KnowledgeStationError
        try:
            out = announce.request_scan(force=force,
                                        trigger="manual" if force else "after_inspection")
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.get("/api/v1/update/announce-scan/last")
    async def announce_scan_last():
        """最近一次公告扫描快照（host 轮询；从未扫过 → {status:'never'}，恒 200）。"""
        from src.core.update import announce
        return {"code": 200, "status": "success", "data": announce.get_scan_state()}

    @app.get("/api/v1/update/announce-sources")
    async def announce_sources_list():
        """源清单（app_config announce.sources；引擎为唯一真值）。"""
        from src.core.update import announce
        sources = announce.get_sources()
        return {"code": 200, "status": "success",
                "data": {"sources": sources, "total": len(sources),
                         "enabled_count": len([s for s in sources
                                               if s.get("enabled") is not False])}}

    @app.post("/api/v1/update/announce-sources")
    async def announce_sources_add(request: Request):
        """添加公告源（校验：必填/http(s)/公网——默认禁内网/上限 50/URL 归一化去重）。
        非法 → 422/UPD-3008。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import announce
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            src = announce.add_source(body.get("name"), body.get("url"),
                                      note=str(body.get("note") or ""))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": {"source": src}}

    @app.put("/api/v1/update/announce-sources/{source_id}")
    async def announce_sources_update(source_id: str, request: Request):
        """部分更新源（name/enabled/note/url）；改 URL → 重置首扫基线
        （响应带 rebaselined:true）。不存在 → 404/UPD-2005。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import announce
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            src = announce.update_source(source_id, body)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": {"source": src}}

    @app.delete("/api/v1/update/announce-sources/{source_id}")
    async def announce_sources_remove(source_id: str):
        """删除源（announcement_observed 历史记录保留）。不存在 → 404/UPD-2005。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import announce
        try:
            left = announce.remove_source(source_id)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success",
                "data": {"sources": left, "total": len(left)}}

    @app.get("/api/v1/update/announce-items")
    async def announce_items(limit: int = 20, source_id: str | None = None):
        """已见公告查询（first_seen 倒序；limit ≤200；可按源过滤）。"""
        from src.core.update import announce
        return {"code": 200, "status": "success",
                "data": announce.list_items(limit=limit, source_id=source_id)}

    @app.post("/api/v1/update/announce-export")
    async def announce_export():
        """生成《公告发现》Excel(.xlsx) 到 exports 目录（最近扫描源状态 +
        公告明细全量，发布日期 DESC），返回下载文件名（配合既有
        GET /export/download 下载）；空库同样出文件；纯只读聚合零库写入。"""
        from src.core.update import announce
        path = announce.export_announce_xlsx()
        return {"code": 200, "status": "success",
                "data": {"path": str(path), "name": Path(path).name}}

    # ---- 找标（F-15~F-18）----

    @app.post("/api/v1/discover/classify")
    async def discover_classify(request: Request):
        """口语描述 → CCS 分类路径或一轮追问（协议对齐问答追问 v2）。"""
        from src.core.update import discover
        try:
            body = await request.json()
        except Exception:
            body = {}
        result = discover.classify(str(body.get("description") or ""))
        return {"code": 200, "status": "success", "data": result}

    @app.post("/api/v1/discover/search")
    async def discover_search(request: Request):
        """按分类路径查网络渠道出结果卡片；drill_level>3 → 422/UPD-3002。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import discover
        try:
            body = await request.json()
        except Exception:
            body = {}
        raw_path = body.get("category_path")
        if isinstance(raw_path, str):
            path = [p for p in raw_path.split("/") if p.strip()]
        elif isinstance(raw_path, list):
            path = [str(p).strip() for p in raw_path if str(p).strip()]
        else:
            return json_error(422, "missing_category_path",
                               "缺少 category_path")
        try:
            cards = discover.search(path, body.get("drill_level", 1))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": cards}

    @app.get("/api/v1/discover/watchlist")
    async def watchlist_get():
        """待下载清单（F-18 暂存批量处理）。"""
        from src.core.update import discover
        return {"code": 200, "status": "success",
                "data": discover.download_later_list()}

    @app.post("/api/v1/discover/watchlist")
    async def watchlist_post(request: Request):
        """加入/移除待下载清单：``{action:'add'|'remove', standard_no, name?}``。
        add 按 norm_no 幂等去重；remove 不存在项为无操作；均返回移除后的剩余清单。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import discover
        try:
            body = await request.json()
        except Exception:
            body = {}
        action = body.get("action")
        standard_no = str(body.get("standard_no") or "").strip()
        if action not in ("add", "remove"):
            return json_error(422, "invalid_action",
                               "action 必须为 add|remove")
        if not standard_no:
            return json_error(422, "missing_standard_no", "缺少 standard_no")
        try:
            if action == "add":
                items = discover.download_later_add(
                    standard_no, str(body.get("name") or ""))
            else:
                items = discover.download_later_remove(standard_no)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success",
                "data": {"items": items, "total": len(items)}}

    # ---- 领域订阅（F-13/A15）----

    @app.get("/api/v1/update/subscriptions")
    async def subscriptions_get():
        """领域订阅列表：vocab 全量 + 每域 enabled 开关（缺省全开）。"""
        from src.core.update import subscriptions
        active = set(subscriptions.get_subscriptions())
        return {"code": 200, "status": "success",
                "data": {"vocab": list(subscriptions.DOMAIN_VOCAB),
                         "domains": [{"tag": t, "enabled": t in active}
                                     for t in subscriptions.DOMAIN_VOCAB]}}

    @app.put("/api/v1/update/subscriptions")
    async def subscriptions_put(request: Request):
        """全量替换式保存订阅：``{tags: ["消防","危化"]}``；非法 tag → 422/UPD-3001。"""
        from src.core.update import subscriptions
        try:
            body = await request.json()
        except Exception:
            body = {}
        tags = body.get("tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            return json_error(422, "invalid_tags", "tags 必须为字符串数组")
        try:
            saved = subscriptions.set_subscriptions(tags)
        except ValueError as e:
            return json_error(422, "UPD-3001", str(e))
        return {"code": 200, "status": "success",
                "data": {"domains": [{"tag": t, "enabled": t in saved}
                                     for t in subscriptions.DOMAIN_VOCAB]}}

    # ---- 万级批量导入（pipeline/11：快扫→异步解析→首检入列）----

    @app.post("/api/v1/ingest/bulk")
    async def bulk_ingest_start(request: Request):
        """启动批量导入：``{src_dir, batch_size?=200}`` → 后台线程快扫建目录，返回 {batch_id}。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.ingestion import bulk as bulk_ingest
        try:
            body = await request.json()
        except Exception:
            body = {}
        src_dir = str(body.get("src_dir") or "").strip()
        if not src_dir:
            return json_error(422, "missing_src_dir", "缺少 src_dir")
        try:
            batch = bulk_ingest.create_bulk_batch(
                src_dir, int(body.get("batch_size") or bulk_ingest.DEFAULT_BATCH_SIZE))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        bid = batch["batch_id"]

        def _run():
            try:
                bulk_ingest.fast_scan(bid)
            except Exception:  # 快扫失败落批次 failed（daemon 线程不吞异常）
                b = bulk_ingest.load_batch(bid)
                if b and b["status"] == "running":
                    bulk_ingest.pause_batch(bid)

        import threading as _th
        _th.Thread(target=_run, daemon=True).start()
        return {"code": 200, "status": "success",
                "data": {"batch_id": bid, "total": batch.get("total", 0)}}

    @app.get("/api/v1/ingest/bulk/{batch_id}")
    async def bulk_ingest_status(batch_id: str):
        """批量导入进度：快扫 checked/total + 解析队列统计 + 隔离/重复错误数。"""
        from src.core.ingestion import bulk as bulk_ingest
        b = bulk_ingest.load_batch(batch_id)
        if b is None:
            return json_error(404, "bulk_batch_not_found", "批次不存在")
        ckpt = b.get("checkpoint") or {}
        queue = ckpt.get("queue", [])
        errors = ckpt.get("errors", [])
        parsed = sum(1 for q in queue if q.get("status") == "parsed")
        return {"code": 200, "status": "success",
                "data": {
                    "batch_id": batch_id, "status": b.get("status"),
                    "total": b.get("total", 0),
                    "scanned": ckpt.get("scanned", 0),
                    "parsed": parsed,
                    "pending": sum(1 for q in queue if q.get("status") != "parsed"),
                    "errors": len(errors),
                    "pause_reason": ckpt.get("pause_reason"),
                }}

    @app.post("/api/v1/ingest/bulk/{batch_id}/resume")
    async def bulk_ingest_resume(batch_id: str, request: Request):
        """恢复解析（快扫完成后调用）：后台线程逐件解析，日预算耗尽转 paused。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.ingestion import bulk as bulk_ingest
        try:
            body = await request.json()
        except Exception:
            body = {}
        try:
            bulk_ingest.pause_batch(batch_id)  # 幂等：把 pending/running 统一为可控点
            b = bulk_ingest.load_batch(batch_id)
            if b is None:
                return json_error(404, "bulk_batch_not_found", "批次不存在")
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        bid = batch_id

        def _run():
            budget_raw = body.get("daily_budget")
            budget = (int(budget_raw) if budget_raw is not None
                      else bulk_ingest.DEFAULT_PARSE_DAILY_BUDGET)
            bulk_ingest.resume_batch(bid, budget)

        import threading as _th
        _th.Thread(target=_run, daemon=True).start()
        return {"code": 200, "status": "success", "data": {"batch_id": bid}}

    @app.post("/api/v1/ingest/bulk/{batch_id}/abort")
    async def bulk_ingest_abort(batch_id: str):
        """终止批次（人工清场）：pending/running/paused → failed；终止后同目录可立即新建批次。"""
        from src.core.ingestion import bulk as bulk_ingest
        b = bulk_ingest.abort_batch(batch_id)
        if b is None:
            return json_error(404, "bulk_batch_not_found", "批次不存在")
        return {"code": 200, "status": "success",
                "data": {"batch_id": batch_id, "status": b.get("status")}}

    # ---- 数据打包 / 还原（F-26）----

    @app.post("/api/v1/data/package/export")
    async def data_package_export(request: Request):
        """全量数据包导出：``{dest_dir?}`` 缺省落 exports 目录；
        返回包目录 + manifest（含七项简报计数与 SHA-256 校验和）。"""
        from src.core.config import get_settings
        from src.core.update import data_package
        try:
            body = await request.json()
        except Exception:
            body = {}
        dest = body.get("dest_dir") or (get_settings().data_dir / "exports")
        try:
            pkg, manifest = data_package.export_package(dest)
        except Exception as e:  # noqa: BLE001 — 打包失败归一 422
            return json_error(422, getattr(e, "code", "package_export_failed"),
                               str(e))
        return {"code": 200, "status": "success",
                "data": {"path": str(pkg), "name": pkg.name, "manifest": manifest}}

    @app.post("/api/v1/data/package/import")
    async def data_package_import(request: Request):
        """数据包导入（strict：目标库非空 → 422/UPD-3003 拒绝）：
        ``{src_path, mode?}``；成功返回含导入简报的 manifest（prepared 语义）。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import data_package
        try:
            body = await request.json()
        except Exception:
            body = {}
        src = body.get("src_path")
        if not src:
            return json_error(422, "missing_src_path", "缺少 src_path")
        try:
            manifest = data_package.import_package(
                src, mode=str(body.get("mode") or "strict"))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": manifest}
