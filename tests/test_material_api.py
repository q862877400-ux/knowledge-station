# -*- coding: utf-8 -*-
"""材料平面 API 测试（Phase A 第四步）。

重点不在"每个端点都能 200"，而在**两条纪律在 HTTP 层同样成立**：
  1. 评审硬门不可绕过：未批准材料在 `/search` 里**搜不到**（硬门写在 SQL 里）；
  2. 校验在端点层是**严格**的（非法枚举 → 422，不是当成默认值放过去）。

另有一条"用户能不能真的用起来"的端到端：建项目 → 往目录丢文件 → scan → 读切片
（评审要能读到内容，否则是盲签）→ 批准 → 搜到。
"""
from __future__ import annotations

import importlib.util
import inspect
import textwrap
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
        """建项目 → 丢文件 → scan → 读切片 → 搜到；撤销则搜不到、再批又搜到。
        S3-b 对账（业主裁定 NOT-DOING #15）：人工上传**免评审** ⇒ scan 出生即 approved、
        直接可搜；安全面移到"撤销/拒绝后搜不到 + 再批恢复"（只紧不松）。
        原文留痕：本测原为「scan → 列表 pending → 搜不到 → 批准 → 搜到」。"""
        c, _ = client
        pid = project["project_id"]
        d = mr.materials_dir(pid)
        _txt(d / "业绩说明.txt", "公司营业收入为一百亿元，同比增长百分之十。")

        # 收件
        r = c.post(f"/api/v1/materials/projects/{pid}/scan", json={}, headers=HDR)
        assert r.status_code == 200, r.text
        assert r.json()["data"]["registered"] == 1
        mid = r.json()["data"]["rows"][0]["material_id"]

        # 列表里看得见；人工上传**出生即可作依据**（免评审，裁定 #15）
        rows = c.get(f"/api/v1/materials/projects/{pid}/materials", headers=HDR).json()["data"]
        assert [x["material_id"] for x in rows] == [mid]
        assert rows[0]["review_status"] == "approved", "人工上传免评审（出生即 approved）"
        assert rows[0]["tier_label"] == mr.TIER_LABELS["T1"]

        # 就位后先能读到内容（盲签防线照旧）
        ck = c.get(f"/api/v1/materials/{mid}/chunks", headers=HDR).json()["data"]
        assert ck["total"] >= 1 and "营业收入" in ck["chunks"][0]["text"]
        assert ck["chunks"][0]["char_start"] == 0

        # 出生即搜得到（免评审）
        hits = c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["hits"]
        assert len(hits) == 1

        # 撤销（判为不可用）⇒ 硬门**照样关得上**（安全面只紧不松）
        rv = c.post(f"/api/v1/materials/{mid}/review",
                    json={"status": "rejected", "note": "核对后发现不可用"}, headers=HDR)
        assert rv.status_code == 200 and rv.json()["data"]["review_status"] == "rejected"
        assert c.get(f"/api/v1/materials/projects/{pid}/search?q=营业收入",
                     headers=HDR).json()["data"]["count"] == 0

        # 再批 ⇒ 搜得到，且引用字段齐备
        rv = c.post(f"/api/v1/materials/{mid}/review",
                    json={"status": "approved", "note": "核对过"}, headers=HDR)
        assert rv.status_code == 200 and rv.json()["data"]["review_status"] == "approved"

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

    @pytest.mark.parametrize("path,method", [
        ("/api/v1/materials/projects/{project_id}/scan", "POST"),
        ("/api/v1/materials/projects/{project_id}/collect", "POST"),
        ("/api/v1/materials/{material_id}/review", "POST"),
        # 重解析比对会**子进程解析**（秒级到分钟级），与 scan 同款 ⇒ 必须 `def`
        ("/api/v1/materials/{material_id}/reverify", "POST"),
        # ⚠ 锚点健康度这两条**也是**（2026-09-18 复核 b10 的 MEDIUM-2）：
        # §10.54 给它加了"源文件字节"那一轴 ⇒ 它会**流式 sha256 每份源文件**，
        # 几十份 PDF 就是一次真实磁盘读。作者当时只想着"比字符串很便宜"，
        # 把它留在 `async def` 里 ⇒ 整个引擎会被卡住（这正是本类存在的理由）。
        ("/api/v1/materials/projects/{project_id}/locators", "GET"),
        ("/api/v1/materials/{material_id}/locators", "GET"),
        # 报告这两条（2026-09-18 复核 b12 的 MEDIUM-2）：内容块组装会经
        # `research_report._attach_locator_status` → `locator.locator_health` **逐份流式 sha256
        # 材料源文件**（复核实测 3 份材料 = 3 次读盘），再叠加 md/html 落盘 ⇒ 与上面
        # locators 两条**同族**。教训写在这里：§10.59 那轮**只修了 2 条、没有审计调用方**，
        # 于是同一个洞在产出物这一侧又留了一个月。
        # ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原来的
        # `("/api/v1/report/research/slides", "POST")`（PPT，要落 pptx）已随 Word/PPT
        # 交付物撤销一并删除。
        ("/api/v1/report/research", "POST"),
        # 健康看板（§10.74）：七条 `COUNT(*)` + `mineru_available()` 的 import 探测——都是
        # **同步 I/O**，留在事件循环里就会占住循环。⚠ 收益**不大**（本机实测总耗时 0.017s、
        # `import mineru` 0.000s、30 万行 COUNT ≈1.1ms），这里守的是**一般纪律**，不是"很慢"。
        ("/api/v1/diagnostics/health-board", "GET"),
        # PDF 渲染/读盘族（§10.75）：这四条都在事件循环里做 PyMuPDF 的重活
        # （逐页 `get_text("dict")` 找题注、`get_pixmap` 截图、`middle.json` 读回、`glob` 资产）。
        # 实测（150 页密排 PDF，题注在末页）：`/figure/1` 请求 0.2324s、事件循环空档 **0.232s**
        # ⇒ 改 `def` 后空档 **0.036s**（回到噪声底）。真机文档更重（真扫描件 + `try_redraw` 的 OCR
        # 路径），所以那个数字是**下界**。
        ("/api/v1/documents/{doc_id}/figure/{fig_no}", "GET"),
        ("/api/v1/documents/{doc_id}/formula/{fno}", "GET"),
        ("/api/v1/documents/{doc_id}/table-image/{page_no}/{tbl_idx}", "GET"),
        ("/api/v1/documents/{doc_id}/tree", "GET"),
        ("/api/v1/documents/{doc_id}/assets/{fname}", "GET"),
        # ⚠ **`/api/v1/documents/{doc_id}/file` 故意不在表里**：它只做查询 + 返回 `FileResponse`，
        # 字节由 Starlette 用 anyio 流式读出 ⇒ 本来就不占事件循环。审计把它列进候选是因为
        # 调用链上有 `fs-copy` **轻标记**——**读代码 + 量过之后判定"不用改"**。
        # 候选清单不是待办清单：留下的每一条都要写清为什么。
        #
        # 落盘/导出族（§10.76）：xlsx / JSON 都是**同步落盘**（openpyxl、写文件），
        # 快照恢复还要读包 + sha256。⚠ **本族基本没测出大收益**——唯一能铺满量的是
        # `/egress/audit/export`（`debug_dump` 有保留上限 1000 行），实测请求 0.0305s、空档
        # 0.030s → 改后 0.016s（已在噪声底）。其余几条要有生产规模的更新批次 /
        # 2.2GB 库快照才有意义，量具跑临时空库只会给出**假小**的数字 ⇒ 那几条按**结构性**判据
        # 进表（同族的 office/render + sha256 已在 §10.71/§10.73/§10.74 实测过）。
        # ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：本族原有的三条 **Word** 端点
        # （`/export/obligations/{list_id}`、`/export/review/{task_id}`、以及
        # `/export/citations` 里的 docx 落盘）随"撤销 Word/PPT 交付物"一并拆除 ⇒
        # 前两条**整条路由消失**、在此表里删除；`/export/citations` 仍在（还有取证据的同步活）。
        # 这条原是 `async def` 只为 `await request.json()`，且随后就有同步活（与 §10.71 的
        # `/report/effect/export` 同款）⇒ body 改走签名，非法 JSON 由"吞成空 body"变成 422。
        ("/api/v1/export/citations", "POST"),
        ("/api/v1/egress/audit/export", "GET"),
        ("/api/v1/snapshots/{snapshot_id}/restore", "POST"),
        ("/api/v1/update/report-xlsx/{batch_id}", "POST"),
        # ---- T2 批次（§10.79）：这 20 条的 `async def` **只为了 `await request.json()`**，
        # 读完 body 之后全是同步重活（LLM 调用 / 抽别名 / 快照落盘 / 网络探测…）。
        # 判据形状与 §10.71/§10.76 同款：body 走签名，坏 body 由 FastAPI 直接 422。
        ("/api/v1/clauses/patches", "POST"),
        ("/api/v1/compliance/gap-analysis", "POST"),
        ("/api/v1/aliases/extract", "POST"),
        ("/api/v1/ks/answer", "POST"),
        ("/api/v1/documents/{old_doc_id}/migrate-patches", "POST"),
        ("/api/v1/clauses/{clause_revision_id}/office-edit", "POST"),
        ("/api/v1/clauses/office-edit/commit", "POST"),
        ("/api/v1/vision/locate", "POST"),
        ("/api/v1/snapshots", "POST"),
        ("/api/v1/update/announce-sources", "GET"),
        ("/api/v1/update/announce-sources", "POST"),
        ("/api/v1/update/announce-sources/{source_id}", "PUT"),
        ("/api/v1/update/announce-sources/{source_id}", "DELETE"),
        ("/api/v1/discover/classify", "POST"),
        ("/api/v1/ingest/bulk", "POST"),
        ("/api/v1/ingest/bulk/{batch_id}/resume", "POST"),
        ("/api/v1/data/package/export", "POST"),
        ("/api/v1/data/package/import", "POST"),
        ("/api/v1/settings/api-config", "GET"),
        ("/api/v1/settings/api-config", "PUT"),
        ("/api/v1/settings/api-config/test", "POST"),
        # ---- T1+重里**非 bulk-db** 的最后两条（§10.79 收尾）：一条要读 Office 会话文件 + 比哈希，
        # 一条要 openpyxl 落盘。剩下 13 条 T1+重**只有 bulk-db**（单行写事务、毫秒级），
        # 按 §10.78 的取舍**故意不转**——闸门不是"什么都往里塞"的筐。
        ("/api/v1/clauses/office-edit/poll", "GET"),
        ("/api/v1/update/announce-export", "POST"),
        # 这条**不是** bulk-db：`clause_repo.delete_patch` 在补丁改的是 `content_text` 时会
        # `_reindex_clause_indexes`（重算 FTS + **重算向量**）⇒ 要加载嵌入模型并推理。
        ("/api/v1/clauses/patches/{patch_id}", "DELETE"),
        # SSE（§10.80）：外层 `def` + **同步生成器**。原先外层只 `await request.json()`、
        # 内层 `async def event_stream()` 里没有一个 `await` ⇒ 一次逐点 LLM 评审把引擎冻住。
        # 它现在同时在**通则之一**（只读 body 的 async）与**通则之二**（无 await 的异步生成器）的
        # 判据之外——**两条通则都不再需要白名单**。
        # ⚠ 删单留痕（NOT-DOING #16，2026-09-22）：该 SSE 路由 `/compliance/review/{task_id}/execute`
        # 已随合同审查删除；白名单恒空的状态由上面两条通则的判据自己守着。
        # ---- §10.93：`/laws/*` 那 5 条（网络 / 长跑）从 `async def + asyncio.to_thread` 改回 `def`。
        # 它们原先**自称**"已经让出事件循环"，但 `asyncio.to_thread` 走的是 asyncio 默认执行器
        # （`min(32, cpu+4)` 个 worker）——**不是**被 `THREADPOOL_TOKENS = 16` 收窄的那口池，
        # 也**不吃**重活闸门的令牌 ⇒ 2026-09-18 建的两道界在这一族上等于不存在。
        # 改回 `def` 后回到有界池子，并**同时**进了重活前缀表（见 `HEAVY_PREFIXES`）。
        # ⚠ 代价（与 §10.86 那 51 条同款）：非法 JSON / 空 body 由 FastAPI 直接 422，
        # 不再是各端点自己的 `bad_json` 分支（仓内无消费者；`plugin` 里那个 `bad_json` 是
        # **主机侧**自己的 body 闸，与引擎无关）。
        ("/api/v1/laws/search", "POST"),
        ("/api/v1/laws/ingest", "POST"),
        ("/api/v1/laws/check-updates", "POST"),
        ("/api/v1/laws/catalog/refresh", "POST"),
        ("/api/v1/laws/verify", "GET"),
        # ---- §10.96 结论草稿：一次**同步** LLM 调用（秒级到分钟级）⇒ 必须 `def`。
        # 它同时吃重活令牌（`/api/v1/report/` 已在 `HEAVY_PREFIXES` 里）。
        ("/api/v1/report/research/draft", "POST"),
    ])
    def test_declared_sync(self, client, path, method):
        """这条路径上**这个 HTTP 方法**的端点必须是 `def`（线程池），不能是 `async def`。

        ⚠ **必须精确到方法**（独立复核 b14 的 LOW-2）：表原先只写路径、断言只看
        `routes[0].endpoint` —— 同一条路径挂多个方法时（`/settings/api-config` 有 GET+PUT、
        `/update/announce-sources` 有 GET+POST、`/clauses/patches` 有 GET+POST、
        `/snapshots` 有 GET+POST），只有**第一个** Route 对象被断言，同路径的**兄弟方法**
        可以悄悄改回 `async def` 而表仍然 GREEN。§10.79 那 2 条兄弟方法（GET 读凭据文件 /
        GET 读配置）当时正是这样"转换了但没被表验到"——25 条转换只对应 23 行参数，就是它们。

        现在参数是 `(路径, 方法)`：**表也不再声称**同路径的其它方法是 `def`。
        ⚠ **§10.86 起**：那两条曾"廉价而故意留 async"的兄弟（`GET /clauses/patches`、
        `GET /snapshots`）已经**一并转成 `def`** —— 因为通则之一改成了"零有效 await ⇒ 必须
        `def`"，不再看轻/重标记（b15 实测标记表会漏）。所以现在**整条 API 面上没有一条
        `async def` 是"零有效 await"的**；这张表仍然只声称它自己列出的 `(路径, 方法)`。
        """
        import asyncio
        c, _ = client
        routes = [r for r in c.app.routes
                  if getattr(r, "path", None) == path
                  and method in (getattr(r, "methods", None) or ())]
        assert routes, f"路由不存在: {method} {path}"
        assert len(routes) == 1, f"{method} {path} 匹配到 {len(routes)} 个 Route（表不再唯一）"
        assert not asyncio.iscoroutinefunction(routes[0].endpoint), (
            f"{method} {path} 做同步重活，必须是 `def`（线程池），不能是 `async def`")

    #: T1（零 `await`-like）必须 `def`；**白名单为空**。
    #: 真要留一个"零 await 的 async 端点"，必须在这里写清"它为什么不会占住事件循环"。
    _T1_ASYNC_ALLOWLIST: set[str] = set()

    #: **async 端点的显式名单**（§10.87，修 b16 的 D4）：`{路径: 为什么它必须是 async}`。
    #:
    #: 为什么从"静态判据"退回到"显式声明"：b16 构造出两条**静态判据不可能判准**的形状——
    #: ① 唯一的 `await` 是 `await _read_json(request)`（助手内部才读 body）；
    #: ② 外层只读 body，嵌套 `async def` 里有真 await 但**从不被迭代**。
    #: 两者实测都堵事件循环 **0.650s**，而"源码里存在非读-body 的 await"这条判据把它们放行。
    #: 根因是**"执行路径上有没有 await"在静态上不可判**（要正确的过程间分析 + 可达性）。
    #: ⇒ 与其继续打补丁，不如把**举证责任反过来**：**async 是例外，必须在名单里写明理由**。
    #: 新出现的 async 端点（不管它长成 H1/H3 还是别的形状）**默认红**。
    #: 名单里的每一条还要满足第二条：**真的有一个非读-body 的 await**（`never_yields` 为 False），
    #: 否则它连"为什么必须是 async"都答不上来。
    _ASYNC_ENDPOINTS: dict[str, str] = {
        "/api/v1/chat/completions":
            "SSE 流式：嵌套 `async def event_stream()` 里有 `await anyio.to_thread.run_sync(...)`"
            "（逐块从线程池取 LLM 输出），迭代期间**真的**让出事件循环",
        # ⚠ §10.93 之后名单只剩这一条：原先把 5 条 `/laws/*` 也写在这里（理由都是
        # "走 `await asyncio.to_thread(...)`"）——那个形状**看着**让出了事件循环，其实换到了
        # **asyncio 默认执行器**那口**无界**的池（`min(32, cpu+4)`），既不受
        # `THREADPOOL_TOKENS = 16` 约束、也不吃重活闸门的令牌 ⇒ 它们已改回 `def`。
        # 名单腐烂由下面那条用例的第二个环节强制（写在名单里但已不是 async ⇒ 红）。
    }

    def test_async端点必须在显式名单里(self, client):
        """**通则（§10.87）**：`/api/` 路由上的每条 `async def` 端点都必须在 `_ASYNC_ENDPOINTS`
        里**写明理由**。

        ⚠ 范围是 `/api/` 前缀下的路由（独立复核 b17 的 INFO：框架自带的 4 条 async 路由不在扫描
        范围内，所以"整条 API 面上每条 async 端点"这种字面说法不成立——本用例的判据就是 `/api/`）。

        来历：§10.86 想用一条静态判据（"零有效 await ⇒ 必须 `def`"）把这一整类消灭掉，
        但独立复核 b16 构造出两条**静态不可判**的逃逸形状（助手包装的 await、从不迭代的嵌套
        async 生成器），各自实测仍能冻结事件循环 **0.650s**——**"执行路径上有没有 await"在静态上
        本来就不可判**。所以这里换一种更强的形状：**async 是例外，必须显式声明 + 写理由**；
        任何新 async 端点（无论什么形状）默认红。

        名单里的每一条还要过第二关：**必须真的有一个非读-body 的 `await`**（或 `async for` 之类的
        真挂起点）——判据是 `audit.effective_real_await()`（§10.88）。
        ⚠ **它不是 `never_yields` 的"加严版"——两个方向都有**（独立复核 b19 的 N1：这句话原写作
        "比 `never_yields` 严一档"，**不处处成立**）：它在 H1（嵌套助手包装读 body）上更**严**，
        但在 `async for`/H5 上更**宽**。判据细节见 `effective_real_await()` 的 docstring。
        """
        import asyncio

        c, _ = client
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe_allow", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        offenders: list[tuple[str, str]] = []
        examined = 0
        seen: set[str] = set()
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            path = getattr(r, "path", None)
            if ep is None or path is None or not path.startswith("/api/"):
                continue
            examined += 1
            if not asyncio.iscoroutinefunction(ep):
                continue
            seen.add(path)
            reason = self._ASYNC_ENDPOINTS.get(path)
            if reason is None:
                offenders.append((path, "**不在名单里**（async 是例外，必须写明理由）"))
                continue
            if not reason.strip():
                offenders.append((path, "名单里的理由**是空的**（等于没写）"))
                continue
            try:
                src = inspect.getsource(ep)
            except (OSError, TypeError):        # pragma: no cover
                continue
            # ⚠ **第二关的判据是 `effective_real_await`**（§10.88，修 b17 的 MEDIUM-2 + MEDIUM-3）：
            # 旧版用 `never_yields`，它对"只有 `async for`/`async with`"的**合法**形状返回 True
            # ⇒ 那种端点在名单里**永远无法自证**（误红、名单不可满足，b17 的 E3 REFUTED）。
            # 新版判据：① `async for/with/yield` 算挂起点；② 读 body 的 await 不算；
            # ③ **调用本端点内嵌套 async 助手**要内联进去再看（b16 的 H1 形状靠这一层判准）；
            # ④ 被引用的嵌套 async 生成器（真流式）算。
            if not audit.effective_real_await(src):
                offenders.append((path, "名单说它必须 async，但它的 await 全是读 body"
                                       "（或只调用了同样只读 body 的嵌套助手）——那是 `def` 的活。"
                                       "**若它是流式端点**（`return StreamingResponse(async_gen())`）："
                                       "`def` 一样能真流式（见 test_def端点返回StreamingResponse"
                                       "仍然真流式），所以改 `def` 是无害的补救"))
        # 名单本身也要与现状一致：写在名单里、但已经不是 async 的 ⇒ 也要红（防止名单腐烂）
        for path in self._ASYNC_ENDPOINTS:
            if path not in seen:
                offenders.append((path, "名单里有它，但它**已经不是 async 端点**（名单腐烂）"))
        assert examined >= 140, f"只枚举到 {examined} 条 API 路由（实测 147）——枚举可能坏了"
        assert not offenders, (
            "async 端点的名单对不上：\n"
            + "\n".join(f"  {p}  {why}" for p, why in offenders)
            + "\n（要新增 async 端点：加进 _ASYNC_ENDPOINTS 并写清它**为什么必须**让出控制权）")

    @staticmethod
    def _unbounded_pool_calls(src: str) -> list[str]:
        """在一段端点源码里找出"把同步活丢进**无界**池"的写法（§10.93）。

        **为什么这两条禁**：`asyncio.to_thread(...)` 与 `loop.run_in_executor(...)` 用的是
        **asyncio 的默认执行器**（`min(32, cpu+4)` 个 worker），它
        **不是**被 `THREADPOOL_TOKENS = 16` 收窄的那口 anyio 池，也**不吃**重活闸门的令牌
        ⇒ 2026-09-18 建的两道界对这种写法**等于不存在**。而且它比 `def` **更坏**：
        `def` 端点进入有界池（最坏 16 条），这种写法最坏 32 条。

        **允许的替代**：① 端点写成 `def`（Starlette 丢进那口有界的池，首选）；
        ② `await anyio.to_thread.run_sync(...)`（同一口池；真流式端点里用它，
        见 `/chat/completions`）。

        判据是 **AST**（不是文本扫描）：注释/docstring 里提到这些名字**不算**
        （§10.78 那个假阳性就是注释被当行为）。
        ⚠ **必须先 `dedent`**：`inspect.getsource()` 对**闭包内**定义的端点（`create_app()`/
        `register()` 里那些）给的是**带缩进**的源码，直接 `ast.parse` 会
        `IndentationError`（本节第一版就这么炸的；`scripts/audit-async-endpoints.py`
        第 187 行早就记了这个坑）。
        """
        import ast as _ast
        import textwrap

        found: list[str] = []
        for node in _ast.walk(_ast.parse(textwrap.dedent(src))):
            if not isinstance(node, _ast.Call):
                continue
            f = node.func
            if not isinstance(f, _ast.Attribute):
                continue
            if f.attr == "run_in_executor":
                found.append("run_in_executor")
            elif (f.attr == "to_thread" and isinstance(f.value, _ast.Name)
                    and f.value.id == "asyncio"):
                found.append("asyncio.to_thread")
        return found

    def test_端点上不许用_asyncio_to_thread(self, client):
        """**通则之三（§10.93）**：`/api/` 端点不许用 `asyncio.to_thread` / `run_in_executor`
        ——那两口池收窄不到、也不进重活闸门。

        来历：`/laws/*` 那 5 条原先写成 `async def` + `await asyncio.to_thread(...)`，
        理由写的是"走 to_thread（§10.79 特意留下的范本形状）"。**那个理由本身是错的**：
        `asyncio.to_thread` 根本不是 §10.81 收窄的那口 anyio 池（两处都记着这条，但没人把它
        变成判据）。本步把那 5 条改回 `def`，并把"不许再这么写"钉成用例——`_ASYNC_ENDPOINTS`
        名单里"理由看起来成立"不再够，**理由本身也要能过判据**。

        ⚠ 判据是**源码级**的：它能挡住"在端点里直接这么写"，挡不住"封装在一个被调用的助手模块里"
        （那要看整个调用图）。**扫不到 ≠ 没有**——所以本用例的 `offenders` 文案点名要求
        "要么写成 `def`、要么 `anyio.to_thread.run_sync`"，而不是只说"别用"。
        """
        import asyncio
        import ast as _ast

        # ---- 先证明判据不空转（合成正/负样本，含"注释里提到"的假阳性形状）----
        assert self._unbounded_pool_calls(
            "import asyncio\nasync def ep():\n    return await asyncio.to_thread(f)\n") == \
            ["asyncio.to_thread"]
        assert self._unbounded_pool_calls(
            "def ep(loop):\n    return loop.run_in_executor(None, f)\n") == ["run_in_executor"]
        assert self._unbounded_pool_calls(
            "async def ep():\n    return await anyio.to_thread.run_sync(f)\n") == []   # 允许
        assert self._unbounded_pool_calls(
            "def ep():\n    return f()\n") == []                                     # 本就 `def`
        assert self._unbounded_pool_calls(
            'def ep():\n    """这里提到 asyncio.to_thread() 只是说明，不是行为。"""\n'
            "    # asyncio.to_thread(f)\n    return 1\n") == []                       # 注释/docstring 不算
        assert self._unbounded_pool_calls("async def ep():\n    await f()\n") == []
        # ⚠ **带缩进的源码**（`inspect.getsource()` 对闭包内端点的真实形状）必须也能解析
        assert self._unbounded_pool_calls(
            '    @app.post("/x")\n    async def ep():\n'
            "        return await asyncio.to_thread(f)\n") == ["asyncio.to_thread"]
        # 判据自己要能解析真实源码（否则合成样本过了、真扫描却静默空转）
        assert _ast.parse("async def ep():\n    await asyncio.to_thread(f)\n")

        c, _ = client
        offenders: list[tuple[str, str]] = []
        examined = 0
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            path = getattr(r, "path", None)
            if ep is None or path is None or not path.startswith("/api/"):
                continue
            examined += 1
            try:
                src = inspect.getsource(ep)
            except (OSError, TypeError):        # pragma: no cover
                continue
            hits = self._unbounded_pool_calls(src)
            if hits:
                offenders.append((path, f"用了 {hits}（无界池 + 不过重活闸门）"))
        assert examined >= 140, f"只枚举到 {examined} 条 API 路由（实测 147）——枚举可能坏了"
        assert not offenders, (
            "这些端点把同步活丢进了**无界**池（`asyncio.to_thread` / `run_in_executor`）：\n"
            + "\n".join(f"  {p}  {why}" for p, why in offenders)
            + "\n（补救二选一：① 端点改成 `def`——Starlette 会把它丢进 anyio 那口"
              "被 THREADPOOL_TOKENS=16 收窄的池，首选；② 确实必须是 async 就写 "
              "`await anyio.to_thread.run_sync(...)`，同一口池。）")

    #: **名单第二层（§10.94）**：名单里的 async 端点**要么被量过、要么写明为什么量不了**。
    #:
    #: 为什么要有这一层：通则一/二/三都是**静态**判据（"有没有真 await"、"在不在名单里"、
    #: "用不用无界池"），它们能拦住"形状不对"，但拦不住"**形状对、实际仍然堵住事件循环**"。
    #: b17/b18/b21 三轮都对这条提过同一句：把仓里那把量具（`scripts/measure-endpoint-blocking.py`，
    #: 心跳协程 + `ASGITransport`）接到名单上当第二层。
    #: ⚠ 诚实前提：名单里**量不出来的**端点必须写进 `_NOT_MEASURABLE_ASYNC` 并说明理由——
    #: 否则"量具接名单"会退化成"点名一条、其余默认放过"，比不做更坏（假覆盖）。
    #: 现在名单只剩 1 条，而且它**量得出来**（下面那条用例真的量）。
    _MEASURED_ASYNC: dict[str, str] = {
        "/api/v1/chat/completions":
            "假 LLM 流每块在**线程**里阻塞 0.3s ×3 + 假 fastembed 加载阻塞 1.0s（两个都 monkeypatch）"
            "⇒ 端点耗时 ≥1.9s，而事件循环最大空档 <0.5s（**加载与分块活都不在循环里**）。"
            "两个反事实都验过（字节级变异 + 复原）：① 把 server.py 里 "
            "`part = await anyio.to_thread.run_sync(_next_chunk)` 改成直接 "
            "`part = _next_chunk()` ⇒ 空档 **0.6011s**；"
            "② 删掉端点开头的 `await anyio.to_thread.run_sync(warm_retrieval_stack)` ⇒ "
            "空档 **1.3382s**（都 ≥0.5s 阈值 ⇒ 用例红在预期断言上）",
    }
    _NOT_MEASURABLE_ASYNC: dict[str, str] = {}   # 目前为空：名单里唯一那条是量得出来的

    def test_名单里的_async_端点要么量过要么写明不可量(self, client, monkeypatch):
        """**量具接名单（第二层，§10.94）**：名单里的每条 async 端点，要么被**量**过，
        要么在 `_NOT_MEASURABLE_ASYNC` 里写明**为什么量不了**（不许静默放过）。

        判据（分两段）：
          1. **口径**：`_MEASURED_ASYNC` 与 `_NOT_MEASURABLE_ASYNC` 必须**恰好覆盖**名单、
             两两不交、理由非空（名单新增一条时这条会红 ⇒ 逼作者做决定）；
          2. **真的量**（`scripts/measure-endpoint-blocking.py` 的心跳 + `ASGITransport`）：
             两个"工作"都放在**线程/缝**后面——
             · 假 LLM 流每块阻塞 0.3s ×3（`stream_chat_completion` 被 monkeypatch）；
             · 假 fastembed `__init__` 阻塞 1.0s（`embedder._import_text_embedding` 这个
               **文档里写明的唯一缝**，不联网、不真装模型）。
             于是要求：端点耗时 ≥ 1.0 + 0.9×0.8（**活真的干了**——否则"空档小"毫无意义）；
             事件循环最大空档 **< 0.5s**（≈ 假加载单笔耗时的一半）。

        ⚠ 这条用例**同时**钉住 §10.94 修的那个缺陷：`/chat/completions` 冷启动时
        fastembed 加载 + jieba 词典都在 `async def` 端点体里 ⇒ 实测把事件循环占了 **6.79s**
        （`var/tmp/probe-chat-blocking.py`：第一次 6.79s / 第二次 0.020s，同进程）。
        现在端点开头有一次 `await anyio.to_thread.run_sync(warm_retrieval_stack)`；
        **把它删掉，这条用例就会红在 0.5s 那个阈值上**。

        ⚠ 为什么这条**允许**用计时：它量的就是"时间"。这里两个慢点都是**自己塞进去的定值**
        （0.3s / 1.0s，不是"机器有多快"），阈值取单笔的 1/2 ⇒ 机器再卡也不会把 20ms 抖成 500ms
        （仓里 `tests/test_measure_harness.py` 的尺子闸门用同款余量）。
        真出现偶发红：**先把这两个常数调大**，不要放松断言。
        """
        import asyncio
        import time as _time

        c, _ = client
        # ---- 1. 口径：覆盖、互斥、理由非空 ----
        measured, unmeasurable = set(self._MEASURED_ASYNC), set(self._NOT_MEASURABLE_ASYNC)
        assert not (measured & unmeasurable), f"同一条既量过又不可量：{measured & unmeasurable}"
        assert measured | unmeasurable == set(self._ASYNC_ENDPOINTS), (
            "名单第二层的口径对不上：\n"
            f"  名单        {sorted(self._ASYNC_ENDPOINTS)}\n"
            f"  已量        {sorted(measured)}\n"
            f"  声明不可量  {sorted(unmeasurable)}\n"
            "（新增 async 端点时必须二选一：真的量一次，或写明为什么量不了）")
        for path, why in {**self._MEASURED_ASYNC, **self._NOT_MEASURABLE_ASYNC}.items():
            assert why.strip(), f"{path} 的理由是空的（等于没写）"

        # ---- 2a. 把"冷启动"造出来（不联网）：假 fastembed 的加载要 1.0s ----
        from src.core.api import server
        from src.core.config import get_settings
        from src.core.retrieval import embedder

        CHUNK_S, N_CHUNKS, MODEL_LOAD_S = 0.3, 3, 1.0

        class _SlowTextEmbedding:
            """替身 fastembed：**加载要 1.0s**、向量维度按真模型的 512。"""

            def __init__(self, *a, **k):
                _time.sleep(MODEL_LOAD_S)

            def embed(self, texts):
                for _ in texts:
                    yield [0.0] * 512

        monkeypatch.setattr(embedder, "_model", None)       # 模拟"本进程还没加载过"
        monkeypatch.setattr(embedder, "_load_error", None)
        monkeypatch.setattr(embedder, "_error_at", 0.0)
        monkeypatch.setattr(embedder, "_import_text_embedding", lambda: _SlowTextEmbedding)

        # ---- 2b. 假 LLM 流：每块在线程里阻塞 0.3s（生产里这段也发生在**线程**里）----
        def fake_stream(query, evidences, history=None, max_tokens=1024,
                        temperature=0.1, allow_clarify=True):
            for i in range(N_CHUNKS):
                _time.sleep(CHUNK_S)
                yield f"第{i + 1}块：监护人不应擅自离开作业现场 [引用:GB-4.10]。"

        monkeypatch.setattr(
            "src.core.llm.deepseek_client.stream_chat_completion", fake_stream)
        monkeypatch.setattr(get_settings(), "llm_api_key", "sk-test")

        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_measure_harness_for_allowlist",
            root / "scripts" / "measure-endpoint-blocking.py")
        assert spec and spec.loader
        harness = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(harness)

        # ⚠ 用**新建**的 app（不在别的循环里跑过）+ 独立事件循环：量的是"这条端点在循环里的行为"
        app = server.create_app("test-token-123")
        out = asyncio.run(harness.measure(
            app, "POST", "/api/v1/chat/completions",
            body={"query": "动火作业监护", "top_k": 1}, headers=HDR))
        assert out["status"] == 200, out
        # ① 活真的干了（否则"空档小"毫无意义）
        assert out["duration_s"] >= MODEL_LOAD_S + CHUNK_S * N_CHUNKS * 0.8, (
            f"端点耗时只有 {out['duration_s']}s，而假加载 {MODEL_LOAD_S}s + 假 LLM 3×{CHUNK_S}s "
            "的活都得跑完 ⇒ 这次测量证明不了任何事（多半替身没被 patch 上）")
        # ⚠ `body_head` 只有前 120 字符（`measure()` 的封顶）⇒ 只能核**首事件形状**，
        # 不能指望它里面出现 `delta`（那是后面的事件）。
        assert out["body_head"].startswith("event: evidence"), out["body_head"]
        # ② 循环没被占住（模型加载与逐块活都不在循环里）
        assert out["samples"] >= 5, out
        assert out["max_gap_s"] < max(MODEL_LOAD_S, CHUNK_S) / 2, (
            f"名单里的 async 端点把事件循环占了 {out['max_gap_s']}s"
            f"（单笔假加载才 {MODEL_LOAD_S}s、单块 {CHUNK_S}s）——它有活**在循环里**跑：{out}")

    def test_T1_零await的async端点必须是def(self, client):
        """**通则之一（§10.86，修复核 b15 的 MEDIUM-1）**：`async def` 且源码里**没有任何
        会让出控制权的语法**（`await` / `async for` / `async with`）⇒ 必须 `def`。

        为什么把判据从"看标记"换成"看有没有 await"：标记表是**启发式**，而它已经漏过四次
        （b12 的 MEDIUM-2、§10.71、§10.79，以及 b15 这次的 MEDIUM-1）。b15 实测的两条**一条
        重标记都命不中**却真会堵库：
          · `DELETE /api/v1/materials/{material_id}` → `write_transaction()`（`BEGIN IMMEDIATE`
            + 3×`DELETE`，裸 `DELETE FROM` 不在任何标记正则里）：持锁 0.6s 时**事件循环空档
            0.647–0.657s**（连 404 都堵）；
          · `GET /api/v1/laws/catalog` → `ensure_catalog_schema()`（`CREATE TABLE/INDEX`，同样
            命不中）：首次请求空档 **0.697s**。
        而"**零 await**"是"必然占住事件循环"的**充分条件**，不依赖任何标记表 ⇒ 盲区消失。
        代价只是把毫秒级的活挪进线程池（P5 性能最低优先），收益是"引擎静默死几十秒"这一整类
        缺陷不再可能出现。

        ⚠ `async for` / `async with` **必须**算"会让出控制权"：它们编译成 `await __anext__` /
        `__aenter__`，但 AST 里**没有 `Await` 节点**——只数 `Await` 会误判成该改 `def`
        （而那种代码改成 `def` 根本不成立）。判据由 `audit.awaits_like()` 提供（b15 的 INFO-1）。
        ⚠ 源码解析失败时 `awaits_like()` 返回 `None` ⇒ **判红**（fail-closed），不放行。
        """
        import asyncio

        c, _ = client
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe_t1", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        offenders = []
        examined = 0
        async_seen: set[str] = set()
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            path = getattr(r, "path", None)
            if ep is None or path is None or not path.startswith("/api/"):
                continue
            examined += 1
            if not asyncio.iscoroutinefunction(ep):
                continue
            async_seen.add(path)
            try:
                src = inspect.getsource(ep)
            except (OSError, TypeError):        # pragma: no cover
                continue
            n = audit.awaits_like(src)
            if n is None:
                offenders.append((path, ["源码解析失败——判据无法生效（fail-closed）"]))
            elif n == 0 and path not in self._T1_ASYNC_ALLOWLIST:
                offenders.append((path, ["零 await-like（T1）"]))
        # ⚠ **反向断言**（防假绿）：枚举坏掉时"全绿"毫无意义。判据从"只看 async"扩到"看全部
        # API 路由"，因为 T1 清零后 async 只剩个位数。§10.93 又降到 **1 条**（`/laws/*` 那 5 条
        # 也改回 `def`）⇒ 条数哨兵彻底失效，改成**与 `_ASYNC_ENDPOINTS` 集合相等**
        # （识别/枚举任一坏掉都会红；不再随端点增减而失效，也不再需要维护魔数）。
        assert examined >= 140, f"只枚举到 {examined} 条 API 路由（实测 147）——枚举/筛选可能坏了"
        assert async_seen == set(self._ASYNC_ENDPOINTS), (
            "扫到的 async 端点集合与 `_ASYNC_ENDPOINTS` 不一致：\n"
            f"  扫到  {sorted(async_seen)}\n"
            f"  名单  {sorted(self._ASYNC_ENDPOINTS)}")
        assert not offenders, (
            "这些 `async def` 端点**从不真正让出控制权**（零 await/async for/async with），"
            "应改 `def`（Starlette 才会丢进线程池）：\n"
            + "\n".join(f"  {p}  {m}" for p, m in offenders)
            + "\n（若确有理由保留 async，请加进 _T1_ASYNC_ALLOWLIST 并写清原因）")

    #: 「唯一 await 只是读 body」的例外：**必须在这里写清理由**，否则通则会把它判红。
    #: ⚠ **目前为空**——`/compliance/review/{task_id}/execute`（原先唯一的例外，SSE）已在 §10.80
    #: 修掉（外层 `def` + **同步生成器**）。留着这个机制是因为：下一条同族端点出现时，
    #: 要么改 `def`，要么在这里写清"为什么它不会占住事件循环"——**不许默默加白名单**。
    _BODY_ONLY_ASYNC_ALLOWLIST: set[str] = set()

    def test_async_endpoints_that_only_read_body_are_not_heavy(self, client):
        """**通则之三（T2）**：`async def` 端点若**唯一的 `await` 只是读 body**（或没有 await），
        却带着**任何重标记** ⇒ 必须是 `def`。

        判据（全部从**代码**取，不看注释——`_code_only` 已删 docstring/注释）：
        1. 端点是 `async def`；
        2. 它**没有** `await`，或者它的 `await` **全部**只是 `request.json()` / `request.body()`；
        3. 它的可达路径上有重标记（`fs-copy` 这类"轻标记"不算——`get_db_connection()` 里就有
           一个 `mkdir`，会传染到任何碰库的助手）。
        命中且不在白名单 ⇒ 红。

        **§10.86 起判据加强（本步）：不再要求"带重标记"** —— 标记表是启发式，b15 实测它漏了
        （裸 `DELETE FROM` / `CREATE INDEX` 都命不中 ⇒ 两条真会堵库的端点被放行）。现在只看
        一件事：**这条 async 端点有没有一个真会让出控制权的 `await`**（`never_yields()` 为
        True = 没有 ⇒ 红）。重标记退居审计报告里的**优先级信号**。判据的来源与理由见上一条
        （`test_T1_零await的async端点必须是def`）；这条留在原名字下，是因为 §10.79–§10.85 的
        历史记录都按这个名字引用它——**名字是历史的，判据是当前的**。

        **白名单**（`_BODY_ONLY_ASYNC_ALLOWLIST`）**目前为空**——那是好事：说明"该转的都转了"。
        真要留一个 `async def`，必须在那里写清"为什么它不会占住事件循环"，不许默默加。
        """
        import asyncio

        c, _ = client
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        offenders = []
        examined = 0
        async_seen: set[str] = set()
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            path = getattr(r, "path", None)
            if ep is None or path is None or not path.startswith("/api/"):
                continue
            examined += 1
            if not asyncio.iscoroutinefunction(ep):
                continue
            async_seen.add(path)
            try:
                src = textwrap.dedent(inspect.getsource(ep))
            except (OSError, TypeError):        # pragma: no cover
                continue
            # ⚠ 判据走**审计脚本的 AST 实现**（§10.85 修 b14 的 MEDIUM-2）：原先这里读
            # **原始源码文本**（`"await " in ln`）⇒ 一句含 `await ` 的 docstring/注释就能
            # **静默豁免**整个端点（复核实测：docstring 写"本端点唯一的 await 只是读 body"
            # ⇒ 闸门 GREEN）。`never_yields()` 用 AST 数 `Await` 节点 ⇒ 注释骗不过它。
            #
            # ⚠ **§10.86 起判据加强**：不再要求"带重标记"。b15 实测两条端点（`DELETE
            # /materials/{id}` 的裸 `DELETE FROM`、`GET /laws/catalog` 的 `CREATE INDEX`）
            # **一条重标记都命不中**却在事件循环里等库写锁 0.65–0.70s ⇒ 标记表当必要条件
            # 就会漏。现在只问一件事：**这条 async 端点有没有一个真会让出控制权的 await**。
            # 重标记仍然有用——但只在审计报告里当**优先级信号**，不再当闸门。
            if not audit.never_yields(src) or path in self._BODY_ONLY_ASYNC_ALLOWLIST:
                continue
            offenders.append((path, ["零有效 await（T1 或只读 body）"]))
        # ⚠ **反向断言**（防假绿）：枚举坏掉时"全绿"毫无意义。原先拿"async 端点 ≥ 4 条"当哨兵，
        # 但 §10.93 把那 5 条 `/laws/*` 也转成 `def` 之后**全库只剩 1 条 async 端点**
        # ——用条数当哨兵已经没有意义（1 条也能"扫过"）。现在改成**集合相等**：
        # 这里扫到的 async 端点集合必须与 `_ASYNC_ENDPOINTS` **完全一致**
        # （识别/枚举任一坏掉都会红；比魔数更贴事实，也不会随端点增减而失效）。
        assert examined >= 140, f"只枚举到 {examined} 条 API 路由（实测 147）——枚举/筛选可能坏了"
        assert async_seen == set(self._ASYNC_ENDPOINTS), (
            "扫到的 async 端点集合与 `_ASYNC_ENDPOINTS` 不一致：\n"
            f"  扫到  {sorted(async_seen)}\n"
            f"  名单  {sorted(self._ASYNC_ENDPOINTS)}")
        assert not offenders, (
            "这些 `async def` 端点的 await **全都只是读 body**（或根本没有 await）⇒ 它其实"
            "从不让出控制权，后面全是同步活在事件循环里跑（应改 `def`；带 body 的顺带把 "
            "body 走签名）：\n"
            + "\n".join(f"  {p}  {m}" for p, m in offenders)
            + "\n（若确有理由保留 async，请加进 _BODY_ONLY_ASYNC_ALLOWLIST 并写清原因）")

    def test_名单第二关的判据_effective_real_await(self):
        """§10.88：名单第二关的判据在**六种形状**上都必须判对（b17 的 MEDIUM-2 + MEDIUM-3）。

        这是名单里"理由成不成立"的唯一自动判据，所以它自己的边界必须先钉住：

        | 形状 | 期望 | 为什么 |
        |---|---|---|
        | H1 `await _read_json(request)`（**嵌套**助手内部才读 body） | **False** | 内联后一次都不让出（b16 实测这种形状堵 0.650s） |
        | H3 外层读 body + 嵌套 async 生成器**从不被引用** | **False** | 它执行路径上没有挂起点 |
        | H4 只有 `async for` | **True** | 编译成 `await __anext__`，等待点常在库源码里（旧判据在这里**误红**） |
        | H2 真流式：嵌套生成器被引用、里面有真 await | **True** | 迭代时真的让出（**不许误伤**） |
        | `await asyncio.to_thread(...)`（属性调用形状；§10.93 后仓内**已无端点**这么写） | **True** | 属性调用 ⇒ 未知但确实会 await |
        | 只有 `await request.json()` | **False** | 读完 body 全是同步活 ⇒ 该 `def` |
        | 解析失败 | **False** | fail-closed（不算"有"⇒ 名单判红） |
        """
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe_eff", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        def _f(src: str) -> bool:
            return audit.effective_real_await(textwrap.dedent(src))

        assert _f('''
            async def ep(request):
                body = await _read_json(request)
                heavy(body)

                async def _read_json(r):
                    return await r.json()
        ''') is False, "H1（嵌套助手包装读 body）必须判成'没有真挂起点'"
        assert _f('''
            async def ep(request):
                body = await request.json()
                async def stream():
                    await something()
                    yield 1
                heavy(body)
        ''') is False, "H3（从不被引用的嵌套 async 生成器）必须判成'没有真挂起点'"
        assert _f('''
            async def ep():
                async for chunk in reader:
                    out.append(chunk)
        ''') is True, "只有 async for 也是真的会让出（b17 的 MEDIUM-2：旧判据在这里误红）"
        assert _f('''
            async def ep(request):
                body = await request.json()
                async def stream():
                    async for c in gen(body):
                        yield c
                return StreamingResponse(stream())
        ''') is True, "真流式（被引用的嵌套生成器里有真 await）不许被判红"
        assert _f('''
            async def ep():
                return await asyncio.to_thread(f, 1, x=2)
        ''') is True, "属性调用（to_thread）算真挂起点"
        assert _f('''
            async def ep(request):
                body = await request.json()
                return heavy(body)
        ''') is False, "只有读 body 的 await ⇒ 该 def"
        assert _f("async def ep(:\n") is False, "解析失败必须 fail-closed"

    def test_def端点返回StreamingResponse仍然真流式(self):
        """§10.89（独立复核 b18 的 MEDIUM-1）：**`def` 端点也能真流式** —— 这是判据的前提。

        b18 构造了一条"真会让出的流式端点"（嵌套 async 生成器被装饰器/模块级注册表登记），
        指出名单第二关会判它红。作者**没有**放宽判据，理由是：闸门问的是"**必须** async 吗"，
        而**否** —— 本用例实测：`def` 端点返回 `StreamingResponse(async_gen())` 与 `async def`
        **逐块行为相同**。⇒ 判红的补救（改 `def`）**无害**；反过来放宽判据会让 H5 那种
        "端点体里先跑 0.65s 同步活、再返回流"的形状混过去。

        ⚠ **判据是 ASGI `send()` 消息边界，不是 body 拼接**（独立复核 b19 的 N3：第一版只断言
        "两种声明都 200 + 拼接后的 body 相同"，把生成器换成一次性 `Response(同样字节)` 也照样绿
        ⇒ **钉不住"流式"**；b19 还指出 httpx 会把流合并成一个 piece，所以"逐块"在客户端侧
        观测不到）。这里直接调 app（ASGI 层）数 `http.response.body` 且 `more_body=True` 的条数。

        ⚠ 它钉的是**框架事实**（Starlette 对异步可迭代对象一律分块发送，与端点是不是 `async def`
        无关）；框架升级后若它红了，§10.89 §1 的论证要重做。
        """
        import asyncio

        from fastapi import FastAPI
        from fastapi.responses import StreamingResponse

        async def gen():
            for i in range(3):
                await asyncio.sleep(0)               # 真挂起点在生成器里
                yield f"chunk{i}|".encode()

        app = FastAPI()

        @app.get("/def_ep")
        def def_ep():
            return StreamingResponse(gen())

        @app.get("/async_ep")
        async def async_ep():
            return StreamingResponse(gen())

        async def collect(path: str) -> list[dict]:
            msgs: list[dict] = []
            # ⚠ ASGI 直调的实测行为（§10.90 初版注释**写错了一条**，独立复核 b20 的 N1 已更正）：
            #   ① `receive()` **永不**返回 `http.disconnect` **不会挂住** —— starlette 1.6 在
            #      `StreamingResponse.__call__` 里用 `create_collapsing_task_group()`，
            #      任一侧跑完就 `cancel_scope.cancel()`，**流式侧结束会连带取消**卡在
            #      `listen_for_disconnect` 上的宿主任务（b20 用 6 种形状 + 不套 `wait_for` 的原始
            #      调用实测：0.0032s 正常返回、3 块齐全）；
            #   ② 但**一上来就回** `http.disconnect` 会被当成客户端提前断开：若流式侧随后撞到
            #      checkpoint（本用例的 `await asyncio.sleep(0)`），响应会**被中止**（实测只发
            #      `http.response.start`、0 块 body）；生成器与 send 都不让出时偶尔也能发完。
            #   ⇒ 这里仍用"**等最后一块 body 发完再回 disconnect**"的写法：它**确定性**地拿到
            #      全部分块，不依赖上面那些时序细节。
            #   ⚠ 另：那个 listen 分支只在 ASGI `spec_version < 2.4` 下存在（b20 用 2.4 测时
            #      任务组根本没进，压根没有 listen 任务）。
            done = asyncio.Event()

            async def receive():
                await done.wait()
                return {"type": "http.disconnect"}

            async def send(m):
                msgs.append(m)
                if m["type"] == "http.response.body" and not m.get("more_body"):
                    done.set()

            scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.3"},
                     "http_version": "1.1", "method": "GET", "scheme": "http",
                     "path": path, "raw_path": path.encode(), "query_string": b"",
                     "root_path": "", "headers": [],
                     "client": ("127.0.0.1", 12345), "server": ("127.0.0.1", 80)}
            await app(scope, receive, send)
            return msgs

        async def main() -> dict[str, tuple[int, list[bytes]]]:
            out: dict[str, tuple[int, list[bytes]]] = {}
            for path in ("/def_ep", "/async_ep"):
                msgs = await collect(path)
                start = next(m for m in msgs if m["type"] == "http.response.start")
                chunks = [m.get("body", b"") for m in msgs
                          if m["type"] == "http.response.body" and m.get("more_body")]
                out[path] = (start["status"], chunks)
            return out

        got = asyncio.run(main())
        for path in ("/def_ep", "/async_ep"):
            status, chunks = got[path]
            assert status == 200, got
            assert len(chunks) >= 3, (
                f"{path} 只发出 {len(chunks)} 块（应 ≥3）——那就不是流式，本用例的前提不成立")
            assert b"".join(chunks) == b"chunk0|chunk1|chunk2|", got
        assert got["/def_ep"][1] == got["/async_ep"][1], (
            "两种声明方式的**分块**必须一致（逐块边界都要相同）")

    def test_内联递归的深度上限被唯一钉住(self):
        """§10.90/§10.91（独立复核 b19 的 N4 + b20 的 N2）："深度上限 = 4" 必须被**唯一**钉住。

        b19 实测：把上限改成 2，**全量 1810 条零红** ⇒ 那条边界只是文档、没人守。
        b20 进一步实测：只钉 3 层/6 层时，**上限改成 3 或 5 也全绿**（钉住的是窗口 {3,4,5}，
        不是 4）。所以这里同时钉**两侧的临界点**：

        | 嵌套层数 | 期望 | 为什么 |
        |---|---|---|
        | 3 层（每层只读 body） | `False` | 没到上限 ⇒ 内联到底 ⇒ 一次都不让出 |
        | **4 层** | `False` | 刚到上限（`depth > 4` 才截断）⇒ 仍能内联到底 |
        | **5 层** | `True` | 第 5 层起截断 ⇒ 按"只朝放行截断"的约定判 True |

        ⇒ 上限被改成 3 ⇒ 第 2 行翻成 True ⇒ 红；改成 5 ⇒ 第 3 行翻成 False ⇒ 红。
        """
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe_depth", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        def chain(depth: int) -> str:
            # ep → h1 → h2 → … 每层都只 await request.json()（读 body，不让出）
            lines = ["async def ep(request):", "    body = await h1(request)",
                     "    return heavy(body)", ""]
            for i in range(1, depth + 1):
                nxt = f"h{i + 1}" if i < depth else None
                lines.append(f"    async def h{i}(request):")
                if nxt:
                    lines.append(f"        return await {nxt}(request)")
                else:
                    lines.append("        return await request.json()")
            return "\n".join(lines)

        assert audit.effective_real_await(chain(3)) is False, (
            "3 层嵌套助手都在读 body ⇒ 判据必须仍然判 False（上限没到）")
        assert audit.effective_real_await(chain(4)) is False, (
            "4 层是**上限本身**（`depth > 4` 才截断）⇒ 仍必须判 False；"
            "这一条把'上限 = 4'与'上限 = 3'区分开（b20 的 N2）")
        assert audit.effective_real_await(chain(5)) is True, (
            "5 层超过上限 ⇒ 按约定判 True（只朝放行截断）；这一条把'上限 = 4'与'上限 = 5'区分开")
        assert audit.effective_real_await(chain(6)) is True, (
            "6 层同理（远离边界的一侧）")

    def test_判据本体的边界样本(self):
        """§10.86：两条判据的**边界形状**（b15 的 INFO-1 / INFO-3）。

        ① `async for` / `async with` **必须**算"会让出控制权"：它们编译成 `await __anext__` /
           `__aenter__`，但 AST 里没有 `Await` 节点 ⇒ 只数 `Await` 会把这种端点判成"零 await
           该改 `def`"，而那种代码改成 `def` **根本不成立**（Info-1）。
        ② **解析失败 ⇒ fail-closed**：`awaits_like → None`（调用方判红）、`never_yields → True`
           （"当它从不 yield"）。旧实现是 `return False`（静默放行）。
        ③ 判据内部必须自己 `dedent`：`inspect.getsource()` 对闭包里的端点给**带缩进**的源码，
           不 dedent 就解析失败 ⇒ 在旧实现下等于**全部缩进端点被放行**。
        """
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe_edges", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        # ① async for / async with
        assert audit.awaits_like(
            "async def f():\n    async for x in g():\n        pass\n") == 1, \
            "async for 必须算'会让出控制权'（它编译成 await __anext__，AST 里却没有 Await 节点）"
        assert audit.awaits_like(
            "async def f():\n    async with s():\n        pass\n") == 1, \
            "async with 同理（await __aenter__）"
        assert audit.never_yields(
            "async def f():\n    async for x in g():\n        pass\n") is True, \
            "只写了 async for 的端点确实'零 Await 节点'——所以判据必须由 awaits_like 兜住"
        # ② 坏源码 ⇒ fail-closed
        assert audit.awaits_like("async def f(:\n") is None, "解析失败必须返回 None（判红）"
        assert audit.never_yields("async def f(:\n") is True, \
            "解析失败必须判成'从不 yield'（fail-closed），不许静默放行"
        # ③ 缩进源码（闭包里的端点就是这种形状）
        indented = "    async def f(r):\n        return await r.json()\n"
        assert audit.awaits_like(indented) == 1
        assert audit.never_yields(indented) is True

    def test_nested_async_generators_without_await_are_rejected(self, client):
        """**通则之二**：端点里嵌套的 `async def` **生成器**若**一个 `await` 都没有** ⇒ 红。

        为什么（§10.80）：`StreamingResponse` 对**异步**可迭代对象是 `async for` 直接迭代
        （starlette 1.6 的 `stream_response`）；一个"没有 await 的 async 生成器"每次 `yield`
        都在**事件循环**里跑。`/compliance/review/{task_id}/execute` 原先正是这个形状：
        它的 `run_review(...)` 是**逐点调 LLM** 的同步生成器 ⇒ 一次评审（几十秒到几分钟）
        把整个引擎冻住，而所有"async def / 只读 body / 重标记"的判据**都看不见它**
        （外层端点当时就是 `async def`，但**唯一的 await 只是 `request.json()`**，
        被判据当成"廉价"）。

        判据：AST 里找 `AsyncFunctionDef` 且体内含 `Yield`（= 异步生成器），
        若整段没有 `Await` ⇒ 命中。
        ⚠ 这条是**零假阳性**的结构判据（有 await 的异步生成器不受影响），所以**没有白名单**。
        """
        c, _ = client
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "ks_audit_probe", root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        offenders = []
        for r in c.app.routes:
            ep = getattr(r, "endpoint", None)
            path = getattr(r, "path", None)
            if ep is None or path is None or not path.startswith("/api/"):
                continue
            try:
                src = textwrap.dedent(inspect.getsource(ep))
            except (OSError, TypeError):    # pragma: no cover
                continue
            for name in audit.nested_async_gen_without_await(src):
                offenders.append((path, name))
        assert not offenders, (
            "这些端点里有**没有 await 的 async 生成器**（它在事件循环里逐条产出，会占住引擎；"
            "`StreamingResponse` 对**同步**生成器会用线程池迭代 ⇒ 把它写成 `def` 生成器）：\n"
            + "\n".join(f"  {p}  内嵌 {name}()" for p, name in offenders))

    def test_没有函数叠着两个_docstring(self):
        """**结构判据**：一个函数/类体里不许**连着两个字符串常量语句**（b14 的 LOW-3）。

        来历：§10.79 批量把 `async def` 改成 `def` 时，有的是在**原 docstring 上面**插了一句
        "为什么改 `def`"，于是变成两个 docstring 上下叠着。Python 只把**第一个**当 `__doc__`，
        第二个成了**死字符串表达式**：不报错、测试全绿，但 `inspect.getdoc()` / 未来的
        OpenAPI 摘要 / 读代码的人都只看到第一句——"文档写了但其实不在文档里"。
        复核当时只在 `announce_export` 上撞见；这里**全库**扫，将来谁再叠一个会红。
        """
        import ast

        offenders = []
        for p in sorted((Path(__file__).resolve().parents[1] / "src").rglob("*.py")):
            try:
                tree = ast.parse(p.read_text(encoding="utf-8"))
            except SyntaxError as e:                              # pragma: no cover
                offenders.append(f"{p}: 语法错误 {e}")
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                         ast.ClassDef)):
                    continue
                body = node.body
                if len(body) >= 2 and all(
                        isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
                        and isinstance(s.value.value, str) for s in body[:2]):
                    offenders.append(f"{p.relative_to(p.parents[1])}:{body[1].lineno} "
                                     f"{node.name}()")
        assert not offenders, (
            "这些函数体里叠着两个字符串常量（只有第一个是 docstring，第二个是死代码）：\n"
            + "\n".join(f"  {o}" for o in offenders))

    def test_两条通则的判据走_AST_不会被注释骗(self):
        """§10.85：判据本身也要验——**注释不是行为**（独立复核 b14 的 MEDIUM-2）。

        复核的对照实验：同一个"只读 body"形状，只改 docstring/注释文本，闸门就放行。
        根因是判据读的是**源码文本**。现在两条判据都在审计脚本里用 AST 实现，这里钉住它：
        ① 含"await"字样的 docstring/注释**不能**让"从不 yield"变成 False；
        ② 真有 `await` 的函数**必须**被判成 False（否则判据会把真异步端点也拖进来）。
        """
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("ks_audit_probe2",
                                                      root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        # ① 注释/docstring 里出现 await ⇒ 仍然是"从不 yield"（真值：它没有 await）
        docstring_case = textwrap.dedent('''
            async def f(body: dict | None = None):
                """本端点唯一的 await 只是读 body（这句是注释，不是行为）"""
                # 这里不 await 任何东西
                return body or {}
        ''')
        assert audit.never_yields(docstring_case) is True, "注释里出现 await 就把判据骗了"
        # ② 真有 await ⇒ False
        real = textwrap.dedent('''
            async def f(body: dict | None = None):
                """注释里写着 await 但这句不生效"""
                x = await something_real()
                return x
        ''')
        assert audit.never_yields(real) is False, "真异步端点被判成'从不 yield'"
        # ③ 嵌套 async 生成器的判据同样不吃注释
        gen_doc = textwrap.dedent('''
            def f():
                async def event_stream():
                    """注释里写 await"""
                    yield 1
                return event_stream
        ''')
        assert audit.nested_async_gen_without_await(gen_doc) == ["event_stream"]

    def test_嵌套生成器判据只数自己作用域(self):
        """§10.86 自查：`yield`/`await` 必须只数**该函数自己作用域**里的。

        为什么（b15 复核期间我自己打出来的两个反例）：
        ① **假阳性**——`async def helper()` 里嵌了一个**同步**生成器 `def inner(): yield 1`；
           `ast.walk(helper)` 会看见那个 `yield` ⇒ 把 `helper` 误判成"没有 await 的 async 生成器"
           （实测旧实现返回 `['helper']`，而 `helper` **根本不是生成器**）。
        ② **假阴性**——一个真 async 生成器，唯一的 `await` 写在嵌套 async 函数里；
           旧实现把嵌套的 `Await` 也算成它自己的 ⇒ 判据放行（闸门静默失效）。
        """
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("ks_audit_probe3",
                                                      root / "scripts" / "audit-async-endpoints.py")
        assert spec and spec.loader
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)

        # ① async 函数 + 嵌套**同步**生成器 ⇒ 不该被当成异步生成器（假阳性）
        fp = textwrap.dedent('''
            def endpoint(body=None):
                async def helper():
                    def inner():
                        yield 1
                    return inner
                return helper
        ''')
        assert audit.nested_async_gen_without_await(fp) == [], \
            "嵌套同步生成器的 yield 被算到外层 async 函数头上了（假阳性）"

        # ② 真 async 生成器 + 唯一的 await 在嵌套函数里 ⇒ 仍须命中（假阴性）
        fn = textwrap.dedent('''
            def endpoint(body=None):
                async def stream():
                    yield 1
                    async def inner():
                        await something()
                    return inner
        ''')
        assert audit.nested_async_gen_without_await(fn) == ["stream"], \
            "嵌套函数里的 await 把外层异步生成器豁免了（假阴性）"

        # ③ 真异步生成器（自己有 await）不受影响（零假阳性）
        ok = textwrap.dedent('''
            def endpoint(body=None):
                async def stream():
                    await asyncio.sleep(0)
                    yield 1
        ''')
        assert audit.nested_async_gen_without_await(ok) == []


    @pytest.mark.parametrize("module,min_routes", [
        # 这个文件里的每一件事都是同步重活（秒级 SQL 聚合 / openpyxl 落盘 / 逐份 sha256），
        # 所以往这里新加端点**默认就该是 `def`**。
        # ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：阈值 6 → **5**。
        # 这个数是**下限**（`seen >= min_routes`）：`routes_report` 真实注册数 7 → **6**
        # （`/report/research/slides` 随 Word/PPT 交付物撤销拆除），故下限同步降 1 保持原来的余量。
        ("src.core.api.routes_report", 5),
        # §10.73（2026-09-18）：入库预览那一族同理——单文件预览 = sha256 + **真解析一份 PDF**
        # （该文件自述"负载下可达 135s"），批量要扫目录，jobs 三件套要读任务表。
        # 改前实测（`scripts/measure-endpoint-blocking.py`，12 页 PDF）：事件循环被堵 **0.468s**
        # ≈整条请求；改 `def` 后掉回噪声底（§10.73 的 before/after 表）。
        ("src.core.api.routes_ingest_preview", 6),
    ])
    def test_module_has_no_async_endpoint(self, client, module, min_routes):
        """**文件级**闸门：这些模块注册的端点，**一个都不许是 `async def`**。

        为什么不接着加白名单条目：b12 的 MEDIUM-2 本身就是"漏了一条、没人发现"。逐条白名单
        挡不住**将来新加**的端点，文件级判据挡得住——这些文件里的每一件事都是同步重活。

        ⚠ 反向断言（`seen >= min_routes`）**不可省**：路由一条都没扫到时"全绿"是**假绿**
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
            if ep is None or getattr(ep, "__module__", None) != module:
                continue
            path = getattr(r, "path", "?")
            seen.append(path)
            if asyncio.iscoroutinefunction(ep):
                bad.append(path)
        assert len(seen) >= min_routes, (
            f"{module} 只扫到 {len(seen)} 条端点（{seen}）——判据可能空过，先确认路由注册")
        assert not bad, f"{module} 里的端点做同步重活，必须全部是 `def`（线程池）：{bad}"


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


