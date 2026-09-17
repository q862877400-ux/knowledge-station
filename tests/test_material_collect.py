# -*- coding: utf-8 -*-
"""自采入口测试（`src/core/materials/collect.py`，Phase C 第一步）。

这一组测试守的是**一条结构性约束**：自采**不能**绕开评审。
所以断言不是"函数能用"，而是：
  · 采集进来的**一律 pending**（本模块连设置它的参数都没有）；
  · 默认 **ephemeral**（业主裁定：其它资料默认当前任务一次性）；
  · 来源（url/domain）**留痕**，否则就是"身份未知"（按 authority 的纪律不能互证）；
  · 内容完全相同 → **不新建**（判重）；内容近似 → 登记但**标注**给人看；
  · 疑似标准正文 → 只**记录** Track L 意图，**不在采集路径上入库**。
"""
from __future__ import annotations

import pytest

from src.core.materials import collect as co
from src.core.storage import material_repo as mr


@pytest.fixture()
def project(db):
    return mr.create_project("采集测试")


_ARTICLE = (
    "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。"
    "该标准由财务部门负责解释，各单位不得自行调整。"
)


def _review_violations(source: str) -> list[str]:
    """在源码里找"能设置评审状态"的代码路径（AST，不看注释/docstring）。

    抽成模块级函数是为了**能自测**：下面既断言真实模块干净，也断言本检测器
    在一个**故意违规**的片段上确实会报出来——否则这条"结构性约束"可能是空转的。
    """
    import ast
    offenders: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Attribute) and node.attr == "set_review":
            offenders.append("set_review()")
        if isinstance(node, ast.Name) and node.id == "set_review":
            offenders.append("set_review")
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in ("review_status", "review", "approved"):
                    offenders.append(f"kwarg {kw.arg}=")
    return offenders


class TestAlwaysPendingAndEphemeral:
    def test_collected_material_is_pending(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="某报道", text=_ARTICLE,
                            url="https://news.example/a/1")
        assert m["review_status"] == "pending", "自采**绝不能**自动批准"
        assert m["origin"] == "collected"

    def test_collected_material_never_enters_retrieval_before_review(self, project):
        """硬门在采集路径上同样成立：未批准 → 搜不到。"""
        pid = project["project_id"]
        co.collect_text(pid, title="某报道", text=_ARTICLE, url="https://news.example/a/1")
        assert mr.search_materials(pid, "住宿标准") == []
        assert mr.approved_materials(pid) == []

    def test_default_lifecycle_is_ephemeral(self, project):
        """业主裁定：其它资料默认**当前任务一次性**；升为长期是**用户**的动作。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="一次性的", text=_ARTICLE, url="https://a.example/1")
        assert m["lifecycle"] == "ephemeral"

    def test_module_exposes_no_way_to_approve(self):
        """**结构性约束**：本模块不得提供任何能设置评审状态的**代码路径**。

        这条是防"以后有人为了省事加一个 auto_approve 参数"——
        那等于把方案 §6 的硬门从采集路径上拆掉。

        ⚠ 必须走 **AST**、不能搜源码文本：模块 docstring 里**正当地**提到了
        `material.review_status='pending'`（讲清楚纪律），文本搜索会把说明文字当成违规
        （本测试第一版就是这么假红的）。
        """
        import inspect
        assert _review_violations(inspect.getsource(co)) == [], "采集路径不得触碰评审状态"
        sig = inspect.signature(co.collect_text)
        assert not any("review" in p for p in sig.parameters), \
            "collect_text 不得收评审相关参数"

    def test_the_structural_detector_itself_works(self):
        """**检测器的自测**：否则上面那条"结构性约束"可能是空转的。

        用一个**故意违规**的片段证明它真的会报；再证明它**不会**因为注释里提到
        `review_status` 就误报（本测试第一版就是文本搜索，被自己的 docstring 弄假红了）。
        """
        assert _review_violations(
            "def f(p, m):\n    m.set_review(p, 'approved')\n") != []
        assert _review_violations(
            "def f(p, m):\n    m.add_material(p, review_status='approved')\n") != []
        assert _review_violations(
            '"""说到 review_status 和 set_review 的说明文字不算违规。"""\n'
            "def f(p, m):\n    m.add_material(p)\n") == []


class TestSourceProvenance:
    def test_url_is_recorded_and_domain_extracted(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="有出处", text=_ARTICLE,
                            url="https://news.example/a/1?x=2")
        assert m["url"] == "https://news.example/a/1?x=2"
        assert m["domain"] == "news.example"

    def test_no_url_means_unknown_identity(self, project):
        """没有 url/domain ⇒ 身份未知 ⇒ 按 authority 的纪律**不能互证**。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="无出处", text=_ARTICLE)
        assert m["domain"] is None
        assert m["url"] is None

    def test_collected_defaults_to_T3_not_trusted(self, project):
        """不给层级时"网上找来的"从 T3 起——**默认不可信，靠证据升级**。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="某帖", text=_ARTICLE, url="https://bbs.example/1")
        assert m["source_tier"] == "T3"

    def test_caller_can_set_a_higher_tier_with_evidence(self, project):
        """调用方有证据时可以给更高层级（判据是"有没有证据"，不是"谁采的"）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="监管公告", text=_ARTICLE,
                            url="https://csrc.gov.cn/x", source_tier="T2")
        assert m["source_tier"] == "T2"

    def test_note_lands_in_tier_reason_for_the_reviewer(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="x", text=_ARTICLE, url="https://a.example/1",
                            note="按用户要求检索「住宿标准」时采集")
        assert "按用户要求检索" in (m["tier_reason"] or "")


class TestDeduplication:
    def test_identical_text_is_not_registered_twice(self, project):
        pid = project["project_id"]
        first = co.collect_text(pid, title="原发", text=_ARTICLE, url="https://a.example/1")
        second = co.collect_text(pid, title="转载", text=_ARTICLE, url="https://b.example/1")
        assert second["duplicate"] is True
        assert second["material_id"] == first["material_id"]
        assert len(mr.list_materials(pid)) == 1, "同一正文只该有一条材料"

    def test_near_duplicate_is_registered_but_flagged(self, project):
        """近似（改了标点）**仍然登记**，但标注 `near_duplicate_of` 给评审人看。

        为什么不直接丢掉：丢掉了评审人就永远看不到"疑似同稿"，
        而"要不要采信"是**人**的判断（我们只负责把事实摆出来）。
        """
        pid = project["project_id"]
        first = co.collect_text(pid, title="原发", text=_ARTICLE, url="https://a.example/1")
        variant = _ARTICLE.replace("，", "  ").replace("。", "！")
        second = co.collect_text(pid, title="转载", text=variant, url="https://b.example/1")
        assert second.get("duplicate") is False
        assert second["near_duplicate_of"] == [first["material_id"]]
        assert "同稿" in (second["tier_reason"] or "")
        assert len(mr.list_materials(pid)) == 2

    def test_different_articles_are_not_flagged(self, project):
        pid = project["project_id"]
        co.collect_text(pid, title="甲", text=_ARTICLE, url="https://a.example/1")
        other = ("有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效，"
                 "各单位应提前做好预算安排。")
        second = co.collect_text(pid, title="乙", text=other, url="https://b.example/1")
        assert second["near_duplicate_of"] == []
        assert second.get("duplicate") is False


class TestTrackL:
    def test_standard_text_is_recognised_and_only_recorded(self, project):
        """认出疑似标准正文 ⇒ 只**记录意图**，不在采集路径上入库（入库在评审通过之后）。"""
        pid = project["project_id"]
        body = ("GB 30871-2022 危险化学品企业特殊作业安全规范\n"
                "5.2.3 动火作业应办理作业审批手续，作业前应进行风险分析。" * 3)
        # ⚠ 断言**前后差值**，不能断言"doc_meta 是空的"：那是**全局**条件，
        # 而套件里别的测试可能已经往 doc_meta 写过东西（本断言第一版就是这么假红的
        # ——单跑绿、全量红）。要测的性质是"**这次调用**没有写 doc_meta"。
        from src.core.storage.sqlite_db import get_db_connection
        before = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        m = co.collect_text(pid, title="GB 30871-2022 危险化学品企业特殊作业安全规范",
                            text=body, url="https://openstd.example/gb30871")
        after = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        assert after == before, "采集路径不得写 doc_meta（Track L 入库是评审通过后的事）"
        assert m["track_l"] is not None
        assert m["track_l"]["standard_no"] == "GB30871-2022"
        assert m["track_l"]["status"] == "pending_review"
        assert m["kind"] == "legal"
        assert "Track L" in (m["tier_reason"] or "")

    def test_non_standard_text_is_other(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="行业观察", text=_ARTICLE, url="https://a.example/1")
        assert m["track_l"] is None
        assert m["kind"] == "other"

    def test_caller_can_override_kind(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="x", text=_ARTICLE, url="https://a.example/1",
                            kind="legal")
        assert m["kind"] == "legal"


class TestInputValidation:
    def test_blank_title_is_refused(self, project):
        with pytest.raises(ValueError, match="title"):
            co.collect_text(project["project_id"], title="   ", text=_ARTICLE)

    def test_blank_text_is_refused(self, project):
        """没有正文的采集件不该登记——那会让评审人对着空白"批准"（盲签）。"""
        with pytest.raises(ValueError, match="text"):
            co.collect_text(project["project_id"], title="x", text="   \n  ")

    def test_chunks_keep_the_fidelity_invariant(self, project):
        """采集件的切片也要满足**逐字取回**（引用点回原文的地基）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="x", text=_ARTICLE, url="https://a.example/1")
        pages = [(1, _ARTICLE)]
        canonical, spans = __import__(
            "src.core.ingestion.material_ingest", fromlist=["x"]).build_document(pages)
        for c in mr.material_chunks(m["material_id"]):
            assert canonical[c["char_start"]:c["char_end"]] == c["text"]

    def test_bad_max_chars_is_refused_by_the_shared_guard(self, project):
        """`max_chars` 的校验只有一处所有者（`material_ingest`），采集路径也要吃到它。"""
        with pytest.raises(ValueError, match="max_chars"):
            co.collect_text(project["project_id"], title="x", text=_ARTICLE, max_chars=0)


class TestDomainHelper:
    @pytest.mark.parametrize("url,expect", [
        ("https://news.example/a/1?x=2", "news.example"),
        ("http://sub.news.example:8080/p", "sub.news.example"),
        ("https://www.a.com", "www.a.com"),          # 归一化在判据层，这里存原样 host
        ("not a url", None),
        (None, None),
        ("", None),
    ])
    def test_domain_of(self, url, expect):
        assert co.domain_of(url) == expect
