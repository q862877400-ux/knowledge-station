# -*- coding: utf-8 -*-
"""材料平面仓库测试（2026-09-17 定位转移 Phase A）。

覆盖四件必须成立的事：
  1. **评审是硬门**：`approved_materials()` 只返回已批准的——未批准材料不得进入分析；
  2. **两个权威轴不合并**：来源可信度（T0~T4）与任务内效力（criterion/reference）各自独立，
     且**用户可改层级并留痕**（`tier_source='user'`）；
  3. **引用可点回原文**：切片保留字符区间（`char_start/char_end`）与页号；
  4. **与法条链零耦合**：操作材料**不改动** `doc_meta` / `clause_revision` / `source_span`
     一行（行为级验证，不是靠"我记得没写"）。
"""
from __future__ import annotations

import pytest

from src.core.storage import material_repo as mr


@pytest.fixture()
def project(db):
    return mr.create_project("测试项目", note="仅测试用")


# ------------------------------------------------------------------ 项目
class TestProject:
    def test_create_and_get(self, db):
        p = mr.create_project("财报分析", authority_policy={"criterion": ["公司制度"]})
        assert p["project_id"].startswith("prj_")
        assert p["name"] == "财报分析"
        # 轴 B 的项目级声明要能往返（JSON）
        assert p["authority_policy"] == {"criterion": ["公司制度"]}
        assert mr.get_project(p["project_id"])["name"] == "财报分析"

    def test_list_contains_created(self, db):
        a = mr.create_project("A")
        b = mr.create_project("B")
        ids = {p["project_id"] for p in mr.list_projects()}
        assert {a["project_id"], b["project_id"]} <= ids

    def test_get_unknown_is_none(self, db):
        assert mr.get_project("prj_不存在") is None


# ------------------------------------------------------------------ 材料默认值
class TestMaterialDefaults:
    def test_new_material_born_status_by_origin(self, project):
        """S3-b（2026-09-22 业主裁定 NOT-DOING #15）：出生评审状态**按来源**——
        人工上传免评审（approved，生而可作依据）；自采照旧 pending（硬门只管自采）。
        对账留痕：本测原名 test_new_material_is_pending_not_usable、原文
        「新材料默认 **pending** —— 未经评审不得使用（这是硬门的前提）。」——
        旧口径对 user 来源已按裁定作废，安全核移到 collected 侧（不放宽）。"""
        up = mr.add_material(project["project_id"], "用户上传的制度.pdf", origin="user")
        assert up["review_status"] == "approved", "人工上传免评审（出生即 approved）"
        col = mr.add_material(project["project_id"], "抓来的网页正文", origin="collected")
        assert col["review_status"] == "pending", "自采必须仍待人批（硬门只管自采）"
        assert col["lifecycle"] == "ephemeral"        # 默认仅本次任务参考
        assert col["doc_id"] is None

    def test_user_material_defaults_to_t1_system(self, project):
        """用户自有原件默认 T1（对其自身内容是初级证据），由 system 判。"""
        m = mr.add_material(project["project_id"], "本公司2025年报.pdf", origin="user")
        assert m["source_tier"] == "T1"
        assert m["tier_source"] == "system"

    def test_collected_material_is_not_trusted_by_default(self, project):
        """**自采默认不可信**（T3 起）：网上找来的在没证据前不该默认可信。"""
        m = mr.add_material(project["project_id"], "某论坛帖子", origin="collected")
        assert m["source_tier"] == "T3"

    def test_invalid_enums_rejected(self, project):
        with pytest.raises(ValueError):
            mr.add_material(project["project_id"], "x", origin="robot")
        with pytest.raises(ValueError):
            mr.add_material(project["project_id"], "x", kind="random")
        with pytest.raises(ValueError):
            mr.add_material(project["project_id"], "x", source_tier="T9")

    def test_tier_evidence_roundtrips(self, project):
        ev = {"domain": "sse.com.cn", "has_original_url": True, "is_primary": True}
        m = mr.add_material(project["project_id"], "公告", origin="collected",
                            source_tier="T2", tier_evidence=ev)
        assert m["tier_evidence"] == ev


# ------------------------------------------------------------------ 硬门
class TestReviewGate:
    def test_approved_materials_is_the_hard_gate(self, project):
        """硬门核原样：自采未经批准不得进作答；人工上传免评审（裁定 #15）出生即在门内。
        对账留痕：原文断言 usable == {ok}（三个 add_material 均为默认 user 来源）——
        现按来源分两侧断言，安全面只紧不松（pending/rejected 依旧被挡）。"""
        pid = project["project_id"]
        upload = mr.add_material(pid, "人工上传（免评审）", origin="user")
        pend = mr.add_material(pid, "自采待评审", origin="collected")
        no = mr.add_material(pid, "自采被拒绝", origin="collected")
        mr.set_review(no["material_id"], "rejected")

        usable = {m["material_id"] for m in mr.approved_materials(pid)}
        assert usable == {upload["material_id"]}, usable
        # 管理/评审界面仍应看得见 pending 与 rejected（否则没法批）
        assert len(mr.list_materials(pid)) == 3
        assert {m["material_id"] for m in mr.list_materials(pid, review_status="pending")} == {pend["material_id"]}
        # 批准后自采放行（硬门对已批自采照旧开）
        mr.set_review(pend["material_id"], "approved")
        assert pend["material_id"] in {m["material_id"] for m in mr.approved_materials(pid)}
        assert no["material_id"] not in {m["material_id"] for m in mr.approved_materials(pid)}

    def test_collected_pending_is_not_in_gate(self, project):
        """自采出生 pending ⇒ 不在门内（硬门前提原样）。
        对账留痕：原名 test_default_pending_is_not_in_gate（原文「还没人看过」走默认 user）——
        人工上传侧已按裁定 #15 免评审（见上一测），前提测试移到 collected 侧。"""
        mr.add_material(project["project_id"], "还没人看过的自采", origin="collected")
        assert mr.approved_materials(project["project_id"]) == []

    def test_review_note_and_timestamp_recorded(self, project):
        m = mr.add_material(project["project_id"], "x")
        assert mr.set_review(m["material_id"], "approved", note="看了原件，可用")
        got = mr.get_material(m["material_id"])
        assert got["review_status"] == "approved"
        assert got["review_note"] == "看了原件，可用"
        assert got["reviewed_at"]

    def test_set_review_unknown_id_returns_false(self, db):
        assert mr.set_review("mat_不存在", "approved") is False

    def test_invalid_status_rejected(self, project):
        m = mr.add_material(project["project_id"], "x")
        with pytest.raises(ValueError):
            mr.set_review(m["material_id"], "maybe")


# ------------------------------------------------------------------ 两个轴
class TestTwoAxes:
    def test_task_role_is_independent_of_source_tier(self, project):
        """公司制度例：**来源层级低**但**是本任务的准则**——两轴必须能并存。

        这正是"不能把材料按一个分数排序"的原因。
        """
        pid = project["project_id"]
        m = mr.add_material(pid, "公司差旅制度", origin="user")
        assert m["source_tier"] == "T1"          # 轴 A：低于国标（T0）
        assert m["task_role"] is None            # 轴 B：还没声明
        assert mr.set_task_role(m["material_id"], "criterion")
        got = mr.get_material(m["material_id"])
        assert got["task_role"] == "criterion"
        assert got["source_tier"] == "T1"        # 两轴互不影响

    def test_user_can_override_tier_and_it_is_recorded(self, project):
        """业主明说"用户可以改效力层级"⇒ 改完要能看出是**人**定的（留痕）。"""
        m = mr.add_material(project["project_id"], "某白皮书", origin="collected")
        assert m["tier_source"] == "system"
        assert mr.set_tier(m["material_id"], "T2", source="user", reason="监管机构官网原文")
        got = mr.get_material(m["material_id"])
        assert (got["source_tier"], got["tier_source"]) == ("T2", "user")
        assert got["tier_reason"] == "监管机构官网原文"

    def test_invalid_tier_and_role_rejected(self, project):
        m = mr.add_material(project["project_id"], "x")
        with pytest.raises(ValueError):
            mr.set_tier(m["material_id"], "T9")
        with pytest.raises(ValueError):
            mr.set_tier(m["material_id"], "T2", source="god")
        with pytest.raises(ValueError):
            mr.set_task_role(m["material_id"], "boss")

    def test_lifecycle_promote(self, project):
        m = mr.add_material(project["project_id"], "x")
        assert m["lifecycle"] == "ephemeral"
        assert mr.set_lifecycle(m["material_id"], "promoted")
        assert mr.get_material(m["material_id"])["lifecycle"] == "promoted"
        with pytest.raises(ValueError):
            mr.set_lifecycle(m["material_id"], "forever")

    def test_tier_labels_cover_all_tiers(self):
        assert set(mr.TIER_LABELS) == set(mr.TIERS)


# ------------------------------------------------------------------ 切片 / 引用
class TestChunks:
    def test_chunks_keep_char_offsets_and_order(self, project):
        m = mr.add_material(project["project_id"], "财报.pdf")
        n = mr.add_chunks(m["material_id"], [
            {"text": "营业收入 100 亿元", "char_start": 0, "char_end": 14, "page": 3},
            {"text": "净利润 10 亿元", "char_start": 15, "char_end": 27, "page": 4},
        ])
        assert n == 2
        got = mr.material_chunks(m["material_id"])
        assert [c["ord"] for c in got] == [0, 1]
        assert got[0]["char_start"] == 0 and got[0]["char_end"] == 14
        assert got[1]["page"] == 4
        assert mr.chunk_count(m["material_id"]) == 2

    def test_empty_text_chunks_are_skipped(self, project):
        m = mr.add_material(project["project_id"], "x")
        assert mr.add_chunks(m["material_id"], [{"text": ""}, {"text": "  "}]) == 0
        assert mr.chunk_count(m["material_id"]) == 0

    def test_char_end_defaults_to_text_length(self, project):
        m = mr.add_material(project["project_id"], "x")
        mr.add_chunks(m["material_id"], [{"text": "abcde", "char_start": 7}])
        c = mr.material_chunks(m["material_id"])[0]
        assert (c["char_start"], c["char_end"]) == (7, 12)


# ------------------------------------------------------------------ 检索（硬门 + 引用字段）
class TestSearch:
    def _seed(self, pid):
        m = mr.add_material(pid, "2025年报", origin="user")
        mr.add_chunks(m["material_id"], [
            {"text": "公司营业收入为一百亿元，同比增长百分之十。", "char_start": 0,
             "char_end": 22, "page": 12},
            {"text": "主要风险：原材料价格波动。", "char_start": 23, "char_end": 38, "page": 30},
        ])
        mr.set_review(m["material_id"], "approved")
        return m

    def test_search_only_returns_approved(self, project):
        """**硬门写在 SQL 里**：未批准的材料不可能被搜出来。"""
        pid = project["project_id"]
        self._seed(pid)                                   # approved
        pend = mr.add_material(pid, "未批准的研报", origin="collected")
        mr.add_chunks(pend["material_id"],
                      [{"text": "公司营业收入为二百亿元，翻倍增长。", "char_start": 0,
                        "char_end": 20, "page": 1}])
        hits = mr.search_materials(pid, "营业收入")
        assert hits, "已批准材料应能搜到"
        assert {h["material_id"] for h in hits} == {h["material_id"] for h in hits}
        assert all(h["title"] != "未批准的研报" for h in hits)

    def test_rejected_material_is_not_searchable(self, project):
        pid = project["project_id"]
        m = self._seed(pid)
        mr.set_review(m["material_id"], "rejected")
        assert mr.search_materials(pid, "营业收入") == []

    def test_search_returns_citation_fields(self, project):
        """命中的每一项都要带"能标注 + 能点回原文"的字段（可见性硬需求）。"""
        pid = project["project_id"]
        self._seed(pid)
        h = mr.search_materials(pid, "营业收入")[0]
        for k in ("material_id", "chunk_id", "text", "char_start", "char_end", "page",
                  "title", "source_tier", "task_role", "tier_label", "role_label"):
            assert k in h, k
        assert h["page"] == 12 and h["char_start"] == 0 and h["char_end"] == 22
        assert h["tier_label"] == mr.TIER_LABELS["T1"]
        assert h["role_label"] == "未声明效力"

    def test_search_labelling_shows_both_axes(self, project):
        pid = project["project_id"]
        m = self._seed(pid)
        mr.set_task_role(m["material_id"], "criterion")     # 轴 B
        mr.set_tier(m["material_id"], "T2", source="user", reason="归到权威第三方")
        h = mr.search_materials(pid, "营业收入")[0]
        assert h["source_tier"] == "T2" and h["role_label"] == "本任务准则"

    def test_search_is_project_scoped(self, project):
        """A 项目的材料不该出现在 B 项目的检索结果里。"""
        other = mr.create_project("另一个项目")
        self._seed(project["project_id"])
        assert mr.search_materials(other["project_id"], "营业收入") == []

    def test_search_junk_query_does_not_raise(self, project):
        self._seed(project["project_id"])
        assert mr.search_materials(project["project_id"], "") == []
        # FTS 语法字符不应把提问打崩（无命中优于 500）
        assert mr.search_materials(project["project_id"], '"(') == []

    def test_limit_respected(self, project):
        pid = project["project_id"]
        m = mr.add_material(pid, "多段材料")
        mr.add_chunks(m["material_id"], [
            {"text": f"营业收入 第{i}段", "char_start": i * 10, "char_end": i * 10 + 8}
            for i in range(6)])
        mr.set_review(m["material_id"], "approved")
        assert len(mr.search_materials(pid, "营业收入", limit=2)) == 2

    def test_bad_arguments_raise_instead_of_silently_finding_nothing(self, project):
        """**坏参数不许静默变成"没有命中"**（verifier 2026-09-17 报的 LOW）。

        原先 `int(limit)` 在 try 内，`limit=None` 的 TypeError 被兜底 `except Exception`
        吃掉 → 静默 `[]`。这与本次战役修掉的 `allow_deep="false"` 是**同一类 bug**：
        调用方参数写错，用户被告知"材料里没找到"，而不是"你的调用坏了"。
        非 `str` 的 query 原先会从 jieba 深处冒 `AttributeError`（契约差）→ 现在显式 `TypeError`。
        """
        pid = project["project_id"]
        with pytest.raises(TypeError, match="limit"):
            mr.search_materials(pid, "营业收入", limit=None)      # type: ignore[arg-type]
        with pytest.raises(TypeError, match="limit"):
            mr.search_materials(pid, "营业收入", limit="3")        # type: ignore[arg-type]
        with pytest.raises(TypeError, match="limit"):
            mr.search_materials(pid, "营业收入", limit=True)       # type: ignore[arg-type]
        for bad in (None, 3, ["营业收入"], {"q": "x"}):
            with pytest.raises(TypeError, match="query"):
                mr.search_materials(pid, bad)                      # type: ignore[arg-type]

    def test_real_sql_failure_is_loud_not_empty(self, project, monkeypatch, caplog):
        """**表/SQL 真坏了必须留痕**，不能伪装成"材料里没有命中"。

        兜底 `except Exception` 的最坏后果就是这个：把
        "material_fts 不存在 / SQL 写错列名" 变成一次安静的空结果，而空结果会被
        上层解释成"材料不支持这个结论"。现按法条侧同款只兜 `sqlite3.OperationalError`
        并 warning。
        """
        import sqlite3
        pid = project["project_id"]

        class _Boom:
            def execute(self, *_a, **_k):
                raise sqlite3.OperationalError("no such table: material_fts")

        monkeypatch.setattr(mr, "get_db_connection", lambda: _Boom())
        with caplog.at_level("WARNING"):
            assert mr.search_materials(pid, "营业收入") == []
        assert any("材料 FTS 查询失败" in r.message for r in caplog.records), \
            "真 SQL 失败必须留下 warning，否则'没有命中'与'检索坏了'无法区分"

    def test_programming_error_is_not_swallowed(self, project, monkeypatch):
        """**非 sqlite 异常必须冒出来**（这是从兜底 `Exception` 收窄的全部意义）。"""
        pid = project["project_id"]

        class _Boom:
            def execute(self, *_a, **_k):
                raise RuntimeError("SQL 里写错了列名（模拟编程错误）")

        monkeypatch.setattr(mr, "get_db_connection", lambda: _Boom())
        with pytest.raises(RuntimeError):
            mr.search_materials(pid, "营业收入")


# ------------------------------------------------------------------ 删除
class TestDelete:
    def test_delete_material_removes_chunks_and_index(self, project):
        pid = project["project_id"]
        m = mr.add_material(pid, "待删材料")
        mr.add_chunks(m["material_id"], [{"text": "营业收入一百亿", "char_start": 0,
                                          "char_end": 7}])
        mr.set_review(m["material_id"], "approved")
        assert mr.search_materials(pid, "营业收入")
        assert mr.delete_material(m["material_id"])
        assert mr.get_material(m["material_id"]) is None
        assert mr.chunk_count(m["material_id"]) == 0
        assert mr.search_materials(pid, "营业收入") == []


# ------------------------------------------------------------------ 隔离
class TestLawChainIsolation:
    def test_material_ops_do_not_touch_law_chain(self, project):
        """**行为级**证明零耦合：材料操作前后，法条链三张表行数完全不变。

        为什么值得单测：本平面存在的**全部理由**就是"别污染法条链"
        （doc_meta.standard_no NOT NULL UNIQUE 装不下财报，且它是取证链承重墙）。
        """
        conn = db = None  # noqa: F841 — 见下方 fixture 取连接
        from src.core.storage.sqlite_db import get_db_connection
        conn = get_db_connection()
        tables = ("doc_meta", "clause_revision", "source_span")
        before = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}

        pid = project["project_id"]
        m = mr.add_material(pid, "财报.pdf", origin="user",
                            content_hash="deadbeef", raw_path="C:/x/财报.pdf")
        mr.add_chunks(m["material_id"], [{"text": "正文", "char_start": 0, "char_end": 2}])
        mr.set_review(m["material_id"], "approved")
        mr.set_tier(m["material_id"], "T2", source="user", reason="r")
        mr.set_task_role(m["material_id"], "reference")
        mr.set_lifecycle(m["material_id"], "promoted")
        mr.link_doc(m["material_id"], "doc_故意不存在的回指")

        after = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
        assert before == after, (before, after)

    def test_link_doc_only_writes_material_side(self, project):
        """Track L 的回指**写在材料侧**（doc_id 列），不改 doc_meta。"""
        m = mr.add_material(project["project_id"], "某国标", origin="collected", kind="legal")
        assert mr.link_doc(m["material_id"], "doc_abc123")
        assert mr.get_material(m["material_id"])["doc_id"] == "doc_abc123"


# ------------------------------------------------------------------ 存储位置
class TestStorageLocation:
    def test_materials_dir_is_under_data_dir_and_per_project(self, project, _isolate_data_dir):
        """材料原件放数据区（代码树零运行产物），且**按项目分目录**。"""
        d = mr.materials_dir(project["project_id"])
        assert d.exists() and d.is_dir()
        assert project["project_id"] in str(d)
        assert str(mr.materials_root()).startswith(str(_isolate_data_dir))
