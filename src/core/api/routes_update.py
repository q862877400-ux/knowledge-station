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
    def update_check(body: dict | None = None):
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
            body = body or {}
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
    def update_batch_progress(batch_id: str):
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
    def update_batch_pause(batch_id: str):
        """断点暂停：运行中在块边界落 checkpoint 后转 paused；幂等；不存在 → 404。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import inspector
        try:
            out = inspector.pause_batch(batch_id)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/batch/{batch_id}/resume")
    def update_batch_resume(batch_id: str):
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
    def update_batches(limit: int = 20):
        """历史批次（created_at 倒序）。"""
        from src.core.update import change_repo
        return {"code": 200, "status": "success",
                "data": change_repo.list_batches(limit)}

    @app.get("/api/v1/update/changes")
    def update_changes(batch_id: str | None = None,
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
    def update_change_ack(change_id: str, body: dict | None = None):
        """用户确认变更事件（body 可选 {"ack": bool}，缺省确认）。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import change_repo
        try:
            body = body or {}
        except Exception:
            body = {}
        try:
            out = change_repo.mark_ack(change_id, bool(body.get("ack", True)))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": out}

    @app.post("/api/v1/update/changes/{change_id}/manual")
    def update_change_manual(change_id: str, body: dict | None = None):
        """人工维护法律状态 ``{legal_status,note}``（manual 渠道语义）。

        非法枚举 → 422/UPD-3001（base.py 冻结错误码表：3001=illegal_legal_status；
        3003 为 batch_not_found，故此处按模块实现抛出的校验层码透传）。
        """
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import change_repo
        try:
            body = body or {}
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

    @app.post("/api/v1/update/report-xlsx/{batch_id}")
    def update_report_xlsx(batch_id: str):
        """生成《更新检查结果》Excel(.xlsx) 到 exports 目录，返回下载文件名
        （配合既有 GET /export/download 下载）；批次不存在 → 404/UPD-2003。
        三 sheet：巡检汇总/变更明细全量/月度趋势。

        ⚠ **2026-09-19（EXECUTION-PLAN 第 4 步）**：同聚合的 Word 版
        `POST /update/report/{batch_id}` 已拆除（业主否决 Word/PPT 交付物，
        `docs/NOT-DOING.md` 第 1 条；"研究/巡检报告落 `.docx`"正是那条裁决点名的一类）。
        `.xlsx` 不是 Word/PPT 交付物，裁决没碰它 ⇒ 本路由原样保留。

        §10.76：openpyxl 落盘 ⇒ `def`。"""
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
    def announce_scan(body: dict | None = None):
        """公告源扫描（F-公告发现）：fire-and-forget daemon 线程执行，响应立即返回。

        - ``force``（默认 false）：false 走时间闸（announce.min_interval_hours 默认 6h
          内扫过 → 200 {status:'skipped'} 不重扫）；true 无视时间闸（手动按钮）；
        - 运行中 → 409/UPD-2006；僵尸扫描（DB running 但进程内无登记）→ 自愈开新扫；
        - 进度经 GET /update/announce-scan/last 轮询（host 1.2s）。
        """
        from src.core.update import announce
        try:
            body = body or {}
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
    def announce_scan_last():
        """最近一次公告扫描快照（host 轮询；从未扫过 → {status:'never'}，恒 200）。"""
        from src.core.update import announce
        return {"code": 200, "status": "success", "data": announce.get_scan_state()}

    @app.get("/api/v1/update/announce-sources")
    def announce_sources_list():
        """源清单（app_config announce.sources；引擎为唯一真值）。

        §10.79：`announce.get_sources()` 要读配置文件 ⇒ 同步 I/O ⇒ `def`。
        """
        from src.core.update import announce
        sources = announce.get_sources()
        return {"code": 200, "status": "success",
                "data": {"sources": sources, "total": len(sources),
                         "enabled_count": len([s for s in sources
                                               if s.get("enabled") is not False])}}

    @app.post("/api/v1/update/announce-sources")
    def announce_sources_add(body: dict | None = None):
        """添加公告源（校验：必填/http(s)/公网——默认禁内网/上限 50/URL 归一化去重）。
        非法 → 422/UPD-3008。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import announce
        body = body or {}
        try:
            # ⚠ `# type: ignore[arg-type]` 的理由（§10.79，mypy 在转换后新报的两处）：
            # 转换前 `body` 是 `Any`（`await request.json()`）⇒ 从不报错；现在是 `dict | None`
            # ⇒ `body.get(...)` 是 `Any | None`，而 `add_source` 形参声明为 `str`。
            # **缺参/非字符串的校验在 `add_source` 内部做**（`_validate_source_payload` → 422/UPD-3008），
            # 所以这里刻意保持与转换前**逐字相同**的宽松传参，不替它先猜（先猜就会把"缺 name"
            # 变成 `""`，那是**改行为**）。
            src = announce.add_source(body.get("name"),  # type: ignore[arg-type]
                                      body.get("url"),  # type: ignore[arg-type]
                                      note=str(body.get("note") or ""))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": {"source": src}}

    @app.put("/api/v1/update/announce-sources/{source_id}")
    def announce_sources_update(source_id: str, body: dict | None = None):
        """部分更新源（name/enabled/note/url）；改 URL → 重置首扫基线
        （响应带 rebaselined:true）。不存在 → 404/UPD-2005。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import announce
        body = body or {}
        try:
            src = announce.update_source(source_id, body)
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": {"source": src}}

    @app.delete("/api/v1/update/announce-sources/{source_id}")
    def announce_sources_remove(source_id: str):
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
    def announce_items(limit: int = 20, source_id: str | None = None):
        """已见公告查询（first_seen 倒序；limit ≤200；可按源过滤）。"""
        from src.core.update import announce
        return {"code": 200, "status": "success",
                "data": announce.list_items(limit=limit, source_id=source_id)}

    @app.post("/api/v1/update/announce-export")
    def announce_export():
        """公告扫描结果导出 xlsx（§10.79：openpyxl 落盘 ⇒ `def`）。

        生成《公告发现》Excel(.xlsx) 到 exports 目录（最近扫描源状态 +
        公告明细全量，发布日期 DESC），返回下载文件名（配合既有
        GET /export/download 下载）；空库同样出文件；纯只读聚合零库写入。

        ⚠ 原先这里是**两个 docstring 上下叠着**（§10.79 转换时把"为什么改 `def`"那句
        加在了原 docstring 上面）——Python 只把**第一个**当 `__doc__`，第二个成了**死字符串
        表达式**（不报错，但读代码的人会以为它在文档里，而 `inspect.getdoc` / 未来的
        OpenAPI 摘要只看第一个）。独立复核 b14 的 LOW-3 抓到；此处**合并成一条**。
        """
        from src.core.update import announce
        path = announce.export_announce_xlsx()
        return {"code": 200, "status": "success",
                "data": {"path": str(path), "name": Path(path).name}}

    # ---- 公告正文入库（切片②，§10.192/§10.193）----

    @app.get("/api/v1/update/announce-ingest/pending")
    def announce_ingest_pending(source_id: str | None = None):
        """入库进度：已发现多少 / 已入库多少 / 还差多少（**不抓网页**，纯本地计数）。

        界面拿它在按钮旁写一句实话（"还有 27 条没进库：现行 19 · 仅参考 6 · 已废止 2"）。
        """
        from src.core.update import web_ingest
        return {"code": 200, "status": "success",
                "data": web_ingest.ingest_summary(source_id=source_id)}

    @app.post("/api/v1/update/announce-ingest")
    def announce_ingest(body: dict | None = None):
        """把**已发现但正文还没进库**的公告批量入库（正文进知识库）。

        body（都可省）：
        - ``limit``：本次最多抓几条（默认 10，**上限 20**，超了按上限走 —— 一次点下去
          抓几百页不是"更努力"，是把请求挂死）；
        - ``source_id``：只处理某个公告源；
        - ``force``：连"业主点名的非规范性类别"（部门决算/公示/挂牌督办）也入 ——
          **逃生口**：我给的范围判错了时，他不必等改代码。

        单次有时间预算（`web_ingest.INGEST_BUDGET_S`）：到点就停，回 ``stopped_early`` +
        ``pending_left``，**不假装做完了**；每条的结果都在 ``items`` 里（失败/跳过不静默）。
        ⚠ 会**真的写库**（这是本端点唯一的目的），且每条要抓一次详情页 ⇒ 同步等待。
        """
        from src.core.update import web_ingest
        payload = body if isinstance(body, dict) else {}
        try:
            limit = int(payload.get("limit") or 10)
        except (TypeError, ValueError):
            # ⚠ **走 `json_error`（真 4xx），不要写成 200 + 信封里一个 error 字段**
            #   （2026-09-24 独立复核 MED-1）：同文件其余 20+ 处 4xx 都是 `json_error`；
            #   写成 200 会让 host 代理的 422 分支**永远不可达**、还会让客户端
            #   `res.ok === true` ⇒ 界面把"参数非法"当"成功、0 条"。
            return json_error(422, "invalid_limit", "limit 必须是整数")
        out = web_ingest.ingest_pending(
            limit=limit, source_id=payload.get("source_id"),
            force=bool(payload.get("force")))
        return {"code": 200, "status": "success", "data": out}

    @app.get("/api/v1/update/announce-ingest/triage")
    def announce_ingest_triage(source_id: str | None = None, limit: int = 200):
        """给"规则判不收、但要不要真清"的那批**分档**（2026-09-24 B2，Jev 管清）。

        ⚠ **只读**：不删库、不改库、不抓正文——只回 clear/review/keep 清单 + 判据。
        真正删除是业主的决定（他的口径：「不是规范性、不需要别人遵守其内容 ⇒ 不入库」；
        但**哪几条属于哪类**由这条端点提供证据，不由它替他下手）。
        Jev 不可用 ⇒ 全部落 `keep`（按规则原样处理，不因外部服务挂了就误清）。
        """
        from src.core.update import web_ingest
        return {"code": 200, "status": "success",
                "data": web_ingest.triage_pending(source_id=source_id, limit=limit)}

    # ---- 找标（F-15~F-18）----

    @app.post("/api/v1/discover/classify")
    def discover_classify(body: dict | None = None):
        """口语描述 → CCS 分类路径或一轮追问（协议对齐问答追问 v2）。"""
        from src.core.update import discover
        body = body or {}
        result = discover.classify(str(body.get("description") or ""))
        return {"code": 200, "status": "success", "data": result}

    @app.post("/api/v1/discover/search")
    def discover_search(body: dict | None = None):
        """按分类路径查网络渠道出结果卡片；drill_level>3 → 422/UPD-3002。

        ⚠ `def` 而不是 `async def`（§10.86 通则之一）：唯一的 `await` 只是 `request.json()`
        ⇒ 读完 body 之后是同步的**网络检索**（秒级），留在事件循环里会把引擎堵住。
        body 改走签名 ⇒ 坏 JSON 由 FastAPI 直接 422（改前是被 `except` 吞成 `{}`、再报
        `missing_category_path`；两者都是 422，但**错误码不同**，与 §10.79 同口径）。
        """
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import discover
        body = body or {}
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
    def watchlist_get():
        """待下载清单（F-18 暂存批量处理）。"""
        from src.core.update import discover
        return {"code": 200, "status": "success",
                "data": discover.download_later_list()}

    @app.post("/api/v1/discover/watchlist")
    def watchlist_post(body: dict | None = None):
        """加入/移除待下载清单：``{action:'add'|'remove', standard_no, name?}``。
        add 按 norm_no 幂等去重；remove 不存在项为无操作；均返回移除后的剩余清单。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import discover
        try:
            body = body or {}
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
    def subscriptions_get():
        """领域订阅列表：vocab 全量 + 每域 enabled 开关（缺省全开）。"""
        from src.core.update import subscriptions
        active = set(subscriptions.get_subscriptions())
        return {"code": 200, "status": "success",
                "data": {"vocab": list(subscriptions.DOMAIN_VOCAB),
                         "domains": [{"tag": t, "enabled": t in active}
                                     for t in subscriptions.DOMAIN_VOCAB]}}

    @app.put("/api/v1/update/subscriptions")
    def subscriptions_put(body: dict | None = None):
        """全量替换式保存订阅：``{tags: ["消防","危化"]}``；非法 tag → 422/UPD-3001。"""
        from src.core.update import subscriptions
        try:
            body = body or {}
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
    def bulk_ingest_start(body: dict | None = None):
        """启动批量导入：``{src_dir, batch_size?=200, reingest?=false, force?=false}``
        → 后台线程快扫建目录，返回 {batch_id}。

        ``reingest`` / ``force``（**同义词**，2026-09-21 KB-FOLDER-PLAN 第 4 步）：
        「明知库里已有同号/同文件的登记也覆盖重导」。透传给既有的
        ``run_full_ingest(reingest=True)``（见 ``bulk.create_bulk_batch``），
        **默认 false = 不覆盖**（原行为）。本地 PDF 这条路以前**没有**这个开关，
        ⇒ 那两篇正文条款为零、被挡在目录外的文件没有回头路（方案 §十七）。
        """
        from src.core.exceptions import KnowledgeStationError
        from src.core.ingestion import bulk as bulk_ingest
        body = body or {}
        src_dir = str(body.get("src_dir") or "").strip()
        if not src_dir:
            return json_error(422, "missing_src_dir", "缺少 src_dir")
        # 两个名字都收（`force` 是 `reingest` 的同义词；两侧任一为真即真）。
        reingest = bool(body.get("reingest") or body.get("force"))
        try:
            batch = bulk_ingest.create_bulk_batch(
                src_dir, int(body.get("batch_size") or bulk_ingest.DEFAULT_BATCH_SIZE),
                reingest=reingest)
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
    def bulk_ingest_status(batch_id: str):
        """批量导入进度：快扫 checked/total + 解析队列统计 + 隔离/重复错误数。

        ⚠ `filing_state_missing`（2026-09-21 第 5 步挂账 ③a）：这一批里**状态行没写进库**
        的文件数（附前 5 个文件名）—— 它们照样会出现在「待分类」里（那里按"没有状态行 =
        排队中"算），但**界面上必须能看出"这批里有文件的状态没写进去"**，所以随终态一起报。
        `reingest` 也一并报出来（界面据此说明这一批是不是"覆盖重导"）。
        """
        from src.core.ingestion import bulk as bulk_ingest
        b = bulk_ingest.load_batch(batch_id)
        if b is None:
            return json_error(404, "bulk_batch_not_found", "批次不存在")
        ckpt = b.get("checkpoint") or {}
        queue = ckpt.get("queue", [])
        errors = ckpt.get("errors", [])
        parsed = sum(1 for q in queue if q.get("status") == "parsed")
        missing = [str(p) for p in (ckpt.get("filing_state_missing") or [])]
        return {"code": 200, "status": "success",
                "data": {
                    "batch_id": batch_id, "status": b.get("status"),
                    "total": b.get("total", 0),
                    "scanned": ckpt.get("scanned", 0),
                    "parsed": parsed,
                    "pending": sum(1 for q in queue if q.get("status") != "parsed"),
                    "errors": len(errors),
                    "pause_reason": ckpt.get("pause_reason"),
                    "filing_state_missing": len(missing),
                    "filing_state_missing_sample": [Path(p).name for p in missing[:5]],
                    "reingest": bool(ckpt.get("reingest")),
                }}

    @app.post("/api/v1/ingest/bulk/{batch_id}/resume")
    def bulk_ingest_resume(batch_id: str, body: dict | None = None):
        """恢复解析（快扫完成后调用）：后台线程逐件解析，日预算耗尽转 paused。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.ingestion import bulk as bulk_ingest
        body = body or {}
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
    def bulk_ingest_abort(batch_id: str):
        """终止批次（人工清场）：pending/running/paused → failed；终止后同目录可立即新建批次。"""
        from src.core.ingestion import bulk as bulk_ingest
        b = bulk_ingest.abort_batch(batch_id)
        if b is None:
            return json_error(404, "bulk_batch_not_found", "批次不存在")
        return {"code": 200, "status": "success",
                "data": {"batch_id": batch_id, "status": b.get("status")}}

    # ---- 数据打包 / 还原（F-26）----

    @app.post("/api/v1/data/package/export")
    def data_package_export(body: dict | None = None):
        """全量数据包导出：``{dest_dir?}`` 缺省落 exports 目录；
        返回包目录 + manifest（含七项简报计数与 SHA-256 校验和）。"""
        from src.core.config import get_settings
        from src.core.update import data_package
        body = body or {}
        dest = body.get("dest_dir") or (get_settings().data_dir / "exports")
        try:
            pkg, manifest = data_package.export_package(dest)
        except Exception as e:  # noqa: BLE001 — 打包失败归一 422
            return json_error(422, getattr(e, "code", "package_export_failed"),
                               str(e))
        return {"code": 200, "status": "success",
                "data": {"path": str(pkg), "name": pkg.name, "manifest": manifest}}

    @app.post("/api/v1/data/package/import")
    def data_package_import(body: dict | None = None):
        """数据包导入（strict：目标库非空 → 422/UPD-3003 拒绝）：
        ``{src_path, mode?}``；成功返回含导入简报的 manifest（prepared 语义）。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.update import data_package
        body = body or {}
        src = body.get("src_path")
        if not src:
            return json_error(422, "missing_src_path", "缺少 src_path")
        try:
            manifest = data_package.import_package(
                src, mode=str(body.get("mode") or "strict"))
        except KnowledgeStationError as e:
            return _upd_error(e, json_error)
        return {"code": 200, "status": "success", "data": manifest}
