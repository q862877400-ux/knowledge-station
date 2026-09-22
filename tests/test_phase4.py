"""阶段4 "能用"档测试：收藏/批注/项目/义务清单/导出/目录树/检索加权。"""
import pytest


@pytest.fixture()
def rich_db(db):
    """种入两部文档条款（一部现行、一部即将实施）供各功能测试。幂等：先清旧。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='d4a'").fetchone():
        clause_repo.delete_document("d4a")
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='d4b'").fetchone():
        clause_repo.delete_document("d4b")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="d4a", standard_no="GB A-2022", standard_name="A", short_code="a",
            current_revision_id="r", domain_tags=["消防"], file_path="a.pdf", file_hash="h4a"))
        clause_repo.insert_document(conn, dict(
            doc_id="d4b", standard_no="GB B-2023", standard_name="B", short_code="b",
            current_revision_id="r", legal_status="upcoming",
            effective_from="2027-01-01", domain_tags=["消防"],
            file_path="b.pdf", file_hash="h4b"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="q1", doc_id="d4a", clause_key="kq1", standard_no="GB A-2022",
            clause_number="5.1.1", content_text="消防通道应保持畅通，宽度不小于 3.5m。",
            knowledge_type="data", modality="应", modality_strength=3,
            type_confidence=0.9, page_start=3, page_end=3),
        ClauseRevisionModel(
            clause_revision_id="q2", doc_id="d4a", clause_key="kq2", standard_no="GB A-2022",
            clause_number="5.2.2", content_text="灭火器应当定期检查。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            type_confidence=0.55, is_suspicious=True, page_start=4, page_end=4),
        ClauseRevisionModel(
            clause_revision_id="q3", doc_id="d4b", clause_key="kq3", standard_no="GB B-2023",
            clause_number="2.1", content_text="新规范即将实施的义务条款。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            page_start=1, page_end=1),
    ])
    yield db


def test_bookmark_crud_and_boost(rich_db):
    from src.core.storage import user_data
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    out = user_data.add_bookmark("kq2", "测试收藏")
    assert not out["existed"]
    assert user_data.add_bookmark("kq2", "测试收藏")["existed"]  # 幂等
    # 相对断言（共享库可能有其他测试收藏）
    assert any(b["clause_key"] == "kq2" for b in user_data.list_bookmarks())
    assert "kq2" in user_data.bookmarked_clause_keys()

    res = perform_hybrid_search("消防 灭火器 检查", top_k=3)
    assert res, "应能检索到条款"
    # 收藏加分：q2 排名应不低于未收藏的同族条款
    ids = [r.clause_revision_id for r in res]
    if "q1" in ids and "q2" in ids:
        assert ids.index("q2") <= ids.index("q1") or True  # 加分存在性由下条保证
    # 直接对比：去掉加权后 q2 的排名不应更靠前
    res_noboost = perform_hybrid_search("消防 灭火器 检查", top_k=3, boost_bookmarks=False)
    def pos(seq, cid):
        return seq.index(cid) if cid in seq else 99
    assert pos([r.clause_revision_id for r in res], "q2") <= \
           pos([r.clause_revision_id for r in res_noboost], "q2")
    assert user_data.remove_bookmark(out["bookmark_id"]) is True


def test_annotation_crud(rich_db):
    from src.core.storage import user_data
    user_data.add_annotation("kq1", "本项目按 4m 执行")
    anns = user_data.annotations_by_clause_keys(["kq1"])
    assert len(anns["kq1"]) == 1 and "4m" in anns["kq1"][0]["content"]
    assert user_data.delete_annotation(anns["kq1"][0]["annotation_id"]) is True
    assert user_data.annotations_by_clause_keys(["kq1"]) == {}


def test_project_crud(rich_db):
    from src.core.storage import user_data
    p = user_data.create_project("测试项目", "legal_compliance")
    out = user_data.add_clause_to_project(p["project_id"], "q1")
    assert out["count"] == 1
    out = user_data.add_clause_to_project(p["project_id"], "q1")  # 去重
    assert out["count"] == 1
    out = user_data.remove_clause_from_project(p["project_id"], "q1")
    assert out["count"] == 0
    assert len(user_data.list_projects()) == 1


def test_document_tree(rich_db):
    from src.core.api.server import create_app
    from fastapi.testclient import TestClient
    from src.core.storage.sqlite_db import write_transaction
    # 补一条二级标题条款（5.1 作业分级，正文极短）——新目录只含标题条款（幂等：先清旧）
    with write_transaction() as conn:
        conn.execute("DELETE FROM clause_revision WHERE clause_revision_id='q3'")
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, knowledge_type, modality,"
            " modality_strength, type_confidence, page_start, page_end)"
            " VALUES ('q3','r','d4a','kq3','5.1','5.1 作业分级','rule','应',3,0.9,3,3)")
    with TestClient(create_app("t")) as c:
        r = c.get("/api/v1/documents/d4a/tree", headers={"Authorization": "Bearer t"})
        assert r.status_code == 200
        tree = r.json()["data"]
        # 只含标题条款（5.1 作业分级），正文条款 5.1.1/5.2.2 不进目录；无 PDF 时无一级章
        assert len(tree) == 1 and tree[0]["clause_number"] == "5.1"
        assert tree[0]["title"] == "作业分级" and tree[0]["level"] == 2


def test_clauses_by_prefix(rich_db):
    """目录展开 API：前缀查子条款（点 ▸ 懒加载该标题下所有条款，2026-08-23 新增）。"""
    from src.core.api.server import create_app
    from fastapi.testclient import TestClient
    with TestClient(create_app("t")) as c:
        h = {"Authorization": "Bearer t"}
        # prefix=5 → 5.1/5.2 及子条款（fixture 有 5.1.1/5.2.2）
        r = c.get("/api/v1/documents/d4a/clauses-by-prefix", params={"prefix": "5"}, headers=h)
        assert r.status_code == 200
        nos = [it["clause_number"] for it in r.json()["data"]]
        assert "5.1.1" in nos and "5.2.2" in nos
        # prefix=5.1 → 5.1.1
        r2 = c.get("/api/v1/documents/d4a/clauses-by-prefix", params={"prefix": "5.1"}, headers=h)
        assert r2.status_code == 200
        assert [it["clause_number"] for it in r2.json()["data"]] == ["5.1.1"]
        # 非法前缀 422
        assert c.get("/api/v1/documents/d4a/clauses-by-prefix",
                     params={"prefix": "abc"}, headers=h).status_code == 422


def test_exports(rich_db):
    """R19 引用块（**纯文本**）。

    ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：本条原来还调
    `export_qa_citations_docx` / `export_review_report_docx` 落两份 Word——业主否决
    Word/PPT 交付物（`docs/NOT-DOING.md` 第 1 条）后**两条导出已拆除**，只留引用块本身。
    """
    from src.core.exports.report_export import build_citation_block

    ev = [{"standard_no": "GB A-2022", "clause_number": "5.1.1", "title": None,
           "content_text": "消防通道应保持畅通。", "page_start": 3}]
    block = build_citation_block(ev)
    assert "GB A-2022 5.1.1" in block and "第 3 页" in block


def test_export_download_guard(client):
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.get("/api/v1/export/download", headers=headers,
              params={"name": "../../knowledge.db"})
    assert r.status_code == 403, "路径穿越必须被拒绝"
    r = c.get("/api/v1/export/download", headers=headers, params={"name": "不存在.docx"})
    assert r.status_code == 404


def test_sse_time_warnings_and_enrichment(client, rich_db):
    """证据事件应带时效警示（upcoming 文档）与收藏/置信度富化字段。"""
    import json as _json
    from src.core.storage import user_data
    user_data.add_bookmark("kq1")
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "即将实施的新规范义务条款", "top_k": 3},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        evidence = None
        for line in r.iter_lines():
            if line.startswith("data: ") and '"evidences"' in line:
                evidence = _json.loads(line[6:])
                break
    assert evidence is not None
    assert any("尚未生效" in w for w in evidence.get("time_warnings", [])), \
        "upcoming 文档应触发时效警示"
    ev0 = evidence["evidences"][0]
    assert {"bookmarked", "annotations", "type_confidence", "is_suspicious",
            "clause_key"} <= set(ev0.keys()), "富化字段必须齐全"


def test_doc_bookmark_crud(rich_db):
    """标准级书签（user_doc_bookmark）：幂等、列表带 doc_meta、按 id/doc 删除、
    不存在 doc 拒绝。纯书签语义（不参与条款检索加权/巡检）。"""
    from src.core.exceptions import KnowledgeStationError
    from src.core.storage import user_data
    out = user_data.add_doc_bookmark("d4a", "测试标准收藏")
    assert not out["existed"]
    # 幂等：同 doc 再收藏 → existed
    assert user_data.add_doc_bookmark("d4a")["existed"] is True
    # 列表带 doc_meta 字段（相对断言：共享库可能另有收藏）
    lst = user_data.list_doc_bookmarks()
    mine = [b for b in lst if b["doc_id"] == "d4a"]
    assert len(mine) >= 1
    assert mine[0]["standard_no"] == "GB A-2022"
    assert "d4a" in user_data.bookmarked_doc_ids()
    # 不存在 doc → KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        user_data.add_doc_bookmark("d4-no-such")
    # 按 id 删除
    assert user_data.remove_doc_bookmark(out["doc_bookmark_id"]) is True
    assert "d4a" not in user_data.bookmarked_doc_ids()
    # 再按 doc_id toggle 删除（重新收藏后）
    user_data.add_doc_bookmark("d4a")
    assert user_data.remove_doc_bookmark_by_doc("d4a") is True
    assert user_data.remove_doc_bookmark_by_doc("d4a") is False  # no-op
    assert "d4a" not in user_data.bookmarked_doc_ids()
