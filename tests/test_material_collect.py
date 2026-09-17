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


class TestLawRecognition:
    """**法规识别**（2026-09-17，Phase C 第八步）：让 Track L 也覆盖法规。

    判据的"第X条"切分复用 `ingestion.law_text.split_law_text`（**不新写第二份正则**），
    这里钉的是**门槛**与**优先级**——宁可漏认，也不要把新闻或标准当法规。
    """

    _LAW = ("《中华人民共和国安全生产法》\n"
            "第一条 为了加强安全生产工作，防止和减少生产安全事故，制定本法。\n"
            "第二条 在中华人民共和国领域内从事生产经营活动的单位，适用本法。\n"
            "第三条 安全生产工作坚持中国共产党的领导。\n"
            "第四条 生产经营单位必须遵守本法和其他有关安全生产的法律法规。\n")

    def test_law_text_is_recognized_with_name_and_clause_count(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="中华人民共和国安全生产法", text=self._LAW,
                            url="https://gov.example/law")
        assert m["kind"] == "legal"
        tl = m["track_l"]
        assert tl["doc_kind"] == "law" and tl["status"] == "pending_review", tl
        assert tl["law_name"] == "中华人民共和国安全生产法", tl
        assert tl["clause_count"] == 4, tl
        # 判级说明必须**如实**写出"层级是我们推断的"（评审人要能看出这一点）
        assert "法规" in (m["tier_reason"] or "")
        assert "推断" in (m["tier_reason"] or "")

    def test_direct_recognizer_thresholds(self):
        """四条证据都要齐：标题/法规名 + **从第一条起** + **立法句式** + 条数门槛。"""
        law = ("第一条 为了规范某某行为，制定本法。\n"
               "第二条 本法适用于某某活动。\n"
               "第三条 某某部门负责监督。\n"
               "第四条 本法自公布之日起施行。\n")
        assert co.looks_like_law("某办法", law)["is_law"] is True
        # 标题不是法规名 ⇒ 不认（否则会把"引用了一条法条的文章"当法规）
        assert co.looks_like_law("一篇行业观察", law)["is_law"] is False
        # 标题不可用但条数够多 ⇒ 仍认（采网页常丢标题）
        many = "\n".join(f"第{n}条 本条内容，本法另有规定的除外。"
                        for n in ["一", "二", "三", "四", "五", "六", "七", "八",
                                  "九", "十", "十一", "十二"])
        r = co.looks_like_law("", many)
        assert r["is_law"] is True and r["clause_count"] == 12, r
        # 同样长的正文但**缺立法句式** ⇒ 不认（新闻/合同正是这样）
        no_recital = "\n".join(f"第{n}条 本条规定了某某事项。" for n in
                              ["一", "二", "三", "四", "五", "六", "七", "八",
                               "九", "十", "十一", "十二"])
        assert co.looks_like_law("", no_recital)["is_law"] is False

    def test_a_single_clause_citation_is_not_a_law(self, project):
        """**零误伤方向**：正文里顺口引用一条"第X条"的文章不许被当成法规。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="行业观察",
                            text="根据《安全生产法》第三条的规定，安全生产工作应当以人为本。"
                                 "本文讨论该条款在实践中的适用问题。",
                            url="https://a.example/1")
        assert m["track_l"] is None and m["kind"] == "other", m

    def test_standard_number_wins_over_law_shape(self, project):
        """**优先级**：同时像标准与法规时，走**标准**那一支（标准号判据更精确）。

        ⚠ 这条同时回答一个**复核误判**（2026-09-17）：复核的 M13 把
        `if std…: / elif law…:` 的 `elif` 改成 `if`，测试**全绿**，于是被记成
        "优先级契约在真冲突下无覆盖"。**不是**：冲突在上游就被消掉了——
        `collect_text` 里 `law = {"is_law": False} if std.get("is_standard") else …`
        这行守卫保证"认成标准时 `law` 恒为假"，所以那个 `elif` 在 std 为真时
        **不可达**，M13 是**等价变异体**（equivalent mutant），本来就不该指望它变红。
        真正承重的是那行守卫（复核的 M12 删掉它 ⇒ **RED**）。
        这里把断言**加严**到"没有法规字段漏出来"，让"标准赢"这条契约更锋利。
        """
        pid = project["project_id"]
        body = ("GB 88888-2088 某安全技术规范\n" + self._LAW)
        m = co.collect_text(pid, title="GB 88888-2088 某安全技术规范", text=body,
                            url="https://openstd.example/x")
        assert m["track_l"]["doc_kind"] == "standard", m["track_l"]
        assert m["track_l"]["standard_no"], m["track_l"]
        # 「赢」要**赢得干净**：法规那一支的字段一个都不许混进来（混进来就会写错库）
        assert "law_name" not in m["track_l"], m["track_l"]
        assert "clause_count" not in m["track_l"], m["track_l"]
        # 判据本身也要说清是"标准赢"，理由要能给人看
        assert "标准" in (m["tier_reason"] or ""), m["tier_reason"]
        assert "法规" not in (m["tier_reason"] or ""), m["tier_reason"]


class TestLawRecognitionFalsePositives:
    """**误伤方向**：新闻 / 合同 / 判决书都不许被认成法规（复核 step-31~34 的 MEDIUM-HIGH）。

    复核给的是**端到端**后果，不只是"识别错"：那篇新闻批准后**真的往 `doc_meta` 插了一行**
    （`standard_no=中华人民共和国安全生产法`、`standard_name=新闻标题`），此后采到真
    《安全生产法》全文再批准时 `find_existing_law` 命中那行新闻 ⇒ `link` 而不是 `import`
    ⇒ **真法规永远进不了库**（脏数据拦住真数据）。所以这一组用例守的是**法条库的干净**。
    """

    def test_news_quoting_law_names_is_not_a_law(self, project):
        """新闻：标题正常、正文引了《…》+ 几条法条 ⇒ **不许**认成法规。"""
        pid = project["project_id"]
        body = ("据新华社报道，应急管理部今日就安全生产问题答记者问。"
                "《中华人民共和国安全生产法》第三条规定，安全生产工作应当以人为本。"
                "《中华人民共和国安全生产法》第四条规定，生产经营单位必须遵守本法。"
                "《中华人民共和国安全生产法》第五条规定，生产经营单位的主要负责人对本单位的"
                "安全生产工作全面负责。")
        m = co.collect_text(pid, title="应急管理部就安全生产问题答记者问", text=body,
                            url="https://news.example/1")
        assert m["track_l"] is None, f"新闻不许被认成法规：{m['track_l']}"
        assert m["kind"] == "other"

    def test_contract_is_not_a_law(self, project):
        """合同：有第一条/第二条、有《设备采购合同》⇒ **不许**认成法规。"""
        pid = project["project_id"]
        body = ("《设备采购合同》\n第一条 甲方同意向乙方采购下列设备。\n"
                "第二条 乙方应按本合同约定的时间交付。\n"
                "第三条 本合同自双方签字之日起生效。\n")
        m = co.collect_text(pid, title="设备采购合同", text=body, url="https://a.example/c")
        assert m["track_l"] is None, m["track_l"]

    def test_judgment_is_not_a_law(self, project):
        """判决书：正文引《合同法》，但自称"本院"而不是"本法"⇒ **不许**认成法规。"""
        pid = project["project_id"]
        body = ("本院认为，根据《合同法》第一条的规定，当事人订立合同应当遵循平等原则。\n"
                "第一条 判决如下。\n"
                "第二条 案件受理费由被告负担。\n"
                "第三条 如不服本判决，可在十五日内上诉。\n")
        m = co.collect_text(pid, title="民事判决书", text=body, url="https://court.example/1")
        assert m["track_l"] is None, m["track_l"]

    def test_law_without_the_recital_phrase_is_still_refused(self, project):
        """缺**立法句式**（"本法"/"本条例"）就不算——这是四条证据之一，不是装饰。"""
        pid = project["project_id"]
        body = ("第一条 由某部门负责解释。\n第二条 自发布之日起施行。\n第三条 未尽事宜另行规定。\n")
        m = co.collect_text(pid, title="某省安全生产条例", text=body, url="https://gov.example/x")
        assert m["track_l"] is None, m["track_l"]

    def test_must_start_at_article_one(self, project):
        """引用的条号**不从第一条开始** ⇒ 是节选/引用，不是法规全文。"""
        pid = project["project_id"]
        body = ("第三条 安全生产工作应当以人为本。本条例适用于本省。\n"
                "第四条 生产经营单位必须遵守本条例。\n"
                "第五条 主要负责人全面负责。\n")
        m = co.collect_text(pid, title="某省安全生产条例", text=body, url="https://gov.example/y")
        assert m["track_l"] is None, m["track_l"]

    def test_law_name_is_never_taken_from_the_body(self, project):
        """**根因钉子**：法规名**只能**来自标题——正文里的 `《…》` 一律不算。

        复核给的那条数据污染正是从这里来的：正文首行出现 `《中华人民共和国安全生产法》`
        （新闻/判决书/合同都在正文里引法条），第一版就把那个书名号当成了法规名。
        这条用例构造的是"**标题不可用 + 正文首行带书名号 + 四条证据里那三条都满足**"，
        但条数只有 3（< 10）⇒ **不许**认成法规（宁可不认，也不能拿正文里的书名号当身份）。
        """
        pid = project["project_id"]
        body = ("《中华人民共和国安全生产法》\n"
                "第一条 为了加强安全生产工作，制定本法。\n"
                "第二条 本法适用于生产经营活动。\n"
                "第三条 某某部门负责监督本法实施。\n")
        assert co._law_name_of("某部门通知", body) is None, "正文里的书名号不许当法规名"
        m = co.collect_text(pid, title="某部门通知", text=body, url="https://news.example/2")
        assert m["track_l"] is None, f"不许拿正文里的书名号当法规身份：{m['track_l']}"

        """真法规（标题是法规名 + 从第一条起 + 有"本法" + ≥3 条）**必须仍然认得出**。"""
        pid = project["project_id"]
        assert co.looks_like_law("中华人民共和国安全生产法", TestLawRecognition._LAW)["is_law"] is True
        m = co.collect_text(pid, title="中华人民共和国安全生产法", text=TestLawRecognition._LAW,
                            url="https://gov.example/law")
        assert m["track_l"]["doc_kind"] == "law", m["track_l"]


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

    def test_binary_container_is_refused_at_the_door(self, project, db):
        """**唯一的采集门**自己就要挡住二进制（不能只靠采集器自觉）。

        为什么挡在这扇门上：登记进去的东西**直接进评审队列**，而"读不了的正文"要等到
        分析时才暴露——那时它可能已经被批准了。判据的所有者是
        `text_utils.looks_like_binary`（采集器也调它，两处同一个实现）。
        """
        pdf = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nstream\nâãÏÓ\x00\nendstream"
        before = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]

        with pytest.raises(ValueError, match="不是文本"):
            co.collect_text(project["project_id"], title="某附件",
                            text=pdf, url="https://a.example/x.pdf")
        assert mr.list_materials(project["project_id"]) == [], "拒收不得留下材料"
        after = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        assert after == before, "拒收不得碰 doc_meta（Track L 只在批准后入库）"

    def test_binary_signature_in_the_middle_is_not_refused(self, project):
        """保守：签名只在**开头**算——正文中间提到 `%PDF-` 的文章不该被误杀。"""
        text = _ARTICLE + "\n附件请提供 %PDF- 格式的原文。"
        m = co.collect_text(project["project_id"], title="报道", text=text,
                            url="https://a.example/1")
        assert m["material_id"].startswith("mat_")


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
