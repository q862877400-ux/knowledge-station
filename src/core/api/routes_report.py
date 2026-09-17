"""效力报告 API 路由（决策 21 · 用户修订版）：纯聚合只读三端点。

- GET  /api/v1/report/effect        骨架+四色统计（秒级同步 GET，无 fire-and-forget）
- GET  /api/v1/report/effect/docs   节点明细（瘦身行，limit 封顶——payload 红线）
- POST /api/v1/report/effect/export openpyxl 落 exports 目录（空库也出文件），
  下载走既有 GET /export/download（穿越防护已有）。
- POST /api/v1/report/research      **研究报告**（Phase D，§10.36）：Markdown + HTML 落盘，
  材料依据按承重能力分组、引用标记逐条校验、未批准材料如实列出（零新增依赖）。

校验语义：非法 window/color/top/l2 → 422（invalid_*）；E2 未知名路径 → 200 空集
（L2/L3/L4 是展示串非稳定 ID，库内重分类后旧名自然为空，404 会让 UI 抖动）。
"""
from __future__ import annotations

from fastapi import Request

from src.core.exceptions import KnowledgeStationError


def register(app, json_error):
    @app.get("/api/v1/report/effect")
    async def effect_report(window: str = "all", color: str | None = None):
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
    async def effect_report_docs(top: str, l2: str, l3: str | None = None,
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
    async def effect_report_by_color(color: str, window: str = "all", limit: int = 20,
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
    async def effect_report_export(request: Request):
        """生成《效力报告》Excel(.xlsx) 到 exports 目录，返回下载文件名
        （配合既有 GET /export/download 下载）；空库同样出文件；零库写入。"""
        from pathlib import Path as _Path

        from src.core.exports import effect_report
        try:
            body = await request.json()
        except Exception:
            body = {}
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
    async def research_report(payload: dict | None = None):
        """**生成一份研究报告**（Markdown + HTML，本地落盘，零新增依赖）。

        这套东西到 §10.35 为止只能"把材料收进来、评审、分组"，**产出物**这一侧还是空的
        （业主的原始要求是"经用户评审确认参考资料可用后再做**分析/产出**（报告、PPT）"）。
        方案 §8 说 PPT 要单独立项、退路是"先出 Markdown/HTML"——**本端点就是那条退路**。

        Body：`{project_id, title?, query?, conclusion_md?, limit?, dry_run?}`
        - `query`：给了就按它检索**已批准**材料并按**承重能力**分组（复用 `authority`，
          分组判据不另写一份）；不给就只列清单；
        - `conclusion_md`：结论正文，里面的 `[[m:i]]` 会被**逐条校验**
          （不存在 / 指向仅线索或不可用 ⇒ 进 `warnings`，绝不静默）；
        - `dry_run=true`：只组装不落盘（返回 markdown/html 供预览）。
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
