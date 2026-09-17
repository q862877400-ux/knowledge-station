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

    @pytest.mark.parametrize("key", [
        "sourceTier", "tier", "review_status", "origin", "lifecycle", "kind", "doc_id",
    ])
    def test_unknown_body_keys_are_refused_not_ignored(self, key, client, project):
        """**未知字段一律拒绝**（2026-09-17 复核 A 的 MEDIUM）。

        原来只挡 `source_tier` **一个拼写**，同义/同名键全部 200 + **静默忽略**——
        与"响亮拒绝、绝不静默丢弃"的立论冲突（硬门未松动，危害是**误导调用方**：
        它以为自己设上了 `review_status='approved'` 之类）。白名单比黑名单可靠。
        """
        c, _ = client
        pid = project["project_id"]
        r = _collect(c, pid, {"url": "https://a.example/x", key: "x"})
        assert r.status_code == 422, f"{key}: {r.status_code} {r.text}"
        assert key in r.text, r.text
        assert _list(c, pid) == []

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


@pytest.fixture()
def track_l_docs(db):
    """登记本类测试往**法条链**写的 doc_id，**测完删干净**（同 `test_material_track_l`）。

    ⚠ 必须清：`db` 是**会话级共用库**，而 `test_quality_rules` 里有一个**全局**断言
    （"质量问题的条款恰好 5 条"）——本类测试是又一处往 `doc_meta`/`clause_revision`
    写东西的材料测试。清理走既有的 `clause_repo.delete_document`（它会连虚拟表孤儿行一起清）。
    """
    created: list[str] = []
    yield created
    from src.core.storage import clause_repo as cr
    for doc_id in created:
        try:
            cr.delete_document(doc_id)
        except Exception:  # noqa: BLE001 — 清理失败不该把测试结论改写成失败
            pass


_STD_TEXT = (
    "GB 88888-2088 某安全技术规范\n"
    "1 范围\n本文件规定了某安全技术要求。\n"
    "3.1 术语\n某术语的定义。\n"
    "3.2 又一条术语\n又一条定义。\n"
    "4.1 要求\n应满足下列要求。\n"
    "4.2 试验方法\n按下列方法试验。\n"
)


def _collect_text_material(c, pid, *, title, text):
    """用**采集门**登记一份文本材料（走 `collect_text` 的公共入口，不经网络）。

    为什么不用 `collect` 路由：那条要真抓网。这里用 `co.collect_text` 直接登记，
    与"AI 自己采到的东西"是**同一条**入库路径（同一个门、同样的 pending/ephemeral）。
    """
    from src.core.materials import collect as co
    return co.collect_text(pid, title=title, text=text, url="https://a.example/1")


class TestApprovalTriggersTrackL:
    """**批准 → Track L 自动跑**（业主裁定 J5："采到库内没有的法规标准，评审通过后自动入库"）。

    ⚠ 这条是本步补的**接线**：`track_l.reconcile()` 此前**没有任何生产调用方**
    （§10.24 写了它、§10.28 还在说"库级能力"），于是"自动入库"这句承诺实际上
    **是死的**——批准之后材料能被检索到，但**永远不会**进法条库。
    """

    def test_standard_material_is_imported_on_approval(self, client, project, track_l_docs):
        c, _ = client
        pid = project["project_id"]
        mid = _collect_text_material(c, pid, title="GB 88888-2088 某安全技术规范",
                                     text=_STD_TEXT)["material_id"]
        r = c.post(f"/api/v1/materials/{mid}/review", json={"status": "approved"}, headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        tl = data.get("track_l")
        assert isinstance(tl, dict), data
        assert tl["action"] in ("import", "link"), tl
        assert tl.get("imported") is True or tl.get("linked") is True, tl
        # 回指必须落库（`doc_id` 是材料侧的列，法条链零改动）
        assert data.get("doc_id"), data
        if tl.get("imported"):
            track_l_docs.append(str(data["doc_id"]))
        # 库内此刻真的有它（按比较键）
        from src.core.materials import track_l as tl_mod
        assert tl_mod.find_existing_doc("GB 88888-2088"), "入库后必须能按比较键查到"

    def test_plain_material_is_skipped_on_approval(self, client, project, db):
        c, _ = client
        pid = project["project_id"]
        before = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        mid = _collect_text_material(c, pid, title="一篇报道",
                                     text="据当地通报，住宿标准每晚不超过八百元，自下月起执行。")["material_id"]
        r = c.post(f"/api/v1/materials/{mid}/review", json={"status": "approved"}, headers=HDR)
        tl = r.json()["data"].get("track_l")
        assert isinstance(tl, dict) and tl["action"] == "skip", tl
        after = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        assert after == before, "不是标准的材料绝不许碰法条链"

    def test_rejection_does_not_run_track_l(self, client, project):
        """拒绝**不触发**：返回体里连 `track_l` 键都不该有（"没决策"与"决策=skip"是两回事）。"""
        c, _ = client
        pid = project["project_id"]
        mid = _collect_text_material(c, pid, title="GB 88888-2088 某安全技术规范",
                                     text=_STD_TEXT)["material_id"]
        r = c.post(f"/api/v1/materials/{mid}/review", json={"status": "rejected"}, headers=HDR)
        assert r.status_code == 200
        assert "track_l" not in r.json()["data"], r.json()["data"]

    def test_track_l_failure_is_reported_not_raised(self, client, project, monkeypatch):
        """Track L 抛错**不改写评审结果**，但必须在 `data.track_l` 里如实报出来。"""
        c, _ = client
        pid = project["project_id"]
        mid = _collect_text_material(c, pid, title="GB 88888-2088 某安全技术规范",
                                     text=_STD_TEXT)["material_id"]

        from src.core.materials import track_l as tl_mod

        def boom(_mid):
            raise RuntimeError("模拟入库炸了")

        monkeypatch.setattr(tl_mod, "reconcile", boom)
        r = c.post(f"/api/v1/materials/{mid}/review", json={"status": "approved"}, headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["review_status"] == "approved", data          # 评审结果保住了
        assert data["track_l"]["action"] == "error"
        assert "模拟入库炸了" in data["track_l"]["why"]


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
        "/api/v1/materials/{material_id}/review",
        # 重解析比对会**子进程解析**（秒级到分钟级），与 scan 同款 ⇒ 必须 `def`
        "/api/v1/materials/{material_id}/reverify",
        # ⚠ 锚点健康度这两条**也是**（2026-09-18 复核 b10 的 MEDIUM-2）：
        # §10.54 给它加了"源文件字节"那一轴 ⇒ 它会**流式 sha256 每份源文件**，
        # 几十份 PDF 就是一次真实磁盘读。作者当时只想着"比字符串很便宜"，
        # 把它留在 `async def` 里 ⇒ 整个引擎会被卡住（这正是本类存在的理由）。
        "/api/v1/materials/projects/{project_id}/locators",
        "/api/v1/materials/{material_id}/locators",
        # 报告这两条（2026-09-18 复核 b12 的 MEDIUM-2）：内容块组装会经
        # `research_report._attach_locator_status` → `locator.locator_health` **逐份流式 sha256
        # 材料源文件**（复核实测 3 份材料 = 3 次读盘），再叠加 openpyxl/pptx 落盘 ⇒ 与上面
        # locators 两条**同族**。教训写在这里：§10.59 那轮**只修了 2 条、没有审计调用方**，
        # 于是同一个洞在产出物这一侧又留了一个月。
        "/api/v1/report/research",
        "/api/v1/report/research/slides",
    ])
    def test_declared_sync(self, client, path):
        import asyncio
        c, _ = client
        routes = [r for r in c.app.routes if getattr(r, "path", None) == path]
        assert routes, f"路由不存在: {path}"
        assert not asyncio.iscoroutinefunction(routes[0].endpoint), (
            f"{path} 做同步重活，必须是 `def`（线程池），不能是 `async def`")

    def test_routes_report_module_has_no_async_endpoint(self, client):
        """**文件级**闸门：`routes_report.py` 注册的端点，**一个都不许是 `async def`**。

        为什么不接着加白名单条目：b12 的 MEDIUM-2 本身就是"漏了一条、没人发现"。这个文件里
        的每一件事——秒级 SQL 聚合、openpyxl/pptx 落盘、逐份 sha256 材料源文件——都是同步
        重活，所以往这里**新加端点时默认就该是 `def`**；逐条白名单挡不住新端点，文件级判据挡得住。

        ⚠ 反向断言（`seen >= 6`）**不可省**：路由一条都没扫到时"全绿"是**假绿**
        （b12 的 `e2e:materials` C2 就是这么空过的）。
        真要在这里放一个 `async def`（例如将来接了原生异步 I/O）：请在**本测试里**写清它为什么
        不阻塞事件循环，再把它挪进白名单——**不要默默删掉这条**。
        """
        import asyncio
        c, _ = client
        seen: list[str] = []
        bad: list[str] = []
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            if ep is None or getattr(ep, "__module__", None) != "src.core.api.routes_report":
                continue
            path = getattr(r, "path", "?")
            seen.append(path)
            if asyncio.iscoroutinefunction(ep):
                bad.append(path)
        assert len(seen) >= 6, (
            f"只扫到 {len(seen)} 条 routes_report 端点（{seen}）——判据可能空过，先确认路由注册")
        assert not bad, f"routes_report.py 里的端点做同步重活，必须全部是 `def`（线程池）：{bad}"


class TestEndpointIndexMatchesReality:
    """模块 docstring 的**端点索引**必须与真实注册的路由**逐条对齐**。

    为什么要有这条（复核 b10 的 G3）：§10.56 补全了那份索引（原先漏了 `tiers` 与三个新端点），
    但**零闸门**——把补上的 4 行删掉，测试套件**全绿**（42 passed）。
    而那个索引就是这一层的"地图"：下一轮接线/复核会照它找端点。

    ⚠ 占位名要**归一**：索引里写的是简写 `{pid}`/`{mid}`，代码里是 `{project_id}`/`{material_id}`
    ——它们指的是同一个位置参数，比较前统一成 `{}`（复核 b10 也是这么对齐的）。
    """

    def test_docstring_index_equals_registered_routes(self, client):
        import re

        from src.core.api import routes_materials

        c, _ = client
        doc = routes_materials.__doc__ or ""
        listed = set()
        for m in re.finditer(r"^\s*-\s+(GET|POST|DELETE|PUT|PATCH)\s+(/api/v1/materials\S*)",
                             doc, re.M):
            path = re.sub(r"\{[^}]*\}", "{}", m.group(2))
            listed.add((m.group(1).upper(), path))

        registered = set()
        for r in c.app.routes:
            path = getattr(r, "path", "") or ""
            if not path.startswith("/api/v1/materials"):
                continue
            for verb in (getattr(r, "methods", None) or set()):
                if verb in ("GET", "POST", "DELETE", "PUT", "PATCH"):
                    registered.add((verb, re.sub(r"\{[^}]*\}", "{}", path)))

        assert listed == registered, (
            "docstring 的端点索引与真实路由不一致：\n"
            f"  只在索引里: {sorted(listed - registered)}\n"
            f"  只在路由里: {sorted(registered - listed)}")


class TestLocatorEndpoints:
    """引用锚点稳定性的三个端点（方案 §12 未决第 5 条，§10.48）。"""

    def _ingest(self, client, project, tmp_path, body: str = "甲。乙。") -> dict:
        c, _ = client
        p = _txt(tmp_path / "doc.txt", body)
        r = c.post(f"/api/v1/materials/projects/{project['project_id']}/scan",
                   json={"origin": "user"}, headers=HDR)
        assert r.status_code == 200, r.text
        # scan 扫的是项目目录；这里直接把文件放进去再扫（与既有端到端用例同款）
        return {"scanned": r.json()["data"]["scanned"], "path": p}

    def test_project_summary_and_single_health(self, client, project, tmp_path):
        """⚠ **不抓网**：材料直接用 `collect_text` 造（离线也要能验端点形状）。

        第一版走了 HTTP `collect` 端点 ⇒ 离线时只能 `skip`，而"跳过的用例"等于
        **没有保证**（本仓的规矩：宁可换成确定的构造方式，也不要一条会跳的断言）。
        """
        c, _ = client
        pid = project["project_id"]
        from src.core.materials import collect as co
        m = co.collect_text(pid, title="报道", text="住宿标准八百元。",
                            url="https://a.example/1")
        mid = m["material_id"]

        h = c.get(f"/api/v1/materials/{mid}/locators", headers=HDR)
        assert h.status_code == 200, h.text
        data = h.json()["data"]
        assert data["status"] in ("ok", "stale", "unknown", "no_locators"), data
        # 网页材料刚入库 ⇒ 指纹一致 ⇒ ok（且措辞不许说成"保证一致"）
        assert data["status"] == "ok", data
        assert "未发现变化" in data["why"], data["why"]

        s = c.get(f"/api/v1/materials/projects/{pid}/locators", headers=HDR)
        assert s.status_code == 200, s.text
        body = s.json()["data"]
        assert body["project_id"] == pid and body["counts"]["ok"] == 1, body
        assert "重解析比对" in body["note"], body["note"]

    def test_old_material_shows_up_as_unknown_in_the_summary(self, client, project):
        """老材料（入库时没记指纹）在总览里算 **unknown** ——**不假装 ok**。"""
        c, _ = client
        pid = project["project_id"]
        from src.core.storage import material_repo as mr
        m = mr.add_material(pid, "老材料", origin="user")
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        s = c.get(f"/api/v1/materials/projects/{pid}/locators", headers=HDR)
        body = s.json()["data"]
        assert body["counts"]["unknown"] == 1, body
        assert any(a["material_id"] == m["material_id"] for a in body["attention"]), body
        h = c.get(f"/api/v1/materials/{m['material_id']}/locators", headers=HDR)
        assert h.json()["data"]["status"] == "unknown", h.json()

    def test_unknown_material_is_404(self, client, project):
        c, _ = client
        assert c.get("/api/v1/materials/mat_缺少/locators", headers=HDR).status_code == 404
        assert c.post("/api/v1/materials/mat_缺少/reverify", headers=HDR).status_code == 404

    def test_reverify_reports_unavailable_without_a_source_file(self, client, project):
        """**没有留存源文件** ⇒ `unavailable`（不是 match）——这条语义必须在端点上如实。"""
        c, _ = client
        from src.core.materials import collect as co
        m = co.collect_text(project["project_id"], title="网页件", text="住宿八百元。",
                            url="https://a.example/2")
        r = c.post(f"/api/v1/materials/{m['material_id']}/reverify", headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["status"] == "unavailable", data
        assert "不是 ok" in data["why"], data["why"]


