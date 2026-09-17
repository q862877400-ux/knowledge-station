# -*- coding: utf-8 -*-
"""材料权威性纪律测试（Phase B 第一步）。

这里测的是**业主最在意的那件事**："不是随便找个什么网络文章就当权威信源"。
所以断言都围绕"**谁被允许承重**"，而不是"标签对不对"：
  · T4 一律**不得**出现在可承重集合里；
  · 单一来源的 T3 **只能当线索**，不得支撑结论；
  · ≥2 个**独立来源**（按域名）才把 T3 升为"辅证"；
  · 同一域名转载多篇**不算**互证（最常见的假互证）；
  · 轴 B 的 `criterion` 单列，且**不因来源层级低而被降级**（公司制度例）。
"""
from __future__ import annotations

import pytest

from src.core.materials import authority as au
from src.core.storage import material_repo as mr


@pytest.fixture()
def project(db):
    return mr.create_project("权威性测试")


def _add(pid, title, text, *, tier, origin="collected", domain=None, role=None,
         review="approved", url=None):
    m = mr.add_material(pid, title, origin=origin, source_tier=tier, domain=domain,
                        url=url)
    mr.add_chunks(m["material_id"], [{"text": text, "char_start": 0,
                                      "char_end": len(text), "page": 1}])
    if role:
        mr.set_task_role(m["material_id"], role)
    mr.set_review(m["material_id"], review)
    return m


class TestBehaviourTable:
    def test_every_tier_has_a_behaviour(self):
        assert set(au.TIER_BEHAVIOUR) == set(mr.TIERS)

    def test_t4_is_excluded_t3_needs_corroboration(self):
        assert au.TIER_BEHAVIOUR["T4"] == "excluded"
        assert au.TIER_BEHAVIOUR["T3"] == "needs_corroboration"
        for t in ("T0", "T1", "T2"):
            assert au.TIER_BEHAVIOUR[t] == "usable"


class TestRules:
    def test_t0_t1_t2_are_usable(self, project):
        pid = project["project_id"]
        _add(pid, "官方原文", "营业收入一百亿元", tier="T0", origin="user")
        _add(pid, "公司年报", "营业收入一百亿元", tier="T1", origin="user")
        _add(pid, "监管公告", "营业收入一百亿元", tier="T2", domain="csrc.gov.cn")
        a = au.assemble_evidence(pid, "营业收入")
        assert len(a["usable"]) == 3
        assert a["leads_only"] == [] and a["excluded"] == []

    def test_single_source_t3_is_LEAD_ONLY(self, project):
        """**核心纪律**：一篇网络文章**不得**支撑结论。"""
        pid = project["project_id"]
        _add(pid, "某论坛帖", "营业收入一百亿元", tier="T3", domain="bbs.example.com")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["counts"]["leads_only"] == 1
        assert a["usable"] == [] and a["corroborated"] == []
        # 安全入口里**不能**有它
        assert au.usable_hits(a) == []
        assert any("未用于支撑结论" in n for n in a["notes"])

    def test_two_independent_domains_promote_t3_to_corroborated(self, project):
        pid = project["project_id"]
        _add(pid, "媒体A", "营业收入一百亿元", tier="T3", domain="a-news.com")
        _add(pid, "媒体B", "营业收入一百亿元", tier="T3", domain="b-news.com")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["counts"]["corroborated"] == 2
        assert len(au.usable_hits(a)) == 2          # 可作**辅证**
        assert all(h["behaviour_label"] == au.BEHAVIOUR_LABELS["corroborated"]
                   for h in a["corroborated"])

    def test_same_domain_twice_is_NOT_corroboration(self, project):
        """**最常见的假互证**：同一站点转载两篇，只有一个来源。"""
        pid = project["project_id"]
        _add(pid, "转载1", "营业收入一百亿元", tier="T3", domain="same-site.com")
        _add(pid, "转载2", "营业收入一百亿元", tier="T3", domain="same-site.com")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["corroborated"] == []
        assert a["counts"]["leads_only"] == 2       # 仍只是线索
        assert au.usable_hits(a) == []

    def test_t4_never_usable_and_is_disclosed(self, project):
        pid = project["project_id"]
        _add(pid, "匿名帖", "营业收入一百亿元", tier="T4", domain="unknown.example")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["counts"]["excluded"] == 1
        assert au.usable_hits(a) == []
        # 如实列出（不假装它不存在），并说明为什么排除
        assert len(a["excluded"]) == 1
        assert any("不可回溯" in n for n in a["notes"])

    def test_t4_with_many_sources_still_excluded(self, project):
        """T4 **多源也不放行**——"不可回溯"是来源性质问题，不是数量问题。"""
        pid = project["project_id"]
        for i in range(3):
            _add(pid, f"匿名{i}", "营业收入一百亿元", tier="T4", domain=f"x{i}.example")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["counts"]["excluded"] == 3 and au.usable_hits(a) == []

    def test_criterion_is_listed_and_not_downgraded_by_tier(self, project):
        """公司制度例（轴 B 独立于轴 A）：来源层级低，但**是本任务的准绳**。"""
        pid = project["project_id"]
        _add(pid, "公司差旅制度", "住宿标准每晚不超过五百元", tier="T1", origin="user",
             role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["criteria"] == 1
        assert a["usable"] == []                    # 单列在 criteria，不重复计入 usable
        assert au.usable_hits(a)[0]["task_role"] == "criterion"
        assert any("本任务准则" in n for n in a["notes"])

    def test_criterion_t3_single_source_still_governs(self, project):
        """用户把一份二手转述**指定为准绳**时，轴 B 优先——但标注仍说实话（T3）。"""
        pid = project["project_id"]
        _add(pid, "某转载的制度", "住宿标准每晚不超过五百元", tier="T3",
             domain="repost.example", role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["criteria"] == 1
        assert a["criteria"][0]["source_tier"] == "T3"      # 标注不撒谎
        assert a["criteria"][0]["role_label"] == "本任务准则"

    def test_unapproved_material_never_reaches_assembly(self, project):
        """评审硬门在检索层就已经挡住 ⇒ 装配层看不到未批准材料（这里再确认一次）。"""
        pid = project["project_id"]
        _add(pid, "待批的官方原文", "营业收入一百亿元", tier="T0", origin="user",
             review="pending")
        a = au.assemble_evidence(pid, "营业收入")
        assert a["counts"]["total"] == 0
        assert any("没有命中" in n for n in a["notes"])

    def test_no_hits_yields_honest_note(self, project):
        a = au.assemble_evidence(project["project_id"], "不存在的词")
        assert a["counts"]["total"] == 0
        assert any("不得建立在材料之上" in n for n in a["notes"])


class TestRendering:
    def test_render_carries_both_axes_and_a_locator(self, project):
        pid = project["project_id"]
        m = _add(pid, "公司年报", "营业收入一百亿元", tier="T1", origin="user")
        a = au.assemble_evidence(pid, "营业收入")
        text = au.render_evidence(a)
        h = a["usable"][0]
        # 标注（**两个轴**）与可点回的位置都要在
        assert h["tier_label"] in text
        assert h["role_label"] in text          # 未声明 task_role 时是「未声明效力」——如实
        assert f"{m['material_id']}@{h['char_start']}-{h['char_end']}" in text
        assert "第1页" in text
        assert "营业收入一百亿元" in text

    def test_render_shows_declared_role_label(self, project):
        """声明了轴 B 之后，渲染里出现的是「本任务准则」而不是「未声明效力」。"""
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚不超过五百元", tier="T1", origin="user",
             role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        text = au.render_evidence(a)
        assert "本任务准则" in text
        assert "本任务准则（轴 B：以它为准绳）" in text

    def test_render_shows_lead_only_section_separately(self, project):
        pid = project["project_id"]
        _add(pid, "某帖", "营业收入一百亿元", tier="T3", domain="one.example")
        text = au.render_evidence(au.assemble_evidence(pid, "营业收入"))
        assert "仅供参考的线索" in text
        assert "可作依据的材料" not in text          # 没有可作依据的就不该出现该节

    def test_render_includes_excluded_section(self, project):
        pid = project["project_id"]
        _add(pid, "匿名", "营业收入一百亿元", tier="T4", domain="anon.example")
        text = au.render_evidence(au.assemble_evidence(pid, "营业收入"))
        assert "已知不可用" in text


class TestNoSingleScoreSorting:
    def test_module_exposes_no_tier_sorting_helper(self):
        """**两轴不可压成一个分数**：本模块不得提供"按层级/综合分排序材料"的函数。

        这条是**结构性约束**（业主裁定"用户可以改层级 + 制度是准则"）：一旦有了单一排序，
        公司制度就会被国标压到后面，正是要避免的错误。
        """
        offenders = [n for n in dir(au)
                     if n.startswith("sort") or "rank" in n.lower() or "score" in n.lower()]
        assert offenders == [], f"不应存在按分数排序材料的 API: {offenders}"


class TestCitationIndices:
    """`[[m:i]]` 编号：模型的引用标记靠它，编号一漂移引用就全指错 ⇒ 钉死。"""

    def test_indices_are_contiguous_across_groups_in_group_order(self, project):
        pid = project["project_id"]
        _add(pid, "制度", "住宿标准每晚不超过五百元", tier="T1", origin="user", role="criterion")
        _add(pid, "年报", "住宿标准每晚不超过五百元", tier="T1", origin="user")
        _add(pid, "媒体A", "住宿标准每晚不超过五百元", tier="T3", domain="a.example")
        _add(pid, "媒体B", "住宿标准每晚不超过五百元", tier="T3", domain="b.example")
        _add(pid, "匿名", "住宿标准每晚不超过五百元", tier="T4", domain="anon.example")
        _add(pid, "某帖", "住宿标准每晚不超过五百元", tier="T3", domain="solo.example")
        a = au.assemble_evidence(pid, "住宿标准", limit=20)

        # 组内顺序 = GROUP_ORDER，编号跨组连续从 0 起
        seq = [h["index"] for key, _t in au.GROUP_ORDER for h in a[key]]
        assert seq == list(range(len(seq))), seq
        # 且**每个**命中都有编号（含 leads_only / excluded——它们也可能被引用）
        assert all("index" in h for key, _t in au.GROUP_ORDER for h in a[key])
        assert a["counts"]["total"] == len(seq)

    def test_render_marks_every_hit_with_its_index(self, project):
        pid = project["project_id"]
        _add(pid, "年报", "营业收入一百亿元", tier="T1", origin="user")
        _add(pid, "匿名", "营业收入一百亿元", tier="T4", domain="anon.example")
        a = au.assemble_evidence(pid, "营业收入")
        text = au.render_evidence(a)
        for key, _t in au.GROUP_ORDER:
            for h in a[key]:
                assert f"[[m:{h['index']}]]" in text, (key, h["index"])
        assert "[[m:0]]" in text and "[[m:1]]" in text

    def test_index_matches_usable_hits_order(self, project):
        """`usable_hits()` 的返回顺序必须与编号一致（下游按它拼引用，不一致就错位）。"""
        pid = project["project_id"]
        _add(pid, "制度", "住宿标准", tier="T1", origin="user", role="criterion")
        _add(pid, "年报", "住宿标准", tier="T1", origin="user")
        a = au.assemble_evidence(pid, "住宿标准")
        assert [h["index"] for h in au.usable_hits(a)] == [0, 1]
