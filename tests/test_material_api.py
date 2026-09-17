# -*- coding: utf-8 -*-
"""材料平面 API 测试（Phase A 第四步）。

重点不在"每个端点都能 200"，而在**两条纪律在 HTTP 层同样成立**：
  1. 评审硬门不可绕过：未批准材料在 `/search` 里**搜不到**（硬门写在 SQL 里）；
  2. 校验在端点层是**严格**的（非法枚举 → 422，不是当成默认值放过去）。

另有一条"用户能不能真的用起来"的端到端：建项目 → 往目录丢文件 → scan → 读切片
（评审要能读到内容，否则是盲签）→ 批准 → 搜到。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.storage import material_repo as mr

HDR = {"Authorization": "Bearer test-token-123"}


def _txt(p: Path, body: str) -> Path:
    p.write_text(body, encoding="utf-8")
    return p


@pytest.fixture()
def project(client):
    c, _ = client
    r = c.post("/api/v1/materials/projects", json={"name": "API 测试项目"}, headers=HDR)
    assert r.status_code == 200, r.text
    return r.json()["data"]


class TestAuthAndValidation:
    def test_requires_token(self, client):
        c, _ = client
        assert c.get("/api/v1/materials/projects").status_code == 401

    def test_create_project_needs_name(self, client):
        c, _ = client
        r = c.post("/api/v1/materials/projects", json={}, headers=HDR)
        assert r.status_code == 422
        assert "materials_bad_request" in r.text

    def test_authority_policy_must_be_object(self, client):
        c, _ = client
        r = c.post("/api/v1/materials/projects",
                   json={"name": "x", "authority_policy": "公司制度"}, headers=HDR)
        assert r.status_code == 422

    def test_unknown_project_is_404(self, client):
        c, _ = client
        assert c.get("/api/v1/materials/projects/prj_缺少/materials",
                     headers=HDR).status_code == 404
        assert c.get("/api/v1/materials/projects/prj_缺少/search?q=x",
                     headers=HDR).status_code == 404

    def test_bad_status_filter_is_422(self, client, project):
        c, _ = client
        r = c.get(f"/api/v1/materials/projects/{project['project_id']}/materials"
                  "?status=maybe", headers=HDR)
        assert r.status_code == 422

    def test_tiers_endpoint_lists_all(self, client):
        c, _ = client
        data = c.get("/api/v1/materials/tiers", headers=HDR).json()["data"]
        assert {d["tier"] for d in data} == set(mr.TIERS)


class TestEndToEnd:
    def test_scan_review_read_then_searchable(self, client, project):
        """建项目 → 丢文件 → scan → 读切片 → 批准 → 搜到（用户侧完整闭环）。"""
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "业绩说明.txt", "公司营业收入为一百亿元，同比增长百分之十。")

        # 收件
        r = c.post(f"/api/v1/materials/projects/{pid}/scan", json={}, headers=HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["registered"] == 1
        mid = r.json()["data"]["rows"][0]["material_id"]

        # 列表里看得见，且是 pending
        rows = c.get(f"/api/v1/materials/projects/{pid}/materials", headers=HDR).json()["data"]
        assert [x["material_id"] for x in rows] == [mid]
        assert rows[0]["review_status"] == "pending"
        assert rows[0]["tier_label"] == mr.TIER_LABELS["T1"]

        # **未批准 → 搜不到**（HTTP 层的硬门）
        assert c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["count"] == 0

        # 评审前要能读到内容（否则是盲签）
        ck = c.get(f"/api/v1/materials/{mid}/chunks", headers=HDR).json()["data"]
        assert ck["total"] >= 1 and "营业收入" in ck["chunks"][0]["text"]
        assert ck["chunks"][0]["char_start"] == 0

        # 批准
        rv = c.post(f"/api/v1/materials/{mid}/review",
                    json={"status": "approved", "note": "核对过"}, headers=HDR)
        assert rv.status_code == 200 and rv.json()["data"]["review_status"] == "approved"

        # 批准后 → 搜得到，且引用字段齐备
        hits = c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["hits"]
        assert len(hits) == 1
        h = hits[0]
        assert h["material_id"] == mid
        assert h["tier_label"] == mr.TIER_LABELS["T1"]
        assert "role_label" in h            # 轴 B 的标注也要在（两个轴一起摆出来）
        assert h["char_end"] > h["char_start"]

    def test_inbox_lists_dropped_files(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "a.txt", "甲")
        (d / "忽略.bin").write_bytes(b"x")
        data = c.get(f"/api/v1/materials/projects/{pid}/inbox", headers=HDR).json()["data"]
        assert [f["file_name"] for f in data["files"]] == ["a.txt"]
        assert data["dir"]

    def test_reject_removes_from_search(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "m.txt", "营业收入九十九亿元")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        c.post(f"/api/v1/materials/{mid}/review", json={"status": "approved"}, headers=HDR)
        assert c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["count"] == 1
        c.post(f"/api/v1/materials/{mid}/review", json={"status": "rejected"}, headers=HDR)
        assert c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["count"] == 0


class TestAxesAndLifecycle:
    def test_tier_change_is_用户可改_and_recorded(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "p.txt", "内容")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        r = c.post(f"/api/v1/materials/{mid}/tier",
                   json={"tier": "T2", "reason": "监管官网原文"}, headers=HDR)
        assert r.status_code == 200
        got = r.json()["data"]
        assert (got["source_tier"], got["tier_source"]) == ("T2", "user")
        assert got["tier_reason"] == "监管官网原文"

    def test_bad_tier_is_422(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "p.txt", "内容")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        assert c.post(f"/api/v1/materials/{mid}/tier", json={"tier": "T9"},
                      headers=HDR).status_code == 422
        assert c.post(f"/api/v1/materials/{mid}/tier", json={},
                      headers=HDR).status_code == 422

    def test_role_criterion_is_settable_and_searchable(self, client, project):
        """公司制度例走 API：来源层级不高，但**是本任务的准则**。"""
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "公司差旅制度.txt", "出差住宿标准为每晚不超过五百元。")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        assert c.post(f"/api/v1/materials/{mid}/role", json={"role": "criterion"},
                      headers=HDR).status_code == 200
        c.post(f"/api/v1/materials/{mid}/review", json={"status": "approved"}, headers=HDR)
        h = c.get(f"/api/v1/materials/projects/{pid}/search?q=住宿标准",
                  headers=HDR).json()["data"]["hits"][0]
        assert h["task_role"] == "criterion" and h["role_label"] == "本任务准则"

    def test_bad_role_is_422(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "p.txt", "内容")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        assert c.post(f"/api/v1/materials/{mid}/role", json={"role": "boss"},
                      headers=HDR).status_code == 422

    def test_lifecycle_promote(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "p.txt", "内容")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        r = c.post(f"/api/v1/materials/{mid}/lifecycle", json={"lifecycle": "promoted"},
                   headers=HDR)
        assert r.json()["data"]["lifecycle"] == "promoted"
        assert c.post(f"/api/v1/materials/{mid}/lifecycle", json={"lifecycle": "forever"},
                      headers=HDR).status_code == 422

    def test_delete_removes_material(self, client, project):
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "p.txt", "内容")
        mid = c.post(f"/api/v1/materials/projects/{pid}/scan", json={},
                     headers=HDR).json()["data"]["rows"][0]["material_id"]
        assert c.delete(f"/api/v1/materials/{mid}", headers=HDR).status_code == 200
        assert c.get(f"/api/v1/materials/{mid}", headers=HDR).status_code == 404
        assert c.delete(f"/api/v1/materials/{mid}", headers=HDR).status_code == 404


# ---------------------------------------------------------------- 自采端点（Phase C-5 接线）
_PAGE = ("<html><head><title>关于住宿标准的通知</title></head>"
         "<body><h1>通知</h1><p>住宿标准每晚不超过八百元，自下月起执行。</p>"
         "<script>var tracker=1;</script></body></html>")


@pytest.fixture()
def site():
    """极简本地站点：`/ok` 正常页、`/pdf` 二进制。"""
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            return

        def do_GET(self):  # noqa: N802
            if self.path == "/ok":
                body, ctype = _PAGE.encode("utf-8"), "text/html; charset=utf-8"
            elif self.path == "/pdf":
                body, ctype = b"%PDF-1.7 not really", "application/pdf"
            elif self.path == "/png-mislabeled":
                # Content-Type 撒谎说自己是 html ⇒ 只能靠**真实字节**认出（复核 REFUTED 那条）
                body, ctype = bytes.fromhex(
                    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
                    "890000000a4944415478da6360000002000154a24f6f0000000049454e44ae426082"), \
                    "text/html; charset=utf-8"
            else:
                body, ctype = b"nope", "text/plain"
            self.send_response(200 if self.path in ("/ok", "/pdf", "/png-mislabeled") else 404)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture()
def allow_local(monkeypatch):
    """把 SSRF 判据换成"公网"以便打本地站点（**生产代码里没有这个开关**）。"""
    from src.core.materials import harvest as hv
    monkeypatch.setattr(hv._announce, "is_private_url", lambda _u: False)


def _collect(c, pid, body):
    return c.post(f"/api/v1/materials/projects/{pid}/collect", json=body, headers=HDR)


class TestCollectEndpoint:
    def test_unknown_project_is_404(self, client):
        c, _ = client
        assert _collect(c, "prj_没有", {"url": "https://a.example/x"}).status_code == 404

    def test_missing_or_blank_url_is_422(self, client, project):
        c, _ = client
        pid = project["project_id"]
        assert _collect(c, pid, {}).status_code == 422
        assert _collect(c, pid, {"url": "   "}).status_code == 422
        assert _collect(c, pid, {"url": 123}).status_code == 422

    def test_source_tier_is_refused_loudly_and_registers_nothing(self, client, project):
        """**采集者不得自 claim 可信度**（轴 A 只能由系统判据起或用户改）。

        拒绝而不是静默忽略：静默丢弃会让调用方以为自己设上了
        （本战役在 `sanitizeParams` 上栽过同款：字段被吞、没人报错）。
        """
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": "https://a.example/x", "source_tier": "T0"})
        assert r.status_code == 422, r.text
        assert "source_tier" in r.text
        assert _list(c, pid) == [], "被拒的调用不得留下材料"

    def test_ssrf_refusal_is_a_reason_not_an_error_code(self, client, project):
        """SSRF 拒绝对是**本次**抓取的结果，不是"你的请求写错了"⇒ 200 + 原因。

        这里**不打桩**：走真实的 `announce.is_private_url`（回环地址必被拒），
        所以这条用例在完全没有网络的机器上也成立。
        """
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": "http://127.0.0.1:9/x"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["collected"] is False and "SSRF" in data["reason"]
        assert _list(c, pid) == [], "被闸门拒掉的 URL 不得留下材料"

    def test_fetch_registers_pending_then_approval_makes_it_searchable(
            self, client, project, site, allow_local):
        """端到端：**采集 → 待评审 → 检索不到 → 批准 → 检索到**。"""
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": f"{site}/ok"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["collected"] is True, data
        m = data["material"]
        # 硬门没有因为"是自采的"而松
        assert m["review_status"] == "pending"
        assert m["origin"] == "collected" and m["lifecycle"] == "ephemeral"
        assert m["url"] == f"{site}/ok" and m["domain"] == "127.0.0.1"
        assert m["title"] == "关于住宿标准的通知"          # 页面标题被取到
        # **轴 A 起点是系统给的 T3**，不是调用方声称的
        assert m["source_tier"] == "T3"
        # 未批准 ⇒ 检索不到
        assert c.get(f"/api/v1/materials/projects/{pid}/search?q=住宿标准",
                     headers=HDR).json()["data"]["count"] == 0
        # 批准后 ⇒ 搜得到（同一份材料）
        c.post(f"/api/v1/materials/{m['material_id']}/review",
               json={"status": "approved"}, headers=HDR)
        hits = c.get(f"/api/v1/materials/projects/{pid}/search?q=住宿标准",
                     headers=HDR).json()["data"]["hits"]
        assert hits and hits[0]["material_id"] == m["material_id"]
        # 页面里的 JS 没有进正文（采集最脏的来源）
        chunks = c.get(f"/api/v1/materials/{m['material_id']}/chunks",
                       headers=HDR).json()["data"]["chunks"]
        assert "tracker" not in "\n".join(ch["text"] for ch in chunks)

    def test_binary_response_is_refused_over_the_route(self, client, project, site, allow_local):
        """"不是网页正文"在**路由层**也挡住了（两条判据：Content-Type 白名单 + 真实字节）。"""
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": f"{site}/pdf"})
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["collected"] is False, data
        assert "不是网页正文" in data["reason"] and "application/pdf" in data["reason"], data
        assert _list(c, pid) == []

    def test_mislabeled_binary_is_refused_by_real_bytes(self, client, project, site, allow_local):
        """Content-Type 撒谎（说自己是 html）也挡得住——判据落在**真实字节**上。"""
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": f"{site}/png-mislabeled"})
        data = r.json()["data"]
        assert data["collected"] is False and "真实字节" in data["reason"], data
        assert _list(c, pid) == []

    def test_route_does_not_offer_a_batch_entry(self, client, project, site, allow_local):
        """**结构性约束**：不得存在批量采集入口（预算/频率上限未定，方案 §11.4）。

        行为判据（不是看源码里有没有某个词）：把 `urls`（复数）当批量传 ⇒ **422**，
        且**一份都不采**。将来要加批量，必须先定预算——这条会变红，逼着那个决定
        被显式做出来，而不是顺手加个数组。
        """
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"urls": [f"{site}/ok", f"{site}/ok"]})
        assert r.status_code == 422, r.text
        assert _list(c, pid) == [], "批量形式不得采集任何一份"


def _list(c, pid):
    r = c.get(f"/api/v1/materials/projects/{pid}/materials", headers=HDR)
    return r.json()["data"]


class TestSlowEndpointsAreDeclaredSync:
    """**结构性约束**：做同步重活的端点必须声明成 `def`（Starlette 才会丢进线程池）。

    为什么这条重要（2026-09-17 自查 + 复核都指向同一处）：uvicorn 是**单事件循环**，
    `async def` 端点里的同步 I/O 会把**整个引擎**卡住——扫描要跑 MinerU（分钟级）、
    采集要抓网（最长 15 秒），期间**别的请求一起等**（GUI 看起来"死掉"）。
    判据是 `iscoroutinefunction(endpoint)`：async 端点就是在事件循环里跑。
    """

    @pytest.mark.parametrize("path", [
        "/api/v1/materials/projects/{project_id}/scan",
        "/api/v1/materials/projects/{project_id}/collect",
    ])
    def test_declared_sync(self, client, path):
        import asyncio
        c, _ = client
        routes = [r for r in c.app.routes if getattr(r, "path", None) == path]
        assert routes, f"路由不存在: {path}"
        assert not asyncio.iscoroutinefunction(routes[0].endpoint), (
            f"{path} 做同步重活，必须是 `def`（线程池），不能是 `async def`")


