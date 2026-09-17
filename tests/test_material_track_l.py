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


def _std_body(std_no: str) -> str:
    return (f"{std_no} 食品安全国家标准 食用动物油脂\n"
            "1 范围 本标准适用于食用动物油脂。\n"
            "2 术语和定义 下列术语和定义适用于本文件。" * 3)


def _collect_standard(pid: str, std_no: str = "GB 10146-2015") -> dict:
    """采一条"疑似标准正文"。

    ⚠ 标准号**可参数化**是必须的：`db` fixture 在一个测试文件内共用一套库，
    于是"库内已有"会被前面的测试建立起来 —— 想测 `import`（库内**没有**）就必须换一个
    **没被任何测试种过**的标准号（本测试第一版没这么做，结果 import 案例永远变成 link）。
    """
    return co.collect_text(pid, title=f"{std_no} 食品安全国家标准 食用动物油脂",
                           text=_std_body(std_no), url="https://openstd.example/x")


def _seed_doc(standard_no: str, name: str = "食用动物油脂") -> str:
    """往法条链塞一条最小 doc_meta（模拟"库内已有"），返回 doc_id。

    ⚠ 这是**测试自己**造的既有数据，不是被测代码写的——用来验证"已有则只回指"。
    `insert_document(conn, doc)` 需要 `file_path`/`file_hash`（NOT NULL），故补齐占位值。
    **必须幂等**：`doc_meta.standard_no` 是 UNIQUE，而 `db` fixture 在同一个文件内
    共用一套库（多个测试会重复种同一条标准）——第二次直接复用既有 doc_id，
    否则就是 `UNIQUE constraint failed`（本测试第一版就这么红的）。
    """
    existing = tl.find_existing_doc(standard_no)
    if existing is not None:
        return existing
    doc_id = f"doc_test_{standard_no.replace(' ', '')}"
    cr.insert_document(get_db_connection(), {
        "doc_id": doc_id, "standard_no": standard_no, "standard_name": name,
        "short_code": standard_no.replace(" ", ""), "legal_status": "effective",
        "legal_hierarchy": "GB", "doc_type": "standard",
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
    def test_approved_standard_already_in_library_links_only(self, project):
        pid = project["project_id"]
        doc_id = _seed_doc("GB 10146-2015")
        m = _collect_standard(pid)
        mr.set_review(m["material_id"], "approved")
        plan = tl.plan_import(m["material_id"])
        assert plan["action"] == "link"
        assert plan["existing_doc_id"] == doc_id

    def test_apply_link_points_the_material_at_the_doc(self, project):
        pid = project["project_id"]
        doc_id = _seed_doc("GB 10146-2015")
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

    def test_find_existing_doc_matches_across_writings(self, project):
        """库内写 `GB 10146-2015`，采集侧给 `GB10146-2015` —— 必须能匹配上。"""
        _seed_doc("GB 10146-2015")
        assert tl.find_existing_doc("GB10146-2015") is not None
        assert tl.find_existing_doc("gb／t 10146-2015") is None   # 前缀不同 → 不该匹配


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
