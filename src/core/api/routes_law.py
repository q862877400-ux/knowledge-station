"""官方法规来源 API 路由（2026-08-26，P3-②）：从 server.py create_app 闭包抽出。

- /api/v1/laws/sources|search|ingest|check-updates（LAW_SOURCE_PLAN P2）
- /api/v1/laws/catalog|refresh|verify（LAW_CATALOG_ONDEMAND_PLAN 任务 1/2）
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import Request

logger = logging.getLogger("ks.api.law")


def register(app, json_error):
    # ===== 官方法规来源（LAW_SOURCE_PLAN P2）：搜索候选 / 入库 =====

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
    async def law_search(request: Request):
        """官方源搜索候选（dry-run，不落库）。
        flk:  {source:'flk', query, effective?}
        govcn: {source:'govcn', query, childtype?, year?, department?}"""
        from src.core.knowledge.law_source import flk_client as flk
        from src.core.knowledge.law_source import govcn_client as govcn
        try:
            body = await request.json()
        except Exception:
            return json_error(422, "bad_json", "请求体非 JSON")
        source = str(body.get("source") or "flk")
        query = str(body.get("query") or "").strip()
        if not query:
            return json_error(422, "missing_query", "缺少 query")
        try:
            if source == "flk":
                data = await asyncio.to_thread(
                    flk.search, query,
                    search_range=int(body.get("field", 1)),
                    sxx=[3] if body.get("effective") else None,
                    page=int(body.get("page", 1)),
                    page_size=min(int(body.get("size", 20)), 100))
                return {"code": 200, "status": "success",
                        "data": flk.parse_rows(data), "total": data.get("total", 0)}
            if source == "govcn":
                data = await asyncio.to_thread(
                    govcn.search, query,
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
    async def law_ingest(request: Request):
        """官方源下载 docx → 转 PDF → 现有管线入库（同步，长任务）。
        flk:  {source:'flk', bbbs, standard_name?, domain_tags?, reingest?}
        govcn: {source:'govcn', url, standard_name?, domain_tags?, reingest?}"""
        from src.core.knowledge.law_source.ingest import (
            ingest_law_from_flk, ingest_law_from_govcn,
        )
        try:
            body = await request.json()
        except Exception:
            return json_error(422, "bad_json", "请求体非 JSON")
        source = str(body.get("source") or "")
        tags = [str(t).strip() for t in (body.get("domain_tags") or []) if str(t).strip()]
        reingest = bool(body.get("reingest"))
        try:
            if source == "flk":
                bbbs = str(body.get("bbbs") or "")
                if not bbbs:
                    return json_error(422, "missing_bbbs", "缺少 bbbs")
                out = await asyncio.to_thread(
                    ingest_law_from_flk, bbbs,
                    standard_name=body.get("standard_name") or None,
                    domain_tags=tags, reingest=reingest)
            elif source == "govcn":
                url = str(body.get("url") or "")
                if not url:
                    return json_error(422, "missing_url", "缺少 url")
                out = await asyncio.to_thread(
                    ingest_law_from_govcn, url,
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
    async def law_check_updates():
        """法规更新检查（只读）：库内官方来源文档 vs 官方源现状 → 时效变更/新版本。"""
        from src.core.knowledge.law_source.update import check_law_updates
        return {"code": 200, "status": "success",
                "data": await asyncio.to_thread(check_law_updates)}

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
    async def law_catalog_refresh():
        """全量遍历 flk 官方清单入本地目录（同步长任务；分类级账本断点续传，可重复执行）。
        返回 {total, by_category, warnings, fetched, skipped, elapsed_sec, ...}。"""
        from src.core.knowledge.law_source.catalog import refresh_catalog
        try:
            data = await asyncio.to_thread(refresh_catalog)
        except Exception as e:  # noqa: BLE001 枚举/网络整体失败 → 明确报错
            return json_error(502, "catalog_refresh_failed", f"法规目录刷新失败: {e}")
        return {"code": 200, "status": "success", "data": data}

    @app.get("/api/v1/laws/verify")
    async def law_verify(request: Request):
        """点开即核验（任务 2）：查单个 bbbs 官方效力状态，完全透传 verify_law dict。
        status=effective/superseded/withdrawn/upcoming/unmarked/not_found/unverified；
        unverified 时 retryable=true；evidence_url=官方证据页供打开。绝不抛错。"""
        from src.core.knowledge.law_source.verify import verify_law
        bbbs = str(request.query_params.get("bbbs") or "").strip()
        if not bbbs:
            return json_error(422, "missing_bbbs", "缺少 bbbs")
        return {"code": 200, "status": "success",
                "data": await asyncio.to_thread(verify_law, bbbs)}
