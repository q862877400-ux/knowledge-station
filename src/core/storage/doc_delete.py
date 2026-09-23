# -*- coding: utf-8 -*-
"""文档批量显式级联删除（2026-08-31，用户验收批量删除 UI 后接线）。

权威级联清单（schema.sql 31 表逐表归类，源自 var/tmp/s_mass_delete.py 实战模式并补全）：
- clause 级（经 clause_revision_id 派生子查询，只参数化 doc_ids 避免占位符爆炸）：
  source_span / clause_patch / legal_obligation（s_mass_delete 漏、此处补全）/
  evidence_edge（source+target 双向）/ clause_fts（FTS5 无 FK，按 rowid 删——契约红线）/
  clause_vec（vec0 无 FK；连接由 get_db_connection 统一加载 sqlite_vec）/ clause_revision
- doc 级：doc_page_geometry / update_change_event（doc_id 可空、FK 只绑 batch）/ watch_list /
  doc_meta / **folder_member(item_kind='file') / doc_filing_state**（2026-09-24 审计 A1 补：
  这两张**没有表级 FK** —— folder_member.item_id 是多态列，见 schema.sql 那段 ——
  不显式删就留下指向不存在文档的悬空挂靠与状态行；同时把重导那条路搅乱，见 reingest.py）
- 用户资产不动：user_bookmark / user_annotation（clause_key 锚定，重入库仍有效）/
  project_list / feedback_log（悬空引用无害——R79 同源：不自动改写用户数据）
- 别名不删：alias_store.source_doc_id 只是溯源标记，同义词是知识资产
- 历史不删：event_log / operation_log / audit_log 只增；本次删除写 event_log 审计
- 不 VACUUM：锁库太重，空间回收走维护面（数据包导出/备份）
- 事务走 write_transaction()（与 clause_repo 同 owner；连接为线程局部缓存，不得 close）
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.storage.sqlite_db import (
    get_db_connection,
    load_vec_extension,
    write_transaction,
)

MAX_BATCH = 500  # 防误传全库；UI 批删场景远用不到


def delete_documents(doc_ids: list[str], actor: str = "local-user",
                     db_path: Path | None = None) -> dict:
    """删除指定文档及全部级联数据。返回 {deleted_docs, deleted_clauses, missing}。

    doc_ids 去重；不存在的 id 进 missing 不报错；单事务（BEGIN IMMEDIATE）全成全败。

    ``db_path``（2026-09-21 增量，默认 None = 配置中心那个库，**既有调用方语义一字未变**）：
    目录模块的 ``purge`` 会真删文件，而它可能跑在**真库副本**上（归位预览/用例）——
    没有这个参数时 ``get_db_connection()`` 会落到默认库，那就是"在副本上操作、删的是真库"。
    """
    ids = sorted({str(d).strip() for d in doc_ids if str(d or "").strip()})
    if not ids:
        raise ValueError("doc_ids 为空")
    if len(ids) > MAX_BATCH:
        raise ValueError(f"单次最多删除 {MAX_BATCH} 个文档（防误传全库），当前 {len(ids)}")

    conn = get_db_connection(db_path)
    # vec0 虚表 DELETE 需要扩展；get_db_connection 默认不加载（R30 降级设计），
    # 此处显式加载（幂等，与 init_schema / s_mass_delete 同模式）
    load_vec_extension(conn)
    ph = ",".join("?" * len(ids))
    exists = {r[0] for r in conn.execute(
        f"SELECT doc_id FROM doc_meta WHERE doc_id IN ({ph})", ids)}
    missing = [d for d in ids if d not in exists]
    targets = sorted(exists)
    if not targets:
        return {"deleted_docs": 0, "deleted_clauses": 0, "missing": missing}

    tph = ",".join("?" * len(targets))
    cl_sub = ("SELECT clause_revision_id FROM clause_revision "
              f"WHERE doc_id IN ({tph})")
    with write_transaction(db_path) as txn:
        deleted_clauses = txn.execute(
            f"SELECT COUNT(*) FROM clause_revision WHERE doc_id IN ({tph})", targets
        ).fetchone()[0]
        # ---- clause 级（先叶后根；FTS/vec 虚表无 FK 必须手动删）----
        txn.execute(f"DELETE FROM source_span WHERE clause_revision_id IN ({cl_sub})", targets)
        txn.execute(f"DELETE FROM clause_patch WHERE clause_revision_id IN ({cl_sub})", targets)
        txn.execute(f"DELETE FROM legal_obligation WHERE clause_revision_id IN ({cl_sub})", targets)
        txn.execute(
            "DELETE FROM evidence_edge WHERE source_clause_id IN "
            f"({cl_sub}) OR target_clause_id IN ({cl_sub})", targets + targets)
        txn.execute(
            "DELETE FROM clause_fts WHERE rowid IN "
            f"(SELECT rowid FROM clause_fts WHERE clause_revision_id IN ({cl_sub}))", targets)
        txn.execute(f"DELETE FROM clause_vec WHERE clause_revision_id IN ({cl_sub})", targets)
        txn.execute(f"DELETE FROM clause_revision WHERE doc_id IN ({tph})", targets)
        # ---- doc 级 ----
        txn.execute(f"DELETE FROM doc_page_geometry WHERE doc_id IN ({tph})", targets)
        txn.execute(f"DELETE FROM update_change_event WHERE doc_id IN ({tph})", targets)
        txn.execute(f"DELETE FROM watch_list WHERE doc_id IN ({tph})", targets)
        # user_doc_bookmark（标准收藏）随文档删除清理：doc_id 锚定、无稳定跨版 key，
        # 不删会留永久孤儿（user_bookmark 用 clause_key 不在此列——跨版平移仍有效）。
        txn.execute(f"DELETE FROM user_doc_bookmark WHERE doc_id IN ({tph})", targets)
        # ---- 目录归属与处理状态（2026-09-24 审计 A1 补进级联清单）----
        # 这两张表**没有表级 FK**（folder_member.item_id 是多态列，见 schema.sql 那段），
        # 不显式删就留一排**指向不存在文档**的悬空行："目录里篇数"读的是 folder_member
        # （JOIN doc_meta 后其实看不见，但行本身留在库里、且会把重导那条路搅乱）。
        # ⚠ 只删 item_kind='file' 那一半（目录与目录之间的边 item_kind='folder' 一个字不动）。
        txn.execute(
            f"DELETE FROM folder_member WHERE item_kind='file' AND item_id IN ({tph})", targets)
        txn.execute(f"DELETE FROM doc_filing_state WHERE doc_id IN ({tph})", targets)
        txn.execute(f"DELETE FROM doc_meta WHERE doc_id IN ({tph})", targets)
        # ---- 审计（只增；明细进 metadata，target_id 不塞长列表）----
        txn.execute(
            "INSERT INTO event_log (event_id, event_type, actor, target_type,"
            " target_id, metadata) VALUES"
            " ('evt_docdel_' || lower(hex(randomblob(12))),"
            " 'document.batch_delete', ?, 'document', ?, ?)",
            (actor, f"batch:{len(targets)}",
             json.dumps({"deleted_docs": len(targets),
                         "deleted_clauses": deleted_clauses,
                         "missing": missing}, ensure_ascii=False)))
    return {"deleted_docs": len(targets),
            "deleted_clauses": deleted_clauses, "missing": missing}
