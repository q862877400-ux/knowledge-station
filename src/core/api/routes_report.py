"""效力报告 API 路由（决策 21 · 用户修订版）：效力报告（只读聚合）+ 材料平面的产出物。

- GET  /api/v1/report/effect        骨架+四色统计（秒级同步 GET，无 fire-and-forget）
- GET  /api/v1/report/effect/docs   节点明细（瘦身行，limit 封顶——payload 红线）
- GET  /api/v1/report/effect/color  全库按色取 top-N（`ks_effect_report` 的数据源）
- POST /api/v1/report/effect/export openpyxl 落 exports 目录（空库也出文件），
  下载走既有 GET /export/download（穿越防护已有）。
- POST /api/v1/report/research      **研究报告**（Phase D，§10.36 + §10.92）：
  Markdown + HTML + **Word** 三形态落盘（同一份内容块），
  材料依据按承重能力分组、引用标记逐条校验、未批准材料如实列出（零新增依赖）。
- POST /api/v1/report/research/slides **同内容的 PPT**（Phase D-2，§10.37）。
- POST /api/v1/report/research/draft  **结论草稿**（Phase D-5a，§10.96）：基于**已批准材料**
  起草一段结论（复用取证链已审计的提示词），返回 `unapproved_draft` 标记 + 引用逐条校验；
  **不落盘、不进报告**——是否采用由用户逐次显式决定。

校验语义：非法 window/color/top/l2 → 422（invalid_*）；E2 未知名路径 → 200 空集
（L2/L3/L4 是展示串非稳定 ID，库内重分类后旧名自然为空，404 会让 UI 抖动）。

⚠ **本文件的端点一律声明成 `def`**（§10.71，复核 b12 的 MEDIUM-2）：它们要么跑秒级
SQL 聚合、要么 openpyxl/pptx 落盘、要么经 `research_report._attach_locator_status`
→ `locator.locator_health` **逐份流式 sha256 材料源文件**。uvicorn 是**单事件循环**
⇒ 任何一个写成 `async def` 都会把**整个引擎**卡住（GUI 看起来"死掉"）。
`/effect/export` 原先写成 `async def` **只是为了 `await request.json()`**；现在直接把
body 写进函数签名（FastAPI 在派发进线程池**之前**就把 body 解析好），代价是**非法 JSON
从"当成空 body"变成 422**——fail-closed，与库里其它端点同口径。
闸门：`tests/test_material_api.py::TestSlowEndpointsAreDeclaredSync`（逐条 + 文件级各一条）。
"""
from __future__ import annotations

from src.core.exceptions import KnowledgeStationError


def register(app, json_error):
    @app.get("/api/v1/report/effect")
    def effect_report(window: str = "all", color: str | None = None):
        """效力报告骨架+四色统计（按文件目录分类体系，永不混排——决策 21 用户修订）。

        - ``window``：all(默认)/upcoming90/recent90/retired90（分桶前过滤）；
        - ``color``：可选 CSV 子集（red,yellow,green,gray），全局色清单视图；
        - 状态以读取时惰性翻转（resolve_status）为准，与决策 22 同口径。
        """
        from src.core.exports import effect_report
        try:
            data = effect_report.collect_effect_report(window=window, color=color)
        except ValueError as e:
            return json_error(422, str(e), f"非法参数: {e}")
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/report/effect/docs")
    def effect_report_docs(top: str, l2: str, l3: str | None = None,
                           l4: str | None = None, window: str = "all",
                           color: str | None = None, limit: int = 1000,
                           offset: int = 0):
        """节点明细（瘦身行 9 字段；排序 red→yellow→gray→green → 标准号升序）。

        - ``top``/``l2`` 必填（防两树 L2 同名）；l3/l4 可选下钻；
        - 未知名路径 → 200 空集（展示串非稳定 ID，不 404）。
        """
        from src.core.exports import effect_report
        try:
            data = effect_report.collect_effect_docs(
                top=top, l2=l2, l3=l3, l4=l4, window=window, color=color,
                limit=limit, offset=offset)
        except ValueError as e:
            return json_error(422, str(e), f"非法参数: {e}")
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/report/effect/color")
    def effect_report_by_color(color: str, window: str = "all", limit: int = 20,
                               per_color: bool = False):
        """全库按色取 top-N 瘦身行（`ks_effect_report` 模型工具的红/黄清单数据源）。

        E2 需 top+l2（防两树 L2 同名）；本端点服务"全库红色清单"这类全局视图，
        limit ≤100；非法色 → 422/invalid_color。
        ``per_color=true``：多色时每色各取 limit 条（模型工具红+黄一次拿全）。
        """
        from src.core.exports import effect_report
        try:
            data = effect_report.collect_effect_by_color(
                color=color, window=window, limit=limit, per_color=per_color)
        except ValueError as e:
            return json_error(422, str(e), f"非法参数: {e}")
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/report/effect/export")
    def effect_report_export(body: dict | None = None):
        """生成《效力报告》Excel(.xlsx) 到 exports 目录，返回下载文件名
        （配合既有 GET /export/download 下载）；空库同样出文件；零库写入。

        Body 走签名（`body: dict | None`）而**不是** `await request.json()`：本端点要跑
        openpyxl 落盘，必须留在线程池里（§10.71）。body 非法 JSON → FastAPI 直接 422。
        """
        from pathlib import Path as _Path

        from src.core.exports import effect_report
        body = body or {}
        window = str(body.get("window") or "all")
        color = body.get("color")
        try:
            path = effect_report.export_effect_report_xlsx(window=window, color=color)
        except ValueError as e:
            return json_error(422, str(e), f"非法参数: {e}")
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success",
                "data": {"path": str(path), "name": _Path(path).name}}

    # ---------------------------------------------------------------- 研究报告（Phase D）
    @app.post("/api/v1/report/research")
    def research_report(payload: dict | None = None):
        """**生成一份研究报告**（Markdown + HTML + Word，本地落盘，零新增依赖）。

        这套东西到 §10.35 为止只能"把材料收进来、评审、分组"，**产出物**这一侧还是空的
        （业主的原始要求是"经用户评审确认参考资料可用后再做**分析/产出**（报告、PPT）"）。
        方案 §8 说 PPT 要单独立项、退路是"先出 Markdown/HTML"——**本端点就是那条退路**。
        §10.92 又按方案 §8 那一行（"报告：`python-docx`（Word）"）补上了 **`.docx`**：
        三种形态**同一份内容块**（`research_report.build_report_blocks`），
        所以 `files`/`names` 是**三个**（`.md` / `.html` / `.docx`），顺序固定。

        Body：`{project_id, title?, query?, conclusion_md?, limit?, dry_run?}`
        - `query`：给了就按它检索**已批准**材料并按**承重能力**分组（复用 `authority`，
          分组判据不另写一份）；不给就只列清单；
        - `conclusion_md`：结论正文，里面的 `[[m:i]]` 会被**逐条校验**
          （不存在 / 指向仅线索或不可用 ⇒ 进 `warnings`，绝不静默）；
        - `dry_run=true`：只组装不落盘（返回 markdown/html 供预览）——
          **不含 docx**：docx 是二进制，塞进 JSON 响应没有意义（§10.92）。

        ⚠ 本端点**逐份流式 sha256 材料源文件**（`_attach_locator_status` → `locator_health`
        的"源文件字节"轴）⇒ 必须是 `def`（§10.71）：几十份 PDF 就是一次真实磁盘读，
        留在事件循环里会把引擎卡住。
        """
        body = payload or {}
        project_id = body.get("project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            return json_error(422, "materials_bad_request", "缺少 project_id")
        for key in ("title", "query", "conclusion_md"):
            val = body.get(key)
            if val is not None and not isinstance(val, str):
                return json_error(422, "materials_bad_request", f"{key} 必须是字符串")
        try:
            limit = max(1, min(int(body.get("limit") or 8), 50))
        except (TypeError, ValueError):
            return json_error(422, "materials_bad_request", "limit 必须是整数")
        from src.core.exports import research_report as rrep
        try:
            if body.get("dry_run") is True:
                data = rrep.build_research_report(
                    project_id.strip(), title=body.get("title"), query=body.get("query"),
                    conclusion_md=body.get("conclusion_md"), limit=limit)
            else:
                data = rrep.write_research_report(
                    project_id.strip(), title=body.get("title"), query=body.get("query"),
                    conclusion_md=body.get("conclusion_md"), limit=limit)
        except ValueError as e:
            return json_error(404, "materials_not_found", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/report/research/slides")
    def research_report_slides(payload: dict | None = None):
        """**同内容的 PPT**（Phase D-2，§10.37）。

        内容块与 Markdown 报告**同源**（`research_report.build_report_blocks`），
        所以不会出现"报告写的和 PPT 不一样"。Body 与 `/report/research` 相同，
        只是落盘成 `.pptx`（超长要点会截断、页数有上限——都写在 PPT 末页）。

        ⚠ 内容块与 Markdown 报告**同源** ⇒ 同样**逐份 sha256 材料源文件**、同样落盘，
        必须是 `def`（§10.71，与 `/report/research` 同一条理由）。
        """
        body = payload or {}
        project_id = body.get("project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            return json_error(422, "materials_bad_request", "缺少 project_id")
        for key in ("title", "query", "conclusion_md"):
            val = body.get(key)
            if val is not None and not isinstance(val, str):
                return json_error(422, "materials_bad_request", f"{key} 必须是字符串")
        try:
            limit = max(1, min(int(body.get("limit") or 8), 50))
        except (TypeError, ValueError):
            return json_error(422, "materials_bad_request", "limit 必须是整数")
        from src.core.exports import slide_export
        try:
            data = slide_export.write_slide_deck(
                project_id.strip(), title=body.get("title"), query=body.get("query"),
                conclusion_md=body.get("conclusion_md"), limit=limit)
        except ValueError as e:
            return json_error(404, "materials_not_found", str(e))
        except RuntimeError as e:       # 缺 python-pptx 时给可操作的错误，不出空文件
            return json_error(500, "ppt_unavailable", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/report/research/draft")
    def research_report_draft(payload: dict | None = None):
        """**起草一段结论（草稿）**（Phase D-5a，§10.96）。

        业主的原始要求是"经用户评审确认参考资料可用后再做分析/产出"，而"写结论"这一步一直是
        **用户手写**（`conclusion_md`）。本端点起一稿，**不改**产出的口径：
        草稿带 `status="unapproved_draft"`，采不采用由用户逐次显式决定。

        Body：`{project_id, query, limit?}`——`query` **必填且非空**（草稿必须先知道要回答什么）。

        三条与 `research_draft` 同源的纪律：
        - **没有可承重材料 ⇒ 一次 LLM 都不调**（返回空草稿 + 警告，绝不靠常识硬写）；
        - LLM 不可用 ⇒ 500 `llm_unavailable`（**不**降级成"凭常识作答"）；
        - 草稿里的 `[[m:i]]`（**材料**引用）用**报告同一个校验器**逐条核：引用了不存在的编号、
          或引用了仅线索/不可用的材料，都进 `warnings`，草稿**原样保留**。
          ⚠ **`[[c:i]]`（法条）本次只做越界检查，不是核验**（本次起草没喂法条证据 ⇒ 那些编号
          无从核验）：若草稿里出现法条编号，会**明说**"无从核验"——**不**假装核过
          （复核 b25 的 LOW-1 指出原 docstring 那句"逐条核"说得太满）。

        ⚠ 必须 `def`：一次同步 LLM 调用（秒级到分钟级）。`/api/v1/report/` 已在
        `HEAVY_PREFIXES` 里 ⇒ 它同时吃重活令牌（§10.82）。
        """
        body = payload or {}
        project_id = body.get("project_id")
        if not isinstance(project_id, str) or not project_id.strip():
            return json_error(422, "materials_bad_request", "缺少 project_id")
        query = body.get("query")
        if not isinstance(query, str) or not query.strip():
            return json_error(422, "materials_bad_request",
                              "缺少 query（起草结论必须先有研究问题）")
        try:
            limit = max(1, min(int(body.get("limit") or 8), 50))
        except (TypeError, ValueError):
            return json_error(422, "materials_bad_request", "limit 必须是整数")
        from src.core.exports import research_draft
        try:
            data = research_draft.draft_conclusion(
                project_id.strip(), query=query.strip(), limit=limit)
        except ValueError as e:
            return json_error(404, "materials_not_found", str(e))
        except KnowledgeStationError as e:
            return json_error(500, getattr(e, "code", "internal_error"), str(e))
        return {"code": 200, "status": "success", "data": data}
