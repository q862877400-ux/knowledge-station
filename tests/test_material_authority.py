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
        # ⚠ **必须是两篇措辞不同的报道**：内容近似会被判成"同一篇稿子"而合并成一个来源
        # （见 TestSameStoryIsNotIndependentSources）。测"独立来源"就得让它们真的独立。
        _add(pid, "媒体A", "据当地通报，住宿标准每晚不超过八百元，自下月起执行。",
             tier="T3", domain="a-news.com")
        _add(pid, "媒体B", "有关部门答复称，住宿费用上限调整为八百元一晚。",
             tier="T3", domain="b-news.com")
        a = au.assemble_evidence(pid, "住宿标准")
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


class TestT4BeatsAxisB:
    """**T4 优先于轴 B**（独立复核 2026-09-17 报的 MEDIUM）。

    旧实现先判 `task_role=='criterion'`，于是 T4+准则落进 `criteria`、进 `usable_hits()`，
    而提示词规则 8 说"本任务准则**优先于法条**"——一篇匿名内容农场的帖子就能压过国标。
    """

    def test_t4_declared_criterion_is_NOT_load_bearing(self, project):
        pid = project["project_id"]
        _add(pid, "匿名帖", "住宿标准每晚八百元", tier="T4", domain="anon.example",
             role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["criteria"] == 0, "T4 不得按准则承重"
        assert a["counts"]["excluded"] == 1
        assert au.usable_hits(a) == [], "T4 绝不可进入承重集合"
        assert a["excluded"][0].get("criterion_blocked_by_tier") is True

    def test_t4_criterion_is_visibly_marked_in_both_notes_and_text(self, project):
        pid = project["project_id"]
        _add(pid, "匿名帖", "住宿标准每晚八百元", tier="T4", domain="anon.example",
             role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        text = au.render_evidence(a)
        # 行内标记：模型不能只看到「本任务准则」+ 规则 8 就照办
        assert "未按准则承重" in text
        assert "已知不可用" in text
        # notes 里也要说清"不是悄悄推翻你的声明"
        assert any("未按准则承重" in n for n in a["notes"]), a["notes"]

    def test_t3_criterion_still_governs(self, project):
        """轴 B 的**正常**用法不能被上一条误伤：T3 单一来源当准则仍然算准则。"""
        pid = project["project_id"]
        _add(pid, "公司制度摘录", "住宿标准每晚五百元", tier="T3", domain="x.example",
             role="criterion")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["criteria"] == 1
        assert a["criteria"][0]["index"] in [h["index"] for h in au.usable_hits(a)]


class TestCorroborationIsFalsifiable:
    """**身份未知不能互证**（独立复核 2026-09-17 报的 MEDIUM）。

    旧口径在无域名/URL 时退到 `material:<id>`，而生产代码**从不设置** domain/url
    ⇒ "任意两份材料都算两个独立来源"，把核心纪律变成不可证伪的装饰：
    实测同一篇文章的两份副本被报成「**2 个独立来源**互证」。
    """

    def test_two_copies_without_any_source_identity_do_NOT_corroborate(self, project):
        pid = project["project_id"]
        # 两份内容几乎相同的 T3，都没有 domain/url（= 现实里所有本地上传材料的样子）
        _add(pid, "文章A", "住宿标准每晚八百元", tier="T3")
        _add(pid, "文章B", "住宿标准每晚八百元。", tier="T3")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 0, "身份未知者不得互证"
        assert a["counts"]["leads_only"] == 2
        assert au.usable_hits(a) == []
        assert any("不能互证" in n for n in a["notes"]), a["notes"]

    def test_url_provides_identity_so_two_domains_corroborate(self, project):
        pid = project["project_id"]
        _add(pid, "媒体A", "据通报，住宿标准每晚不超过八百元，自下月起执行。",
             tier="T3", url="https://a-news.com/x/1")
        _add(pid, "媒体B", "有关部门答复称，住宿费用上限调整为八百元一晚。",
             tier="T3", url="http://b-news.com/y?z=1")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 2
        assert len(au.usable_hits(a)) == 2

    def test_url_identity_normalizes_scheme_www_and_case(self, project):
        """`A.COM` / `www.a.com` / `http://a.com` 是**同一个**来源（旧口径算 3 个）。"""
        pid = project["project_id"]
        _add(pid, "A1", "住宿标准每晚八百元", tier="T3", domain="A.COM")
        _add(pid, "A2", "住宿标准每晚八百元", tier="T3", domain="www.a.com")
        _add(pid, "A3", "住宿标准每晚八百元", tier="T3", url="http://a.com/p?q=1")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 0, "同一域名的三种写法不是三个来源"
        assert a["counts"]["leads_only"] == 3

    def test_unknown_identity_does_not_drag_down_known_corroboration(self, project):
        """混合场景：两个已知域名互证 ⇒ 那两条升为辅证；身份未知的那条仍只是线索。"""
        pid = project["project_id"]
        _add(pid, "媒体A", "据通报，住宿标准每晚不超过八百元，自下月起执行。",
             tier="T3", domain="a-news.com")
        _add(pid, "媒体B", "有关部门答复称，住宿费用上限调整为八百元一晚。",
             tier="T3", domain="b-news.com")
        _add(pid, "无出处", "住宿标准每晚八百元", tier="T3")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 2
        assert a["counts"]["leads_only"] == 1
        assert len(au.usable_hits(a)) == 2


class TestSameStoryIsNotIndependentSources:
    """**一稿多发不是多源互证**（2026-09-17 加近重复检测后钉住）。

    独立复核实测：只按域名判"独立来源"时，**同一篇通稿被两个站点转载**会被算成
    两个独立来源，于是二手转述被升成"多源互证"。域名这一层挡不住一稿多发——必须看内容。
    """

    def test_identical_text_on_two_domains_is_ONE_source(self, project):
        pid = project["project_id"]
        same = "据通报，住宿标准每晚不超过八百元，自下月起执行。"
        _add(pid, "转载A", same, tier="T3", domain="a-news.com")
        _add(pid, "转载B", same, tier="T3", domain="b-news.com")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 0, "同一篇稿子两个域名 ≠ 两个独立来源"
        assert a["counts"]["leads_only"] == 2
        assert au.usable_hits(a) == []
        assert any("一稿多发" in n or "内容近似" in n for n in a["notes"]), a["notes"]

    def test_copy_with_reworded_punctuation_is_still_ONE_source(self, project):
        """只改标点/空白/全半角的"转载"仍是同一篇（归一化后相等）。"""
        pid = project["project_id"]
        _add(pid, "转载A", "据通报，住宿标准每晚不超过八百元，自下月起执行。",
             tier="T3", domain="a-news.com")
        _add(pid, "转载B", "据通报  住宿标准每晚不超过八百元 ； 自下月起执行！",
             tier="T3", domain="b-news.com")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 0, "改了标点仍是同一篇稿子"
        assert a["counts"]["leads_only"] == 2

    def test_same_domain_two_articles_is_still_ONE_source(self, project):
        """同一家媒体的两篇不同文章 = 一个来源（这是域名图的节点语义）。"""
        pid = project["project_id"]
        _add(pid, "同站A", "据通报，住宿标准每晚不超过八百元，自下月起执行。",
             tier="T3", domain="a-news.com")
        _add(pid, "同站B", "有关部门答复称，住宿费用上限调整为八百元一晚。",
             tier="T3", domain="a-news.com")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 0, "同一家媒体的两篇不算两个来源"
        assert a["counts"]["leads_only"] == 2

    def test_syndicated_pair_plus_one_real_second_source(self, project):
        """`a.com` X + `b.com` 转载 X + `c.com` **另一篇** ⇒ 合并后是 **2** 个来源 ⇒ 可互证。"""
        pid = project["project_id"]
        x = "据通报，住宿标准每晚不超过八百元，自下月起执行。"
        _add(pid, "原发", x, tier="T3", domain="a-news.com")
        _add(pid, "转载", x, tier="T3", domain="b-news.com")
        _add(pid, "另一家", "有关部门答复称，住宿费用上限调整为八百元一晚。",
             tier="T3", domain="c-news.com")
        a = au.assemble_evidence(pid, "住宿标准")
        assert a["counts"]["corroborated"] == 3          # a/b 合并成一个来源 + c = 2 来源
        assert any("a-news.com" in n and "b-news.com" in n and "同一来源" in n
                   for n in a["notes"]), a["notes"]


class TestNoSingleScoreSorting:
    def test_module_exposes_no_tier_sorting_helper(self):
        """**两轴不可压成一个分数**：本模块不得提供"按层级/综合分排序材料"的函数。

        这条是**结构性约束**（业主裁定"用户可以改层级 + 制度是准则"）：一旦有了单一排序，
        公司制度就会被国标压到后面，正是要避免的错误。
        ⚠ 这条只是**命名级**检查（独立复核 2026-09-17 指出：它抓不到
        `order_materials_by_tier()`）。真正抓得住的是下面那条**行为级**断言。
        """
        offenders = [n for n in dir(au)
                     if n.startswith("sort") or "rank" in n.lower() or "score" in n.lower()]
        assert offenders == [], f"不应存在按分数排序材料的 API: {offenders}"

    def test_usable_order_follows_groups_not_tiers(self, project):
        """**行为级**两轴护栏：承重集合的顺序按"组"（准则在前）而**不是**按层级。

        构造一个"按层级排"与"按组排"结论**相反**的场景：
          · T1 材料被声明为准则（轴 B）→ 应排在 criteria
          · T0 材料是一般可作依据 → 排在 usable
        任何"按来源层级排序"的实现都会把 T0 排到 T1 前面 —— 本断言立刻红。
        """
        pid = project["project_id"]
        _add(pid, "公司制度", "住宿标准每晚五百元", tier="T1", origin="user",
             role="criterion")
        _add(pid, "官方国标", "住宿标准每晚五百元", tier="T0")
        a = au.assemble_evidence(pid, "住宿标准")
        hits = au.usable_hits(a)
        assert [h["index"] for h in hits] == [0, 1], \
            "准则组必须先于依据组（按层级排会把 T0 提到最前）"
        assert hits[0]["source_tier"] == "T1" and hits[0]["task_role"] == "criterion"
        assert hits[1]["source_tier"] == "T0"
        # 两组各自独立存在，没有被合并成一个跨层级的排序表
        assert a["counts"]["criteria"] == 1 and a["counts"]["usable"] == 1


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
