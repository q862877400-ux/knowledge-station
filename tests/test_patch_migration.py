"""Task 10.4 补丁跨修订平移测试：(a)平移 (b)冲突入队 (c)孤儿入队 + content_hash 回填。

⚠ 共享会话库：所有 doc/clause id 必须唯一化（每次运行加随机后缀），
否则跨 pytest 会话残留数据导致断言不可复现。
"""
from ulid import ULID


def _uniq(prefix: str) -> str:
    return f"{prefix}_{ULID()}"  # 完整 ULID（前 8 hex 是时间戳，同毫秒会撞，勿截断）


def _mk_doc(db, doc_id: str, standard_no: str, file_hash: str, short_code: str | None = None):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=doc_id, standard_no=standard_no, standard_name=standard_no,
            short_code=short_code or standard_no.replace(" ", "").replace("-", "")[:8],
            current_revision_id=f"rev_{doc_id}",
            domain_tags=[], file_path=f"{doc_id}.pdf", file_hash=file_hash))


def _mk_clause(db, doc_id: str, cid: str, no: str, text: str):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES (?,?,?,?,?,?,1,1,?)",
            (cid, f"rev_{doc_id}", doc_id,
             clause_repo.make_clause_key(doc_id, no), no, text,
             clause_repo.content_hash(text)))


def test_migrate_patches_three_branches(db):
    from src.core.storage import clause_repo
    old, new = _uniq("old"), _uniq("new")
    # 旧版（short_code=GBT，GB T-2022）：三条款 + 两个补丁
    _mk_doc(db, old, "GB T-2022", "h_old", short_code="GBT")
    _mk_clause(db, old, f"{old}c1", "5.2.1", "动火作业应有专人监护。")
    _mk_clause(db, old, f"{old}c2", "5.2.2", "可燃气体浓度不大于0.5%。")
    _mk_clause(db, old, f"{old}c3", "5.2.3", "删除条款原文。")
    clause_repo.upsert_patch(f"{old}c1", "content_text", "动火作业应设专人监护（修正）。")
    clause_repo.upsert_patch(f"{old}c2", "content_text", "可燃气体浓度不大于0.5%（补标点）。")
    clause_repo.upsert_patch(f"{old}c3", "content_text", "删除条款原文（修正）。")  # 孤儿场景需有补丁

    # 新版（同 short_code=GBT，GB T-2025）：5.2.1 原文不变（平移）、5.2.2 原文已变（冲突）、5.2.3 缺失（孤儿）
    _mk_doc(db, new, "GB T-2025", "h_new", short_code="GBT")
    _mk_clause(db, new, f"{new}c1", "5.2.1", "动火作业应有专人监护。")
    _mk_clause(db, new, f"{new}c2", "5.2.2", "可燃气体浓度不大于1.0%（新版改数值）。")

    out = clause_repo.migrate_patches(old, new)
    # 每个 content_text 补丁联动 is_suspicious 补丁（人工纠错=人工复核），按条款号去重断言分支
    assert "5.2.1" in out["migrated_keys"] and "5.2.1" not in out["conflicted_keys"]
    assert "5.2.2" in out["conflicted_keys"] and "5.2.2" not in out["migrated_keys"]
    assert "5.2.3" in out["orphaned_keys"]
    assert out["migrated"] >= 1 and out["conflicted"] >= 1 and out["orphaned"] == 1

    # 平移后：新版 5.2.1 读路径应显示修正内容（含 content_text + is_suspicious 两类补丁）
    m = clause_repo.fetch_full_clause(db, f"{new}c1")
    assert "（修正）" in m.content_text
    assert "content_text" in m.patched_fields

    # 幂等：再跑不产生重复补丁（rowcount 判重）
    out2 = clause_repo.migrate_patches(old, new)
    assert out2["migrated"] == 0 and out2["conflicted"] == 0 and out2["orphaned"] == 0
    n_patches = db.execute(
        "SELECT COUNT(*) FROM clause_patch WHERE clause_revision_id=?",
        (f"{new}c1",)).fetchone()[0]
    assert n_patches == 2, "新条款应恰好 2 条补丁（content_text + is_suspicious）"

    # 冲突项进入人工确认队列
    row = db.execute(
        "SELECT status FROM remapping_queue WHERE old_doc_id=? AND new_doc_id=?"
        " AND old_clause_key=(SELECT clause_key FROM clause_revision WHERE clause_revision_id=?)",
        (old, new, f"{old}c2")).fetchone()
    assert row is not None and row["status"] == "pending"


def test_content_hash_backfill(db):
    """content_hash 列迁移 + 存量回填（幂等）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    bd = _uniq("bd")
    _mk_doc(db, bd, "GB B-2022", "hb")
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end)"
            " VALUES (?,?,?,?,?,?,1,1)", (_uniq("ch"), "r", bd, "k", "1.1", "原文内容"))
    n = clause_repo.ensure_content_hash_column()
    assert n >= 1
    assert clause_repo.ensure_content_hash_column() >= 0
    # 回填校验：任意存量行 content_hash 非空
    row = db.execute(
        "SELECT content_hash FROM clause_revision WHERE doc_id=? LIMIT 1", (bd,)).fetchone()
    assert row["content_hash"] == clause_repo.content_hash("原文内容")


def test_content_hash_on_insert(db):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    hdoc = _uniq("hd")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=hdoc, standard_no="GB H-2022", standard_name="h", short_code="h",
            current_revision_id="r", domain_tags=[], file_path="h.pdf", file_hash="hh"))
    clause_repo.insert_clauses([ClauseRevisionModel(
        clause_revision_id=_uniq("hc"), doc_id=hdoc, clause_key="hk", standard_no="GB H-2022",
        clause_number="1.1", content_text="哈希测试内容", page_start=1, page_end=1)])
    row = db.execute(
        "SELECT content_hash FROM clause_revision WHERE doc_id=? LIMIT 1", (hdoc,)).fetchone()
    assert row["content_hash"] == clause_repo.content_hash("哈希测试内容")


def test_migrate_patches_api(client, db):
    from src.core.storage import clause_repo
    old, new = _uniq("oldA"), _uniq("newA")
    _mk_doc(db, old, "GB API-2022", "ha", short_code="APIX")
    _mk_clause(db, old, f"{old}x", "6.1", "内容A")
    clause_repo.upsert_patch(f"{old}x", "content_text", "内容A（修正）")
    _mk_doc(db, new, "GB API-2025", "hb", short_code="APIX")
    _mk_clause(db, new, f"{new}x", "6.1", "内容A")
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    r = c.post(f"/api/v1/documents/{old}/migrate-patches", headers=headers,
               json={"to": new})
    assert r.status_code == 200
    assert r.json()["data"]["migrated"] >= 1
    # 缺少目标 → 422
    assert c.post(f"/api/v1/documents/{old}/migrate-patches", headers=headers,
                  json={}).status_code == 422
    assert c.post(f"/api/v1/documents/{old}/migrate-patches",
                  json={"to": new}).status_code == 401
