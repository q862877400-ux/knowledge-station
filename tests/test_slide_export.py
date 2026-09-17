# -*- coding: utf-8 -*-
"""研究报告 → PPT 导出测试（`src/core/exports/slide_export.py`，Phase D 第二步）。

守三件事：
  1. **内容同源**：幻灯片块来自 `research_report.build_report_blocks`（不另组织一套内容）；
  2. **诚实**：要点超长会截断并标 `…`、页数超限会**在 PPT 里写明**"后续见报告"；
  3. **真的能打开**：落盘的 `.pptx` 是真文件（zip + OOXML），不是空壳。
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from src.core.exports import research_report as rr
from src.core.exports import slide_export as se
from src.core.materials import collect as co
from src.core.storage import material_repo as mr

HDR = {"Authorization": "Bearer test-token-123"}


@pytest.fixture()
def project(db):
    return mr.create_project("PPT 导出测试")


def _blocks() -> list[tuple[str, object]]:
    return [
        ("h1", "某调研报告"),
        ("p", "生成时间：2026-09-17 12:00"),
        ("h2", "一、研究问题"),
        ("p", "住宿标准是多少？"),
        ("h2", "三、依据（按**承重能力**分组）"),
        ("pre", "- [[m:0]] [T1·可作依据] 材料#mat_1@0-10\n  住宿标准每晚不超过八百元。"),
        ("h2", "四、清单"),
        ("ul", ["甲，[T3·仅线索 / 未声明效力]，评审=approved",
                "乙，[T1·用户自有原始件 / 本任务准则]，评审=pending"]),
        ("h2", "（这一页没有内容）"),
    ]


class TestSlideModel:
    def test_mapping(self):
        slides = se.build_slides(_blocks(), title="某调研报告")
        assert slides[0]["title"] == "某调研报告"
        titles = [s["title"] for s in slides]
        assert "一、研究问题" in titles and "四、清单" in titles
        assert "（这一页没有内容）" not in titles, "只有标题没内容的页不该出现"
        # `pre`（依据区）逐行成为要点；`ul` 逐条
        assert any("[[m:0]]" in b for b in slides[2]["bullets"])
        assert any("乙" in b for b in slides[-1]["bullets"])

    def test_markdown_bold_is_flattened(self):
        """报告里的 `**粗体**` 在 PPT 里是纯文本（不做富文本解析）。"""
        slides = se.build_slides([("h1", "T"), ("h2", "**粗**"), ("p", "**很粗**的正文")],
                                 title="T")
        assert slides[1]["title"] == "粗"
        assert slides[1]["bullets"] == ["很粗的正文"]

    def test_long_bullet_is_clipped_with_ellipsis(self):
        slides = se.build_slides([("h1", "T"), ("h2", "S"), ("p", "字" * 500)], title="T")
        bullet = slides[1]["bullets"][0]
        assert bullet.endswith("…") and len(bullet) <= se.MAX_BULLET_CHARS + 1

    def test_too_many_slides_is_declared_inside_the_deck(self):
        """页数超限时**在 PPT 里**写明"后续见报告"——不假装全放得下。"""
        blocks: list[tuple[str, object]] = [("h1", "T")]
        for i in range(se.MAX_SLIDES + 10):
            blocks.extend([("h2", f"第 {i} 节"), ("p", f"内容 {i}")])
        slides = se.build_slides(blocks, title="T")
        assert len(slides) <= se.MAX_SLIDES
        assert "Markdown 报告" in slides[-1]["title"]
        assert "只放了前" in slides[-1]["bullets"][0]


class TestWriteDeck:
    def test_writes_a_real_pptx(self, project, tmp_path, monkeypatch):
        pid = project["project_id"]
        m = co.collect_text(pid, title="一篇报道", text="住宿标准每晚不超过八百元。",
                            url="https://a.example/1")
        mr.set_review(m["material_id"], "approved")     # 计数看的是**已批准**材料
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = se.write_slide_deck(pid, title="某调研", query="住宿标准")
        path = Path(out["path"])
        assert path.exists() and path.suffix == ".pptx"
        assert path.name.startswith("研究报告-") and "某调研" in path.name
        # 真的是 OOXML 包（zip 里有 presentation.xml）——不是空壳
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
        assert any(n.endswith("presentation.xml") for n in names)
        assert any(n.startswith("ppt/slides/slide") for n in names)
        assert out["slide_count"] >= 3, out          # 首页 + 内容 + 末页说明
        assert out["counts"]["approved"] == 1

    def test_last_slide_carries_the_honest_notes(self, project, tmp_path, monkeypatch):
        """诚实边界要跟到产出物里（不能只写在文档里）。"""
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = se.write_slide_deck(pid, title="T")
        from pptx import Presentation
        prs = Presentation(out["path"])
        last = prs.slides[-1]
        text = "\n".join(sh.text_frame.text for sh in last.shapes if sh.has_text_frame)
        assert "未外发" in text and "两个轴分开看" in text and "评审是用户的判断" in text

    def test_missing_project_raises_valueerror(self, db):
        with pytest.raises(ValueError, match="项目不存在"):
            se.write_slide_deck("prj_不存在")

    def test_missing_dependency_fails_loudly(self, monkeypatch):
        """缺 python-pptx 时给**可操作**的错误（不是静默出一个空文件）。"""
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *a, **kw):
            if name == "pptx":
                raise ImportError("No module named 'pptx'")
            return real_import(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(RuntimeError, match="python-pptx"):
            se._presentation()


class TestEndpoint:
    def test_slides_endpoint_writes_and_returns_path(self, client, project, tmp_path,
                                                     monkeypatch):
        from src.core.exports import research_report as mod
        monkeypatch.setattr(mod, "_exports_dir", lambda: tmp_path)
        c, _ = client
        pid = project["project_id"]
        r = c.post("/api/v1/report/research/slides",
                   json={"project_id": pid, "title": "接口 PPT", "query": "住宿标准"},
                   headers=HDR)
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert Path(data["path"]).exists() and data["name"].endswith(".pptx")
        assert data["slide_count"] >= 2

    def test_missing_project_is_404(self, client):
        c, _ = client
        r = c.post("/api/v1/report/research/slides", json={"project_id": "prj_没有"},
                   headers=HDR)
        assert r.status_code == 404, r.text

    def test_validation(self, client, project, tmp_path, monkeypatch):
        from src.core.exports import research_report as mod
        monkeypatch.setattr(mod, "_exports_dir", lambda: tmp_path)
        c, _ = client
        pid = project["project_id"]
        assert c.post("/api/v1/report/research/slides", json={},
                      headers=HDR).status_code == 422
        assert c.post("/api/v1/report/research/slides",
                      json={"project_id": pid, "title": 1}, headers=HDR).status_code == 422
        assert c.post("/api/v1/report/research/slides",
                      json={"project_id": pid, "limit": "x"}, headers=HDR).status_code == 422
        assert c.post("/api/v1/report/research/slides", json={"project_id": pid}).status_code == 401
