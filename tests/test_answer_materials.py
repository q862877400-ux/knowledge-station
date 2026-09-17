# -*- coding: utf-8 -*-
"""材料进答案链（Phase B 第二步）。

业主的验收句是：**"声明『本项目以公司制度为准』后，答案准绳从国标切到制度；
T3 单独引用被拒"**。本文件测的就是这句话在提示词层成不成立。

三条硬不变量：
  1. **不给项目范围 ⇒ 提示词与没有材料平面之前逐字一致**（回归保证，不是"差不多"）；
  2. 材料作为**另一个平面**追加，`[[m:i]]` 与法条 `[[c:i]]` **不混**；
  3. **未批准材料永远进不了提示词**（评审硬门在答案链上同样成立）。
"""
from __future__ import annotations

import pytest

from src.core.llm import ks_answer as ka
from src.core.materials import authority as au
from src.core.storage import material_repo as mr
from src.core.text_utils import fts_match_expr as mi_fts


@pytest.fixture()
def project(db):
    return mr.create_project("制度测试")


def _add(pid, title, text, *, tier, origin="user", domain=None, role=None,
         review="approved", url=None):
    m = mr.add_material(pid, title, origin=origin, source_tier=tier, domain=domain, url=url)
    mr.add_chunks(m["material_id"], [{"text": text, "char_start": 0,
                                      "char_end": len(text), "page": 1}])
    if role:
        mr.set_task_role(m["material_id"], role)
    mr.set_review(m["material_id"], review)
    return m


_LAW_EV = [{
    "standard_no": "GB 30871-2022", "clause_number": "5.2.3", "page_start": 3,
    "legal_status": "current", "snippet": "动火作业应办理审批手续。",
    "doc_id": "d1", "_clause_key": "k1", "title": "动火作业",
}]


class TestNoScopeIsByteIdentical:
    """**回归保证**：不带项目范围时，提示词一个字都不变。"""

    def test_prompt_unchanged_without_materials(self):
        msgs = ka.build_messages("动火作业怎么分级", _LAW_EV, "default")
        assert ka.MATERIAL_SYSTEM_ADDENDUM not in msgs[0]["content"]
        assert "参考资料" not in msgs[1]["content"]
        # 与显式传 None 完全一致（不是"看起来差不多"）
        assert msgs == ka.build_messages("动火作业怎么分级", _LAW_EV, "default", None)

    def test_none_and_empty_string_are_equivalent(self):
        a = ka.build_messages("q", _LAW_EV, "default", "")
        b = ka.build_messages("q", _LAW_EV, "default", None)
        assert a == b


class TestMaterialsSection:
    def test_materials_appended_as_separate_section(self, project):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", role="criterion")
        text = au.render_evidence(au.assemble_evidence(pid, "住宿标准"))
        msgs = ka.build_messages("住宿标准是多少", _LAW_EV, "default", text)
        user = msgs[1]["content"]
        # 法条一节 + 参考资料另起一节
        assert "证据条款：" in user
        assert "参考资料（**非法规证据**" in user
        assert "住宿标准每晚不超过五百元" in user
        # 序号不混：法条是 [c:0]，材料是 [[m:0]]
        assert "[c:0]" in user and "[[m:0]]" in user
        # system 里带上材料规则
        assert ka.MATERIAL_SYSTEM_ADDENDUM in msgs[0]["content"]

    def test_addendum_carries_criterion_precedence_and_tier_rules(self):
        """规则文本必须真的说了那四件事（**提示词就是产物**，直接断言文字）。"""
        s = ka.MATERIAL_SYSTEM_ADDENDUM
        assert "本任务准则（轴 B）" in s and "优先于法条" in s
        assert "必须显式说明冲突" in s
        assert "不得单独支撑结论" in s and "单一来源，未经互证" in s
        assert "不得用于结论" in s
        # 两个平面不许混
        assert "分属两个平面" in s


class TestCitationMarkers:
    def test_material_marker_does_not_trip_law_index_check(self):
        """`[[m:0]]` 不能被法条越界校验误判（两个平面各有各的编号空间）。"""
        parsed = ka.parse_llm_answer(
            '{"derivation":"按制度 [[m:0]] 应为 500 元。","conclusion":"500 元"}',
            evidence_count=1, material_count=1)
        assert parsed["warnings"] == [], parsed["warnings"]

    def test_out_of_range_material_marker_is_flagged(self):
        parsed = ka.parse_llm_answer(
            '{"derivation":"见 [[m:7]]。","conclusion":"x"}',
            evidence_count=1, material_count=1)
        assert any("[[m:7]] 越界" in w for w in parsed["warnings"]), parsed["warnings"]

    def test_imagined_material_marker_is_flagged_when_no_materials(self):
        """**没给材料却引材料** = 凭想象引用，必须报出来（默认参数下同样成立）。"""
        parsed = ka.parse_llm_answer('{"derivation":"见 [[m:0]]。","conclusion":"x"}',
                                     evidence_count=1)
        assert any("material_count=0" in w for w in parsed["warnings"]), parsed["warnings"]

    def test_law_marker_still_checked(self):
        parsed = ka.parse_llm_answer('{"derivation":"见 [[c:5]]。","conclusion":"x"}',
                                     evidence_count=1)
        assert any("[[c:5]] 越界" in w for w in parsed["warnings"])

    @pytest.mark.parametrize("marker,expect", [
        ("[[m:-1]]", "[[m:-1]] 越界"),
        ("[[c:-1]]", "[[c:-1]] 越界"),
    ])
    def test_negative_indices_are_flagged(self, marker, expect):
        """**负数越界必须被抓**（独立复核 2026-09-17 报的缺陷）。

        旧正则 `\\d+` 匹配不到 `-1`，于是 `[[m:-1]]` 既不算标记、也不会被越界校验抓到
        （`i < 0` 那条分支是**死代码**）。
        """
        parsed = ka.parse_llm_answer(f'{{"derivation":"见 {marker}。","conclusion":"x"}}',
                                     evidence_count=3, material_count=3)
        assert any(expect in w for w in parsed["warnings"]), parsed["warnings"]

    def test_conclusion_is_scanned_too(self):
        """**结论区也要扫**：规则 1 要求"每条结论后紧跟引用标记"，而旧实现只扫推导区。

        独立复核实测：越界标记只写在 conclusion 里时 `warnings == []` ——
        **最该被检查的位置反而没查**。
        """
        parsed = ka.parse_llm_answer(
            '{"derivation":"没有标记","conclusion":"按参考资料 [[m:0]] 应为 500 元"}',
            evidence_count=1, material_count=0)
        assert any("material_count=0" in w for w in parsed["warnings"]), parsed["warnings"]


class TestAnswerIntegration:
    """端到端（LLM 用假生成器）：范围 → 取材料 → 进提示词 → 记录可审计。"""

    def _stub_llm(self, monkeypatch, captured: dict):
        def fake_stream(messages, **_kw):
            captured["messages"] = messages
            yield '{"derivation":"按项目制度 [[m:0]]（系统提示见规则 8）。","conclusion":"以制度为准"}'
        monkeypatch.setattr(ka, "_stream_llm", fake_stream)

    def test_scoped_answer_injects_materials_and_records_usage(self, project, monkeypatch):
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", role="criterion")
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)

        out = ka.answer("住宿标准是多少", params={"material_project_id": pid})
        # ① 材料真的进了提示词
        assert "住宿标准每晚不超过五百元" in cap["messages"][1]["content"]
        assert ka.MATERIAL_SYSTEM_ADDENDUM in cap["messages"][0]["content"]
        # ② 记录可审计
        mu = out["material_usage"]
        assert mu["project_id"] == pid and mu["counts"]["criteria"] == 1
        assert mu["usable_indices"] == [0]
        assert mu["project_found"] is True
        # ③ notes 如实（且**不**越权断言"结论已依据制度"）
        assert any("【参考资料】" in n for n in out["notes"])
        # ④ _meta 里也留痕
        assert out["_meta"]["material_project_id"] == pid
        assert out["_meta"]["material_total"] == 1

    def test_unscoped_answer_has_no_material_usage(self, monkeypatch):
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)
        out = ka.answer("动火作业怎么分级")
        assert out["material_usage"] is None
        assert out["_meta"]["material_project_id"] is None
        assert "参考资料" not in cap["messages"][1]["content"]
        assert not any("【参考资料】" in n for n in out["notes"])

    def test_unapproved_material_never_reaches_prompt(self, project, monkeypatch):
        """**评审硬门在答案链上同样成立**：pending 材料的正文不得出现在提示词里。"""
        pid = project["project_id"]
        _add(pid, "未审稿", "绝密未审内容XYZ", tier="T1", review="pending")
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)
        out = ka.answer("绝密", params={"material_project_id": pid})
        assert "绝密未审内容XYZ" not in cap["messages"][1]["content"]
        assert out["material_usage"]["counts"]["total"] == 0

    def test_unknown_project_is_reported_as_not_found(self, monkeypatch):
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)
        out = ka.answer("住宿标准", params={"material_project_id": "prj_不存在"})
        mu = out["material_usage"]
        assert mu["project_found"] is False
        assert any("不存在" in n for n in out["notes"]), out["notes"]

    def test_t3_lead_only_is_labelled_in_prompt(self, project, monkeypatch):
        """**业主验收点的后半句**：单独一条二手转述必须以"仅线索"进提示词，不得当依据。"""
        pid = project["project_id"]
        _add(pid, "某论坛帖", "住宿标准据说每晚八百元", tier="T3", domain="bbs.example")
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)
        out = ka.answer("住宿标准", params={"material_project_id": pid})
        user = cap["messages"][1]["content"]
        assert "仅供参考的线索（单一来源，未用于支撑结论）" in user
        assert "可作依据的材料" not in user
        assert out["material_usage"]["counts"]["leads_only"] == 1
        assert out["material_usage"]["usable_indices"] == []      # 承重集合为空

    def test_material_load_failure_is_not_silent(self, project, monkeypatch):
        """材料取不到时必须说出来——否则会产出一份"看着正常、其实没用上制度"的答案。"""
        pid = project["project_id"]

        def boom(*_a, **_k):
            raise RuntimeError("磁盘读失败（模拟）")

        monkeypatch.setattr(au, "assemble_evidence", boom)
        cap: dict = {}
        self._stub_llm(monkeypatch, cap)
        out = ka.answer("住宿标准", params={"material_project_id": pid})
        assert out["material_usage"]["error"]
        assert any("载入失败" in n for n in out["notes"]), out["notes"]
        assert "参考资料" not in cap["messages"][1]["content"]


class TestNaturalLanguageRecall:
    """**我的答案链测试自己抓出来的检索缺陷**（2026-09-17）：

    `search_materials` 原先把分词结果**裸**传给 FTS5 MATCH ⇒
      ① 隐式 AND："住宿标准是多少"搜不到含"住宿标准…"的材料（自然语言提问基本失效）；
      ② 标点触发语法错误并被兜底 except 吞成"没有命中"：
         `'GB 30871-2022'` → `no such column: 2022`；`'5.2.3'` → `syntax error near "."`。
    根因是**同一个机制被写了两份**、而材料侧那份更差（法条侧 `_fts_query` 早就
    加引号 + 剥标点 + OR）。现共用 `text_utils.fts_match_expr`。
    """

    @pytest.fixture()
    def seeded(self, project):
        pid = project["project_id"]
        m = mr.add_material(pid, "公司制度")
        mr.add_chunks(m["material_id"], [
            {"text": "住宿标准每晚不超过五百元", "char_start": 0, "char_end": 12, "page": 1},
            {"text": "动火作业应办理审批 GB 30871-2022 第5.2.3条", "char_start": 13,
             "char_end": 43, "page": 1},
        ])
        mr.set_review(m["material_id"], "approved")
        return pid

    def test_natural_language_question_matches(self, seeded):
        """**最关键的一条**：用户用自然语言提问，必须能命中材料。"""
        assert mr.search_materials(seeded, "住宿标准是多少"), \
            "自然语言提问搜不到材料 ⇒ 材料平面对用户等于不可用"
        assert mr.search_materials(seeded, "报销标准是多少")

    def test_standard_number_query_does_not_silently_fail(self, seeded):
        """带连字符的标准号不再触发 FTS 语法错误后静默空结果。"""
        hits = mr.search_materials(seeded, "GB 30871-2022")
        assert hits, "标准号查询静默无命中（旧实现会报 no such column: 2022 后被吞）"

    def test_expression_builder_quotes_every_term(self):
        """每个词都加引号 ⇒ 标点不可能被当 FTS 语法。"""
        expr = mi_fts("GB 30871-2022")
        assert expr and all(p.startswith('"') and p.endswith('"') for p in expr.split(" OR ")), expr
        assert "-" not in expr.split(" OR ")[0]

    def test_expression_uses_or_not_implicit_and(self):
        expr = mi_fts("住宿标准是多少")
        assert " OR " in expr, f"隐式 AND 会让自然语言提问 0 命中: {expr}"

    def test_known_limit_all_single_char_query(self, seeded):
        """**已知边界（钉住，别当 bug 反复"修"）**：全单字符词的查询无 FTS 表达式。

        `5.2.3` 分词只剩 `5`/`2`/`3`，构造器按设计丢弃单字符词 ⇒ 空表达式 ⇒ 无命中。
        法条侧靠"精确条款号通道"覆盖这类查询，材料侧**暂无**对应通道。
        这里钉住的是：它**安静地返回空**（不抛、不 500），且我们**知道**这是边界。
        """
        assert mi_fts("5.2.3") == ""
        assert mr.search_materials(seeded, "5.2.3") == []


class TestFtsMatchExprIsTheSingleOwner:
    """`fts_match_expr` 必须与法条侧迁走前的旧实现**逐字等价**（迁移不改行为）。"""

    #: 旧 `hybrid_engine._fts_query` 的算法（迁移前的实现，作为参照保留）。
    @staticmethod
    def _old_ref(text: str) -> str:
        import re as _re
        from src.core.text_utils import segment_for_fts
        words = [w for w in segment_for_fts(text).split() if len(w) > 1]
        quoted = []
        for w in words:
            for tok in _re.sub(r"[^\w\u4e00-\u9fff]", " ", w).split():
                if len(tok) > 1:
                    quoted.append(f'"{tok}"')
        return " OR ".join(quoted)

    @pytest.mark.parametrize("text", [
        "动火作业怎么分级", "GB 30871-2022", "5.2.3", "住宿标准是多少", "的", " ", "",
        "聚丙烯(PP)树脂", "额定电压1kV(Um=1.2kV)", "abc", "a b", "《安全生产法》第96条",
        "应符合GB/T 1234-2020的规定", "100%", "A-B_C", "①②③",
    ])
    def test_matches_old_law_side_implementation(self, text):
        from src.core.text_utils import fts_match_expr
        assert fts_match_expr(text) == self._old_ref(text), f"迁移改变了行为: {text!r}"

    def test_law_side_delegates_to_the_owner(self):
        from src.core.retrieval.hybrid_engine import _fts_query
        from src.core.text_utils import fts_match_expr
        assert _fts_query("动火作业怎么分级") == fts_match_expr("动火作业怎么分级")

    def test_duplicate_query_side_tokenizer_is_gone(self):
        """verifier 报的"第三份查询侧分词实现"已随迁移**删除**（不是只记一笔）。"""
        from src.core.retrieval import hybrid_engine
        assert not hasattr(hybrid_engine, "_seg"), \
            "hybrid_engine._seg 应已删除：它是一份行为不同的查询侧分词，正是分叉源"

