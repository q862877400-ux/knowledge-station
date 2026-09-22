"""Phase 12 测试：Office 往返 / 双向溯源 / 批量问答。"""
import pytest
from ulid import ULID


def _seed_clause(db, doc_id=None, cid=None, no="5.1", text="消防通道应保持畅通，宽度不小于 3.5m。",
                 standard_no=None):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    doc_id = doc_id or f"p12_{ULID()}"
    standard_no = standard_no or f"GB P12-{ULID()}"  # 完整 ULID（前 6/8 hex 是时间戳，同毫秒会撞）
    cid = cid or f"p12c_{ULID()}"
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=doc_id, standard_no=standard_no, standard_name=standard_no,
            short_code="P12", current_revision_id="r", domain_tags=["消防"],
            file_path="p.pdf", file_hash=f"h{ULID()}"))
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES (?,?,?,?,?,?,1,1,?)",
            (cid, "r", doc_id, f"k{cid}", no, text, clause_repo.content_hash(text)))
    return cid


def test_office_roundtrip_full_cycle(db, tmp_path, monkeypatch):
    """12.1：创建会话 → 模拟编辑（改写 docx）→ 轮询检出 → 提交落库 → 撤销/清理。"""
    from src.core.exports import office_roundtrip as rt
    from src.core.storage import clause_repo

    launched = []
    monkeypatch.setattr(rt, "_launch_office", lambda p, rect=None: launched.append(str(p)))

    cid = _seed_clause(db)
    sess = rt.create_edit_session(cid, rect={"left": 0, "top": 0, "width": 640, "height": 480})
    assert sess.docx_path.exists()
    assert len(launched) == 1, "创建会话必须拉起本机 Word/WPS 打开临时文档（2026-08-23 修：此前只生成 docx 未拉起）"
    assert str(sess.docx_path) in launched[0]

    # 未修改 → 无提案
    p = rt.poll_edit_session(sess.session_id)
    assert p.proposed is None

    # 模拟编辑：改写 docx 正文
    from docx import Document
    doc = Document(str(sess.docx_path))
    doc.paragraphs[-1].text = "消防通道应保持畅通，宽度不小于 4.0m（已修改）。"
    doc.save(str(sess.docx_path))

    p = rt.poll_edit_session(sess.session_id)
    assert p.proposed is not None
    # proposed 双字段（2026-08-23 改）：WPS 内容回填编辑器，不再直接落库
    assert "4.0m" in p.proposed["text"]

    out = rt.commit_edit_session(sess.session_id)
    assert out["field_name"] == "content_text"
    m = clause_repo.fetch_full_clause(db, cid)
    assert "4.0m" in m.content_text, "Office 编辑应走补丁落库"

    # 越界检测：插入图片部件 → 拒绝
    sess2 = rt.create_edit_session(cid)
    import zipfile, shutil
    fake = tmp_path / "with_img.docx"
    shutil.copy(sess2.docx_path, fake)
    # 直接调用 _contains_disallowed 验证（构造 zip 内 media 部件）
    import os
    from pathlib import Path
    zpath = sess2.docx_path
    zpath.unlink()
    with zipfile.ZipFile(str(zpath), "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("word/media/image1.png", b"\x89PNG")
    reason = rt._contains_disallowed(zpath)
    assert reason is not None and "图片" in reason

    # 取消会话清理
    sess3 = rt.create_edit_session(cid)
    assert rt.cancel_edit_session(sess3.session_id) is True
    assert not sess3.docx_path.exists()


def test_backlinks(db):
    """12.2：条款被 收藏/义务清单/审查点 引用时全量召回。"""
    from src.core.exports.backlinks import query_backlinks
    from src.core.storage import clause_repo, user_data
    cid = _seed_clause(db, doc_id="p12b")
    cr = db.execute("SELECT clause_key FROM clause_revision WHERE clause_revision_id=?", (cid,)).fetchone()
    key = cr["clause_key"]

    user_data.add_bookmark(key, "测试收藏")
    obl = user_data.save_obligation_list(
        "消防管理", [{"clause_revision_id": cid, "obligation_text": "应保持通道畅通"}])

    data = query_backlinks(cid)
    assert data["total"] >= 2
    assert len(data["backlinks"]["bookmarks"]) == 1
    assert len(data["backlinks"]["obligations"]) == 1


def test_phase12_api(client, db, monkeypatch):
    from src.core.exports import office_roundtrip as rt
    monkeypatch.setattr(rt, "_launch_office", lambda p, rect=None: None)
    cid = _seed_clause(db, doc_id="p12api")
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    # backlinks API
    r = c.get(f"/api/v1/clauses/{cid}/backlinks", headers=headers)
    assert r.status_code == 200
    # ⚠ 删单留痕（NOT-DOING #16）：原「batch QA API」四行随 /api/v1/batch/qa 删除。
    # office-edit start
    r = c.post(f"/api/v1/clauses/{cid}/office-edit", headers=headers)
    assert r.status_code == 200
    sess_id = r.json()["data"]["session_id"]
    r = c.delete(f"/api/v1/clauses/office-edit/{sess_id}", headers=headers)
    assert r.status_code == 200
    # 401
    assert c.get(f"/api/v1/clauses/{cid}/backlinks").status_code == 401
