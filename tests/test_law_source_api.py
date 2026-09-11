"""官方法规来源 API 测试（LAW_SOURCE_PLAN P2）：sources / search / ingest（mock 网络）。"""
import pytest


def test_law_sources_lists_whitelist(client):
    c, token = client
    r = c.get("/api/v1/laws/sources", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    sources = {s["source"] for s in r.json()["data"]}
    assert {"flk", "govcn"} <= sources


def test_law_search_flk(monkeypatch, client):
    c, token = client

    def fake_flk_search(content, **kw):
        return {"code": 200, "total": 1, "rows": [{
            "bbbs": "bbbs_x", "title": "中华人民共和国消防法", "flxz": "法律",
            "zdjgName": "全国人大常委会", "gbrq": "2021-04-29",
            "sxrq": "2021-04-29", "sxx": 3}]}

    import src.core.api.server as srv
    monkeypatch.setattr("src.core.knowledge.law_source.flk_client.search", fake_flk_search)
    r = c.post("/api/v1/laws/search", json={"source": "flk", "query": "消防法",
                                            "effective": True},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200 and body["total"] == 1
    assert body["data"][0]["bbbs"] == "bbbs_x"


def test_law_search_govcn(monkeypatch, client):
    c, token = client

    def fake_govcn_search(keyword, **kw):
        return {"code": 200, "searchVO": {"catMap": {"gongwen": {"listVO": [{
            "title": "国务院办公厅关于消防的通知", "pcode": "国办发〔2024〕1号",
            "source": "国务院办公厅", "pubtime": "1700000000000",
            "piclinksurl": "https://www.gov.cn/zhengce/content/1.htm"}]}}}}

    import src.core.api.server as srv
    monkeypatch.setattr("src.core.knowledge.law_source.govcn_client.search", fake_govcn_search)
    r = c.post("/api/v1/laws/search", json={"source": "govcn", "query": "消防"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["data"][0]["pcode"] == "国办发〔2024〕1号"


def test_law_search_rejects_third_party(monkeypatch, client):
    """白名单外域被拒（403），不静默放行。"""
    c, token = client

    def boom(keyword, **kw):
        from src.core.knowledge.law_source.http import check_host
        check_host("https://evil.example.com/x")  # 抛 ValueError

    monkeypatch.setattr("src.core.knowledge.law_source.govcn_client.search", boom)
    r = c.post("/api/v1/laws/search", json={"source": "govcn", "query": "x"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "白名单" in r.json()["message"]


def test_law_ingest_flk(monkeypatch, client):
    c, token = client
    called = {}

    def fake_ingest(bbbs, **kw):
        called.update(bbbs=bbbs, kw=kw)
        return {"status": "ok", "doc_id": "doc_law1", "total_clauses": 77,
                "source": "flk", "source_id": bbbs}

    import src.core.api.server as srv
    monkeypatch.setattr("src.core.knowledge.law_source.ingest.ingest_law_from_flk", fake_ingest)
    r = c.post("/api/v1/laws/ingest", json={"source": "flk", "bbbs": "bbbs1",
                                            "domain_tags": ["消防", "法律"]},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert called["bbbs"] == "bbbs1"
    assert called["kw"]["domain_tags"] == ["消防", "法律"]


def test_law_ingest_requires_bbbs_or_url(client):
    c, token = client
    r = c.post("/api/v1/laws/ingest", json={"source": "flk"},
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422


# ===== 法规总目录 + 点开即核验（docs/LAW_CATALOG_ONDEMAND_PLAN.md 任务 1/3）=====


def test_law_catalog_query_shape_and_filter(client):
    """GET /api/v1/laws/catalog 返回分页形状；q 标题子串过滤（隔离共享库）。"""
    from src.core.knowledge.law_source.catalog import ensure_catalog_schema
    from src.core.storage.sqlite_db import write_transaction
    c, token = client
    ensure_catalog_schema()
    mark = "API目录独占词W9"
    with write_transaction() as txn:
        txn.execute(
            "INSERT OR IGNORE INTO law_catalog (title,bbbs,flxz,sxx,category,gbrq,sxrq)"
            " VALUES (?,?,?,?,?,?,?)",
            (f"{mark}条例", "bbapi-1", "部门规章", 3, "API分类",
             "2024-01-01", "2024-06-01"))
    r = c.get("/api/v1/laws/catalog", params={"q": mark, "page_size": 10},
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200 and body["status"] == "success"
    data = body["data"]
    assert {"items", "total", "page", "page_size", "pages", "categories"} <= set(data)
    assert data["total"] >= 1
    assert data["items"][0]["bbbs"] == "bbapi-1"
    assert data["items"][0]["title"] == f"{mark}条例"
    assert "API分类" in data["categories"]


def test_law_catalog_refresh_mocked(monkeypatch, client):
    """POST /api/v1/laws/catalog/refresh 透传 refresh_catalog 结果（mock 网络）。"""
    c, token = client
    fake = {"total": 10, "by_category": {"法律T": 10}, "warnings": [],
            "fetched": 10, "skipped": 0, "written": 10, "elapsed_sec": 1}
    monkeypatch.setattr("src.core.knowledge.law_source.catalog.refresh_catalog",
                        lambda: fake)
    r = c.post("/api/v1/laws/catalog/refresh",
               headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200 and body["data"]["total"] == 10
    assert body["data"]["warnings"] == []


def test_law_verify_passthrough(monkeypatch, client):
    """GET /api/v1/laws/verify?bbbs= 透传 verify_law 载荷（mock 网络）。"""
    c, token = client
    fake = {"status": "effective", "status_text": "现行有效",
            "evidence_url": "https://flk.npc.gov.cn/detail?id=bbv1",
            "checked_at": "2026-08-24T10:00:00+08:00", "cached": False,
            "retryable": False}
    monkeypatch.setattr("src.core.knowledge.law_source.verify.verify_law",
                        lambda _bbbs: fake)
    r = c.get("/api/v1/laws/verify", params={"bbbs": "bbv1"},
              headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 200 and body["data"]["status"] == "effective"
    assert body["data"]["evidence_url"].endswith("bbv1")


def test_law_verify_missing_bbbs(client):
    c, token = client
    r = c.get("/api/v1/laws/verify", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 422
