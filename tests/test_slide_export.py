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
        """页数超限时**在 PPT 里**写明"后续见报告"——不假装全放得下。

        ⚠ 上限是**交付物**的（含末页）⇒ `build_slides` 只给 `MAX_SLIDES - 1` 张内容页
        （复核 b7 的 MEDIUM-2：旧实现 `build_slides` 给 30 张、`write_slide_deck` 再加末页
        ⇒ 落盘 **31** 页，而常量与文档都写 30，属过度声称）。
        """
        blocks: list[tuple[str, object]] = [("h1", "T")]
        for i in range(se.MAX_SLIDES + 10):
            blocks.extend([("h2", f"第 {i} 节"), ("p", f"内容 {i}")])
        slides = se.build_slides(blocks, title="T")
        assert len(slides) <= se.MAX_SLIDES - 1, len(slides)
        assert "Markdown 报告" in slides[-1]["title"]
        assert "只放了前" in slides[-1]["bullets"][0]

    def test_a_page_with_too_many_bullets_is_paginated(self):
        """**真正的无界轴**是每页要点数（复核实测单页 120 条）⇒ 按**行预算**续页。

        ⚠ 判据在 2026-09-17 改过一次（复核 b8 的 MEDIUM-3）：上一版按"条数 ≤ 12"分页，
        而复核算过几何——正文框可用 ≈ 6.19in、一行 ≈ 0.30in ⇒ 约 20 行，
        12 条 × 40 字 ≈ **24 行 ≈ 7.20in 已经溢出**。现在按**估算行数**分页，
        并且断言"每页估算行数 ≤ 行预算"（这正是复核建议的钉法）。
        """
        blocks: list[tuple[str, object]] = [
            ("h1", "T"), ("h2", "依据"),
            # 每条 6 字 ≈ 1 行 ⇒ 需要约 MAX_LINES_PER_SLIDE × 3 条才撑出 4 页
            ("ul", [f"第 {i} 条依据" for i in range(se.MAX_LINES_PER_SLIDE * 3 + 1)]),
        ]
        slides = se.build_slides(blocks, title="T")
        lines = [sum(se.estimate_lines(b) for b in s["bullets"]) for s in slides]
        assert all(n <= se.MAX_LINES_PER_SLIDE for n in lines), lines
        # 1 首页（无要点）+ 4 页内容（第 4 页只 1 条）
        assert len(slides) == 5, [s["title"] for s in slides]
        assert "（续 2）" in slides[2]["title"], [s["title"] for s in slides]
        # 没触发页数上限时**条数守恒**（续页不丢内容）
        assert sum(len(s["bullets"]) for s in slides) == se.MAX_LINES_PER_SLIDE * 3 + 1

    def test_long_bullets_are_split_by_the_line_budget_not_a_bullet_count(self):
        """**长要点**也要按行算：10 条 × 120 字 ≈ 30 行 ⇒ 必须拆成至少两页。

        这是复核 b8 的 MEDIUM-3 的正面形态：只数条数会放过"少量超长要点"的溢出。
        """
        blocks: list[tuple[str, object]] = [
            ("h1", "T"), ("h2", "依据"), ("ul", ["字" * 120 for _ in range(10)]),
        ]
        slides = se.build_slides(blocks, title="T")
        body = [s for s in slides if s["bullets"]]
        assert len(body) >= 2, [len(s["bullets"]) for s in body]
        lines = [sum(se.estimate_lines(b) for b in s["bullets"]) for s in body]
        assert all(n <= se.MAX_LINES_PER_SLIDE for n in lines), lines

    def test_overflow_page_declares_how_many_bullets_were_dropped(self):
        """**页数上限触发时丢的条数必须写在页上**（复核 b8 的 MEDIUM-2）。

        复核给的是**报告设计范围内**的输入（三份清单各填到 `LIST_CAP`）而丢了 47% 的要点，
        而上一版只说"只放了前 N 页"——不说丢了多少条，用户没法判断损失。
        """
        blocks: list[tuple[str, object]] = [("h1", "T")]
        for i in range(se.MAX_SLIDES + 40):
            blocks.extend([("h2", f"第 {i} 节"), ("ul", [f"条目 {i}-{j}" for j in range(6)])])
        slides = se.build_slides(blocks, title="T")
        assert len(slides) <= se.MAX_SLIDES - 1, len(slides)
        tail = " ".join(slides[-1]["bullets"])
        assert "未放入本 PPT" in tail, tail
        assert "完整清单见同名 Markdown 报告" in tail, tail

    def test_line_budget_matches_the_real_slide_geometry(self):
        """**行预算必须与真实版式一致**（复核 b8 的 MEDIUM-3 的"钉法"要求；b9 又补了宽度那一半）。

        不信任常量：这里**从真实 `Presentation()` 重算**几何——幻灯片尺寸、正文框高度
        （`slide_height - 1_200_000` EMU）、行高（`LINE_HEIGHT_FACTOR × ASSUMED_FONT_PT`）
        ——再断言"行预算 × 行高 ≤ 正文框高度"。任何一边改了而另一边没跟上，这条就红。
        """
        from pptx import Presentation
        prs = Presentation()
        body_h_pt = (prs.slide_height - 1_200_000) / 12_700            # EMU → pt
        line_pt = se.LINE_HEIGHT_FACTOR * se.ASSUMED_FONT_PT
        capacity = body_h_pt / line_pt
        assert capacity >= se.MAX_LINES_PER_SLIDE, (capacity, se.MAX_LINES_PER_SLIDE)
        # 常量侧的几何也要与真实模板一致（防止"写死一份、模板另一份"）
        assert se.SLIDE_WIDTH_EMU == prs.slide_width, (se.SLIDE_WIDTH_EMU, prs.slide_width)
        assert se.SLIDE_HEIGHT_EMU == prs.slide_height
        assert abs(se.BODY_HEIGHT_PT - body_h_pt) < 0.01
        # ---- 宽度那一半（复核 b9 的 MEDIUM-3）----
        # ⚠ **不能**拿整张幻灯片宽当时正文宽：文本框默认左右各 0.1in 内边距，
        # 真正能用的是 `slide_width - margin_left - margin_right`。这里直接问真实的
        # `text_frame.margin_*`（而不是相信本文件里的常量），常量若与库的默认值分叉就红。
        blank = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
        box = prs.slides.add_slide(blank).shapes.add_textbox(
            0, 1_000_000, prs.slide_width, prs.slide_height - 1_200_000)
        usable_emu = prs.slide_width - box.text_frame.margin_left - box.text_frame.margin_right
        assert abs(se.BODY_WIDTH_EMU - usable_emu) <= 2, (se.BODY_WIDTH_EMU, usable_emu)
        assert abs(se.TEXT_INSET_EMU - box.text_frame.margin_left) <= 1, (
            se.TEXT_INSET_EMU, box.text_frame.margin_left)
        # 每行容量 = **可用**宽（pt）/ 字号（pt）——中文 1 字 ≈ 1 em
        per_line = (usable_emu / 12_700) / se.ASSUMED_FONT_PT
        assert abs(per_line - se.CHARS_PER_LINE_EMS) < 0.01, (per_line, se.CHARS_PER_LINE_EMS)
        # 并且它**小于**"整张宽 / 字号"——上一版就是拿这个偏乐观的数当了容量
        naive = (prs.slide_width / 12_700) / se.ASSUMED_FONT_PT
        assert se.CHARS_PER_LINE_EMS < naive, (se.CHARS_PER_LINE_EMS, naive)

    def test_a_full_line_of_cjk_is_38_chars_because_the_prefix_takes_room(self):
        """**渲染级实测的临界点**（复核 b9 的 MEDIUM-3）：一行放 **38** 个 CJK 字。

        复核用 LibreOffice→PDF→PyMuPDF 量出来的：38 字/条 **完整**（684/684 字），
        39 字起就换第二行、超出部分**被渲染器裁掉**（39 字只剩 429/702）。
        我们这个估算器必须**复现同一个临界点**——它由两件事决定：
        可用宽 705.6pt / 18pt = 39.2 em，再扣掉渲染时自动加的 `· ` 前缀（≈1 em）。
        """
        assert se.estimate_lines("字" * 38) == 1, se.estimate_lines("字" * 38)
        assert se.estimate_lines("字" * 39) == 2, se.estimate_lines("字" * 39)
        assert se.estimate_lines("字" * 40) == 2, se.estimate_lines("字" * 40)

    def test_a_page_that_really_fits_is_not_split(self):
        """**反向对照**：真放得下的页面不许被拆（否则上一条只是"永远多拆"）。

        18 条 × 38 字 = 18 行，正好用满行预算 ⇒ **一页**（实测渲染也是完整的 684/684）。
        """
        slides = se.build_slides([("ul", ["字" * 38] * se.MAX_LINES_PER_SLIDE)], title="T")
        assert len(slides) == 1, [len(s["bullets"]) for s in slides]

    def test_bullets_that_would_be_clipped_are_paginated_instead(self):
        """**这条是本步的核心**：复核 b9 实测会被裁字的输入，现在必须**续页**而不是丢字。

        18 条 × 40 字：旧估算器判"18 行一页"，真排 2 行/条 ⇒ 22+ 行被塞进 20.6 行的框，
        渲染器把多出来的**字符**裁掉（丢 39%）。被裁掉的字符**不会**出现在任何"丢了多少条"
        的提示里——条数守恒，字符不守恒。修好之后应当**拆成两页**。
        """
        slides = se.build_slides([("ul", ["字" * 40] * se.MAX_LINES_PER_SLIDE)], title="T")
        assert len(slides) == 2, [len(s["bullets"]) for s in slides]
        for s in slides:
            assert sum(se.estimate_lines(b) for b in s["bullets"]) <= se.MAX_LINES_PER_SLIDE, s
        # 条数**一条不少**（续页不是删除）
        assert sum(len(s["bullets"]) for s in slides) == se.MAX_LINES_PER_SLIDE

    def test_ascii_bullets_are_cheaper_than_cjk_bullets(self):
        """半角字符按 0.5 全角当量折算 ⇒ 同样**字符数**时英文占行更少。

        为什么值得钉：一律按"字符数"会把英文清单**高估**行数（拆得更碎），
        而它的反面（低估中文）才是危险方向——两条都要有明确行为。
        """
        zh = "字" * 80              # 80 全角（+前缀）⇒ 3 行
        en = "a" * 80               # 80 × 0.5 = 40 当量（+前缀）⇒ 2 行
        assert se.estimate_lines(zh) == 3, se.estimate_lines(zh)
        assert se.estimate_lines(en) == 2, se.estimate_lines(en)
        assert se.estimate_lines(en) < se.estimate_lines(zh)

    def test_line_budget_matches_the_real_slide_geometry_placeholder(self):
        pass

    def test_limits_come_from_the_report_blocks(self):
        """末页的"已知限制"**从报告块取**（唯一内容所有者），不是手写第二份。

        `**粗体**` 会被压成纯文本（PPT 不做富文本解析）——所以断言写"压平之后"的值。
        """
        blocks = [("h1", "T"), ("h2", "六、已知限制（这份报告**不**保证什么）"),
                  ("ul", ["甲限制", "**乙**限制"])]
        assert se.limits_from_blocks(blocks) == ["甲限制", "乙限制"]
        # 取不到时**不编造**（返回一条说明，异常要看得见）
        bad = se.limits_from_blocks([("h1", "T")])
        assert len(bad) == 1 and "异常" in bad[0], bad


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
        """诚实边界要跟到产出物里（不能只写在文档里）。

        ⚠ **本用例的断言在 2026-09-17 改过一次方向**（复核 b7 的 MEDIUM-3）：末页那几句
        以前是 `slide_export` **手写**的第二份内容（PPT 里多 3 句、报告里多 2 句）。
        现在末页从**报告的块**取（`limits_from_blocks`）⇒ 断言要对着**报告里的那一份**说，
        而不是对着当初手写的那份措辞说；并且**反过来**断言"报告里的每条限制都在 PPT 里"
        ——那才是"同一份内容"的可检验形态。
        """
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = se.write_slide_deck(pid, title="T")
        from pptx import Presentation
        prs = Presentation(out["path"])
        last = prs.slides[-1]
        text = "\n".join(sh.text_frame.text for sh in last.shapes if sh.has_text_frame)
        assert "未外发" in text and "两个轴" in text and "待评审" in text
        # 报告 → PPT 的**逐条**包含（唯一内容所有者的可检验形态）
        model = rr.build_report_blocks(pid, title="T")
        for line in se.limits_from_blocks(model["blocks"]):
            assert se._plain(line) in text, line

    def test_delivered_page_count_never_exceeds_the_cap(self, project, tmp_path, monkeypatch):
        """**交付物**总页数 ≤ `MAX_SLIDES`（复核 b7 的 MEDIUM-2：旧实现落盘 31 页）。"""
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = se.write_slide_deck(pid, title="T")
        from pptx import Presentation
        prs = Presentation(out["path"])
        assert len(prs.slides._sldIdLst) <= se.MAX_SLIDES          # noqa: SLF001
        assert out["slide_count"] == len(prs.slides._sldIdLst)      # noqa: SLF001

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
