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
