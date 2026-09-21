# -*- coding: utf-8 -*-
"""第 6 步「按目录范围提问」：**检索层**的范围过滤（六条通道）+ 答案层的范围契约。

## 这组用例在守什么（每条都有反向）

1. **范围内答得出 / 范围外答不出**（两个方向都要）——范围是真的在**检索层**生效，
   不是"取回 top_k 之后再筛"：那条老路会让范围外的命中**吃掉候选名额**，症状是
   "范围内明明有、却答不出"（下面的 `test_scope_filter_is_in_retrieval_not_post_filter`
   专门钉它：范围外 3 条强命中 + 范围内 1 条弱命中、top_k=1 ⇒ 必须返回范围内那条）。
2. **六条召回通道**（exact / fts / vec / modality / legal_element / behavior_scope）
   **每一条**都被范围约束（不许只堵一条）。
3. **空范围绝不许退化成全库**（照 `folder_scope` / `scope/resolve` 的既有立论）：
   `doc_ids=[]` ⇒ 一条都不返回；答案层 `kb_doc_ids=[]` ⇒ **不做任何检索**、如实说"范围内没有"。
4. **两种"夹"不混**：`folder_id`（收藏夹）仍旧只对**证据**做后置过滤、**不动检索**；
   `kb_folder_ids`（知识库目录）才是检索层范围；两者同时给 ⇒ 证据是**交集**。
5. **目录不存在 ⇒ 报错（不是空范围、更不是全库）**：`KbScopeNotFound`（端点 404）。

⚠ 本文件**自己隔离**（私有临时数据目录，照 `tests/test_ks_answer.py` 的先例）：用例真的建库、
真的插条款，不隔离就会写进会话级共享库、污染别的模块（第 5 步被复核抓过一次）。
⚠ 向量通道那条**不依赖 BGE**：直接往 `clause_vec` 塞假向量（512 维）⇒ 模型离线也能验"向量通道被堵住"。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from src.core.domain.models import ClauseRevisionModel
from src.core.storage import clause_repo


@pytest.fixture(scope="module", autouse=True)
def _own_data_dir():
    """本模块私有的临时数据目录（跑完即弃；其他模块零影响，见文件头）。"""
    with tempfile.TemporaryDirectory(prefix="ks_scope_", ignore_cleanup_errors=True) as td:
        old = os.environ.get("KS_DATA_DIR")
        os.environ["KS_DATA_DIR"] = td
        from src.core import config
        config.reset_settings()
        from src.core.storage.sqlite_db import close_thread_connection, init_schema
        close_thread_connection()
        init_schema()
        yield Path(td)
        config.reset_settings()
        close_thread_connection()
        if old is None:
            os.environ.pop("KS_DATA_DIR", None)
        else:
            os.environ["KS_DATA_DIR"] = old


@pytest.fixture(autouse=True)
def _offline_embedder(monkeypatch):
    """向量引擎强制离线（与 `test_ks_answer` 同一手法）：不加载模型、不去下模型。"""
    from src.core.retrieval import embedder as _emb
    monkeypatch.setattr(_emb, "is_available", lambda: False)
    yield


def _clause(cid: str, no: str, text: str, doc: str, standard: str = "GB 50016-2022",
            modality: str | None = None, subject: str | None = None,
            behavior_scope: str | None = None, ktype: str = "rule") -> ClauseRevisionModel:
    return ClauseRevisionModel(
        clause_revision_id=cid, doc_id=doc, clause_key=f"key_{cid}",
        standard_no=standard, clause_number=no, title=None, content_text=text,
        knowledge_type=ktype, modality=modality,
        modality_strength={"严禁": 5, "不应": 4, "应": 3}.get(modality),
        subject=subject, behavior_scope=behavior_scope,
        legal_status="effective", page_start=1, page_end=1)


@pytest.fixture(scope="module")
def scope_db(_own_data_dir):
    """两篇文档：`in_doc`（**范围内**）与 `out_doc`（**范围外**），各带六条通道要用的条款。"""
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    docs = [
        dict(doc_id="in_doc", standard_no="GB 90001-2026", standard_name="范围内那份标准",
             short_code="GB90001", current_revision_id="r_in",
             domain_tags=["测试"], file_path="in.pdf", file_hash="h_in"),
        dict(doc_id="out_doc", standard_no="GB 90002-2026", standard_name="范围外那份标准",
             short_code="GB90002", current_revision_id="r_out",
             domain_tags=["测试"], file_path="out.pdf", file_hash="h_out"),
    ]
    for d in docs:
        clause_repo.insert_document(conn, d)
    clause_repo.insert_clauses([
        # 范围内：一条弱命中（FTS 只命中一个词）+ 六通道各一条
        _clause("in_weak", "1.0.1", "范围内的普通条款（只提到一次防火间距）", "in_doc"),
        _clause("in_exact", "5.2.3", "范围内的精确号条款：防火间距不应小于13m", "in_doc"),
        _clause("in_mod", "1.0.2", "范围内模态条款", "in_doc", modality="严禁"),
        _clause("in_sub", "1.0.3", "范围内义务主体条款", "in_doc", ktype="legal",
                subject="建设单位"),
        _clause("in_beh", "1.0.4", "范围内行为客体条款", "in_doc",
                behavior_scope="动火作业 审批"),
        # 范围外：三条**强命中**（同一批关键词反复出现）——正是"会被 top_k 吃掉"的那批
        _clause("out_hot1", "5.2.3", "范围外强命中：防火间距 防火间距 防火间距 不应小于13m", "out_doc",
                standard="GB 90002-2026"),
        _clause("out_hot2", "5.2.3", "范围外强命中：防火间距 防火间距 不应小于13m", "out_doc",
                standard="GB 90002-2026"),
        _clause("out_hot3", "1.0.9", "范围外强命中：防火间距与防火分区", "out_doc",
                standard="GB 90002-2026", modality="严禁", ktype="legal", subject="建设单位",
                behavior_scope="动火作业 审批"),
    ])
    return conn


IN_SCOPE = ["in_doc"]
OUT_SCOPE = ["out_doc"]


def _ids(rows) -> list[str]:
    return [r.clause_revision_id for r in rows]


# ═════════════ 1. 两个方向：范围内答得出 / 范围外答不出 ═════════════

def test_answer_is_findable_only_inside_the_scope(scope_db):
    """范围 = 范围内那篇 ⇒ 命中；范围 = 范围外那篇 ⇒ **同一条条款查不到**（两个方向都判）。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    hit = perform_hybrid_search("5.2.3", top_k=5, channels=["exact"], doc_ids=IN_SCOPE)
    assert "in_exact" in _ids(hit), f"范围内应当查得到那条：{_ids(hit)}"
    miss = perform_hybrid_search("5.2.3", top_k=5, channels=["exact"], doc_ids=OUT_SCOPE)
    assert "in_exact" not in _ids(miss), f"范围外**不许**返回范围内的条款：{_ids(miss)}"
    assert "out_hot1" in _ids(miss), "范围外那篇自己的条款应当查得到（否则是过度过滤）"


def test_unrestricted_search_still_sees_both(scope_db):
    """反向哨兵：不给范围（`doc_ids=None`）时**两篇都能查到** —— 证明上一条不是"检索坏了"。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    both = _ids(perform_hybrid_search("5.2.3", top_k=10, channels=["exact"]))
    assert "in_exact" in both and "out_hot1" in both, both


def test_scope_filter_is_in_retrieval_not_post_filter(scope_db):
    """**核心判据**：范围过滤必须发生在**检索层**。

    场景：范围外 3 条强命中 + 范围内 1 条弱命中，`top_k=1`。
      · 若过滤发生在"取回 top_k 之后"⇒ 候选按**全库**排序，前 1 名是范围外那条 ⇒ 筛完**空**、
        "范围内明明有却答不出"（这正是任务书点名要避免的那种实现）；
      · 在检索层过滤 ⇒ 候选里只有范围内那条 ⇒ **必须返回它**。
    """
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    res = perform_hybrid_search("防火间距 不应小于13m", top_k=1, channels=["fts"],
                                rerank=False, doc_ids=IN_SCOPE)
    assert _ids(res) == ["in_exact"], (
        "范围内那条没被返回 ⇒ 过滤很可能发生在取回之后（top_k 被范围外的命中吃掉了）："
        f"{_ids(res)}")


# ═════════════ 2. 六条通道都被堵住 ═════════════

def test_every_channel_is_restricted(scope_db):
    """六条召回通道**逐条**验证：范围外的那篇在任何一条通道上都进不来。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    cases = [
        ("exact", dict(query="5.2.3", channels=["exact"]), "in_exact"),
        ("fts", dict(query="防火间距", channels=["fts"]), "in_weak"),
        ("modality", dict(query="严禁使用", channels=["modality"],
                          modality_filter="严禁"), "in_mod"),
        ("legal_element", dict(query="建设单位", channels=["legal_element"],
                               subject_filter="建设单位"), "in_sub"),
        ("behavior_scope", dict(query="动火作业", channels=["behavior_scope"],
                                behavior_scope_filter="动火作业"), "in_beh"),
    ]
    for name, kwargs, expected_in in cases:
        rows = perform_hybrid_search(top_k=10, rerank=False, doc_ids=IN_SCOPE, **kwargs)
        ids = _ids(rows)
        assert expected_in in ids, f"通道 {name} 在范围内应当有命中：{ids}"
        assert not any(i.startswith("out_") for i in ids), \
            f"通道 {name} **没被范围堵住**：{ids}"
    # 向量通道单独判（不依赖模型，见下面那条）


def test_vec_channel_is_restricted_without_the_model(scope_db, monkeypatch):
    """**向量通道**也要被堵住 —— 直接塞假向量，模型离线也能验。

    ⚠ 实测口径（`var/tmp/probe-vec-scope.py`，sqlite-vec v0.1.9）：范围约束必须写成
    **子查询**（`clause_revision_id IN (SELECT … json_each(?))`）—— 字面量列表形式会走
    "先 KNN 再筛"（全局最近的两条都在范围外时返回**空**，那就是假报"范围内没有"）。
    """
    from src.core.retrieval import embedder as emb
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension
    conn = get_db_connection()
    load_vec_extension(conn)
    # 方向：in_weak 与查询向量最**远**、out_hot1/2 最近 ⇒ 若"先 KNN 再筛"，范围内一条都不剩
    vecs = {
        "in_weak": [0.0] * 511 + [1.0],
        "out_hot1": [1.0] + [0.0] * 511,
        "out_hot2": [0.9, 0.1] + [0.0] * 510,
    }
    # ⚠ 再灌 25 条**范围外**、与查询向量完全一致的近邻：全局 top-20 全是它们 ⇒
    #   "先 KNN 再筛"的写法会返回**空**（假报"范围内没有"）；带约束地找 k 个才会返回范围内那条。
    clause_repo.insert_clauses([
        _clause(f"out_bulk{i}", f"9.9.{i}", "范围外批量近邻", "out_doc",
                standard="GB 90002-2026") for i in range(25)
    ])
    for cid, v in vecs.items():
        conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (cid,))
        conn.execute("INSERT INTO clause_vec(clause_revision_id, embedding) VALUES (?,?)",
                     (cid, json.dumps(v)))
    for i in range(25):
        conn.execute("DELETE FROM clause_vec WHERE clause_revision_id=?", (f"out_bulk{i}",))
        conn.execute("INSERT INTO clause_vec(clause_revision_id, embedding) VALUES (?,?)",
                     (f"out_bulk{i}", json.dumps([1.0] + [0.0] * 511)))
    conn.commit()
    monkeypatch.setattr(emb, "is_available", lambda: True)
    monkeypatch.setattr(emb, "embed_query", lambda q: [1.0] + [0.0] * 511)
    rows = perform_hybrid_search("随便问点什么", top_k=5, channels=["vec"], rerank=False,
                                 doc_ids=IN_SCOPE)
    ids = _ids(rows)
    assert ids, ("向量通道在范围内**一条都没返回** ⇒ 范围约束写成了「先 KNN 再筛」"
                 "（范围外的近邻把 k=20 的名额吃光了）")
    assert not any(i.startswith("out_") for i in ids), f"向量通道没被范围堵住：{ids}"


# ═════════════ 3. 空范围绝不退化成全库 ═════════════

def test_empty_scope_returns_nothing_never_the_whole_kb(scope_db):
    """`doc_ids=[]` = "范围内一篇都没有" ⇒ **一条都不返回**（绝不退化成全库）。"""
    from src.core.retrieval.hybrid_engine import perform_hybrid_search, search_with_details
    res = perform_hybrid_search("5.2.3", top_k=10, doc_ids=[])
    assert res == [], f"空范围竟然返回了 {_ids(res)}（= 退化成全库了）"
    out = search_with_details("5.2.3", top_k=10, doc_ids=[])
    assert out["results"] == [] and out["expanded"] == []
    assert out["debug"]["doc_scope"] == {"active": True, "doc_count": 0, "empty": True}


# ═════════════ 4. 答案层：范围回显 / 未知目录 / 两种"夹"不混 ═════════════

@pytest.fixture(scope="module")
def kb_folders(scope_db):
    """知识库目录：顶层「甲」挂着 in_doc，顶层「乙」挂着 out_doc（返回两个 id）。"""
    from src.core.knowledge import folder_store as fs
    a = fs.create_folder("甲", None)
    b = fs.create_folder("乙", None)
    fs.add_member(a["folder_id"], "file", "in_doc")
    fs.add_member(b["folder_id"], "file", "out_doc")
    return {"in": a["folder_id"], "out": b["folder_id"]}


def test_answer_scope_is_echoed_and_restricts_retrieval(scope_db, kb_folders, monkeypatch):
    """`ks_answer.answer(kb_folder_ids=[甲])`：检索被限定（范围外那篇的证据进不来）+ 范围如实回显。

    ⚠ 这条**不 mock 检索**（第 5 步踩过"自己验自己"的坑）：判的是**可观察的结果** ——
    范围外那份标准里堆了三处强命中，`top_k=2` 时若过滤发生在"取回之后"，
    候选名额会被它们占满 ⇒ 证据里**看不到范围内那条**。
    """
    from src.core.llm import ks_answer
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    data = ks_answer.answer("5.2.3 防火间距", params={
        "kb_folder_ids": [kb_folders["in"]], "top_k": 2, "channels": ["exact", "fts"]})
    assert data["scope"]["doc_count"] == 1 and data["scope"]["empty"] is False
    assert data["scope"]["folder_count"] == 1
    docs = {ev["doc_id"] for ev in data["evidence"]}
    assert docs == {"in_doc"}, f"范围外的条款混进了证据（或范围内那条没进来）：{docs}"
    assert any("知识库目录范围" in n for n in data["notes"]), data["notes"]
    assert data["_meta"]["kb_scope"]["doc_count"] == 1


def test_answer_rejects_unknown_folder_instead_of_falling_back(scope_db):
    """目录不存在 ⇒ **报错**（`KbScopeNotFound`），绝不静默当成"没给范围"全库检索。"""
    from src.core.llm import ks_answer
    with pytest.raises(ks_answer.KbScopeNotFound):
        ks_answer.answer("5.2.3", params={"kb_folder_ids": ["fld_does_not_exist"]})
    with pytest.raises(ValueError):
        ks_answer.answer("5.2.3", params={"kb_folder_ids": []})
    with pytest.raises(ValueError):
        ks_answer.answer("5.2.3", params={"kb_doc_ids": []})


def test_answer_with_empty_doc_scope_does_not_search(scope_db, monkeypatch):
    """空范围（目录存在但里面一篇没有）⇒ **不检索**、如实说"范围内没有"，且**不调 LLM 拿全库编答案**。"""
    from src.core.knowledge import folder_store as fs
    from src.core.llm import ks_answer
    empty = fs.create_folder("空目录", None)["folder_id"]
    called: list = []

    def _boom(*a, **kw):
        called.append(1)
        raise AssertionError("空范围不该发生检索")

    monkeypatch.setattr("src.core.retrieval.hybrid_engine.perform_hybrid_search", _boom)
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    data = ks_answer.answer("5.2.3", params={"kb_folder_ids": [empty]})
    assert called == [], "空范围竟然走了检索（= 可能退化成全库）"
    assert data["evidence"] == []
    assert data["scope"]["empty"] is True and data["scope"]["doc_count"] == 0
    assert any("没有做任何检索" in n for n in data["notes"]), data["notes"]


def test_bookmark_folder_and_kb_scope_are_two_different_things(scope_db, kb_folders, monkeypatch):
    """两种"夹"不混：`folder_id`（收藏夹）**不动检索**（只后置过滤证据），`kb_folder_ids` 才限定检索。

    同时给时证据是**交集**：知识库范围先限定检索，收藏夹再过滤证据。
    ⚠ 判据全部是**可观察结果**（不 spy 内部调用）：
      · 只给收藏夹（收藏的是**范围外**那篇的条款）⇒ 证据**非空且全在范围外**
        —— 若收藏夹把检索也限定了（或把它当成知识库范围），这里会是空；
      · 同时给"知识库范围=甲（in_doc）"+ 同一个收藏夹 ⇒ 证据**空**（交集），而 scope 回显 doc_count=1。
    """
    from src.core.llm import ks_answer
    from src.core.storage import user_data
    monkeypatch.setattr(ks_answer, "_stream_llm",
                        lambda messages: iter(["【推导区】\n推导\n【结论区】\n结论"]))
    folder = user_data.create_folder("范围测试收藏夹")
    user_data.add_bookmark("key_out_hot1", folder_id=folder["folder_id"])
    only_bm = ks_answer.answer("5.2.3 防火间距", params={
        "folder_id": folder["folder_id"], "channels": ["exact", "fts"]})
    bm_docs = {ev["doc_id"] for ev in only_bm["evidence"]}
    assert bm_docs == {"out_doc"}, (
        f"收藏夹那一路只该**后置过滤**证据（不该去动检索层）：{bm_docs}")
    assert only_bm["scope"] is None, "没给知识库范围时 scope 必须是 None（不是空对象）"
    both = ks_answer.answer("5.2.3 防火间距", params={
        "kb_folder_ids": [kb_folders["in"]], "folder_id": folder["folder_id"],
        "channels": ["exact", "fts"]})
    assert both["scope"]["doc_count"] == 1, both["scope"]
    assert both["evidence"] == [], (
        "两者同时给时应当是**交集**（知识库范围限定检索 + 收藏夹过滤证据）⇒ 这里应为空："
        f"{[ev['doc_id'] for ev in both['evidence']]}")


def test_api_returns_404_for_unknown_kb_folder(client, kb_folders):
    """端点级：`POST /api/v1/ks/answer` 带不存在的目录 ⇒ **404**（不是 200 + 空答案）。"""
    from _kb_folder_api_fixtures import api, error_code
    c, token = client
    st, code = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": ["fld_nope_scope"]}}))
    assert (st, code) == (404, "kb_scope_not_found"), (st, code)
    st2, code2 = error_code(api(c, token, "post", "/api/v1/ks/answer", json={
        "query": "5.2.3", "params": {"kb_folder_ids": []}}))
    assert (st2, code2) == (422, "bad_request"), (st2, code2)
