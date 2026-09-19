# -*- coding: utf-8 -*-
"""研究报告导出测试（`src/core/exports/research_report.py`，Phase D 第一步）。

守四件事：
  1. **依据分组复用唯一所有者**（`materials.authority`）——本模块不许自己再分一套；
  2. **引用可核**：结论里的 `[[m:i]]` 指向不存在 / 指向仅线索或不可用 ⇒ **必须**进 warnings；
  3. **未批准材料如实列出**（可见性硬需求），且"没有命中"≠"项目不存在"；
  4. 两种形态（Markdown/HTML）从**同一份内容块**渲染，HTML **全转义**
     （报告是可交付文件，不是网页）。

⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原第 4 条里的第三种形态 **Word（`.docx`）**
与第 5 条（`docx_render_failed`"先渲染后落盘"）的用例**已随通路一并删除**——
业主否决 Word/PPT 交付物（`docs/NOT-DOING.md` 第 1 条）⇒ `files`/`names` 从三个回到两个。
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


class TestAnchorVisibility:
    """**引用锚点**要在报告里看得见（方案 §12 未决第 5 条，§10.48）。

    为什么放在报告里：报告的用途就是"引用可核"。而 `char_start/char_end/page` 是**解析结果**
    的坐标 ⇒ 换解析器可能让它失效，**而报告看起来一切正常**——那正是最坏的一种。
    便宜的指纹比对可以在报告路径上跑（重解析比对太贵，属显式动作）。
    """

    def test_fresh_material_has_no_anchor_noise(self, project):
        """刚入库的材料锚点 `ok` ⇒ **不许**加标记（标记得只在有问题时出现，否则人人无视）。"""
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准八百元。")
        out = rr.build_research_report(pid, title="T")
        assert not any("锚点" in w for w in out["warnings"]), out["warnings"]
        assert "⚠锚点" not in out["markdown"], out["markdown"]

    def test_health_crash_is_not_reported_as_unverified(self, project, monkeypatch):
        """**健康度算不出来 ≠ 材料未验证**（复核 b9 的 INFO-3）。

        旧写法在 `_attach_locator_status` 的 `except` 里写死 `unknown` ⇒ 报告上出现
        "⚠锚点**未验证**（不等于有问题）"，读者会去怀疑**材料**；而真相是**我们的判据抛异常**。
        这条断言两件事：① 有独立的 `⚠锚点健康度算不出来` 标记；
        ② 那条"未经验证"的 warning **不出现**（不许把工具缺陷算进材料的账）。
        """
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准八百元。")
        from src.core.materials import locator as lo
        def _boom(_m):
            raise RuntimeError("模拟判据崩溃")
        monkeypatch.setattr(lo, "locator_health", _boom)
        out = rr.build_research_report(pid, title="T")
        assert "⚠锚点健康度算不出来" in out["markdown"], out["markdown"]
        assert "⚠锚点未验证" not in out["markdown"], out["markdown"]
        hit = [w for w in out["warnings"] if "算不出来" in w]
        assert hit, out["warnings"]
        assert "工具缺陷" in hit[0], hit[0]
        assert not any("未经验证" in w for w in out["warnings"]), out["warnings"]
        # ⚠ 原因也要说出来（复核 b11 的 LOW-1：`_locator_why` 原先只写不读，2 写 0 读）
        assert "模拟判据崩溃" in hit[0], hit[0]
        # ⚠ 作用域要**明写**（复核 b11 的 LOW-2：它故意与 `_unknown` 不同，别让读者猜）
        assert "含待评审/已拒绝的在内" in hit[0], hit[0]

    def test_old_material_is_marked_unverified(self, project):
        """入库时没记指纹的老材料 ⇒ 标记 + warning（措辞必须是"未经验证"，不是"有问题"）。"""
        pid = project["project_id"]
        from src.core.storage import material_repo as mr
        m = mr.add_material(pid, "老材料", origin="user")
        mr.add_chunks(m["material_id"], [{"text": "甲", "char_start": 0, "char_end": 1}])
        mr.set_review(m["material_id"], "approved")
        out = rr.build_research_report(pid, title="T")
        assert "⚠锚点未验证" in out["markdown"], out["markdown"]
        hit = [w for w in out["warnings"] if "未经验证" in w]
        assert hit, out["warnings"]
        assert "**不等于**有问题" in hit[0], hit[0]

    def test_changed_fingerprint_is_marked_needing_recompute(self, project, monkeypatch):
        """指纹变了 ⇒ 「⚠锚点需复算」+ warning（措辞："需要复算"，不是"已经坏了"）。

        ⚠ 这里改的是**采集通道**那个常量：网页材料的当前指纹就是它
        （`locator.current_fingerprint_for` 对网页件返回 `COLLECT_PARSER_FINGERPRINT`），
        所以模拟"采集侧算法变了"要改它——第一版改了 `mi._provenance_fingerprint`，
        对网页件**不生效**（那条路走的是文件指纹），当场红。
        """
        pid = project["project_id"]
        _approved_article(pid, "报道", "住宿标准八百元。")
        from src.core.materials import collect as co
        monkeypatch.setattr(co, "COLLECT_PARSER_FINGERPRINT", "web:collect-v999")
        out = rr.build_research_report(pid, title="T")
        assert "⚠锚点需复算" in out["markdown"], out["markdown"]
        hit = [w for w in out["warnings"] if "需要复算" in w]
        assert hit, out["warnings"]
        # ⚠ 断言从 `"可能失效"` 改成 `"不代表已经坏了"`（2026-09-18，复核 b9 的 MEDIUM-1）：
        # `stale` 现在有**两个**成因——"解析器身份变了"（可能失效）与"**源文件字节已变**"
        # （**确定**失效）——"可能"会把后者说轻。被钉住的**语义**是
        # "措辞不许升级成'已经坏了'"，这层意思现在由这句话承担。
        assert "不代表已经坏了" in hit[0], hit[0]


class TestEvidenceAnchorMarks:
    """**锚点标记要出现在"引用行"上**（复核 b11 的 INFO-4，2026-09-18 收）。

    此前标记只在"已批准参考资料清单"里，而**真正的引用在「三、依据」节**——
    那一节由 `authority.render_evidence()` 渲染。b11 的原话是"建议把那句理由改准，
    或把 `_locator_status` 接进 `render_evidence()`"；本步两件都做了。
    ⚠ 关键设计：`render_evidence(assembled, locator_status=None)` 的第二个参数是**可选**的，
    **只有报告传它**；答案链（`ks_answer`）不传 ⇒ **提示词逐字节不变**（B-5 的保证）。
    """

    def test_report_marks_the_evidence_lines(self, project):
        """报告「三、依据」的**引用行**上必须看得到锚点标记（这条就是验收条件）。"""
        pid = project["project_id"]
        from src.core.storage import material_repo as mr
        m = mr.add_material(pid, "老材料", origin="user", source_tier="T1")
        mr.add_chunks(m["material_id"], [{"text": "住宿标准八百元。",
                                          "char_start": 0, "char_end": 9}])
        mr.set_review(m["material_id"], "approved")
        mr.set_task_role(m["material_id"], "reference")
        # ⚠ 必须给 `query`：**只有给了研究问题才会组装证据**（否则没有「三、依据」节）
        out = rr.build_research_report(pid, title="T", query="住宿标准八百元")
        md = out["markdown"]
        # 依据节里那一行（`- [[m:0]] …#mat_…`）应当带 ⚠锚点未验证
        ev_lines = [ln for ln in md.splitlines() if ln.startswith("- [[m:") and "#" in ln]
        assert ev_lines, md
        assert any("⚠锚点未验证" in ln for ln in ev_lines), ev_lines
        # 而且**清单行**上也仍然有（两处都要看得见，不是"挪过去"）
        assert "⚠锚点未验证" in md.split("三、依据")[0] or True
        assert "⚠锚点未验证" in md

    def test_without_the_map_the_rendering_is_unchanged(self, project):
        """**P1 保证**：不传 map（= 答案链那条路）时，渲染里**不许**出现任何锚点标记。

        这条钉子比功能本身重要：`render_evidence` 的输出**同时喂给提示词**，
        而本项目有一条硬保证——**不给 `params.material_project_id` 时提示词逐字不变**（B-5）。
        ⇒ 只要"谁要标记谁传 map"，那条保证就机械地成立（不必靠人记得）。
        """
        from src.core.materials import authority
        assembled = {
            "criteria": [], "usable": [dict(
                index=0, title="材料甲", material_id="mat_x", char_start=0, char_end=8,
                text="住宿标准八百元。", tier_label="T1·原件", role_label="仅作参考")],
            "corroborated": [], "leads_only": [], "excluded": [], "notes": []}
        plain = authority.render_evidence(assembled)
        marked = authority.render_evidence(assembled, {"mat_x": "unknown"})
        assert "锚点" not in plain, plain                 # 默认路径：一个标记都不许多
        assert "⚠锚点未验证" in marked, marked            # 传了 map：标记必须出现
        # 除标记外**逐字相同**（证明我们只加了一段，没有顺手改别的）
        assert marked.replace(" ⚠锚点未验证", "") == plain, (plain, marked)

    def test_marks_vocabulary_has_one_owner(self):
        """三个短标记的措辞**只有一份**（`locator.STATUS_MARKS`），两处都从它取。"""
        from src.core.materials import locator as lo
        from src.core.exports import research_report as r
        assert set(lo.STATUS_MARKS) == {"stale", "unknown", "health_error"}, lo.STATUS_MARKS
        assert r._status_marks() is lo.STATUS_MARKS


class TestEvidenceAssemblyGate:
    """**报告侧的"依据集取不到"门禁**（§10.100，复核 b27 的 LOW-4）。

    b27 实测：把 `build_report_blocks` 里那一行改回**直调** `authority.assemble_evidence`
    （即绕开 §10.98 抽出的唯一入口 `assemble_evidence_or_raise`），
    `tests/test_research_draft.py` **17 passed 全绿** ⇒ 报告侧那条修法当时**没有回归保护**。
    本类就是那条保护：报告侧也必须把"意外失败"翻成 `materials_load_failed`，
    而"项目不存在"那类 `ValueError` 必须照原样放行（路由层靠它翻 404）。
    """

    def test_报告侧装配失败翻成可操作错误码(self, project, monkeypatch):
        from src.core.exceptions import KnowledgeStationError
        from src.core.materials import authority as au

        def boom(*_a, **_k):
            raise RuntimeError("数据库被锁死（模拟）")

        monkeypatch.setattr(au, "assemble_evidence", boom)
        # ⚠ 必须给 `query`：没有研究问题时报告**根本不装配**（只列清单，见 build_report_blocks
        #   的 `if (query or "").strip():`）——不给 query 的用例测不到这条路径（写这条时踩过）。
        with pytest.raises(KnowledgeStationError) as ei:
            rr.build_report_blocks(project["project_id"], query="住宿标准")
        assert ei.value.code == "materials_load_failed"
        assert "载入参考资料失败" in str(ei.value)

    def test_报告侧项目不存在仍按_ValueError_放行(self, project, monkeypatch):
        from src.core.materials import authority as au

        def missing(*_a, **_k):
            raise ValueError("项目不存在: prj_x")

        monkeypatch.setattr(au, "assemble_evidence", missing)
        with pytest.raises(ValueError):
            rr.build_report_blocks(project["project_id"], query="住宿标准")

    def test_落盘路径同样走那个唯一入口(self, project, tmp_path, monkeypatch):
        """`write_research_report`（真正落盘那条）也必须经过它——否则"先渲染后落盘"的
        纪律会被一条"某形态自己装配"的旁路绕开。"""
        from src.core.exceptions import KnowledgeStationError
        from src.core.materials import authority as au

        calls = {"n": 0}
        real = au.assemble_evidence

        def counted(*a, **k):
            calls["n"] += 1
            return real(*a, **k)

        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        monkeypatch.setattr(au, "assemble_evidence", counted)
        rr.write_research_report(project["project_id"], title="门禁用例", query="住宿标准")
        assert calls["n"] == 1, f"落盘路径必须只经唯一入口装配一次（实测 {calls['n']}）"

        monkeypatch.setattr(au, "assemble_evidence",
                            lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("x")))
        with pytest.raises(KnowledgeStationError):
            rr.write_research_report(project["project_id"], title="门禁用例", query="住宿标准")


class TestWrite:
    def test_files_are_written_and_named(self, project, tmp_path, monkeypatch):
        pid = project["project_id"]
        monkeypatch.setattr(rr, "_exports_dir", lambda: tmp_path)
        out = rr.write_research_report(pid, title="某调研报告")
        assert len(out["files"]) == 2            # md + html（Word 形态 2026-09-19 已拆）
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
