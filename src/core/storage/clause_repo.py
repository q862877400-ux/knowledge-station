"""条款仓储：写入 clause_revision / source_span / clause_fts / clause_vec。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any, Iterable, Literal

from ulid import ULID

from src.core.domain.models import ClauseRevisionModel, SourceSpanModel
from src.core.retrieval import embedder
from src.core.storage.sqlite_db import (
    get_db_connection, load_vec_extension, write_transaction,
)


def make_clause_key(doc_id: str, normalized_clause_no: str) -> str:
    return hashlib.sha256(f"{doc_id}{normalized_clause_no}".encode("utf-8")).hexdigest()[:24]


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_law_source_columns() -> None:
    """官方来源溯源列迁移（docs/LAW_SOURCE_PLAN.md §5）：
    doc_meta 增加 source / source_id / source_url / downloaded_at / source_status。
    SQLite 无 ADD COLUMN IF NOT EXISTS，PRAGMA 检查后逐列 ALTER；幂等。
    """
    conn = get_db_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()}
    for col in ("source", "source_id", "source_url", "downloaded_at", "source_status"):
        if col not in cols:
            conn.execute(f"ALTER TABLE doc_meta ADD COLUMN {col} TEXT")
    conn.commit()


def ensure_content_hash_column() -> int:
    """Task 10.4 迁移：clause_revision 增加 content_hash（快照可验证，红线 v2 #2）。

    SQLite 无 ADD COLUMN IF NOT EXISTS，需 PRAGMA 检查；存量行回填。幂等。
    返回回填行数（供运维日志感知规模）。
    """
    conn = get_db_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(clause_revision)").fetchall()}
    if "content_hash" not in cols:
        conn.execute("ALTER TABLE clause_revision ADD COLUMN content_hash TEXT")
        conn.commit()
    # 回填空值（存量数据 + 手工插入的行）
    cur = conn.execute(
        "SELECT clause_revision_id, content_text FROM clause_revision"
        " WHERE content_hash IS NULL OR content_hash=''")
    rows = cur.fetchall()
    if rows:
        with write_transaction() as txn:
            for r in rows:
                txn.execute(
                    "UPDATE clause_revision SET content_hash=? WHERE clause_revision_id=?",
                    (content_hash(r["content_text"]), r["clause_revision_id"]))
    return len(rows)


def ensure_page_breaks_column() -> None:
    """B3 迁移（2026-09-01）：clause_revision 增加 page_breaks（页界 run-start 编码）。

    纯增量列、无回填：存量快照没有行级页界信息，NULL = 未采集，渲染层按
    NULL 跳过分隔（快照不可变红线——绝不给存量编造页界）。幂等。
    """
    conn = get_db_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(clause_revision)").fetchall()}
    if "page_breaks" not in cols:
        conn.execute("ALTER TABLE clause_revision ADD COLUMN page_breaks TEXT")
        conn.commit()


def ensure_figure_html_column() -> None:
    """C2 迁移（2026-09-01）：clause_revision 增加 figure_html（插图占位通道）。

    纯增量列、无回填：存量快照没有插图占位，NULL = 未采集。幂等。
    """
    conn = get_db_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(clause_revision)").fetchall()}
    if "figure_html" not in cols:
        conn.execute("ALTER TABLE clause_revision ADD COLUMN figure_html TEXT")
        conn.commit()


def ensure_catalog_hidden_column() -> None:
    """目录卫生迁移（2026-08-28）：doc_meta 增加 catalog_hidden。

    用户口径：坏档（坍缩/乱码污染）先从目录隐藏，修复重导入后自动回归——
    覆盖式重导入是「删旧行 + 插新行」，新行落 DEFAULT 0 即重新可见；
    管线在正文条款为零（坍缩）时把新行置 1，坏档永不回流目录。幂等。
    """
    conn = get_db_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(doc_meta)").fetchall()}
    if "catalog_hidden" not in cols:
        conn.execute(
            "ALTER TABLE doc_meta ADD COLUMN catalog_hidden INTEGER NOT NULL DEFAULT 0")
        conn.commit()


_MIGRATED: set[str] = set()


def ensure_additive_columns() -> None:
    """**追加列**迁移的**唯一入口**：保证"读代码需要的列"都存在（纯 ALTER，**不回填**）。

    ## 为什么需要这么一个入口（2026-09-17 冷启动缺陷）
    `schema.sql` 用的是 `CREATE TABLE IF NOT EXISTS`，而 `catalog_hidden` / `page_breaks` /
    `figure_html` 这三列**不在 `schema.sql` 里**——它们只由本模块的迁移函数添加。
    在此之前，那条迁移只挂在**写路径**上（`_ensure_content_hash_once()`，由
    `insert_document` 触发）⇒ **一个全新的库（还没有任何入库）里这三列根本不存在**，
    而**读者**照样用它们：

      · `exports/effect_report._load_docs()`：`... WHERE catalog_hidden = 0` ⇒
        `/api/v1/report/effect` 直接 **500 `no such column: catalog_hidden`**
        （界面上的「效力报告」第一眼就是服务器错误）；
      · `api/server.py` 的目录端点（3 处）同理。

    实测（§10.43）：一次性引擎 + 空 KS_DATA_DIR，`GET /api/v1/report/effect?window=all`
    → 500，traceback 落在 `effect_report.py:133`。

    ## 为什么不把 `ensure_content_hash_column()` 也并进来
    那个函数**会回填**（全表扫 + UPDATE）：那是**写路径**的事，放在启动路径上会把
    "一次全表扫"摊到每次启动。启动只需要**形状**对。回填仍留在写路径
    （`_ensure_content_hash_once`）。
    """
    ensure_catalog_hidden_column()
    ensure_page_breaks_column()
    ensure_figure_html_column()


def _ensure_content_hash_once() -> None:
    """迁移在进程内只执行一次。

    INSERT 路径始终写入 content_hash，首次迁移后不可能再出现 NULL 行；
    旧实现每次批量入库都重跑「无索引全表扫描」，在百万条款库上是纯浪费，
    且回填分支的 commit 会拦腰提交调用方已开启的写事务。
    """
    if "content_hash" in _MIGRATED:
        return
    ensure_content_hash_column()
    ensure_additive_columns()
    _MIGRATED.add("content_hash")
    _MIGRATED.add("page_breaks")
    _MIGRATED.add("figure_html")


def _seg(text: str) -> str:
    """FTS 分词：**委托给 text_utils 的唯一实现**（2026-09-17）。

    保留这个私有名只是为了不动既有调用点；实现只有一份，`material_fts` 用同一个函数
    ——否则法条与材料两条检索线会各自漂移（同一句话一边搜得到一边搜不到）。
    """
    from src.core.text_utils import segment_for_fts
    return segment_for_fts(text)


def insert_document(conn: sqlite3.Connection, doc: dict[str, Any]) -> None:
    conn.execute(
        """INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,
           current_revision_id, legal_status, legal_hierarchy, standard_type, doc_type,
           quality_grade, domain_tags, effective_from, published_at, superseded_by, normative_refs,
           file_path, file_hash, source, source_id, source_url, downloaded_at, source_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (doc["doc_id"], doc["standard_no"], doc["standard_name"], doc["short_code"],
         doc.get("current_revision_id", ""), doc.get("legal_status", "effective"),
         doc.get("legal_hierarchy", "GB"), doc.get("standard_type", "mandatory"),
         doc.get("doc_type", "standard"), doc.get("quality_grade", "A"),
         json.dumps(doc.get("domain_tags", []), ensure_ascii=False),
         doc.get("effective_from"), doc.get("published_at"), doc.get("superseded_by"),
         json.dumps(doc.get("normative_refs", []), ensure_ascii=False),
         doc["file_path"], doc["file_hash"],
         doc.get("source"), doc.get("source_id"), doc.get("source_url"),
         doc.get("downloaded_at"), doc.get("source_status")))


def insert_page_geometries(conn: sqlite3.Connection, doc_id: str,
                           geometries: dict[int, dict[str, Any]]) -> None:
    for page_no, g in geometries.items():
        conn.execute(
            "INSERT OR REPLACE INTO doc_page_geometry "
            "(doc_id, page_number, width, height, rotation, crop_box, media_box) VALUES (?,?,?,?,?,?,?)",
            (doc_id, page_no, g["width"], g["height"], g.get("rotation", 0),
             json.dumps(g.get("crop_box")) if g.get("crop_box") else None,
             json.dumps(g.get("media_box")) if g.get("media_box") else None))


def insert_clauses(clauses: list[ClauseRevisionModel],
                   content_type: str = "normal") -> int:
    """批量写入条款 + FTS + 向量索引（独立短事务）。返回成功条数。"""
    with write_transaction() as conn:
        return insert_clauses_in_txn(conn, clauses, content_type)


def insert_clauses_in_txn(conn: sqlite3.Connection,
                          clauses: list[ClauseRevisionModel],
                          content_type: str = "normal") -> int:
    """在调用方事务内写入条款+FTS+向量（T05 管线用：整个入库单事务原子提交）。

    content_type: normal | 前置说明 | 附则 | 附录（R65：前置说明仅参与全文检索）
    向量引擎离线时跳过 clause_vec 写入（不阻塞入库，R30 精神）。
    """
    _ensure_content_hash_once()  # 幂等迁移：进程内仅首调执行（旧库补列/回填）
    vec_batch: list[tuple[str, list[float]]] = []
    vec_ok = embedder.is_available()
    if vec_ok:
        try:
            embs = embedder.embed_batch(
                [f"{c.title or ''}\n{c.content_text[:512]}" for c in clauses])
            vec_batch = list(zip([c.clause_revision_id for c in clauses], embs))
        except Exception:
            vec_ok = False

    for c in clauses:
        conn.execute(
            """INSERT INTO clause_revision
               (clause_revision_id, doc_revision_id, doc_id, clause_key, clause_number,
                title, content_text, content_markdown, table_summary, formula_number,
                formula_desc, image_text, hierarchy_path, knowledge_type, type_confidence,
                modality, modality_strength, modality_confidence, behavior_scope, subject,
                object, behavior, applicability_condition, restriction, exception,
                legal_refs, is_mandatory, is_suspicious, ocr_confidence, content_type,
                page_start, page_end, cross_refs, explanation_ref, content_hash,
                page_breaks, figure_html)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (c.clause_revision_id, c.doc_id, c.doc_id, c.clause_key, c.clause_number,
             c.title, c.content_text, c.content_markdown, c.table_summary,
             c.formula_number, c.formula_desc, c.image_text, c.hierarchy_path,
             c.knowledge_type, c.type_confidence, c.modality, c.modality_strength,
             c.modality_confidence, c.behavior_scope, c.subject, c.object, c.behavior,
             c.applicability_condition, c.restriction, c.exception,
             json.dumps(c.legal_refs, ensure_ascii=False),
             int(c.is_mandatory), int(c.is_suspicious), c.ocr_confidence,
             content_type, c.page_start, c.page_end,
             json.dumps(c.cross_refs, ensure_ascii=False), c.explanation_ref,
             content_hash(c.content_text),
             json.dumps(c.page_breaks, ensure_ascii=False)
             if c.page_breaks else None,
             c.figure_html))
        for s in c.source_spans:
            conn.execute(
                "INSERT INTO source_span (span_id, clause_revision_id, page_number, "
                "bbox_json, span_type, sort_order) VALUES (?,?,?,?,?,?)",
                (s.span_id or str(ULID()), c.clause_revision_id, s.page_number,
                 json.dumps(s.bbox), s.span_type, s.sort_order))
        conn.execute(
            "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no, title,"
            " content_segmented, modality, subject, behavior_scope_segmented)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (c.clause_revision_id, c.clause_number, c.standard_no, c.title or "",
             _seg(c.content_text), c.modality or "", c.subject or "",
             _seg(c.behavior_scope or "")))
    if vec_ok:
        for cid, emb in vec_batch:
            conn.execute(
                "INSERT OR REPLACE INTO clause_vec (clause_revision_id, embedding) VALUES (?, ?)",
                (cid, _serialize_vec(emb)))
    return len(clauses)


def delete_document(doc_id: str) -> int:
    """删除文档并清理其全部数据。

    注意：clause_vec / clause_fts 是虚拟表，不受外键级联约束，
    必须先显式清理，否则残留孤儿行污染检索（第二阶段自检发现的 bug）。

    性能（E10，2026-08-28 试点实测）：clause_fts.clause_revision_id 是
    UNINDEXED 列，逐行 DELETE = 每行全表扫描 24 万行 FTS 索引，覆盖式重入库
    单文档卡 15 分钟。clause_fts 用单条子查询批量删除（单次扫描）；
    clause_vec 主键列删除走 executemany 批处理。
    """
    conn = get_db_connection()
    vec_ok = load_vec_extension(conn)
    with write_transaction() as txn:
        rows = txn.execute(
            "SELECT clause_revision_id FROM clause_revision WHERE doc_id=?",
            (doc_id,)).fetchall()
        if rows:
            if vec_ok:
                ids = [r["clause_revision_id"] for r in rows]
                for i in range(0, len(ids), 500):
                    txn.executemany(
                        "DELETE FROM clause_vec WHERE clause_revision_id=?",
                        [(x,) for x in ids[i:i + 500]])
            # fts5 的 clause_revision_id 无索引：IN 子查询只扫 FTS 一遍
            txn.execute(
                "DELETE FROM clause_fts WHERE clause_revision_id IN "
                "(SELECT clause_revision_id FROM clause_revision WHERE doc_id=?)",
                (doc_id,))
        txn.execute("DELETE FROM doc_meta WHERE doc_id=?", (doc_id,))
    if not vec_ok:
        import logging
        logging.getLogger(__name__).warning("sqlite-vec 不可用，clause_vec 未清理（将有孤儿行）")
    return len(rows)


def _serialize_vec(emb: list[float]) -> str:
    return json.dumps(emb)


EDGE_TYPES = ('clause_relation', 'exception_relation', 'definition_relation',
              'reference_relation', 'correction_relation')


def insert_edges_in_txn(conn: sqlite3.Connection,
                        edges: list[tuple[str, str, str, float, str]]) -> int:
    """在调用方事务内写入证据依赖图边。

    edges: (edge_type, source_clause_id, target_clause_id, confidence, status)
    """
    for edge_type, src, dst, conf, status in edges:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"非法边类型: {edge_type}")
        conn.execute(
            "INSERT INTO evidence_edge (edge_id, edge_type, source_clause_id,"
            " target_clause_id, confidence, status) VALUES (?,?,?,?,?,?)",
            (f"edge_{ULID()}", edge_type, src, dst, conf, status))
    return len(edges)


PATCHABLE_FIELDS = ("content_text", "title", "table_summary", "content_markdown", "is_suspicious", "user_confirmed")


def _reindex_clause_indexes(conn: sqlite3.Connection,
                            clause_revision_id: str, content_text: str,
                            title: str | None, modality: str | None,
                            subject: str | None, behavior_scope: str | None) -> None:
    """补丁写入/回滚后同步 FTS 与向量索引（须在调用方事务内执行）。"""
    conn.execute(
        "UPDATE clause_fts SET title=?, content_segmented=?, modality=?, subject=?,"
        " behavior_scope_segmented=? WHERE clause_revision_id=?",
        (title or "", _seg(content_text), modality or "", subject or "",
         _seg(behavior_scope or ""), clause_revision_id))
    from src.core.retrieval import embedder
    if embedder.is_available():
        try:
            emb = embedder.embed_query(f"{title or ''}\n{content_text[:512]}")
            conn.execute(
                "INSERT OR REPLACE INTO clause_vec (clause_revision_id, embedding)"
                " VALUES (?, ?)", (clause_revision_id, _serialize_vec(emb)))
        except Exception:
            pass  # 向量引擎离线时保留旧向量，不阻塞补丁（R30 精神）


def upsert_patch(clause_revision_id: str, field_name: str, patched_value: str,
                 patch_reason: str | None = None) -> dict:
    """创建/更新纠错补丁：补丁 + FTS 重写 + 向量重算 同事务原子提交。"""
    from src.core.exceptions import KnowledgeStationError
    if field_name not in PATCHABLE_FIELDS:
        raise KnowledgeStationError(
            f"非法补丁字段: {field_name}，允许 {PATCHABLE_FIELDS}", code="invalid_patch_field")
    if not patched_value or not patched_value.strip():
        raise KnowledgeStationError("补丁内容不能为空", code="invalid_patch_value")

    from ulid import ULID as _ULID
    with write_transaction() as conn:
        row = conn.execute(
            "SELECT cr.clause_revision_id, cr.title, cr.modality, cr.subject,"
            " cr.behavior_scope, dm.doc_type"
            " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.clause_revision_id = ?", (clause_revision_id,)).fetchone()
        if row is None:
            raise KnowledgeStationError(
                f"条款不存在: {clause_revision_id}", code="clause_not_found")

        existing = conn.execute(
            "SELECT patch_id FROM clause_patch"
            " WHERE clause_revision_id=? AND field_name=?",
            (clause_revision_id, field_name)).fetchone()
        if existing:
            patch_id = existing["patch_id"]
            conn.execute(
                "UPDATE clause_patch SET patched_value=?, patch_reason=?,"
                " updated_at=datetime('now') WHERE patch_id=?",
                (patched_value, patch_reason, patch_id))
        else:
            patch_id = f"patch_{_ULID()}"
            conn.execute(
                "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
                " patched_value, patch_reason) VALUES (?,?,?,?,?)",
                (patch_id, clause_revision_id, field_name, patched_value, patch_reason))

        if field_name == "content_text":
            title = row["title"]
            _reindex_clause_indexes(conn, clause_revision_id, patched_value, title,
                                    row["modality"], row["subject"], row["behavior_scope"])
            # 人工纠错 = 人工复核确认 → 存疑自动转可信（补丁层覆写，快照零侵入）
            sus = conn.execute(
                "SELECT patch_id FROM clause_patch WHERE clause_revision_id=?"
                " AND field_name='is_suspicious'", (clause_revision_id,)).fetchone()
            if sus:
                conn.execute(
                    "UPDATE clause_patch SET patched_value='false',"
                    " patch_reason='人工纠错联动', updated_at=datetime('now')"
                    " WHERE patch_id=?", (sus["patch_id"],))
            else:
                conn.execute(
                    "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
                    " patched_value, patch_reason) VALUES (?,?,?,?,?)",
                    (f"patch_{_ULID()}", clause_revision_id, "is_suspicious",
                     "false", "人工纠错联动"))
        conn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type, target_id,"
            " after_state) VALUES (?,?,?,?,?,?)",
            (str(_ULID()), "patch_upsert", "user", "clause_patch", patch_id,
             json.dumps({"clause_revision_id": clause_revision_id, "field_name": field_name},
                        ensure_ascii=False)))
    return {"patch_id": patch_id, "clause_revision_id": clause_revision_id,
            "field_name": field_name, "patched_value": patched_value}


def list_patches(clause_revision_id: str | None = None, limit: int = 100) -> list[dict]:
    conn = get_db_connection()
    if clause_revision_id:
        rows = conn.execute(
            "SELECT * FROM clause_patch WHERE clause_revision_id=? ORDER BY updated_at DESC"
            " LIMIT ?", (clause_revision_id, limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM clause_patch ORDER BY updated_at DESC LIMIT ?",
            (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_patch(patch_id: str) -> bool:
    """删除补丁 = 回滚到不可变原始值（FTS/向量按原文重算）。"""
    from src.core.exceptions import KnowledgeStationError
    from ulid import ULID as _ULID
    with write_transaction() as conn:
        row = conn.execute("SELECT * FROM clause_patch WHERE patch_id=?",
                           (patch_id,)).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM clause_patch WHERE patch_id=?", (patch_id,))
        if row["field_name"] == "content_text":
            orig = conn.execute(
                "SELECT cr.title, cr.content_text, cr.modality, cr.subject, cr.behavior_scope"
                " FROM clause_revision cr WHERE cr.clause_revision_id=?",
                (row["clause_revision_id"],)).fetchone()
            if orig is not None:
                _reindex_clause_indexes(conn, row["clause_revision_id"], orig["content_text"],
                                        orig["title"], orig["modality"], orig["subject"],
                                        orig["behavior_scope"])
        conn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type, target_id)"
            " VALUES (?,?,?,?,?)",
            (str(_ULID()), "patch_delete", "user", "clause_patch", patch_id))
    return True


def migrate_patches(old_doc_id: str, new_doc_id: str) -> dict:
    """Task 10.4 补丁跨修订平移（P1 数据正确性，v5.1 附录 #5）。

    旧 doc 的活跃补丁按 clause_key 向新 doc 平移：
      (a) 新条款原始值 == 旧条款原始值（补丁基准未变）→ 平移到新 revision（event_log 记录）；
      (b) 原始值已变（补丁可能与新版冲突）→ 进 remapping_queue status=pending 人工确认；
      (c) clause_key 在新版不存在（条款删除）→ remapping_queue 标记孤儿。
    幂等：已平移的旧补丁（reason 含 auto-migrated）跳过。旧补丁保留（历史留痕）。
    """
    ensure_content_hash_column()
    ensure_page_breaks_column()
    conn = get_db_connection()
    # 旧 doc 活跃补丁（join 条款取 稳定标识 = short_code + clause_number）
    # 注意：① clause_key 掺入 doc_id 跨修订不同，不能用于跨 doc 匹配；
    # ② standard_no 带年代（UNIQUE），新旧版本号不同；short_code 跨版本稳定（GB30871）。
    patches = conn.execute(
        "SELECT cp.patch_id, cp.clause_revision_id, cp.field_name, cp.patched_value,"
        " cp.patch_reason, cr.clause_key, cr.clause_number, cr.content_text, dm.short_code"
        " FROM clause_patch cp"
        " JOIN clause_revision cr ON cr.clause_revision_id = cp.clause_revision_id"
        " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.doc_id=? AND (cp.patch_reason IS NULL OR cp.patch_reason NOT LIKE '%auto-migrated%')",
        (old_doc_id,)).fetchall()
    new_clauses = conn.execute(
        "SELECT cr.clause_key, cr.clause_revision_id, cr.clause_number, cr.content_text, dm.short_code"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.doc_id=?", (new_doc_id,)).fetchall()
    new_by_ident = {(r["short_code"], r["clause_number"]): r for r in new_clauses}

    migrated, conflicted, orphaned = [], [], []
    with write_transaction() as txn:
        for p in patches:
            ident = (p["short_code"], p["clause_number"])
            new_c = new_by_ident.get(ident)
            if new_c is None:
                # (c) 孤儿：remapping_queue 无 UNIQUE 约束，先查后插保证幂等
                dup = txn.execute(
                    "SELECT 1 FROM remapping_queue WHERE old_clause_key=? AND old_doc_id=?"
                    " AND new_doc_id=? AND new_clause_key=''",
                    (p["clause_key"], old_doc_id, new_doc_id)).fetchone()
                if dup is None:
                    txn.execute(
                        "INSERT INTO remapping_queue (queue_id, old_clause_key,"
                        " new_clause_key, old_doc_id, new_doc_id, status)"
                        " VALUES (?,?,?,?,?,?)",
                        (f"remap_{ULID()}", p["clause_key"], "", old_doc_id, new_doc_id, "pending"))
                    orphaned.append(ident[1])
                continue
            if new_c["content_text"] == p["content_text"]:
                # (a) 基准未变 → 平移（新 revision 上建新补丁，标记 auto-migrated 幂等）
                cur = txn.execute(
                    "INSERT OR IGNORE INTO clause_patch (patch_id, clause_revision_id,"
                    " field_name, patched_value, patch_reason) VALUES (?,?,?,?,?)",
                    (f"patch_{ULID()}", new_c["clause_revision_id"], p["field_name"],
                     p["patched_value"],
                     f"{p['patch_reason'] or ''} auto-migrated from {old_doc_id}".strip()))
                if cur.rowcount:
                    migrated.append(ident[1])
                    txn.execute(
                        "INSERT INTO event_log (event_id, event_type, actor, target_type,"
                        " target_id, metadata) VALUES (?,?,?,?,?,?)",
                        (str(ULID()), "patch_migrated", "system", "clause_patch", p["patch_id"],
                         json.dumps({"old_doc_id": old_doc_id, "new_doc_id": new_doc_id,
                                     "clause_number": ident[1]}, ensure_ascii=False)))
            else:
                # (b) 原始值已变 → 人工确认队列（先查后插保证幂等）
                dup = txn.execute(
                    "SELECT 1 FROM remapping_queue WHERE old_clause_key=? AND old_doc_id=?"
                    " AND new_doc_id=?",
                    (p["clause_key"], old_doc_id, new_doc_id)).fetchone()
                if dup is None:
                    txn.execute(
                        "INSERT INTO remapping_queue (queue_id, old_clause_key,"
                        " new_clause_key, old_doc_id, new_doc_id, status)"
                        " VALUES (?,?,?,?,?,?)",
                        (f"remap_{ULID()}", p["clause_key"], new_c["clause_key"],
                         old_doc_id, new_doc_id, "pending"))
                    conflicted.append(ident[1])
    migrated_keys = sorted(set(migrated))
    conflicted_keys = sorted(set(conflicted))
    orphaned_keys = sorted(set(orphaned))
    return {"migrated": len(migrated_keys), "conflicted": len(conflicted_keys),
            "orphaned": len(orphaned_keys), "migrated_keys": migrated_keys,
            "conflicted_keys": conflicted_keys, "orphaned_keys": orphaned_keys}


def fetch_full_clause(conn: sqlite3.Connection,
                      clause_revision_id: str) -> ClauseRevisionModel | None:
    row = conn.execute(
        "SELECT cr.*, dm.standard_no, dm.legal_status, dm.legal_hierarchy, dm.doc_type,"
        " dm.standard_type, dm.effective_from"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
        " WHERE cr.clause_revision_id = ?", (clause_revision_id,)).fetchone()
    if row is None:
        return None

    # 阶段2.1 纠错补丁透明覆写：原始快照永不被修改（R79）
    patches = conn.execute(
        "SELECT field_name, patched_value FROM clause_patch WHERE clause_revision_id=?",
        (clause_revision_id,)).fetchall()
    patch_map = {p["field_name"]: p["patched_value"] for p in patches}
    content_text = patch_map.get("content_text", row["content_text"])
    title = patch_map.get("title", row["title"])
    table_summary = patch_map.get("table_summary", row["table_summary"])
    content_markdown = patch_map.get("content_markdown", row["content_markdown"])

    # 人工可信/存疑切换（补丁层覆写，快照零侵入）
    is_suspicious = row["is_suspicious"]
    if "is_suspicious" in patch_map:
        is_suspicious = str(patch_map["is_suspicious"]).lower() in ("true", "1")

    # 补丁改写正文后重跑规则分型（仅覆写返回值，不回写快照）
    # knowledge_type 值域：DB 列只存 Literal（'data'|'rule'|'legal'，写入方为
    # classify/pipeline），补丁重分类同为 Literal——显式声明自文档化
    # （sqlite row 取值是 Any，本就无需 ignore）。
    knowledge_type: Literal["data", "rule", "legal"] = (
        row["knowledge_type"] or "rule")
    type_confidence = row["type_confidence"] or 1.0
    modality = row["modality"]
    modality_strength = row["modality_strength"]
    exception = row["exception"]
    if "content_text" in patch_map:
        from src.core.knowledge.classifier import classify_clause
        tc = classify_clause(content_text, doc_type=row["doc_type"] or "standard")
        knowledge_type = tc.knowledge_type
        type_confidence = tc.type_confidence
        modality = tc.modality
        modality_strength = tc.modality_strength
        exception = tc.exception or exception

    spans = conn.execute(
        "SELECT span_id, page_number, bbox_json, span_type, sort_order FROM source_span"
        " WHERE clause_revision_id = ? ORDER BY sort_order", (clause_revision_id,)).fetchall()
    return ClauseRevisionModel(
        clause_revision_id=row["clause_revision_id"],
        doc_id=row["doc_id"],
        clause_key=row["clause_key"],
        standard_no=row["standard_no"],
        clause_number=row["clause_number"],
        title=title,
        content_text=content_text,
        content_markdown=content_markdown,
        table_summary=table_summary,
        formula_number=row["formula_number"],
        formula_desc=row["formula_desc"],
        image_text=row["image_text"],
        hierarchy_path=row["hierarchy_path"],
        knowledge_type=knowledge_type,
        type_confidence=type_confidence,
        modality=modality,
        modality_strength=modality_strength,
        modality_confidence=row["modality_confidence"],
        behavior_scope=row["behavior_scope"],
        subject=row["subject"],
        object=row["object"],
        behavior=row["behavior"],
        applicability_condition=row["applicability_condition"],
        restriction=row["restriction"],
        exception=exception,
        legal_refs=json.loads(row["legal_refs"] or "[]"),
        is_mandatory=bool(row["is_mandatory"]),
        is_suspicious=is_suspicious,
        ocr_confidence=row["ocr_confidence"] or 1.0,
        # ⚠ **不要**写成 `row["legal_status"] or "effective"`（2026-09-17 独立复核 b7 的 HIGH，
        # §10.44）：`doc_meta.legal_status` 允许 NULL，采集件（Track L 入库的网页文本）
        # 写的**就是** NULL = 未核验。把它洗白成 "effective" 会让它通过
        # `ks_answer._is_effective`（`legal_status == "effective"`）⇒ 进证据集、
        # 进提示词（`效力=effective`）——**"未核验的网页文本被当现行法条引用"**，
        # 而这正是 §10.39 那条修复的动机（当时只钉到 `doc_meta` 那一列，没跑到底）。
        # 现在 NULL 原样返回：`resolve_status(None, …)` 返回 None，
        # `STATUS_COLOR[None] == 'gray'`（效力报告 ⚪），`_is_effective` 为 False（不入证）。
        legal_status=row["legal_status"],
        legal_hierarchy=row["legal_hierarchy"] or "GB",
        # ⚠ 这一列以前**根本没读**，而 `query/understanding.rank_with_hierarchy` 却按
        # `getattr(c, 'standard_type', 'mandatory')` 排序 ⇒ 恒取默认值 ⇒ 该项零区分度
        # （2026-09-17 独立复核 b7 的 MEDIUM-4）。现在如实带出：NULL（未登记/采集件）
        # 就是"不知道"，排序时**不优先**。
        standard_type=row["standard_type"],
        effective_from=row["effective_from"] or None,
        page_start=row["page_start"],
        page_end=row["page_end"],
        cross_refs=json.loads(row["cross_refs"] or "[]"),
        explanation_ref=row["explanation_ref"],
        # B3：旧库未跑迁移时 row 可能没有该列（防御性 keys() 检查）；NULL = 未采集
        page_breaks=(json.loads(row["page_breaks"])
                     if "page_breaks" in row.keys() and row["page_breaks"] else None),
        figure_html=(row["figure_html"]
                     if "figure_html" in row.keys() else None),
        patched_fields=sorted(patch_map.keys()),
        source_spans=[SourceSpanModel(
            span_id=s["span_id"], page_number=s["page_number"],
            bbox=json.loads(s["bbox_json"]), span_type=s["span_type"] or "text",
            sort_order=s["sort_order"] or 0) for s in spans],
    )


def resolve_clause(standard_no: str, clause_number: str) -> ClauseRevisionModel | None:
    """按 标准号+条款号 精确解析条款（引用兜底：LLM 引用未进证据列表的条款时用）。

    标准号做宽容匹配：先精确，再忽略发布年份按主体匹配（如 GB/T 3608-2008 → GB 3608-2025）。
    取该标准下 rowid 最新的条款（版本链下游优先）。

    条款号做**原样优先 + 归一重试**（2026-09-17）：先按调用方给的写法查；只有查不到时才用
    `normalize_clause_number` 归一（全角→半角、去空白、去前导零）再查一次。这样既能接受
    「５．２．１」「05.2.1」「 5.2.1 」这类写法，又**不会**让库里真实存在的带前导零条款
    （实测 520,504 条里仅 '06'/'08' 两条与归一结果不同）因归一而查不到。
    纯增量：任何原本能命中的查询，命中结果不变。
    """
    import re as _re

    conn = get_db_connection()
    # 三个候选，**必须按"历史行为优先"的顺序试**，否则就不是纯增量：
    #   verbatim = 调用方原样（**旧实现正是用它查的**，去空白会改变结果）；
    #   raw      = 去首尾空白；norm = 归一（全角→半角 / 去空白 / 去前导零）。
    verbatim = clause_number or ""
    raw = verbatim.strip()
    try:
        from src.core.knowledge.classifier import normalize_clause_number
        norm = normalize_clause_number(raw)
    except Exception:
        # ⚠ 归一**可能对任意用户输入抛异常**：`str.isdigit()` 对 ¹²³ / ₀-₉ / 埃塞俄比亚
        # 数字等 128 个码点为 True，而 `int()` 拒绝它们 → ValueError。归一若放在查询之前
        # 且不兜住，端点会被任意字符串打成 500（本改动第一版就踩了，verifier 抓出）。
        # 降级为"不归一"，等于完全退回旧行为。
        norm = raw

    def _lookup(cn: str) -> Any:
        """1) 精确标准号匹配（含版本年份）；2) 年份宽容（按标准数字主体）。"""
        r = conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.clause_number = ? AND dm.standard_no = ?"
            " ORDER BY cr.rowid DESC LIMIT 1",
            (cn, standard_no)).fetchone()
        if r:
            return r
        m = _re.search(r"(\d{4,5})", standard_no.strip())
        if not m:
            return None
        return conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " WHERE cr.clause_number = ? AND dm.standard_no LIKE ?"
            " ORDER BY cr.rowid DESC LIMIT 1",
            (cn, "%" + m.group(1) + "%")).fetchone()

    row = _lookup(verbatim)
    if not row and raw != verbatim:
        row = _lookup(raw)
    if not row and norm not in (verbatim, raw):
        row = _lookup(norm)
    # 3) 表格引用 fallback：条款号形如「表2」时，解析到正文引用该表的条款
    #    判据同时试 raw（旧行为）与 norm（新增，于是「表 2」也能进这条分支）
    tbl = next((c for c in (raw, norm) if _re.match(r"^表\d+$", c)), None)
    if not row and tbl:
        like = "%" + tbl + "%"
        row = conn.execute(
            "SELECT DISTINCT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
            " LEFT JOIN clause_patch cp ON cp.clause_revision_id=cr.clause_revision_id"
            " AND cp.field_name='content_text'"
            " WHERE dm.standard_no = ? AND (cr.content_text LIKE ? OR cp.patched_value LIKE ?)"
            " ORDER BY cr.rowid DESC LIMIT 1",
            (standard_no, like, like)).fetchone()
        if not row:
            m = _re.search(r"(\d{4,5})", standard_no.strip())
            if m:
                row = conn.execute(
                    "SELECT DISTINCT cr.clause_revision_id FROM clause_revision cr"
                    " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
                    " LEFT JOIN clause_patch cp ON cp.clause_revision_id=cr.clause_revision_id"
                    " AND cp.field_name='content_text'"
                    " WHERE dm.standard_no LIKE ? AND (cr.content_text LIKE ? OR cp.patched_value LIKE ?)"
                    " ORDER BY cr.rowid DESC LIMIT 1",
                    ("%" + m.group(1) + "%", like, like)).fetchone()
    if not row:
        return None
    return fetch_full_clause(conn, row["clause_revision_id"])
