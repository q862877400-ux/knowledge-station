# -*- coding: utf-8 -*-
"""Track L 决策测试（`src/core/materials/track_l.py`，Phase C 第二步）。

守的是**三道门与一条纪律**：
  · 未批准 ⇒ `blocked`（评审硬门**没有例外**——绝不能让材料绕过评审进法条库）；
  · 不是标准 ⇒ `skip`；
  · 库内已有 ⇒ `link`（只回指，不写 doc_meta）；
  · 库内没有 ⇒ `import`（**本模块不做**，且必须能被看到"还没入库"）；
  · **本模块只读 doc_meta**：任何路径都不得写它。
"""
from __future__ import annotations

import pytest

from src.core.materials import collect as co
from src.core.materials import track_l as tl
from src.core.storage import clause_repo as cr
from src.core.storage import material_repo as mr
from src.core.storage.sqlite_db import get_db_connection


@pytest.fixture()
def project(db):
    return mr.create_project("Track L 测试")


@pytest.fixture()
def law_docs(db):
    """登记本测试往**法条链**写的 doc_id，**测完删干净**。

    ⚠ 为什么必须清（2026-09-17 被既有测试抓到）：`db` 是**会话级共用库**，
    而材料平面其它测试只写材料表、**不碰** `doc_meta`/`clause_revision`。
    Track L 的入库测试是**第一处**往法条链写东西的材料测试，于是
    `tests/test_quality_rules.py::test_qh_02_quality_issues_endpoint_shape`
    （断言"质量问题的条款恰好 5 条"——一个**全局**假设）当场变红：
    它数到了 8 条（我插的 `GB66666-2066` 的条款也在里面）。
    清理走**既有的** `clause_repo.delete_document`（它自己会清 `clause_fts`/`clause_vec`
    孤儿行——那两处虚拟表不受外键级联约束，手写 DELETE 很容易漏）。
    """
    created: list[str] = []
    yield created
    for doc_id in created:
        try:
            cr.delete_document(doc_id)
        except Exception:  # noqa: BLE001 — 清理失败不该把测试结论改写成失败
            pass


def _std_body(std_no: str) -> str:
    """一份**像真的**标准正文。

    ⚠ 必须含**两级**条款号（`3.1`/`4.2`）：GB 切分器（`law_text._GB_SPLIT`）要的是
    `\\d+[．.]\\d+`（两级），而 `1 范围` / `2 术语和定义` 这种**单级**章标题**切不出来**。
    本测试第一版只写了单级标题，于是入库返回 `error: 未识别到任何'第X条'条文`
    ——**那是测试用了不真实的正文**，不是代码的错。
    （真 GB 标准正文确实带两级条款号；这条限制本身是有意义的边界，见下面
    `test_unparsable_body_fails_loudly_instead_of_silently`。）
    """
    return (f"{std_no} 食品安全国家标准 食用动物油脂\n"
            "1 范围\n本标准适用于食用动物油脂。\n"
            "2 规范性引用文件\n下列文件中的条款通过本标准的引用而成为本标准的条款。\n"
            "3 术语和定义\n"
            "3.1 食用动物油脂 指以动物脂肪为原料加工的油脂。\n"
            "3.2 酸价 指中和1克油脂中游离脂肪酸所需的氢氧化钾毫克数。\n"
            "4 技术要求\n"
            "4.1 感官要求 应符合表1的规定。\n"
            "4.2 理化指标 酸价应不超过3.0 mg/g。\n"
            "4.3 污染物限量 应符合GB 2762的规定。")


def _collect_standard(pid: str, std_no: str = "GB 10146-2015") -> dict:
    """采一条"疑似标准正文"。

    ⚠ 标准号**可参数化**是必须的：`db` fixture 在一个测试文件内共用一套库，
    于是"库内已有"会被前面的测试建立起来 —— 想测 `import`（库内**没有**）就必须换一个
    **没被任何测试种过**的标准号（本测试第一版没这么做，结果 import 案例永远变成 link）。
    """
    return co.collect_text(pid, title=f"{std_no} 食品安全国家标准 食用动物油脂",
                           text=_std_body(std_no), url="https://openstd.example/x")


def _seed_doc(standard_no: str, name: str = "食用动物油脂", register: list | None = None,
              doc_type: str = "standard", legal_hierarchy: str = "GB") -> str:
    """往法条链塞一条最小 doc_meta（模拟"库内已有"），返回 doc_id。

    ⚠ 这是**测试自己**造的既有数据，不是被测代码写的——用来验证"已有则只回指"。
    `insert_document(conn, doc)` 需要 `file_path`/`file_hash`（NOT NULL），故补齐占位值。
    **必须幂等**：`doc_meta.standard_no` 是 UNIQUE，而 `db` fixture 在同一个文件内
    共用一套库（多个测试会重复种同一条标准）——第二次直接复用既有 doc_id，
    否则就是 `UNIQUE constraint failed`（本测试第一版就这么红的）。
    `register` 传入时把新建的 doc_id 记进去，由 `law_docs` fixture 测完删干净。

    法规也走这个助手（`doc_type="法律法规"` + 名称当 `standard_no`，与既有法规管线一致）
    ——法规那侧的"库内已有"判据不同（`find_existing_law` 按名称），但**种子数据的形状**相同。
    """
    existing = tl.find_existing_doc(standard_no)
    if existing is not None:
        return existing
    doc_id = f"doc_test_{standard_no.replace(' ', '')}"
    if register is not None:
        register.append(doc_id)
    cr.insert_document(get_db_connection(), {
        "doc_id": doc_id, "standard_no": standard_no, "standard_name": name,
        "short_code": standard_no.replace(" ", ""), "legal_status": "effective",
        "legal_hierarchy": legal_hierarchy, "doc_type": doc_type,
        "file_path": f"/tmp/{doc_id}.pdf", "file_hash": f"hash_{doc_id}",
    })
    return doc_id


class TestGates:
    def test_missing_material_is_skip(self, db):
        assert tl.plan_import("mat_不存在")["action"] == "skip"

    def test_unapproved_material_is_BLOCKED(self, project):
        """**评审硬门没有例外**：未批准的材料绝不可能进法条库。"""
        pid = project["project_id"]
        m = _collect_standard(pid)
        assert m["review_status"] == "pending"
        plan = tl.plan_import(m["material_id"])
        assert plan["action"] == "blocked"
        assert "未批准" in plan["why"]

    def test_rejected_material_is_also_blocked(self, project):
        pid = project["project_id"]
        m = _collect_standard(pid)
        mr.set_review(m["material_id"], "rejected")
        assert tl.plan_import(m["material_id"])["action"] == "blocked"

    def test_non_standard_material_is_skip_even_if_approved(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="行业观察", text="住宿标准每晚八百元。" * 5,
                            url="https://a.example/1")
        mr.set_review(m["material_id"], "approved")
        plan = tl.plan_import(m["material_id"])
        assert plan["action"] == "skip"
        assert "track_l" in plan["why"]

    def test_approved_standard_without_library_copy_needs_import(self, project):
        pid = project["project_id"]
        m = _collect_standard(pid)
        mr.set_review(m["material_id"], "approved")
        plan = tl.plan_import(m["material_id"])
        assert plan["action"] == "import"
        assert plan["standard_no"]
        assert "既有 ingest 管线" in plan["why"]


class TestLinkWhenLibraryAlreadyHasIt:
    def test_approved_standard_already_in_library_links_only(self, project, law_docs):
        pid = project["project_id"]
        doc_id = _seed_doc("GB 10146-2015", register=law_docs)
        m = _collect_standard(pid)
        mr.set_review(m["material_id"], "approved")
        plan = tl.plan_import(m["material_id"])
        assert plan["action"] == "link"
        assert plan["existing_doc_id"] == doc_id

    def test_apply_link_points_the_material_at_the_doc(self, project, law_docs):
        pid = project["project_id"]
        doc_id = _seed_doc("GB 10146-2015", register=law_docs)
        m = _collect_standard(pid)
        mr.set_review(m["material_id"], "approved")
        out = tl.apply_link(m["material_id"])
        assert out["linked"] is True
        assert mr.get_material(m["material_id"])["doc_id"] == doc_id

    def test_apply_link_on_import_does_NOTHING_and_says_so(self, project):
        """`import` 动作下 **什么都不写**，且返回值必须让人看到"还没入库"。"""
        pid = project["project_id"]
        # 换一个**没有任何测试种过**的标准号，才走得到 import 分支
        m = _collect_standard(pid, "GB 99999-2099")
        mr.set_review(m["material_id"], "approved")
        before = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        out = tl.apply_link(m["material_id"])
        after = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        assert out["action"] == "import" and out["linked"] is False
        assert after == before, "本模块不得写 doc_meta"
        assert mr.get_material(m["material_id"])["doc_id"] is None

    def test_apply_link_refuses_when_blocked(self, project):
        """未批准时 `apply_link` 也必须**拒绝**（不能因为"只是回指"就放行）。"""
        pid = project["project_id"]
        m = _collect_standard(pid)
        out = tl.apply_link(m["material_id"])
        assert out["action"] == "blocked" and out["linked"] is False


class TestStandardNoKey:
    """比较键：把库内写法与采集侧写法归一到同一把尺子。"""

    @pytest.mark.parametrize("a,b", [
        ("GB 10146-2015", "GB10146-2015"),           # 空格
        ("GB/T 1234-2020", "GBT1234-2020"),          # 斜杠
        ("GB/T 1234-2020", "GB／T 1234－2020"),       # 全角斜杠 + 全角连字符
        ("gb 10146-2015", "GB 10146-2015"),          # 大小写
        ("GB 1094.2-2013", "GB 1094.2－2013"),       # 部分号必须保留
    ])
    def test_equivalent_writings_share_a_key(self, a, b):
        from src.core.text_utils import standard_no_key
        assert standard_no_key(a) == standard_no_key(b)

    @pytest.mark.parametrize("a,b", [
        ("GB 10769-2010", "GB 10769-2025"),          # **不同版本是不同文件**
        ("GB 10146-2015", "GB 10147-2015"),          # 不同标准
        ("GB 1094.2-2013", "GB 1094.3-2013"),        # 不同部分
    ])
    def test_different_standards_do_not_collide(self, a, b):
        from src.core.text_utils import standard_no_key
        assert standard_no_key(a) != standard_no_key(b)

    def test_empty_is_empty(self):
        from src.core.text_utils import standard_no_key
        assert standard_no_key(None) == ""
        assert standard_no_key("   ") == ""

    def test_find_existing_doc_matches_across_writings(self, project, law_docs):
        """库内写 `GB 10146-2015`，采集侧给 `GB10146-2015` —— 必须能匹配上。"""
        _seed_doc("GB 10146-2015", register=law_docs)
        assert tl.find_existing_doc("GB10146-2015") is not None
        assert tl.find_existing_doc("gb／t 10146-2015") is None   # 前缀不同 → 不该匹配


class TestLawNameKey:
    """法规比较键：**保留版本/修正标记**（与标准号键的方向**相反**）。

    为什么要有**直接**断言（2026-09-17 复核的 LOW）：复核的 M11 把本函数改成
    "去掉括号里的内容"之后，测试只因为**别的**用例撞上 `doc_meta.standard_no` 的
    UNIQUE 约束才变红——那是**连带**，判据本身**没有被钉住**。
    这条判据的后果很重（P1 准确性上最坏的一种）：`（2021年修正）` 与 `（2014年修正）`
    归一成同一个键 ⇒ "库里有 2014 版"会被当成"新版已经有了" ⇒ 新版正文**不入库**、
    引用**指向旧版**，而报告看起来一切正常。
    """

    def test_the_amendment_year_is_part_of_the_identity(self):
        from src.core.text_utils import law_name_key
        assert law_name_key("安全生产法（2021年修正）") != law_name_key("安全生产法（2014年修正）")
        # 反向：**同一年**的两种写法仍是一部法（括号/书名号/空白不该造成分歧）
        assert (law_name_key("安全生产法（2021年修正）")
                == law_name_key("《安全生产法》（2021年修正）"))

    @pytest.mark.parametrize("a,b", [
        ("《中华人民共和国安全生产法》", "中华人民共和国安全生产法"),
        ("中华人民共和国 安全生产法", "中华人民共和国安全生产法"),
        ("中华人民共和国安全生产法", "中华人民共和国安全生产法"),
    ])
    def test_same_law_in_different_writings_shares_a_key(self, a, b):
        from src.core.text_utils import law_name_key
        assert law_name_key(a) == law_name_key(b)

    def test_empty_is_empty(self):
        from src.core.text_utils import law_name_key
        assert law_name_key(None) == ""
        assert law_name_key("   ") == ""

    def test_find_existing_law_does_not_point_a_new_amendment_at_an_old_one(
            self, project, law_docs):
        """库里只有 **2014 修正版**时，**2021 修正版**必须判成"库内没有"。

        这是 `law_name_key` 保留年份的**行为级**后果：判成"已有"就只会 `link`，
        新版正文永远进不了库（与复核 step-31~34 那条"脏数据拦住真数据"同型，
        只是这次拦的是**旧版本**）。
        """
        _seed_doc("中华人民共和国安全生产法（2014年修正）",
                  name="中华人民共和国安全生产法（2014年修正）",
                  register=law_docs, doc_type="法律法规", legal_hierarchy="法律")
        assert tl.find_existing_law("中华人民共和国安全生产法（2014年修正）") is not None
        assert tl.find_existing_law("《中华人民共和国安全生产法》（2021年修正）") is None


class TestIntentParsing:
    def test_intent_is_read_from_tier_evidence(self, project):
        pid = project["project_id"]
        m = _collect_standard(pid)
        intent = tl.track_l_intent(mr.get_material(m["material_id"]))
        assert isinstance(intent, dict) and intent.get("standard_no")

    def test_non_standard_has_no_intent(self, project):
        pid = project["project_id"]
        m = co.collect_text(pid, title="观察", text="住宿标准每晚八百元。" * 5,
                            url="https://a.example/1")
        assert tl.track_l_intent(mr.get_material(m["material_id"])) is None

    def test_broken_json_evidence_does_not_raise(self):
        assert tl.track_l_intent({"tier_evidence": "{ not json"}) is None
        assert tl.track_l_intent({"tier_evidence": None}) is None
        assert tl.track_l_intent(None) is None
        assert tl.track_l_intent({"tier_evidence": {"track_l": "不是字典"}}) is None

    def test_actions_constant_is_the_single_definition(self):
        assert set(tl.ACTIONS) == {"skip", "blocked", "link", "import"}


class TestImportToLibrary:
    """Track L 的**入库**那一半：走既有 `law_text.ingest_law_text`（不重写切分/分型/建边）。"""

    def test_unapproved_never_touches_the_law_chain(self, project):
        """**最要紧的一条**：未批准时入库函数必须彻底不动法条链。"""
        pid = project["project_id"]
        m = _collect_standard(pid, "GB 88888-2088")
        before_docs = get_db_connection().execute(
            "SELECT count(*) FROM doc_meta").fetchone()[0]
        before_clauses = get_db_connection().execute(
            "SELECT count(*) FROM clause_revision").fetchone()[0]
        out = tl.import_to_library(m["material_id"])
        after_docs = get_db_connection().execute(
            "SELECT count(*) FROM doc_meta").fetchone()[0]
        after_clauses = get_db_connection().execute(
            "SELECT count(*) FROM clause_revision").fetchone()[0]
        assert out["action"] == "blocked" and out["imported"] is False
        assert (after_docs, after_clauses) == (before_docs, before_clauses), \
            "未批准的材料绝不可能进法条库"

    def test_approved_standard_is_imported_and_linked(self, project, law_docs):
        pid = project["project_id"]
        std = "GB 88888-2088"
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True, out
        law_docs.append(out["doc_id"])          # 测完删干净（共享库！）
        assert out["doc_id"]
        assert out["linked"] is True
        assert out["total_clauses"] and out["total_clauses"] > 0
        # 回指真的写进了材料平面的列
        assert mr.get_material(m["material_id"])["doc_id"] == out["doc_id"]
        # 落库口径与全库一致：doc_type=standard（生产库 6417 行全是 standard）
        row = get_db_connection().execute(
            "SELECT doc_type, standard_no, legal_hierarchy, source_url FROM doc_meta"
            " WHERE doc_id=?", (out["doc_id"],)).fetchone()
        assert row["doc_type"] == "standard"
        # ⚠ 落库写法是 `auto_tag` 的**归一形**（无空格），而库内既有行是 `GB 10146-2015`（带空格）
        # ——这是**已知的观感不一致**（判重走 standard_no_key，不受影响）。
        # 钉住实际行为，免得有人以为是笔误而"顺手"改坏。
        assert row["standard_no"] == "GB88888-2088", row["standard_no"]
        assert tl.find_existing_doc(std) is not None, "两种写法必须被比较键认作同一部"
        assert row["source_url"] == "https://openstd.example/x", "溯源必须落库"
        # 条款也真的进去了（能被检索/解析）
        n = get_db_connection().execute(
            "SELECT count(*) FROM clause_revision WHERE doc_id=?", (out["doc_id"],)).fetchone()[0]
        assert n > 0

    def test_imported_standard_is_resolvable_by_the_law_chain(self, project, law_docs):
        """入库之后，法条链**自己**的查询要能找到它（否则"入库"没有意义）。"""
        pid = project["project_id"]
        std = "GB 77777-2077"
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True
        law_docs.append(out["doc_id"])          # 测完删干净（共享库！）
        # 用标准号比较键能找到（库里是 GB 77777-2077 这种写法）
        assert tl.find_existing_doc(std) == out["doc_id"]

    def test_second_import_of_same_material_is_idempotent(self, project, law_docs):
        """再跑一次不该造出第二部标准（既有管线的查重会让它退化为回指）。

        第二次用 **`reconcile`**（Track L 的单一入口）：此时库里已有 ⇒ 决策变 `link`
        ⇒ 它只回指、不重复入库。这也测到了 `reconcile` 的分派。
        """
        pid = project["project_id"]
        std = "GB 66666-2066"
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        first = tl.import_to_library(m["material_id"])
        assert first["imported"] is True
        law_docs.append(first["doc_id"])        # 测完删干净（共享库！）
        docs_after_first = get_db_connection().execute(
            "SELECT count(*) FROM doc_meta").fetchone()[0]
        second = tl.reconcile(m["material_id"])
        docs_after_second = get_db_connection().execute(
            "SELECT count(*) FROM doc_meta").fetchone()[0]
        assert docs_after_second == docs_after_first, "第二次不该再插一部"
        assert second["action"] == "link" and second["imported"] is False
        assert second["linked"] is True

    def test_reconcile_dispatches_link_and_never_writes_for_blocked(self, project, law_docs):
        """`reconcile` 的分派：link 走回指；blocked/skip 什么都不做且如实回报。"""
        pid = project["project_id"]
        # link 分支
        std = "GB 33333-2033"
        _seed_doc(std, register=law_docs)
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.reconcile(m["material_id"])
        assert out["action"] == "link" and out["linked"] is True and out["imported"] is False
        # blocked 分支
        m2 = _collect_standard(pid, "GB 22222-2022")
        blocked = tl.reconcile(m2["material_id"])
        assert blocked["action"] == "blocked"
        assert blocked["imported"] is False and blocked["linked"] is False

    def test_material_without_chunks_refuses_to_import(self, project):
        """没有正文的采集件不得入库——那会造出一部空标准。"""
        pid = project["project_id"]
        m = _collect_standard(pid, "GB 55555-2055")
        mr.set_review(m["material_id"], "approved")
        # 手动清掉切片，模拟"解析不出正文"
        with __import__("src.core.storage.sqlite_db", fromlist=["x"]).write_transaction() as txn:
            txn.execute("DELETE FROM material_chunk WHERE material_id=?", (m["material_id"],))
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is False
        assert "没有切片" in out["why"] or "没有正文" in out["why"]

    def test_unparsable_body_fails_loudly_instead_of_silently(self, project, law_docs):
        """切不出条款时必须**如实报错**，不能静默"成功"或造出一部空标准。

        这也钉住一条**真限制**：GB 切分器要**两级**条款号，只有单级章标题
        （`1 范围` / `2 术语和定义`）的正文**切不出来**。网页抓来的正文很可能长这样，
        所以这条路径必须能被看到，而不是变成一部空标准。
        """
        pid = project["project_id"]
        m = co.collect_text(pid, title="GB 44444-2044 某标准",
                            text="GB 44444-2044 某标准\n1 范围\n本标准适用于某物。\n"
                                 "2 术语和定义\n下列术语适用于本文件。",
                            url="https://openstd.example/x")
        mr.set_review(m["material_id"], "approved")
        before = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        out = tl.import_to_library(m["material_id"])
        after = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        assert out["imported"] is False
        assert out.get("import_status") == "error"
        assert "第X条" in (out.get("why") or ""), out
        assert after == before, "切不出条款时不得留下半部文档"

    def test_collected_LAW_text_is_now_recognized_and_imported(self, project, law_docs):
        """**法规正文现在能走通了**（2026-09-17 起）。

        ⚠ 这条替换掉旧测试 `test_collected_LAW_text_is_out_of_scope_today`：
        当时（C-3）这里钉的是**已知边界**——`track_l` 意图来自 `looks_like_standard`，
        而复用的是 `auto_tag` 的**标准号正则** ⇒ 没有标准号的法规**认不出来**、
        `plan_import` 直接 `skip`。现在 `collect.looks_like_law` 补上了那个识别，
        所以这条从"钉住走不通"改成"钉住走得通"（**旧断言必须跟着改，否则它会变成
        一条阻止修复的假门**）。
        """
        pid = project["project_id"]
        body = ("中华人民共和国民法典\n" + "第一条 为了保护民事主体的合法权益，制定本法。\n"
                "第二条 民法调整平等主体的自然人、法人和非法人组织之间的人身关系和财产关系。\n"
                "第三条 民事主体的人身权利、财产权利以及其他合法权益受法律保护。")
        m = co.collect_text(pid, title="中华人民共和国民法典(节选)", text=body,
                            url="https://gov.example/law")
        assert m["kind"] == "legal"
        assert m["track_l"]["doc_kind"] == "law", m["track_l"]
        assert m["track_l"]["law_name"] == "中华人民共和国民法典", m["track_l"]
        # 未批准 ⇒ 仍然 blocked（硬门没有例外）
        assert tl.plan_import(m["material_id"])["action"] == "blocked"
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True, out
        law_docs.append(out["doc_id"])          # 共享库：测完删干净
        assert out["doc_kind"] == "law"
        # 法规口径：`doc_type='法律法规'`、`standard_no` 存**名称**（与既有法规管线一致）
        row = get_db_connection().execute(
            "SELECT doc_type, standard_no, legal_hierarchy, legal_status, quality_grade,"
            " standard_type FROM doc_meta WHERE doc_id=?",
            (out["doc_id"],)).fetchone()
        assert row["doc_type"] == "法律法规", dict(row)
        assert row["standard_no"] == "中华人民共和国民法典", dict(row)
        assert row["legal_hierarchy"] == "法律", dict(row)      # 以"法"结尾 ⇒ 安全推断
        # **法规分支的诚实元数据同样要有断言**（2026-09-17）：两个分支调的是同一个
        # `_collected_doc_meta()`，但只钉标准分支的话，法规分支的调用点整行删掉
        # **不会有任何测试变红**（复核式的"对称缺口"）。采网页不知道效力 ⇒ 未知。
        assert row["legal_status"] is None, dict(row)
        assert row["quality_grade"] == "C", dict(row)
        assert row["standard_type"] is None, dict(row)
        assert tl.find_existing_law("《中华人民共和国民法典》") == out["doc_id"]
        # 再跑一次 ⇒ 既有管线的查重命中 ⇒ 退化为回指，不造第二部
        again = tl.reconcile(m["material_id"])
        assert again["action"] == "link" and again["imported"] is False

    def test_import_of_law_without_a_name_refuses_loudly(self, project, monkeypatch):
        """法规名没取到 ⇒ **拒绝入库**（没有名字就没法在库里认它，宁可不入）。"""
        pid = project["project_id"]
        m = co.collect_text(pid, title="某地方规定节选",
                            text="第一条 为了规范某某行为。\n第二条 适用于本区域。\n第三条 由某部门负责解释。",
                            url="https://gov.example/x")
        mr.set_review(m["material_id"], "approved")
        monkeypatch.setattr(tl, "plan_import", lambda _mid: {
            "action": "import", "material_id": m["material_id"], "doc_kind": "law",
            "law_name": None, "why": "（测试构造）"})
        before = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        out = tl.import_to_library(m["material_id"])
        after = get_db_connection().execute("SELECT count(*) FROM doc_meta").fetchone()[0]
        assert out["imported"] is False and "law_name" in out["why"], out
        assert after == before, "拒绝时必须一份都不写"

    def test_hierarchy_and_clause_type_are_honest(self):
        """复核 step-31~34 的两条 MEDIUM：**标准条款的类型**与**采集件的效力/质量默认值**。

        ① `ingest_law_text` 里 `classify_clause(..., doc_type="法律法规")` 原是**写死**的 ⇒
           Track L 入的**标准**条款被判成 `knowledge_type='legal'`（标准条款不是法条）；
        ② 采集件原来吃 `insert_document` 的默认 `legal_status='effective'`/`quality_grade='A'`/
           `standard_type='mandatory'` ⇒ 未核验的网页文本被当**现行有效**引用、
           效力报告算 🟢。现在显式写诚实值（未知 / C / 不声明类型）。
        """
        assert tl._collected_doc_meta() == {"legal_status": None, "quality_grade": "C",
                                            "standard_type": None}

    def test_imported_standard_clauses_are_rules_not_legal(self, project, law_docs):
        """标准入库后，条款的 `knowledge_type` 必须是 `rule`（不是 `legal`）。"""
        pid = project["project_id"]
        std = "GB 12321-2021"
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True, out
        law_docs.append(out["doc_id"])
        kinds = {r[0] for r in get_db_connection().execute(
            "SELECT DISTINCT knowledge_type FROM clause_revision WHERE doc_id=?",
            (out["doc_id"],)).fetchall()}
        # 正例：不含 `legal`（法条型）。`data` 是分类器对"含数值/单位"的条款的正常判法
        # （`classify_clause` 的既有语义），所以这里只钉"**不是法条**"。
        assert kinds and "legal" not in kinds, kinds
        assert kinds <= {"rule", "data"}, kinds

    def test_imported_collected_doc_is_marked_unknown_not_effective(self, project, law_docs):
        """采集件落库后：效力**未知**（不是 effective）、质量 **C**、类型**不声明**。

        ⚠ **本测试的 docstring 曾被复核 b7 判为过度声称**（§10.44）：原文写"这三条**决定**
        '未核验的网页文本会不会被当成现行有效'"，而当时它**只**钉了 `doc_meta` 那一列——
        **答案链上的洗白发生在另一处**：`clause_repo.fetch_full_clause` 里
        `legal_status=row["legal_status"] or "effective"` 把 NULL 又变回现行有效
        （`ClauseRevisionModel.legal_status` 当时还是非可选 `str`），于是它照样通过
        `ks_answer._is_effective`（`== "effective"`）进证据、进提示词。
        ⇒ 现在这条**跑到底**：库列、条款模型、答案链的可引性，三处都断言。
        """
        pid = project["project_id"]
        std = "GB 12421-2021"
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True, out
        law_docs.append(out["doc_id"])
        row = get_db_connection().execute(
            "SELECT legal_status, quality_grade, standard_type FROM doc_meta WHERE doc_id=?",
            (out["doc_id"],)).fetchone()
        assert row["legal_status"] is None, dict(row)
        assert row["quality_grade"] == "C", dict(row)
        assert row["standard_type"] is None, dict(row)
        # 效力报告的口径：None ⇒ gray（⚪ 状态未知/未登记），不是 🟢 现行有效
        from src.core.exports.effect_report import STATUS_COLOR
        assert STATUS_COLOR[None] == "gray"

        # ---- ② 条款模型必须如实带出 NULL（不是被洗白成 "effective"）----
        cid = get_db_connection().execute(
            "SELECT clause_revision_id FROM clause_revision WHERE doc_id=? LIMIT 1",
            (out["doc_id"],)).fetchone()["clause_revision_id"]
        clause = cr.fetch_full_clause(get_db_connection(), cid)
        assert clause is not None
        assert clause.legal_status is None, clause.legal_status

        # ---- ③ **行为级**：它不得被 `ks_answer` 当现行版引用 ----
        from src.core.llm import ks_answer as ka
        ev = ka._clause_to_evidence(clause)
        assert ev["legal_status"] is None, ev["legal_status"]
        assert ka._is_effective(ev) is False, ev
        assert ka._filter_effective([ev]) == [], "未核验的采集件不得进证据集"

    def test_collected_standard_lands_in_the_standard_tree(self, project, law_docs):
        """**进对树**：`auto_tag` 的归一形 `GB12321-2021`（无空格）也要被认成标准。

        复核实测：`doc_catalog._STD_NO_PREFIX` 用 `\\b` 判定 ⇒ `GB12321-2021` 里
        `GB` 与 `1` 之间没有词边界 ⇒ 被归到**法规树**（`top='law'`），效力报告同源。
        修在**判据的所有者**（`doc_catalog`）而不是"把数据改个写法"。
        """
        from src.core.knowledge.doc_catalog import classify_document
        pid = project["project_id"]
        std = "GB 12321-2021"           # 采集侧写库的形态（auto_tag 归一形）
        m = _collect_standard(pid, std)
        mr.set_review(m["material_id"], "approved")
        out = tl.import_to_library(m["material_id"])
        assert out["imported"] is True, out
        law_docs.append(out["doc_id"])
        row = get_db_connection().execute(
            "SELECT standard_no, standard_name, doc_type, legal_hierarchy, domain_tags"
            " FROM doc_meta WHERE doc_id=?", (out["doc_id"],)).fetchone()
        doc = {"standard_no": row["standard_no"], "standard_name": row["standard_name"],
               "doc_type": row["doc_type"], "legal_hierarchy": row["legal_hierarchy"],
               "domain_tags": []}
        assert classify_document(doc)["top"] == "std", (row["standard_no"], classify_document(doc))

    def test_law_hierarchy_is_conservative_and_says_undecided(self):
        """层级推断**只用不会错的规则**，其余一律 `未定`（**不假装知道位阶**）。

        为什么：判效力层级要看**发行机关**（`条例` 可能是国务院行政法规、也可能是省人大
        地方性法规），采网页拿不到 ⇒ 猜错就是把错误的位阶写进法规库。
        """
        assert tl._law_hierarchy("中华人民共和国安全生产法") == "法律"
        assert tl._law_hierarchy("最高人民法院关于适用《中华人民共和国民法典》的解释") == "司法解释"
        # ⚠ **宪法单列**（复核 step-31~34 的 MEDIUM）：它不以"法律"归类——目录里另有
        #   「宪法及宪法相关法」这一档，而 `_HIER_TO_TIER` 会把"法律"直映成「法律（狭义）」。
        assert tl._law_hierarchy("中华人民共和国宪法") == "宪法"
        assert tl._law_hierarchy("中华人民共和国宪法修正案") == "宪法"
        # 这些**都**拿不准 ⇒ 未定（既有目录层会自己按名称关键词再兜一层，兜不到显示"未定级"）
        assert tl._law_hierarchy("危险化学品安全管理条例") == "未定"
        assert tl._law_hierarchy("XX省安全生产条例") == "未定"
        assert tl._law_hierarchy("安全生产违法行为行政处罚办法") == "未定"
        assert tl._law_hierarchy("") == "未定"


class TestTreeClassificationOfStandardNumbers:
    """`doc_catalog._STD_NO_PREFIX` 的判据要容纳**无空格写法**（复核 step-31~34 的 MEDIUM）。

    原来用 `\\b` 收尾 ⇒ `GB12321-2021`（`auto_tag` 的归一形）与 `DB11/T 1234-2020`
    （地方标准）都过不了 ⇒ 被归到**法规树**（效力报告同源）。
    修在**判据的所有者**，而不是"把数据改个写法"——这样任何未来形态也不会再错。
    """

    @pytest.mark.parametrize("std_no", [
        "GB12321-2021", "GB 12321-2021", "GB/T 12041.1-2010", "GBT12041.1-2010",
        "DB11/T 1234-2020", "DB11T1234-2020", "AQ 4272-2016", "JGJ 130-2011",
        "GBZ 1-2010", "GBZ1-2010",          # 职业卫生标准也是标准（原来漏在白名单外）
        "GBZ／T",                            # **全角斜杠**（U+FF0F）：生产库实测有这一行，
                                             # 兄弟函数都做了归一，只有这里漏（复核 b8 的 LOW-4）
        "GB",                               # 光杆前缀（退化输入）：**不许掉进法规树**（复核实测的回退）
    ])
    def test_standard_numbers_go_to_the_standard_tree(self, std_no):
        from src.core.knowledge.doc_catalog import classify_document
        doc = {"standard_no": std_no, "standard_name": "某标准", "doc_type": "standard",
               "legal_hierarchy": "GB", "domain_tags": []}
        assert classify_document(doc)["top"] == "std", (std_no, classify_document(doc))

    @pytest.mark.parametrize("std_no", [
        "中华人民共和国安全生产法", "危险化学品安全管理条例",
    ])
    def test_law_names_do_not_become_standards(self, std_no):
        """反方向也不能错：法规名不许被当成标准号（白名单**不是**"任何带数字的东西"）。"""
        from src.core.knowledge.doc_catalog import classify_document
        doc = {"standard_no": std_no, "standard_name": std_no, "doc_type": "法律法规",
               "legal_hierarchy": "法律", "domain_tags": []}
        assert classify_document(doc)["top"] == "law", (std_no, classify_document(doc))
