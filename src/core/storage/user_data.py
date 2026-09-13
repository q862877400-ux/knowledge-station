"""用户资产层（阶段4）：收藏 R25 / 批注 R33 / 项目清单 R34 / 义务清单 R-L9。

批注与收藏绑定稳定 clause_key（R79 跨修订平移不丢）；项目清单存 clause_revision_id。
"""
from __future__ import annotations

import json

from ulid import ULID

from src.core.exceptions import KnowledgeStationError
from src.core.storage.sqlite_db import get_db_connection, write_transaction


# ---------- 收藏 R25 ----------

def add_bookmark(clause_key: str, remark: str | None = None,
                 folder_id: str | None = None) -> dict:
    """条款级收藏。folder_id 可选（未分类 = NULL）。

    幂等键 = (clause_key, remark)——同一条款同一备注只收一条；重复调用返回 existed:True
    **且不移动已有收藏的夹**（改夹走 move_*，收藏动作不做隐式搬家）。
    folder_id 必须已存在（应用层引用完整性，见 sqlite_db._ensure_bookmark_folder_columns）。
    """
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        row = conn.execute(
            "SELECT bookmark_id FROM user_bookmark WHERE clause_key=? AND remark IS ?",
            (clause_key, remark)).fetchone()
        if row:
            return {"bookmark_id": row["bookmark_id"], "clause_key": clause_key, "existed": True}
        bid = f"bm_{ULID()}"
        conn.execute(
            "INSERT INTO user_bookmark (bookmark_id, clause_key, remark, folder_id)"
            " VALUES (?,?,?,?)",
            (bid, clause_key, remark, folder_id))
    return {"bookmark_id": bid, "clause_key": clause_key, "existed": False}


def remove_bookmark(bookmark_id: str) -> bool:
    with write_transaction() as conn:
        cur = conn.execute("DELETE FROM user_bookmark WHERE bookmark_id=?", (bookmark_id,))
    return cur.rowcount > 0


def remove_bookmark_by_clause_key(clause_key: str) -> bool:
    """按 clause_key 取消收藏（取消收藏 toggle 用；无此收藏为 no-op）。"""
    with write_transaction() as conn:
        cur = conn.execute("DELETE FROM user_bookmark WHERE clause_key=?", (clause_key,))
    return cur.rowcount > 0


def list_bookmarks() -> list[dict]:
    conn = get_db_connection()
    return [dict(r) for r in conn.execute(
        "SELECT b.bookmark_id, b.clause_key, b.remark, b.folder_id, b.created_at,"
        " cr.clause_revision_id, cr.clause_number, cr.title, cr.content_text,"
        " cr.doc_id, cr.page_start,"
        " dm.standard_no, dm.legal_status"
        " FROM user_bookmark b"
        " LEFT JOIN clause_revision cr ON cr.clause_key = b.clause_key"
        " LEFT JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " ORDER BY b.created_at DESC").fetchall()]


def bookmarked_clause_keys() -> set[str]:
    conn = get_db_connection()
    return {r["clause_key"] for r in
            conn.execute("SELECT clause_key FROM user_bookmark").fetchall()}


# ---------- 标准级书签（增强③-A，doc 级；区别于条款收藏 user_bookmark） ----------

def add_doc_bookmark(doc_id: str, remark: str | None = None,
                     folder_id: str | None = None) -> dict:
    """收藏一本标准（纯书签）。doc_id UNIQUE——重复收藏返回 existed:True（不隐式改夹）。
    doc 不存在（doc_meta 无此 id）→ KnowledgeStationError（FK 保护 + 明确语义）。
    folder_id 必须已存在；未分类 = NULL。"""
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        exists = conn.execute(
            "SELECT 1 FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone()
        if exists is None:
            raise KnowledgeStationError(f"文档不存在: {doc_id}", code="doc_not_found")
        row = conn.execute(
            "SELECT doc_bookmark_id FROM user_doc_bookmark WHERE doc_id=?",
            (doc_id,)).fetchone()
        if row:
            return {"doc_bookmark_id": row["doc_bookmark_id"],
                    "doc_id": doc_id, "existed": True}
        bid = f"dmb_{ULID()}"
        conn.execute(
            "INSERT INTO user_doc_bookmark (doc_bookmark_id, doc_id, remark, folder_id)"
            " VALUES (?,?,?,?)",
            (bid, doc_id, remark, folder_id))
    return {"doc_bookmark_id": bid, "doc_id": doc_id, "existed": False}


def remove_doc_bookmark(doc_bookmark_id: str) -> bool:
    with write_transaction() as conn:
        cur = conn.execute(
            "DELETE FROM user_doc_bookmark WHERE doc_bookmark_id=?",
            (doc_bookmark_id,))
    return cur.rowcount > 0


def remove_doc_bookmark_by_doc(doc_id: str) -> bool:
    """按 doc_id 取消收藏（顶部按钮 toggle 用）。"""
    with write_transaction() as conn:
        cur = conn.execute(
            "DELETE FROM user_doc_bookmark WHERE doc_id=?", (doc_id,))
    return cur.rowcount > 0


def list_doc_bookmarks() -> list[dict]:
    conn = get_db_connection()
    return [dict(r) for r in conn.execute(
        "SELECT b.doc_bookmark_id, b.doc_id, b.remark, b.folder_id, b.created_at,"
        " dm.standard_no, dm.standard_name, dm.doc_type, dm.legal_status"
        " FROM user_doc_bookmark b"
        " LEFT JOIN doc_meta dm ON dm.doc_id = b.doc_id"
        " ORDER BY b.created_at DESC").fetchall()]


def bookmarked_doc_ids() -> set[str]:
    conn = get_db_connection()
    return {r["doc_id"] for r in
            conn.execute("SELECT doc_id FROM user_doc_bookmark").fetchall()}


# ---------- 收藏夹目录（2026-10 收藏目录功能） ----------

def _require_folder(folder_id: str) -> None:
    """应用层引用完整性：folder_id 必须已存在（老库补列无表级 FK）。"""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT 1 FROM user_bookmark_folder WHERE folder_id=?",
        (folder_id,)).fetchone()
    if row is None:
        raise KnowledgeStationError(f"收藏夹不存在: {folder_id}", code="folder_not_found")


def create_folder(folder_name: str) -> dict:
    """新建收藏夹。空名拒绝；重名拒绝（UNIQUE(folder_name)）。"""
    name = (folder_name or "").strip()
    if not name:
        raise KnowledgeStationError("收藏夹名称不能为空", code="invalid_folder_name")
    if len(name) > 60:
        raise KnowledgeStationError("收藏夹名称过长（≤60 字符）", code="invalid_folder_name")
    fid = f"bmf_{ULID()}"
    with write_transaction() as conn:
        dup = conn.execute(
            "SELECT folder_id FROM user_bookmark_folder WHERE folder_name=?",
            (name,)).fetchone()
        if dup:
            raise KnowledgeStationError(
                f"收藏夹已存在: {name}", code="folder_name_conflict")
        conn.execute(
            "INSERT INTO user_bookmark_folder (folder_id, folder_name) VALUES (?,?)",
            (fid, name))
    return {"folder_id": fid, "folder_name": name}


def rename_folder(folder_id: str, new_name: str) -> dict:
    name = (new_name or "").strip()
    if not name:
        raise KnowledgeStationError("收藏夹名称不能为空", code="invalid_folder_name")
    if len(name) > 60:
        raise KnowledgeStationError("收藏夹名称过长（≤60 字符）", code="invalid_folder_name")
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE user_bookmark_folder SET folder_name=? WHERE folder_id=?",
            (name, folder_id))
        if cur.rowcount == 0:
            raise KnowledgeStationError(
                f"收藏夹不存在: {folder_id}", code="folder_not_found")
    return {"folder_id": folder_id, "folder_name": name}


def delete_folder(folder_id: str) -> dict:
    """删除收藏夹：**只删夹，收藏回「未分类」**（folder_id 置 NULL），绝不连坐删收藏。"""
    with write_transaction() as conn:
        cur = conn.execute(
            "DELETE FROM user_bookmark_folder WHERE folder_id=?", (folder_id,))
        if cur.rowcount == 0:
            raise KnowledgeStationError(
                f"收藏夹不存在: {folder_id}", code="folder_not_found")
        # 收藏本身保留，回到未分类
        conn.execute(
            "UPDATE user_bookmark SET folder_id=NULL WHERE folder_id=?", (folder_id,))
        conn.execute(
            "UPDATE user_doc_bookmark SET folder_id=NULL WHERE folder_id=?", (folder_id,))
    return {"folder_id": folder_id, "removed": True}


def list_folders() -> list[dict]:
    """全部收藏夹（含计数：doc 收藏数 + 条款收藏数），按创建时间升序。"""
    conn = get_db_connection()
    return [dict(r) for r in conn.execute(
        "SELECT f.folder_id, f.folder_name, f.created_at,"
        " (SELECT COUNT(*) FROM user_doc_bookmark b"
        "   WHERE b.folder_id = f.folder_id) AS doc_count,"
        " (SELECT COUNT(*) FROM user_bookmark b"
        "   WHERE b.folder_id = f.folder_id) AS clause_count"
        " FROM user_bookmark_folder f ORDER BY f.created_at").fetchall()]


def get_folder(folder_id: str) -> dict | None:
    conn = get_db_connection()
    r = conn.execute(
        "SELECT folder_id, folder_name, created_at FROM user_bookmark_folder"
        " WHERE folder_id=?", (folder_id,)).fetchone()
    return dict(r) if r is not None else None


def move_bookmark_to_folder(bookmark_id: str, folder_id: str | None) -> bool:
    """把一条条款收藏移入夹 / 移回未分类（folder_id=None）。"""
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE user_bookmark SET folder_id=? WHERE bookmark_id=?",
            (folder_id, bookmark_id))
    return cur.rowcount > 0


def move_doc_bookmark_to_folder(doc_bookmark_id: str, folder_id: str | None) -> bool:
    """把一条标准收藏移入夹 / 移回未分类（folder_id=None）。"""
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE user_doc_bookmark SET folder_id=? WHERE doc_bookmark_id=?",
            (folder_id, doc_bookmark_id))
    return cur.rowcount > 0


def move_bookmark_by_clause_key(clause_key: str, folder_id: str | None) -> bool:
    """按 clause_key 移动条款收藏（新收藏入库时指定夹的 toggle 路径）。"""
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE user_bookmark SET folder_id=? WHERE clause_key=?",
            (folder_id, clause_key))
    return cur.rowcount > 0


def move_doc_bookmark_by_doc(doc_id: str, folder_id: str | None) -> bool:
    """按 doc_id 移动标准收藏（新收藏入库时指定夹的 toggle 路径）。"""
    if folder_id is not None:
        _require_folder(folder_id)
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE user_doc_bookmark SET folder_id=? WHERE doc_id=?",
            (folder_id, doc_id))
    return cur.rowcount > 0


def folder_scope(folder_id: str) -> dict | None:
    """夹内提问的检索范围（ks_answer 过滤链数据源）。

    返回 {"folder_id", "folder_name", "doc_ids": set[str], "clause_keys": set[str]}
    —— **并集语义**：夹内标准级收藏 → 该 doc 全部条款入范围（以 doc_ids 表达，
    证据按 doc_id 匹配）；夹内条款级收藏 → 仅那几条（clause_keys）。
    收藏夹不存在 → None（调用方如实降级，绝不静默放全库）。
    空 = 合法的空夹（两个集合都空）。
    """
    conn = get_db_connection()
    folder = conn.execute(
        "SELECT folder_id, folder_name FROM user_bookmark_folder"
        " WHERE folder_id=?", (folder_id,)).fetchone()
    if folder is None:
        return None
    doc_ids = {r["doc_id"] for r in conn.execute(
        "SELECT doc_id FROM user_doc_bookmark WHERE folder_id=?", (folder_id,)).fetchall()}
    clause_keys = {r["clause_key"] for r in conn.execute(
        "SELECT clause_key FROM user_bookmark WHERE folder_id=?", (folder_id,)).fetchall()}
    return {
        "folder_id": folder["folder_id"],
        "folder_name": folder["folder_name"],
        "doc_ids": doc_ids,
        "clause_keys": clause_keys,
    }


# ---------- 批注 R33 ----------

def add_annotation(clause_key: str, content: str,
                   annotation_type: str = "personal") -> dict:
    if not content.strip():
        raise KnowledgeStationError("批注内容不能为空", code="invalid_annotation")
    aid = f"ann_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO user_annotation (annotation_id, clause_key, content, annotation_type)"
            " VALUES (?,?,?,?)", (aid, clause_key, content, annotation_type))
    return {"annotation_id": aid, "clause_key": clause_key}


def list_annotations(clause_key: str | None = None) -> list[dict]:
    conn = get_db_connection()
    if clause_key:
        rows = conn.execute(
            "SELECT * FROM user_annotation WHERE clause_key=? ORDER BY created_at DESC",
            (clause_key,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM user_annotation ORDER BY created_at DESC LIMIT 200").fetchall()
    return [dict(r) for r in rows]


def delete_annotation(annotation_id: str) -> bool:
    with write_transaction() as conn:
        cur = conn.execute("DELETE FROM user_annotation WHERE annotation_id=?", (annotation_id,))
    return cur.rowcount > 0


def annotations_by_clause_keys(keys: list[str]) -> dict[str, list[dict]]:
    if not keys:
        return {}
    conn = get_db_connection()
    ph = ",".join("?" * len(keys))
    out: dict[str, list[dict]] = {}
    for r in conn.execute(
            f"SELECT annotation_id, clause_key, content, annotation_type FROM user_annotation"
            f" WHERE clause_key IN ({ph}) ORDER BY created_at", keys).fetchall():
        out.setdefault(r["clause_key"], []).append(dict(r))
    return out


# ---------- 项目清单 R34 ----------

def create_project(project_name: str, project_type: str = "engineering") -> dict:
    pid = f"proj_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO project_list (project_id, project_name, project_type,"
            " clause_revision_ids) VALUES (?,?,?,?)", (pid, project_name, project_type, "[]"))
    return {"project_id": pid, "project_name": project_name}


def add_clause_to_project(project_id: str, clause_revision_id: str) -> dict:
    with write_transaction() as conn:
        row = conn.execute(
            "SELECT clause_revision_ids FROM project_list WHERE project_id=?",
            (project_id,)).fetchone()
        if row is None:
            raise KnowledgeStationError(f"项目不存在: {project_id}", code="project_not_found")
        ids = json.loads(row["clause_revision_ids"])
        if clause_revision_id not in ids:
            ids.append(clause_revision_id)
        conn.execute(
            "UPDATE project_list SET clause_revision_ids=?, updated_at=datetime('now')"
            " WHERE project_id=?", (json.dumps(ids), project_id))
    return {"project_id": project_id, "count": len(ids)}


def remove_clause_from_project(project_id: str, clause_revision_id: str) -> dict:
    with write_transaction() as conn:
        row = conn.execute(
            "SELECT clause_revision_ids FROM project_list WHERE project_id=?",
            (project_id,)).fetchone()
        if row is None:
            raise KnowledgeStationError(f"项目不存在: {project_id}", code="project_not_found")
        ids = [i for i in json.loads(row["clause_revision_ids"]) if i != clause_revision_id]
        conn.execute(
            "UPDATE project_list SET clause_revision_ids=?, updated_at=datetime('now')"
            " WHERE project_id=?", (json.dumps(ids), project_id))
    return {"project_id": project_id, "count": len(ids)}


def list_projects() -> list[dict]:
    conn = get_db_connection()
    return [dict(r) for r in conn.execute(
        "SELECT * FROM project_list ORDER BY updated_at DESC").fetchall()]


# ---------- 义务清单与检查表 R-L9 ----------

def save_obligation_list(business_description: str, items: list[dict],
                         mode: str = "list") -> dict:
    lid = f"obl_{ULID()}"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO obligation_list (list_id, business_description, mode, items)"
            " VALUES (?,?,?,?)",
            (lid, business_description, mode, json.dumps(items, ensure_ascii=False)))
    return {"list_id": lid, "count": len(items)}


def update_obligation_list(list_id: str, items: list[dict]) -> bool:
    with write_transaction() as conn:
        cur = conn.execute(
            "UPDATE obligation_list SET items=? WHERE list_id=?",
            (json.dumps(items, ensure_ascii=False), list_id))
    return cur.rowcount > 0


def get_obligation_list(list_id: str) -> dict | None:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM obligation_list WHERE list_id=?", (list_id,)).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["items"] = json.loads(out["items"])
    return out
