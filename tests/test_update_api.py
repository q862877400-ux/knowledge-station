"""阶段六·批次5：更新模块 API 接线测试（pipeline/02 §3 端点契约）。

全部离线零联网（pipeline/05 §4-8）：
- 401 抽查走鉴权中间件短路，handler 不执行、零副作用；
- classify 为纯函数；search 仅测 drill_level=4 校验层拒绝（校验先于任何网络调用，
  见 discover.search 实现顺序）；watchlist 只落 app_config 单键；
- report/pause/resume/ack/manual 对不存在资源走业务错误码短路，不触网。

注意（会话级共享库）：watchlist 链路用例结束必须清空
'discover.download_later'——test_update_discover 的下载清单用例以空表开场断言。
"""
from __future__ import annotations

import pytest

# (method, path, json_body) —— 覆盖批次5 全部 15 个新端点（≥6 条要求）
_AUTH_CASES = [
    ("post", "/api/v1/update/check", {"tier": "tier0"}),
    ("get", "/api/v1/update/batch/bul_missing", None),
    ("post", "/api/v1/update/batch/bul_missing/pause", None),
    ("post", "/api/v1/update/batch/bul_missing/resume", None),
    ("get", "/api/v1/update/batches", None),
    ("get", "/api/v1/update/changes", None),
    ("post", "/api/v1/update/changes/chg_missing/ack", None),
    ("post", "/api/v1/update/changes/chg_missing/manual",
     {"legal_status": "effective", "note": "x"}),
    ("post", "/api/v1/update/report-xlsx/bul_missing", None),
    ("post", "/api/v1/discover/classify", {"description": "消防"}),
    ("post", "/api/v1/discover/search",
     {"category_path": ["C", "C80"], "drill_level": 1}),
    ("get", "/api/v1/discover/watchlist", None),
    ("post", "/api/v1/discover/watchlist",
     {"action": "add", "standard_no": "GB 4715-2024"}),
    ("post", "/api/v1/data/package/export", {}),
    ("post", "/api/v1/data/package/import", {"src_path": "nowhere"}),
    ("get", "/api/v1/update/subscriptions", None),
    ("put", "/api/v1/update/subscriptions", {"tags": ["消防"]}),
    ("post", "/api/v1/ingest/bulk", {"src_dir": "C:/nonexistent"}),
    ("get", "/api/v1/ingest/bulk/bul_missing", None),
    ("post", "/api/v1/ingest/bulk/bul_missing/resume", {"daily_budget": 10}),
]


@pytest.mark.parametrize("method,path,json_body", _AUTH_CASES,
                         ids=[f"{m.upper()} {p}" for m, p, _ in _AUTH_CASES])
def test_update_endpoints_require_token(client, method, path, json_body):
    """无 token 一律 401（除 health 外全站口径），错误体 unauthorized。"""
    c, _token = client
    kw = {"json": json_body} if json_body is not None else {}
    r = getattr(c, method)(path, **kw)
    assert r.status_code == 401, f"{method.upper()} {path} 未拦截匿名访问"
    body = r.json()
    assert body["status"] == "error"
    assert body["error"] == "unauthorized"


def test_classify_hit_and_broad_two_modes(client):
    """classify 正常态（唯一 leaf 命中给路径）/ 过泛态（一轮追问 ≤3 问）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}

    r = c.post("/api/v1/discover/classify",
               json={"description": "帮我找消防的标准"}, headers=h)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["category_path"] == ["C", "C80"]
    assert 0 < data["confidence"] <= 1
    assert "questions" not in data

    r2 = c.post("/api/v1/discover/classify",
                json={"description": "我要下载安全的国标"}, headers=h)
    assert r2.status_code == 200
    broad = r2.json()["data"]
    assert "category_path" not in broad          # 过泛不硬选
    assert broad["questions"] and len(broad["questions"]) <= 3
    assert all(cand["path"][0] == "C" for cand in broad["candidates"])


def test_search_drill_level_over_limit_error_code(client):
    """drill_level=4 → 422 / UPD-3002（校验层冻结码；校验先于联网，离线安全）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/discover/search",
               json={"category_path": ["C", "C80"], "drill_level": 4}, headers=h)
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "UPD-3002"
    assert body["status"] == "error"


def test_pause_resume_and_get_missing_batch_404(client):
    """批次不存在：GET 进度 / pause / resume 均 404 + UPD-2003。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    missing = "bul_no_such_batch_api"
    for method in ("get", "post"):
        url = f"/api/v1/update/batch/{missing}"
        if method == "post":
            for action in ("pause", "resume"):
                r = c.post(f"{url}/{action}", headers=h)
                assert r.status_code == 404, action
                assert r.json()["error"] == "UPD-2003"
        else:
            r = c.get(url, headers=h)
            assert r.status_code == 404
            assert r.json()["error"] == "UPD-2003"


def test_watchlist_add_list_remove_idempotent_chain(client):
    """F-18 幂等链：add → list → 重复 add 不翻倍 → remove → 空 → 再 remove 无操作。
    结束态清空 download_later（保护共享库内其他用例的空表开场断言）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    wl = "/api/v1/discover/watchlist"

    # 清场（会话级共享库防串扰）
    for it in c.get(wl, headers=h).json()["data"]:
        c.post(wl, json={"action": "remove",
                         "standard_no": it["standard_no"]}, headers=h)

    r1 = c.post(wl, json={"action": "add", "standard_no": "GB 4715-2024",
                          "name": "点型感烟火灾探测器"}, headers=h)
    assert r1.status_code == 200
    assert r1.json()["data"]["total"] == 1

    # 重复添加（同号不同排版）幂等：仍是一条
    r2 = c.post(wl, json={"action": "add", "standard_no": "GB  4715-2024",
                          "name": "点型感烟火灾探测器"}, headers=h)
    assert r2.status_code == 200
    assert r2.json()["data"]["total"] == 1

    listed = c.get(wl, headers=h).json()["data"]
    assert len(listed) == 1
    assert set(listed[0]) >= {"standard_no", "name", "added_at"}
    assert listed[0]["name"] == "点型感烟火灾探测器"

    rm = c.post(wl, json={"action": "remove",
                          "standard_no": "GB4715-2024"}, headers=h)  # 归一号匹配
    assert rm.status_code == 200 and rm.json()["data"]["items"] == []
    assert c.get(wl, headers=h).json()["data"] == []

    # 再 remove 不存在项 = 无操作，仍 200
    rm2 = c.post(wl, json={"action": "remove",
                           "standard_no": "GB 4715-2024"}, headers=h)
    assert rm2.status_code == 200 and rm2.json()["data"]["items"] == []


def test_report_missing_batch_business_error(client):
    """report 对不存在批次 → 404 业务错误码 UPD-2003（不产出文件）。

    ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原先打的是 `/api/v1/update/report/{batch_id}`
    （**Word** 版）——该端点已随业主否决 Word/PPT 交付物一并拆除
    （`docs/NOT-DOING.md` 第 1 条）⇒ 改打**留存的 Excel 版** `/update/report-xlsx/{batch_id}`，
    判据（404 + `UPD-2003` + `status=error`）逐字不变。
    """
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/update/report-xlsx/upd_no_such_batch", headers=h)
    assert r.status_code == 404
    body = r.json()
    assert body["error"] == "UPD-2003"
    assert body["status"] == "error"


def test_manual_illegal_status_422_module_frozen_code(client):
    """manual 非法 legal_status → 422；码取 change_repo.manual_status 冻结实现
    UPD-3001（illegal_legal_status；指令文案的 3003 是 batch_not_found 位段）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/update/changes/chg_missing/manual",
               json={"legal_status": "draft", "note": "人工标注"},
               headers=h)
    assert r.status_code == 422
    body = r.json()
    assert body["error"] == "UPD-3001"
    assert "draft" in body["message"]

    # 缺字段同样 422/UPD-3001
    r2 = c.post("/api/v1/update/changes/chg_missing/manual",
                json={"note": "无状态"}, headers=h)
    assert r2.status_code == 422 and r2.json()["error"] == "UPD-3001"


def test_ack_missing_change_404(client):
    """ack 对不存在变更事件 → 404 / UPD-2002。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.post("/api/v1/update/changes/chg_no_such/ack", headers=h)
    assert r.status_code == 404
    assert r.json()["error"] == "UPD-2002"


def test_batches_and_changes_listing_shape(client):
    """历史批次与变更明细列表端点：包裹格式正确、返回 list（空库亦然）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    rb = c.get("/api/v1/update/batches?limit=5", headers=h)
    assert rb.status_code == 200
    assert isinstance(rb.json()["data"], list)

    rc = c.get("/api/v1/update/changes?change_type=no_change&limit=10", headers=h)
    assert rc.status_code == 200
    body = rc.json()
    assert isinstance(body["data"], list)
    assert body["total"] == len(body["data"])


def test_subscriptions_get_default_all_enabled(client):
    """订阅 GET：缺省全开（vocab 全量 enabled=True）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/update/subscriptions", headers=h)
    assert r.status_code == 200
    data = r.json()["data"]
    assert isinstance(data["vocab"], list) and len(data["vocab"]) >= 5
    assert all(d["enabled"] for d in data["domains"])
    assert {d["tag"] for d in data["domains"]} == set(data["vocab"])


def test_subscriptions_put_save_and_get_consistent(client):
    """订阅 PUT：全量替换保存后 GET 一致；重复 PUT 幂等。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r1 = c.put("/api/v1/update/subscriptions", json={"tags": ["消防", "化工"]}, headers=h)
    assert r1.status_code == 200
    saved = r1.json()["data"]["domains"]
    assert {d["tag"] for d in saved if d["enabled"]} == {"消防", "化工"}

    r2 = c.get("/api/v1/update/subscriptions", headers=h)
    active = {d["tag"] for d in r2.json()["data"]["domains"] if d["enabled"]}
    assert active == {"消防", "化工"}

    r3 = c.put("/api/v1/update/subscriptions", json={"tags": ["消防", "化工"]}, headers=h)
    assert r3.status_code == 200
    assert {d["tag"] for d in r3.json()["data"]["domains"] if d["enabled"]} == {"消防", "化工"}


def test_subscriptions_illegal_tag_422(client):
    """订阅 PUT：非法 tag → 422/UPD-3001，且不落库（GET 仍为全开或上次状态）。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    r = c.put("/api/v1/update/subscriptions", json={"tags": ["不存在的领域XX"]}, headers=h)
    assert r.status_code == 422
    assert r.json()["error"] == "UPD-3001"
    r2 = c.get("/api/v1/update/subscriptions", headers=h)
    assert r2.status_code == 200  # 状态未损坏


def test_doc_full_clauses_returns_rich_text_with_page(client):
    """2026-08-27 全文富文本预览接口：某文档全部条款含 content_html 与 page_start。"""
    c, token = client
    h = {"Authorization": f"Bearer {token}"}
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    # id 用文件前缀唯一名：conftest 数据目录为 session 级（跨测试文件共享库），
    # 通用短 id（如 'c1'）会与 test_retrieval 等先跑文件的残留数据撞 UNIQUE（2026-08-31）
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES ('doc_upd_full','GB 1-2025','测试标准','GB1','r1','[]','/x.pdf','h1')")
    conn.execute(
        "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id, clause_key,"
        " clause_number, content_text, content_markdown, page_start, page_end)"
        " VALUES ('cr_upd_full','r1','doc_upd_full','k1','1.1','第一段 全文内容',"
        " '<p>第一段 全文内容</p>', 3, 3)")
    conn.commit()
    r = c.get("/api/v1/documents/doc_upd_full/clauses", headers=h)
    assert r.status_code == 200
    clauses = r.json()["data"]["clauses"]
    assert clauses and clauses[0]["clause_number"] == "1.1"
    assert clauses[0]["page_start"] == 3
    assert "第一段" in clauses[0]["content_html"]
