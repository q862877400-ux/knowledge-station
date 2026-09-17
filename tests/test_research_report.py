# -*- coding: utf-8 -*-
"""研究报告导出测试（`src/core/exports/research_report.py`，Phase D 第一步）。

守四件事：
  1. **依据分组复用唯一所有者**（`materials.authority`）——本模块不许自己再分一套；
  2. **引用可核**：结论里的 `[[m:i]]` 指向不存在 / 指向仅线索或不可用 ⇒ **必须**进 warnings；
  3. **未批准材料如实列出**（可见性硬需求），且"没有命中"≠"项目不存在"；
  4. 两种形态（Markdown/HTML）从同一份渲染，HTML **全转义**（报告是可交付文件，不是网页）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.exports import research_report as rr
from src.core.materials import collect as co
from src.core.storage import material_repo as mr

HDR = {"Authorization": "Bearer test-token-123"}


@pytest.fixture()
def project(db):
    return mr.create_project("研究报告测试")


def _approved_article(pid: str, title: str, text: str) -> dict:
    m = co.collect_text(pid, title=title, text=text, url="https://a.example/1")
    mr.set_review(m["material_id"], "approved")
    return m


class TestBuild:
    def test_sections_and_counts(self, project):
        pid = project["project_id"]
        _approved_article(pid, "一篇已批准报道", "住宿标准每晚不超过八百元，自下月起执行。")
        co.collect_text(pid, title="一篇待评审报道", text="尚未评审的内容。",
                        url="https://b.example/1")
        out = rr.build_research_report(pid, title="某调研", query="住宿标准")
        md = out["markdown"]
        assert "# 某调研" in md
        assert "研究问题" in md and "住宿标准" in md
        assert "依据（按**承重能力**分组" in md
        assert "已批准参考资料清单" in md
        assert "尚未批准的材料" in md
        assert "一篇待评审报道" in md              # 未批准也要**如实列出**
        assert out["counts"] == {"approved": 1, "pending": 1, "rejected": 0}
        assert "本地生成，未外发" in md

    def test_grouping_reuses_the_authority_owner(self, project):
        """**结构性约束**：分组标题必须来自 `authority.GROUP_ORDER`（不许自己再写一套）。"""
        from src.core.materials import authority
        pid = project["project_id"]
        _approved_article(pid, "报道", "宿舍改造的住宿标准是每晚不超过八百元。")
        out = rr.build_research_report(pid, query="住宿标准")
        titles = [t for _k, t in authority.GROUP_ORDER]
        assert any(t in out["markdown"] for t in titles), out["markdown"][:400]

    def test_pending_is_never_silently_dropped(self, project):
        pid = project["project_id"]
        co.collect_text(pid, title="待评审甲", text="内容甲。", url="https://a.example/1")
        out = rr.build_research_report(pid)
        assert "待评审甲" in out["markdown"]
        assert "不会进入任何结论" in out["markdown"]

    def test_no_approved_materials_says_so(self, project):
        pid = project["project_id"]
        out = rr.build_research_report(pid)
        assert "没有已批准的材料" in out["markdown"]

    def test_missing_project_raises(self, db):
        with pytest.raises(ValueError, match="项目不存在"):
            rr.build_research_report("prj_不存在")

    def test_html_is_escaped(self, project):
        """标题/结论里的 HTML 必须**转义**（报告是可交付文件，不是网页）。"""
        pid = project["project_id"]
        out = rr.build_research_report(pid, title="<script>alert(1)</script>")
        assert "<script>" not in out["html"]
        assert "&lt;script&gt;" in out["html"]
        # Markdown 侧保留原样（它是纯文本）
        assert "<script>" in out["markdown"]


class TestCitationChecking:
    def test_unknown_index_is_warned(self, project):
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准每晚不超过八百元。")
        out = rr.build_research_report(pid, query="住宿标准",
                                       conclusion_md="据 [[m:99]] 可知。")
        assert out["citations"]["unknown"] == [99]
        assert any("不存在" in w for w in out["warnings"]), out["warnings"]

    def test_valid_index_is_not_warned(self, project):
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准每晚不超过八百元，自下月起执行。")
        out = rr.build_research_report(pid, query="住宿标准",
                                       conclusion_md="据 [[m:0]] 可知。")
        assert out["citations"]["unknown"] == []
        assert out["citations"]["material_refs"] == [0]

    def test_law_refs_are_counted_but_not_pretended_verified(self, project):
        """`[[c:i]]` 本次**无法校验** ⇒ 如实计数（不假装查过）。"""
        pid = project["project_id"]
        out = rr.build_research_report(pid, conclusion_md="按 [[c:1]] 与 [[c:2]] 办。",
                                       query="住宿标准")
        assert out["citations"]["unchecked_law_refs"] == [1, 2]

    def test_conclusion_without_query_is_declared_unchecked(self, project):
        """不给 `query` 就没有依据集可比 ⇒ **必须**说出来（不许默默放过引用）。

        ⚠ **结构化字段也要如实**（2026-09-17 复核 b7 的 LOW-3）：原来只把"有 N 个引用
        无法校验"写进 warning 文案，而 `citations["material_refs"]` 仍是**空列表**——
        读结构化字段的消费者会得出"结论里没有材料引用"这个**相反**的结论。
        """
        pid = project["project_id"]
        out = rr.build_research_report(pid, conclusion_md="据 [[m:3]] 可知。")
        assert any("无法校验" in w for w in out["warnings"]), out["warnings"]
        # 结构化字段与文案必须说同一件事
        assert out["citations"]["material_refs"] == [3], out["citations"]

    def test_negative_index_is_caught(self, project):
        """负数编号也要被抓（历史缺陷：提示词侧曾漏掉 `[[m:-1]]`）。"""
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准八百元。")
        out = rr.build_research_report(pid, query="住宿标准", conclusion_md="据 [[m:-1]]。")
        assert out["citations"]["unknown"] == [-1], out["citations"]


class TestWrite:
    def test_files_are_written_and_named(self, project, tmp_path, monkeypatch):
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = rr.write_research_report(pid, title="某调研报告")
        assert len(out["files"]) == 2
        names = out["names"]
        assert names[0].endswith(".md") and names[1].endswith(".html")
        assert "某调研报告" in names[0]
        assert Path(out["files"][0]).read_text(encoding="utf-8") == out["markdown"]
        assert Path(out["files"][1]).read_text(encoding="utf-8") == out["html"]

    def test_unsafe_title_is_sanitised(self, project, tmp_path, monkeypatch):
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = rr.write_research_report(pid, title="a/b:c*d?e<f>g|h i")
        name = out["names"][0]
        assert not set('/\\:*?"<>| ') & set(name.replace("研究报告-", "").split("-")[0])


class TestTrackLStatus:
    def test_lists_track_l_targets_without_writing(self, project, db):
        """`track_l_status` 只读（不得往法条链写任何东西）。"""
        pid = project["project_id"]
        co.collect_text(pid, title="GB 88888-2088 某规范",
                        text="GB 88888-2088 某规范\n3.1 术语\n某定义。\n4.1 要求\n应满足。",
                        url="https://openstd.example/x")
        before = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        rows = rr.track_l_status(pid)
        after = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        assert before == after
        assert rows and rows[0]["action"] == "blocked", rows   # 未批准 ⇒ blocked
        assert rows[0]["doc_kind"] == "standard", rows


class TestEndpoint:
    def test_export_writes_files_and_returns_them(self, client, project, tmp_path, monkeypatch):
        from src.core.exports import research_report as mod
        monkeypatch.setattr(mod, "_exports_dir", lambda: tmp_path)
        c, _ = client
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准每晚不超过八百元。")
        r = c.post("/api/v1/report/research",
                   json={"project_id": pid, "title": "接口调研", "query": "住宿标准"},
                   headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert data["counts"]["approved"] == 1
        assert len(data["files"]) == 2 and all(Path(f).exists() for f in data["files"])

    def test_dry_run_does_not_write(self, client, project, tmp_path, monkeypatch):
        from src.core.exports import research_report as mod
        monkeypatch.setattr(mod, "_exports_dir", lambda: tmp_path)
        c, _ = client
        r = c.post("/api/v1/report/research",
                   json={"project_id": project["project_id"], "dry_run": True}, headers=HDR)
        assert r.status_code == 200, r.text
        assert "files" not in r.json()["data"]
        assert r.json()["data"]["markdown"]
        assert list(tmp_path.iterdir()) == [], "dry_run 不许落盘"

    def test_missing_project_is_404(self, client):
        c, _ = client
        r = c.post("/api/v1/report/research", json={"project_id": "prj_没有"}, headers=HDR)
        assert r.status_code == 404, r.text

    def test_missing_project_id_is_422(self, client):
        c, _ = client
        assert c.post("/api/v1/report/research", json={}, headers=HDR).status_code == 422

    def test_wrong_types_are_422(self, client, project):
        c, _ = client
        pid = project["project_id"]
        assert c.post("/api/v1/report/research",
                      json={"project_id": pid, "query": 123}, headers=HDR).status_code == 422
        assert c.post("/api/v1/report/research",
                      json={"project_id": pid, "limit": "abc"}, headers=HDR).status_code == 422

    def test_requires_token(self, client):
        c, _ = client
        assert c.post("/api/v1/report/research", json={}).status_code == 401
