"""收藏夹目录（2026-10 收藏目录功能）：user_data CRUD / 移动 / folder_scope /
server 端点 / ks_answer 夹内提问过滤链。

设计裁决（业主批准）：
- 一条收藏同一时间只属于一个夹（folder_id 单列，改夹 = 移动）。
- 删夹 → 收藏回「未分类」（folder_id 置 NULL），绝不连坐删收藏。
- 夹内提问检索范围 = 夹内标准级收藏（整本 doc）∪ 夹内条款级收藏（单条）。
- 夹不存在/查询失败 → 过滤不执行 + notes 如实降级，绝不静默放全库。
"""
import pytest


@pytest.fixture()
def folder_db(db):
    """种一部文档两条条款 + 两个收藏夹，供夹功能测试。幂等：先清旧。"""
    from src.core.storage import user_data
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    # 清残留（会话级临时库，但 id 常量需幂等）
    for t in ("user_bookmark", "user_doc_bookmark", "user_bookmark_folder"):
        db.execute(f"DELETE FROM {t}")
    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='bfa'").fetchone():
        clause_repo.delete_document("bfa")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="bfa", standard_no="GB FA-2024", standard_name="夹测试标准",
            short_code="fa", current_revision_id="r", domain_tags=["消防"],
            file_path="fa.pdf", file_hash="hfa"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id="bfq1", doc_id="bfa", clause_key="bfk1",
            standard_no="GB FA-2024", clause_number="5.1.1",
            content_text="消防通道应保持畅通，宽度不小于 3.5m。",
            knowledge_type="data", modality="应", modality_strength=3,
            type_confidence=0.9, page_start=3, page_end=3),
        ClauseRevisionModel(
            clause_revision_id="bfq2", doc_id="bfa", clause_key="bfk2",
            standard_no="GB FA-2024", clause_number="5.2.2",
            content_text="灭火器应当定期检查。",
            knowledge_type="rule", modality="应当", modality_strength=3,
            type_confidence=0.55, page_start=4, page_end=4),
    ])
    user_data.create_folder("收藏夹一")
    user_data.create_folder("收藏夹二")
    yield db
    for t in ("user_bookmark", "user_doc_bookmark", "user_bookmark_folder"):
        db.execute(f"DELETE FROM {t}")


def _fid(db, name: str) -> str:
    return db.execute(
        "SELECT folder_id FROM user_bookmark_folder WHERE folder_name=?",
        (name,)).fetchone()["folder_id"]


# ---------- user_data：夹 CRUD ----------

def test_folder_crud(folder_db):
    from src.core.storage import user_data
    from src.core.exceptions import KnowledgeStationError
    lst = {f["folder_name"] for f in user_data.list_folders()}
    assert lst == {"收藏夹一", "收藏夹二"}

    # 空名 / 重名拒绝
    with pytest.raises(KnowledgeStationError):
        user_data.create_folder("  ")
    with pytest.raises(KnowledgeStationError):
        user_data.create_folder("收藏夹一")

    # 重命名 + 改回
    f1 = _fid(folder_db, "收藏夹一")
    assert user_data.rename_folder(f1, "新名字")["folder_name"] == "新名字"
    assert user_data.rename_folder(f1, "收藏夹一")["folder_name"] == "收藏夹一"
    with pytest.raises(KnowledgeStationError):
        user_data.rename_folder("bmf_no_such", "x")


def test_folder_delete_keeps_bookmarks(folder_db):
    """删夹 → 收藏回未分类（folder_id NULL），收藏行本身绝不删。"""
    from src.core.storage import user_data
    f1 = _fid(folder_db, "收藏夹一")
    user_data.add_doc_bookmark("bfa", folder_id=f1)
    user_data.add_bookmark("bfk1", folder_id=f1)

    out = user_data.delete_folder(f1)
    assert out["removed"] is True
    # 收藏还在，回未分类
    assert user_data.list_doc_bookmarks()[0]["doc_id"] == "bfa"
    assert folder_db.execute(
        "SELECT folder_id FROM user_doc_bookmark WHERE doc_id='bfa'").fetchone()[0] is None
    assert user_data.list_bookmarks()[0]["clause_key"] == "bfk1"
    assert folder_db.execute(
        "SELECT folder_id FROM user_bookmark WHERE clause_key='bfk1'").fetchone()[0] is None
    # 删不存在的夹 → 抛
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        user_data.delete_folder("bmf_ghost")


def test_add_bookmark_with_folder_and_move(folder_db):
    """带夹收藏 + 移动（同夹改选 = 移动语义）+ 未分类。"""
    from src.core.storage import user_data
    f1, f2 = _fid(folder_db, "收藏夹一"), _fid(folder_db, "收藏夹二")

    # 收藏时指定夹
    out = user_data.add_bookmark("bfk1", folder_id=f1)
    assert out["existed"] is False
    assert user_data.list_bookmarks()[0]["folder_id"] == f1

    # 重复收藏（同 remark）→ existed 且**不隐式改夹**
    out2 = user_data.add_bookmark("bfk1", folder_id=f2)
    assert out2["existed"] is True
    assert user_data.list_bookmarks()[0]["folder_id"] == f1

    # 显式移动
    assert user_data.move_bookmark_by_clause_key("bfk1", f2) is True
    assert user_data.list_bookmarks()[0]["folder_id"] == f2
    # 移回未分类
    assert user_data.move_bookmark_by_clause_key("bfk1", None) is True
    assert user_data.list_bookmarks()[0]["folder_id"] is None
    # 不存在的夹 → 拒绝
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        user_data.move_bookmark_by_clause_key("bfk1", "bmf_ghost")

    # doc 收藏同款
    user_data.add_doc_bookmark("bfa", folder_id=f2)
    assert user_data.list_doc_bookmarks()[0]["folder_id"] == f2
    assert user_data.move_doc_bookmark_by_doc("bfa", f1) is True
    assert user_data.list_doc_bookmarks()[0]["folder_id"] == f1


# ---------- folder_scope（ks_answer 数据源） ----------

def test_folder_scope_union_semantics(folder_db):
    """范围 = 夹内 doc 收藏（整本）∪ 夹内条款收藏（单条）；不存在 → None。"""
    from src.core.storage import user_data
    f1, f2 = _fid(folder_db, "收藏夹一"), _fid(folder_db, "收藏夹二")
    user_data.add_doc_bookmark("bfa", folder_id=f1)      # 整本入夹一
    user_data.add_bookmark("bfk2", folder_id=f2)         # 单条入夹二

    s1 = user_data.folder_scope(f1)
    assert s1["folder_name"] == "收藏夹一"
    assert s1["doc_ids"] == {"bfa"}
    assert s1["clause_keys"] == set()

    s2 = user_data.folder_scope(f2)
    assert s2["doc_ids"] == set()
    assert s2["clause_keys"] == {"bfk2"}

    # 空夹 = 合法空范围
    user_data.create_folder("空夹")
    f3 = _fid(folder_db, "空夹")
    s3 = user_data.folder_scope(f3)
    assert s3["doc_ids"] == set() and s3["clause_keys"] == set()

    # 不存在 → None（调用方如实降级）
    assert user_data.folder_scope("bmf_ghost") is None


# ---------- server 端点 ----------

def test_folder_endpoints(folder_db):
    import json as _json
    c, token = None, None
    from fastapi.testclient import TestClient
    from src.core.api.server import create_app
    with TestClient(create_app("test-token-123")) as client:
        token = "test-token-123"
        h = {"Authorization": f"Bearer {token}"}

        # 建/列/重命名/删除
        r = client.post("/api/v1/bookmark-folders", json={"folder_name": "端点夹"},
                        headers=h)
        assert r.status_code == 200, r.text
        fid = r.json()["data"]["folder_id"]
        # 重名 → 409 folder_name_conflict（客户端据此给「已存在」提示）
        r = client.post("/api/v1/bookmark-folders", json={"folder_name": "端点夹"},
                        headers=h)
        assert r.status_code == 409 and r.json()["error"] == "folder_name_conflict"
        r = client.get("/api/v1/bookmark-folders", headers=h)
        names = {f["folder_name"] for f in r.json()["data"]}
        assert "端点夹" in names

        r = client.put(f"/api/v1/bookmark-folders/{fid}",
                       json={"folder_name": "改名夹"}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["folder_name"] == "改名夹"

        # 收藏 + 移动 + 树
        r = client.post("/api/v1/doc-bookmarks",
                        json={"doc_id": "bfa"}, headers=h)
        assert r.status_code == 200
        r = client.post("/api/v1/bookmark-folders/move-doc",
                        json={"doc_id": "bfa", "folder_id": fid}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["moved"] is True

        r = client.post("/api/v1/bookmarks",
                        json={"clause_key": "bfk1"}, headers=h)
        assert r.status_code == 200
        r = client.post("/api/v1/bookmark-folders/move-clause",
                        json={"clause_key": "bfk1", "folder_id": fid}, headers=h)
        assert r.status_code == 200 and r.json()["data"]["moved"] is True

        r = client.get("/api/v1/bookmark-folders/tree", headers=h)
        assert r.status_code == 200, r.text
        tree = r.json()["data"]
        by_name = {f["folder_name"]: f for f in tree}
        assert "改名夹" in by_name and "未分类" in by_name
        target = by_name["改名夹"]
        assert target["doc_count"] == 1 and target["clause_count"] == 1
        # 文档节点：分类路径 + 条款收藏列表
        doc = target["docs"][0]
        assert doc["doc_id"] == "bfa"
        assert isinstance(doc["path"], dict) and set(doc["path"]) == {"l1", "l2", "l3", "l4"}
        assert doc["doc_bookmarked"] is True
        assert {cb["clause_key"] for cb in doc["clause_bookmarks"]} == {"bfk1"}

        # 删夹 → 收藏回未分类（树里体现）
        r = client.delete(f"/api/v1/bookmark-folders/{fid}", headers=h)
        assert r.status_code == 200
        r = client.get("/api/v1/bookmark-folders/tree", headers=h)
        by_name = {f["folder_name"]: f for f in r.json()["data"]}
        unf = by_name["未分类"]
        assert unf["doc_count"] == 1 and unf["clause_count"] == 1


# ---------- ks_answer 夹内提问过滤链 ----------

def _monkeypatch_scope(monkeypatch, scope):
    from src.core.storage import user_data
    monkeypatch.setattr(user_data, "folder_scope", lambda fid: scope)


def test_answer_folder_id_filters_by_union(folder_db, monkeypatch):
    """folder_id → 证据限定在（doc_ids ∪ clause_keys）内，notes 如实说明。"""
    from src.core.llm import ks_answer
    _monkeypatch_scope(monkeypatch, {
        "folder_id": "bmf_test", "folder_name": "收藏夹一",
        "doc_ids": {"bfa"}, "clause_keys": set()})
    data = ks_answer.answer("消防 通道 宽度", params={"folder_id": "bmf_test"})
    assert data["evidence"], "整本入夹的文档条款应命中"
    assert all(e["doc_id"] == "bfa" for e in data["evidence"])
    assert any("【收藏夹】" in n and "收藏夹一" in n for n in data["notes"])


def test_answer_folder_id_clause_only_scope(folder_db, monkeypatch):
    """条款级收藏 → 只有那一条入范围（同文档其他条款被滤掉）。"""
    from src.core.llm import ks_answer
    _monkeypatch_scope(monkeypatch, {
        "folder_id": "bmf_test", "folder_name": "夹二",
        "doc_ids": set(), "clause_keys": {"bfk1"}})
    data = ks_answer.answer("消防 检查", params={"folder_id": "bmf_test"})
    # 命中范围（bfk1 = 5.1.1 消防通道）或空（检索排序不保证），但绝不能出现 bfk2
    for e in data["evidence"]:
        assert e["clause_key"] != "bfk2" if "clause_key" in e else True
    assert all(e["doc_id"] == "bfa" and e["clause_number"] != "5.2.2"
               for e in data["evidence"]) if data["evidence"] else True


def test_answer_folder_id_missing_folder_degrades_honestly(folder_db, monkeypatch):
    """夹不存在（folder_scope → None）→ 过滤不执行，notes 如实说明，不静默全库。"""
    from src.core.llm import ks_answer
    _monkeypatch_scope(monkeypatch, None)
    data = ks_answer.answer("消防 通道", params={"folder_id": "bmf_ghost"})
    assert any("未能" in n and "收藏夹" in n for n in data["notes"]), data["notes"]


def test_answer_folder_id_scope_query_failure_degrades_honestly(folder_db, monkeypatch):
    """folder_scope 抛异常 → 同上如实降级。"""
    from src.core.storage import user_data
    def _boom(fid):
        raise RuntimeError("db broken")
    monkeypatch.setattr(user_data, "folder_scope", _boom)
    from src.core.llm import ks_answer
    data = ks_answer.answer("消防 通道", params={"folder_id": "bmf_x"})
    assert any("未能" in n and "收藏夹" in n for n in data["notes"]), data["notes"]


def test_answer_folder_id_empty_folder_returns_empty_honestly(folder_db, monkeypatch):
    """空夹 = 合法空范围 → 证据空 + notes 说明已限定（不是查库失败）。"""
    from src.core.llm import ks_answer
    _monkeypatch_scope(monkeypatch, {
        "folder_id": "bmf_test", "folder_name": "空夹",
        "doc_ids": set(), "clause_keys": set()})
    data = ks_answer.answer("消防 通道", params={"folder_id": "bmf_test"})
    assert data["evidence"] == []
    assert any("已限定" in n and "空夹" in n for n in data["notes"]), data["notes"]


def test_answer_folder_id_widens_candidate_pool(folder_db, monkeypatch):
    """夹范围激活时候选池扩容（同 bookmarks_only 的 BOOKMARKS_MIN_TOP_K）。"""
    from src.core.llm import ks_answer
    from src.core.retrieval import hybrid_engine
    calls = {}
    orig = hybrid_engine.search_with_details
    def spy(query, **kw):
        calls["top_k"] = kw.get("top_k")
        return orig(query, **kw)
    monkeypatch.setattr(hybrid_engine, "search_with_details", spy)
    ks_answer.answer("消防 通道", params={"folder_id": "bmf_t", "top_k": 3})
    assert calls["top_k"] >= ks_answer.BOOKMARKS_MIN_TOP_K
