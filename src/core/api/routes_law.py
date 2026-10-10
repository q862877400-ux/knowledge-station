"""官方法规来源 API 路由（2026-08-26，P3-②）：从 server.py create_app 闭包抽出。

- /api/v1/laws/sources|search|ingest|check-updates（LAW-SOURCE-PLAN P2）
- /api/v1/laws/catalog|refresh|verify（LAW_CATALOG_ONDEMAND_PLAN 任务 1/2）

⚠ **本文件的端点一律声明成 `def`**（§10.93 收口 §10.79 的遗留项）：
这 5 条原先写成 `async def` **只为了** `await request.json()`（search/ingest）或
`await asyncio.to_thread(...)`（全部 5 条）。后者看起来像"已经让出事件循环了"，
其实**换错了一口池子**——`asyncio.to_thread` 走的是 **asyncio 的默认执行器**
（`min(32, cpu+4)` 个 worker），**不是** Starlette/anyio 那口被 `THREADPOOL_TOKENS = 16`
收窄过的池，也**不吃**重活闸门（`HEAVY_TOKENS = 4`）的令牌 ⇒ 这两道 2026-09-18 建立的
界在这一族端点上等于不存在（详见 §10.93；`tests/test_threadpool_bound.py` 有一条
**行为级**用例把这个不对称钉住）。改回 `def` 之后它们回到那口有界的池子。

代价（与 §10.86 那 51 条同款，诚实登记）：body 由 FastAPI 在派发进线程池**之前**解析，
所以**非法 JSON / 空 body 的报错形状变了**——原先是本文件的
`json_error(422, "bad_json", "请求体非 JSON")`，现在是 FastAPI 自己的 422 校验错误
（空 body ⇒ `payload is None` ⇒ 走各端点自己的"缺少 xxx"分支，状态码仍是 422）。
"""
from __future__ import annotations

import logging

from fastapi import Request

logger = logging.getLogger("ks.api.law")


def register(app, json_error):
    # ===== 官方法规来源（LAW-SOURCE-PLAN P2）：搜索候选 / 入库 =====

    @app.get("/api/v1/laws/sources")
    def law_sources():
        """官方来源白名单元信息（前端法规抓取面板数据源）。"""
        return {"code": 200, "status": "success", "data": [
            {"source": "flk", "name": "国家法律法规数据库",
             "home": "https://flk.npc.gov.cn/",
             "detail": "法律/行政法规/监察法规/司法解释/地方性法规（全国人大主办）"},
            {"source": "govcn", "name": "国务院政策文件库",
             "home": "https://www.gov.cn/zhengce/xxgk/gjgzk/index.htm",
             "detail": "国务院文件/部门文件（国令/国发/国办发等，按文号/机关/年份检索）"},
        ]}

    @app.post("/api/v1/laws/search")
    def law_search(payload: dict | None = None):
        """官方源搜索候选（dry-run，不落库）。
        flk:  {source:'flk', query, effective?}
        govcn: {source:'govcn', query, childtype?, year?, department?}"""
        from src.core.knowledge.law_source import flk_client as flk
        from src.core.knowledge.law_source import govcn_client as govcn
        body = payload or {}
        source = str(body.get("source") or "flk")
        query = str(body.get("query") or "").strip()
        if not query:
            return json_error(422, "missing_query", "缺少 query")
        try:
            if source == "flk":
                data = flk.search(query,
                                  search_range=int(body.get("field", 1)),
                                  sxx=[3] if body.get("effective") else None,
                                  page=int(body.get("page", 1)),
                                  page_size=min(int(body.get("size", 20)), 100))
                return {"code": 200, "status": "success",
                        "data": flk.parse_rows(data), "total": data.get("total", 0)}
            if source == "govcn":
                data = govcn.search(query,
                                    field=str(body.get("field", "title")),
                                    page=int(body.get("page", 0)),
                                    size=min(int(body.get("size", 20)), 100),
                                    childtype=str(body.get("childtype") or ""),
                                    year=str(body.get("year") or ""),
                                    department=str(body.get("department") or ""))
                rows = govcn.parse_rows(data)
                return {"code": 200, "status": "success",
                        "data": rows, "total": len(rows)}
        except ValueError as e:
            return json_error(403, "source_not_allowed", str(e))
        except Exception as e:  # noqa: BLE001 网络/接口异常统一上报
            return json_error(502, "source_fetch_failed", f"官方源请求失败: {e}")
        return json_error(400, "bad_source", "source 仅支持 flk / govcn")

    @app.post("/api/v1/laws/ingest")
    def law_ingest(payload: dict | None = None):
        """官方源下载 docx → 转 PDF → 现有管线入库（同步，长任务）。
        flk:  {source:'flk', bbbs, standard_name?, domain_tags?, reingest?}
        govcn: {source:'govcn', url, standard_name?, domain_tags?, reingest?}"""
        from src.core.knowledge.law_source.ingest import (
            ingest_law_from_flk, ingest_law_from_govcn,
        )
        body = payload or {}
        source = str(body.get("source") or "")
        tags = [str(t).strip() for t in (body.get("domain_tags") or []) if str(t).strip()]
        reingest = bool(body.get("reingest"))
        try:
            if source == "flk":
                bbbs = str(body.get("bbbs") or "")
                if not bbbs:
                    return json_error(422, "missing_bbbs", "缺少 bbbs")
                out = ingest_law_from_flk(
                    bbbs,
                    standard_name=body.get("standard_name") or None,
                    domain_tags=tags, reingest=reingest)
            elif source == "govcn":
                url = str(body.get("url") or "")
                if not url:
                    return json_error(422, "missing_url", "缺少 url")
                out = ingest_law_from_govcn(
                    url,
                    standard_name=body.get("standard_name") or None,
                    domain_tags=tags, reingest=reingest)
            else:
                return json_error(400, "bad_source", "source 仅支持 flk / govcn")
        except ValueError as e:
            return json_error(403, "source_not_allowed", str(e))
        except Exception as e:  # noqa: BLE001
            return json_error(502, "ingest_failed", f"法规入库失败: {e}")
        code = 200 if out.get("status") == "ok" else 422
        return {"code": code,
                "status": "success" if code == 200 else "error",
                "data": out}

    @app.post("/api/v1/laws/check-updates")
    def law_check_updates():
        """法规更新检查（只读）：库内官方来源文档 vs 官方源现状 → 时效变更/新版本。"""
        from src.core.knowledge.law_source.update import check_law_updates
        return {"code": 200, "status": "success",
                "data": check_law_updates()}

    # ===== 法规总目录 + 点开即核验（docs/LAW_CATALOG_ONDEMAND_PLAN.md 任务 1/2）=====

    @app.get("/api/v1/laws/catalog")
    def law_catalog(request: Request):
        """法规总目录查询（本地 law_catalog 表；flk 全量清单，任务 1）。
        ?q=标题子串 & category=分类 & sxx=时效(1废止/2已修改/3现行/4未生效)
        & page= & page_size=（上限 200；缺省 50）。"""
        from src.core.knowledge.law_source.catalog import query_catalog
        try:
            qp = request.query_params
            page_size = min(int(str(qp.get("page_size", 50) or "50")), 200)
            data = query_catalog(
                q=str(qp.get("q") or ""),
                category=str(qp.get("category") or ""),
                sxx=str(qp.get("sxx") or ""),
                page=int(str(qp.get("page", 1) or "1")),
                page_size=page_size)
        except (TypeError, ValueError) as e:
            return json_error(422, "bad_params", f"查询参数非法: {e}")
        return {"code": 200, "status": "success", "data": data}

    @app.post("/api/v1/laws/catalog/refresh")
    def law_catalog_refresh():
        """全量遍历 flk 官方清单入本地目录（同步长任务；分类级账本断点续传，可重复执行）。
        返回 {total, by_category, warnings, fetched, skipped, elapsed_sec, ...}。"""
        from src.core.knowledge.law_source.catalog import refresh_catalog
        try:
            data = refresh_catalog()
        except Exception as e:  # noqa: BLE001 枚举/网络整体失败 → 明确报错
            return json_error(502, "catalog_refresh_failed", f"法规目录刷新失败: {e}")
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/laws/verify")
    def law_verify(request: Request):
        """点开即核验（任务 2）：查单个 bbbs 官方效力状态，完全透传 verify_law dict。
        status=effective/superseded/withdrawn/upcoming/unmarked/not_found/unverified；
        unverified 时 retryable=true；evidence_url=官方证据页供打开。绝不抛错。"""
        from src.core.knowledge.law_source.verify import verify_law
        bbbs = str(request.query_params.get("bbbs") or "").strip()
        if not bbbs:
            return json_error(422, "missing_bbbs", "缺少 bbbs")
        return {"code": 200, "status": "success",
                "data": verify_law(bbbs)}

    @app.get("/api/v1/laws/history")
    def law_history(request: Request):
        """一部法规的**历次版本链**（spec 006 US2；flk 详情接口的 `lsyg` 历史沿革）。

        `?bbbs=` 必填。返回 `data.versions`（按公布日期降序）+ `data.count`。

        ⚠ **空链与查询失败必须区分**（spec FR-007）：
        - 官方无 `lsyg` ⇒ `200` + `versions: []`（确实没有历次版本）；
        - 官方不可达 ⇒ `502`，**绝不**用空列表冒充"无版本"。
        """
        from src.core.knowledge.law_source import flk_client as flk
        bbbs = str(request.query_params.get("bbbs") or "").strip()
        if not bbbs:
            return json_error(422, "missing_bbbs", "缺少 bbbs")
        try:
            versions = flk.history(bbbs)
        except ValueError as e:
            return json_error(403, "source_not_allowed", str(e))
        except Exception as e:  # noqa: BLE001 网络/接口异常统一上报（不伪装成空链）
            return json_error(502, "history_fetch_failed", f"官方源请求失败: {e}")
        return {"code": 200, "status": "success",
                "data": {"bbbs": bbbs, "count": len(versions),
                         "versions": versions}}

    # ===== 合规护栏判定（2026-09-24，Jev / TypeSafe System One）=====

    @app.get("/api/v1/laws/change-signals")
    def law_change_signals(request: Request, signal: str | None = None, limit: int = 100):
        """**最近哪些法规/标准变了**（2026-09-24，§10.195 业主第一目的"实时获取发布/更新/修改/废止"）。

        读 `doc_meta.change_signal`——**确定性规则**算出来的，不是模型输出（见
        `web_ingest.classify_change_signal`）。`signal` 省略 = 四类都回；给了就只回那一类
        （`draft`/`repealed`/`revised`/`issued`）；非法值给 422（**不静默当"全部"**）。
        ⚠ 这是**线索**不是结论：它说"这份文件是某条发生变化的证据"，具体变成什么了要点开原文。
        """
        from src.core.storage.sqlite_db import get_db_connection
        kinds = ("draft", "repealed", "revised", "issued")
        want = (signal or "").strip()
        if want and want not in kinds:
            return json_error(422, "invalid_signal", f"signal 只能是 {kinds} 之一")
        n = max(1, min(int(limit or 100), 500))
        sql = ("SELECT doc_id, standard_no, standard_name, legal_status, change_signal,"
               " published_at, effective_from, source_url"
               " FROM doc_meta WHERE change_signal IS NOT NULL")
        args: list = []
        if want:
            sql += " AND change_signal=?"
            args.append(want)
        sql += " ORDER BY COALESCE(published_at,'') DESC, doc_id DESC LIMIT ?"
        args.append(n)
        rows = get_db_connection().execute(sql, args).fetchall()
        by_kind = {r[0]: r[1] for r in get_db_connection().execute(
            "SELECT change_signal, COUNT(*) FROM doc_meta"
            " WHERE change_signal IS NOT NULL GROUP BY 1").fetchall()}
        return {"code": 200, "status": "success",
                "data": {"count": len(rows), "by_signal": by_kind,
                         "items": [dict(r) for r in rows]}}

    @app.post("/api/v1/laws/compliance-guard")
    def compliance_guard(body: dict | None = None):
        """判一段用户输入要不要带上合规查库流程（`jev_guard.judge` 的薄端点）。

        - 返回 `data.available=false` 表示 **Jev 不可用**（没配 Key / 熔断 / 响应不合契约）
          —— 调用方据此退回词表，**不得**当"判定为不触发"。
        - `verdict` ∈ `trigger`（带完整规则）/ `review`（中间档）/ `silent`（安静）。
        - ⚠ 同步端点（**`def` 不是 `async def`**，见本文件头 §10.93：绕开线程池闸门）。
          Jev 有 2s 超时 + 熔断（`jev_client`），最坏情况就是这次调用等 2s。
        """
        from src.core.llm import jev_guard
        payload = body if isinstance(body, dict) else {}
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            return json_error(422, "missing_text", "缺少 text")
        verdict = jev_guard.judge(text)
        if verdict is None:
            return {"code": 200, "status": "success",
                    "data": {"available": False, "verdict": "unknown"}}
        return {"code": 200, "status": "success",
                "data": {"available": True, **verdict}}
