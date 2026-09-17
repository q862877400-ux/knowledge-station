"""R27 入库预览（Dry-Run）+ 批量分桶 API 路由——**只读**三端点。

- POST /api/v1/ingest/preview          单文件预览报告（R27 完整体检）
- POST /api/v1/ingest/preview/batch    目录批量预览 + ✅/⚠️/❌ 分桶（决策 2）
- GET  /api/v1/ingest/preview/inbox    列出候选目录下的 PDF（不含体检）

## 只读纪律（与 `src/core/ingestion/dry_run.py` 一致）
不写库、不建表、不动用户文件；临时解析产物只落 `data_dir/dryrun/tmp/<hash16>/`。
响应里始终带 `egress`：**默认 `none`**（预览不调云通道），调用方显式传 `allow_deep=true`
时如实变成 `deep_channel`（2026-09-17 D5 前这里是恒 `none` + 直接 422 拒绝深度通道）。
另有 `deep_fallback_skipped` 表示"这份文档真的本该深度分析却被跳过"。
⇒ 前端能如实告诉用户"这次有没有可能外发"。

## 校验语义
- 非法请求（缺 path / 非 PDF / 路径不是文件 / 目录不存在）→ 422 `preview_bad_request`；
- 文件不存在 → 404 `preview_file_not_found`；
- **坏文档不是 HTTP 错误**：解析失败也返回 200，由报告里的 `verdict="block"` 表达
  （HTTP 层错误会让"100% 拦截"变成"看到报错不知道拦了什么"）。

## ⚠ 这六条端点**一律声明成 `def`**（§10.73，2026-09-18）
本文件的每一件事都是**同步重活**：单文件预览要 sha256 + 真解析一份 PDF、批量要扫目录、
jobs 三件套要读任务表。uvicorn 是**单事件循环** ⇒ 写成 `async def` 会把**整个引擎**卡住。
这不是理论：`scripts/measure-endpoint-blocking.py` 在**改前**实测 12 页 PDF
——请求 0.474s、事件循环**空档 0.468s**（≈整条请求全堵）；改 `def` 之后同一条用例的空档
掉回**心跳分辨率**（§10.73 有 before/after 表）。而本文件上面那句"负载下可达 135s"
意味着：**最坏情况下整个引擎会静默死两分钟**。
闸门：`tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync`（逐条 + 文件级各一条）。
"""
from __future__ import annotations

from pathlib import Path

from src.core.exceptions import KnowledgeStationError

#: 批量同步接口的硬上限。**注意它不是超时保护**（单本预览在负载下实测可达 135s，
#: 200 本远超任何 HTTP 超时）——它防的是单请求的内存/payload 膨胀。真正的节流靠
#: `sample` 默认 5（决策 2「新语料源先抽样 3~5 本」）；全量万级需要异步版本（见台账）。
_BATCH_LIMIT = 200


def _parse_allow_deep(body: dict | None) -> tuple[bool, str]:
    """严格取 `allow_deep`：返回 ``(值, 错误消息)``，错误消息非空即应 422。

    ⚠ **必须是严格布尔**（2026-09-17 独立复核 F4）：原实现是
    ``bool(body.get("allow_deep") or False)``，而 JSON 字符串 ``"false"`` 是**真值**
    ⇒ "传 false" 反而**开启了外发**，与"默认安全"的设计意图直接冲突（已实测复现）。
    同文件对 `paths`/`sample`/`limit_files`/`batch_size` 都做了严格校验，这里是唯一破口。
    只接受 JSON 的 `true`/`false`（Python `bool`）；`1`/`0`/`"true"`/`"false"` 一律拒绝
    ——整数 1 在别的语言里虽是常见真值写法，但"猜他想要什么"正是出事的根源。
    """
    raw = (body or {}).get("allow_deep", False)
    if isinstance(raw, bool):
        return raw, ""
    return False, (f"allow_deep 必须是布尔值 true/false，收到 {type(raw).__name__}"
                   f"（{raw!r}）；不接受 \"true\"/\"false\" 字符串或 1/0")


def register(app, json_error):
    @app.post("/api/v1/ingest/preview")
    def ingest_preview(payload: dict):
        """单文件预览报告（R27）：总页数/条款数/质量分级/前后 5 条样例/可疑清单/分型预览/
        法理要素质量/标准号猜测/查重。只读；**默认不外发**，`allow_deep=true` 才走云深度通道。"""
        from src.core.ingestion import dry_run
        raw_path = (payload or {}).get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return json_error(422, "preview_bad_request", "缺少 path（要预览的 PDF 绝对路径）")
        p = Path(raw_path.strip())
        if not p.exists():
            return json_error(404, "preview_file_not_found", f"文件不存在: {p}")
        if not p.is_file():
            return json_error(422, "preview_not_a_file", f"路径不是文件: {p}")
        # 「是不是 PDF」的判定**只有一个所有者**（`dry_run`，按内容魔数——DSH 附件是
        # 无扩展名的哈希文件，只卡 `.pdf` 会误拒真实语料）。这里只把它的判定转成请求级 422。
        doc_type = str((payload or {}).get("doc_type") or "standard")
        # 显式允许深度通道（云优先 = 可能外发）。2026-09-17 D5：原先这里直接 422 拒绝，
        # 现在**真的接线**，并把决定权交还调用方——但**默认仍是 False**（不外发），
        # 且报告里的 `egress` 会如实标成 `deep_channel`（红线 4 / D2：不禁止，但必须留痕）。
        # F4：严格布尔，防 "false" 字符串被当成开启。
        allow_deep, deep_err = _parse_allow_deep(payload)
        if deep_err:
            return json_error(422, "preview_bad_request", deep_err)
        try:
            data = dry_run.analyze_preview_report(p, doc_type=doc_type,
                                                 deep_fallback=allow_deep)
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        if data.get("status") == "error" and data.get("error_code") == "unsupported_type":
            return json_error(422, "preview_unsupported_type", data.get("error_message") or "")
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/ingest/preview/batch")
    def ingest_preview_batch(payload: dict):
        """目录批量预览 + 分桶（决策 2）：先抽样几本，再看 ✅/⚠️/❌ 总账。

        单文件失败不中断整批；`sample=0` 表示不抽样（全量，受 `limit_files` 上限约束）。
        """
        from src.core.ingestion import dry_run
        body = payload or {}
        targets = body.get("paths")
        directory = body.get("dir")
        if not targets and not directory:
            return json_error(422, "preview_bad_request", "需要 dir（目录）或 paths（文件列表）")
        try:
            if targets:
                if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
                    return json_error(422, "preview_bad_request", "paths 必须是字符串数组")
                paths = [Path(t) for t in targets]
            else:
                paths = dry_run.scan_preview_dir(str(directory),
                                                 recursive=bool(body.get("recursive")))
        except NotADirectoryError:
            return json_error(404, "preview_dir_not_found", f"目录不存在: {directory}")

        sample = body.get("sample", dry_run.BATCH_DEFAULT_SAMPLE)
        try:
            sample = int(sample)
        except (TypeError, ValueError):
            return json_error(422, "preview_bad_request", "sample 必须是整数（0 = 不抽样）")
        if sample < 0:
            return json_error(422, "preview_bad_request", "sample 不能为负")
        limit_files = body.get("limit_files", dry_run.BATCH_MAX_FILES)
        try:
            limit_files = min(int(limit_files), _BATCH_LIMIT)
        except (TypeError, ValueError):
            return json_error(422, "preview_bad_request", "limit_files 必须是整数")
        if not paths:
            return json_error(404, "preview_no_candidates", "候选目录下没有 PDF")

        allow_deep, deep_err = _parse_allow_deep(body)
        if deep_err:
            return json_error(422, "preview_bad_request", deep_err)
        data = dry_run.preview_batch(paths, sample=sample,
                                    doc_type=str(body.get("doc_type") or "standard"),
                                    deep_fallback=allow_deep,
                                    limit_files=limit_files)
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/ingest/preview/inbox")
    def ingest_preview_inbox(dir: str, recursive: bool = False, limit: int = 200):
        """列出候选目录下的 PDF（只列名与大小，不做体检——体检走 POST 端点）。"""
        from src.core.ingestion import dry_run
        try:
            files = dry_run.scan_preview_dir(dir, recursive=recursive,
                                             limit=min(int(limit), _BATCH_LIMIT))
        except NotADirectoryError:
            return json_error(404, "preview_dir_not_found", f"目录不存在: {dir}")
        rows = []
        for f in files:
            try:
                st = f.stat()
                rows.append({"path": str(f), "file_name": f.name, "size": st.st_size,
                             "mtime": st.st_mtime})
            except OSError:
                continue
        return {"code": 200, "status": "success",
                "data": {"dir": str(dir), "count": len(rows), "files": rows}}

    # ---------------- 异步批量预览（全量万级，2026-09-12 L239 施工）----------------
    # 三件套：POST jobs（立即返回 job_id）→ GET jobs/{id}（进度+瘦身行分页）→
    # POST jobs/{id}/abort（协作式中断）。任务表进程内（只读红线：不落库账本）；
    # 僵尸语义照 announce.py（登记 running 而线程死 → GET 时自愈标 failed）。
    @app.post("/api/v1/ingest/preview/jobs")
    def ingest_preview_job_start(payload: dict):
        """启动异步批量预览任务：``{paths: [绝对路径…]}`` 或 ``{dir, recursive?}``。

        ``batch_size>0`` 只跑前 N 件（试跑）；默认全量（这正是本接口的用途——
        同步接口的 200 上限不是超时保护）。立即返回 job_id，不等结果。
        ``allow_deep=true`` 才允许走云深度通道（**默认不外发**，2026-09-17 D5）。
        """
        from src.core.ingestion import preview_jobs
        body = payload or {}
        targets = body.get("paths")
        directory = body.get("dir")
        if not targets and not directory:
            return json_error(422, "preview_bad_request",
                              "需要 dir（目录）或 paths（文件列表）")
        try:
            if targets:
                if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
                    return json_error(422, "preview_bad_request",
                                      "paths 必须是字符串数组")
                paths = [str(t) for t in targets]
            else:
                from src.core.ingestion import dry_run
                files = dry_run.scan_preview_dir(
                    str(directory), recursive=bool(body.get("recursive")))
                paths = [str(f) for f in files]
        except NotADirectoryError:
            return json_error(404, "preview_dir_not_found", f"目录不存在: {directory}")
        if not paths:
            return json_error(404, "preview_no_candidates", "候选目录下没有 PDF")
        try:
            batch_size = int(body.get("batch_size") or 0)
        except (TypeError, ValueError):
            return json_error(422, "preview_bad_request", "batch_size 必须是整数")
        allow_deep, deep_err = _parse_allow_deep(body)
        if deep_err:
            return json_error(422, "preview_bad_request", deep_err)
        view = preview_jobs.create_job(
            paths, doc_type=str(body.get("doc_type") or "standard"),
            deep_fallback=allow_deep,
            sample=0, batch_size=batch_size)
        return {"code": 200, "status": "success", "data": view}

    @app.get("/api/v1/ingest/preview/jobs/{job_id}")
    def ingest_preview_job_status(job_id: str, rows_offset: int = 0,
                                        rows_limit: int = 200):
        """任务进度：status/total/done/三桶计数 + 瘦身行分页（默认前 200 行）。

        僵尸自愈在此路径（GET 时发现线程死而状态非 terminal → 标 failed）。
        """
        from src.core.ingestion import preview_jobs
        view = preview_jobs.get_job(job_id, rows_offset=rows_offset,
                                    rows_limit=rows_limit)
        if view is None:
            return json_error(404, "preview_job_not_found", f"任务不存在: {job_id}")
        return {"code": 200, "status": "success", "data": view}

    @app.post("/api/v1/ingest/preview/jobs/{job_id}/abort")
    def ingest_preview_job_abort(job_id: str):
        """协作式中断：置 stop_flag，worker 最多再跑 16 件后停并标 aborted。

        已完成的行保留（用户拿得到部分结果）。terminal 后再 abort 是幂等 no-op。
        """
        from src.core.ingestion import preview_jobs
        view = preview_jobs.abort_job(job_id)
        if view is None:
            return json_error(404, "preview_job_not_found", f"任务不存在: {job_id}")
        return {"code": 200, "status": "success", "data": view}
