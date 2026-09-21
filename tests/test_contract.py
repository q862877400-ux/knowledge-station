"""T00 契约冒烟测试：模型可实例化、SSE 事件与通道枚举冻结、DDL 可执行。"""
import pytest

from src.core.domain.models import (
    SSE_EVENT_ORDER, SEARCH_CHANNELS, MODALITY_STRENGTH,
    ClauseRevisionModel, DocumentMetaModel, EvidenceEdgeModel, ModalityViolation,
    PageGeometryModel, ReviewPointModel, SourceSpanModel, VerificationResult,
)


def test_sse_event_order_frozen():
    assert SSE_EVENT_ORDER == ["evidence", "status", "delta", "verification", "done"]


def test_search_channels_frozen():
    assert SEARCH_CHANNELS == [
        "exact", "fts", "vec", "modality", "legal_element", "behavior_scope"]


def test_modality_strength_dict_frozen():
    assert MODALITY_STRENGTH["严禁"] == 5
    assert MODALITY_STRENGTH["不得"] == 4
    assert MODALITY_STRENGTH["应"] == 3
    assert MODALITY_STRENGTH["宜"] == 2
    assert MODALITY_STRENGTH["可以"] == 1
    assert MODALITY_STRENGTH["鼓励"] == 0


def test_models_instantiate():
    span = SourceSpanModel(span_id="s1", page_number=3, bbox=[72.0, 310.5, 520.0, 395.2])
    geo = PageGeometryModel(page_number=3, width=595, height=842, rotation=90,
                            crop_box=[0, 0, 595, 842], media_box=[0, 0, 612, 792])
    clause = ClauseRevisionModel(
        clause_revision_id="clrev_1", doc_id="doc_1", clause_key="k" * 24,
        standard_no="GB 50016-2022", clause_number="5.2.3", content_text="防火间距不应小于13m",
        knowledge_type="rule", modality="不应", modality_strength=4,
        page_start=42, page_end=42, source_spans=[span])
    assert clause.modality_strength == 4
    assert geo.rotation == 90
    doc = DocumentMetaModel(
        doc_id="doc_1", standard_no="GB 50016-2022", standard_name="建筑设计防火规范",
        short_code="GB50016", current_revision_id="r1", legal_status="effective",
        file_path="x.pdf", file_hash="h" * 64)
    edge = EvidenceEdgeModel(edge_id="e1", edge_type="exception_relation",
                             source_clause_id="a", target_clause_id="b")
    point = ReviewPointModel(point_id="p1", task_id="t1", point_type="违约金条款",
                             point_content="违约金30%", verdict="yellow", verdict_reason="过高")
    viol = ModalityViolation(clause_revision_id="clrev_1", source_modality="应",
                             output_modality="宜", source_strength=3, output_strength=2,
                             violation_type="modality_weakened")
    result = VerificationResult(is_valid=False, modality_violations=[viol])
    assert not result.is_valid


def test_invalid_knowledge_type_rejected():
    with pytest.raises(Exception):
        ClauseRevisionModel(
            clause_revision_id="x", doc_id="d", clause_key="k", standard_no="s",
            clause_number="1", content_text="t", knowledge_type="bogus",
            page_start=1, page_end=1)


def test_schema_all_tables(db):
    from src.core.storage.sqlite_db import list_tables
    tables = set(list_tables())
    expected = {
        "doc_meta", "doc_page_geometry", "clause_revision", "source_span",
        "clause_fts", "clause_vec", "alias_store", "evidence_edge",
        "user_bookmark", "user_doc_bookmark", "user_bookmark_folder",
        "user_annotation", "project_list", "review_task",
        "review_point", "obligation_list", "gap_analysis", "legal_obligation",
        "internal_policy", "app_config", "write_queue", "event_log", "debug_dump",
        "remapping_queue", "snapshot_meta", "operation_log", "audit_log",
        "feedback_log", "watch_list", "clause_patch",
    }
    missing = expected - tables
    assert not missing, f"缺少表: {missing}"


def test_bookmark_folder_schema(db):
    """收藏夹目录（2026-10）契约：夹表 + 两张收藏表的 folder_id 列 + 夹名 UNIQUE。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(user_bookmark_folder)").fetchall()}
    missing = {"folder_id", "folder_name", "created_at"} - cols
    assert not missing, f"user_bookmark_folder 缺列: {missing}"
    uniques = {r[1] for r in db.execute("PRAGMA index_list(user_bookmark_folder)").fetchall()}
    assert any("user_bookmark_folder" in u for u in uniques), \
        f"缺 folder_name UNIQUE: {uniques}"
    for table in ("user_bookmark", "user_doc_bookmark"):
        tcols = {r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()}
        assert "folder_id" in tcols, f"{table} 缺 folder_id 列: {tcols}"


def test_doc_bookmark_columns(db):
    """user_doc_bookmark（标准级书签）契约：列集 + doc_id UNIQUE + FK 级联。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(user_doc_bookmark)").fetchall()}
    required = {"doc_bookmark_id", "doc_id", "remark", "created_at"}
    missing = required - cols
    assert not missing, f"user_doc_bookmark 缺列: {missing}"
    uniques = {r[1] for r in db.execute("PRAGMA index_list(user_doc_bookmark)").fetchall()}
    # sqlite 为 UNIQUE 约束自动建 sqlite_autoindex_user_doc_bookmark_1
    assert any("user_doc_bookmark" in u for u in uniques), f"缺 doc_id UNIQUE: {uniques}"


def test_egress_audit_contract(db):
    """Task 10.0 契约（v5 红线 #4 外发可审计）：debug_dump 必须承载外发审计所需字段。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(debug_dump)").fetchall()}
    required = {"dump_id", "trigger_type", "query", "prompt",
                "llm_output", "verification_result", "logs", "created_at"}
    missing = required - cols
    assert not missing, f"debug_dump 缺审计字段: {missing}"
    # 统一登记入口必须存在（后续 rerank/VLM/云解析共用）
    from src.core.llm import egress_audit
    assert callable(getattr(egress_audit, "record_egress", None))
    assert callable(getattr(egress_audit, "query_egress", None))


# ===== 更新模块数据契约（阶段三，契约先行：先改本文件再动 schema） =====


# ===== 排版还原批次1 数据契约（2026-09-01，契约先行：先改本文件再动 schema） =====


def test_clause_revision_page_breaks_column(db):
    """B3 页界列：clause_revision.page_breaks TEXT 可空（run-start 编码
    [[行号,PDF页],...]）；NULL=存量未采集，渲染层跳过分隔（契约增量见
    pipeline/03-contract-delta.md 排版还原批次1）。"""
    cols = {r[1]: r for r in db.execute("PRAGMA table_info(clause_revision)").fetchall()}
    assert "page_breaks" in cols, "clause_revision 缺 page_breaks 列（B3 页界契约）"
    assert cols["page_breaks"]["type"] == "TEXT"
    # 纯增量列：可空、无 NOT NULL（存量行 NULL = 未采集，不许回填编造页界）
    assert not cols["page_breaks"]["notnull"]
    # 迁移幂等：对已建库重跑 ensure 不抛错、不改动
    from src.core.storage.clause_repo import ensure_page_breaks_column
    ensure_page_breaks_column()
    cols2 = {r[1] for r in db.execute("PRAGMA table_info(clause_revision)").fetchall()}
    assert "page_breaks" in cols2


def test_clause_revision_figure_html_column(db):
    """C2 插图通道列：clause_revision.figure_html TEXT 可空（fig-strip 占位
    串）；NULL=存量未采集（契约增量见 pipeline/03-contract-delta.md
    排版还原批次1补充）。"""
    cols = {r[1]: r for r in db.execute("PRAGMA table_info(clause_revision)").fetchall()}
    assert "figure_html" in cols, "clause_revision 缺 figure_html 列（C2 插图契约）"
    assert cols["figure_html"]["type"] == "TEXT"
    assert not cols["figure_html"]["notnull"]
    from src.core.storage.clause_repo import ensure_figure_html_column
    ensure_figure_html_column()
    cols2 = {r[1] for r in db.execute("PRAGMA table_info(clause_revision)").fetchall()}
    assert "figure_html" in cols2


def test_update_tables_exist(db):
    """29/30 号表存在性（pipeline/02 §2 数据契约增量）。"""
    from src.core.storage.sqlite_db import list_tables
    tables = set(list_tables())
    for name in ("update_check_batch", "update_change_event"):
        assert name in tables, f"缺少更新模块契约表: {name}"


def test_update_tables_ulid_pk_style(db):
    """29/30 表主键为 ULID 风格 TEXT 主键，DDL 注释声明 upd_/chg_ 前缀。"""
    from pathlib import Path
    import src.core.storage.sqlite_db as sqlite_db_mod
    ddl = Path(sqlite_db_mod.__file__).with_name("schema.sql").read_text(encoding="utf-8")
    assert "-- ULID 前缀 upd_" in ddl, "update_check_batch 主键缺 ULID 前缀注释"
    assert "-- ULID 前缀 chg_" in ddl, "update_change_event 主键缺 ULID 前缀注释"
    for table, pk in (("update_check_batch", "batch_id"),
                      ("update_change_event", "change_id")):
        info = {r["name"]: r for r in db.execute(f"PRAGMA table_info({table})").fetchall()}
        col = info[pk]
        assert col["pk"] == 1 and col["type"] == "TEXT", f"{table} 主键须为 TEXT ULID 风格"


def test_update_batch_check_enums(db):
    """update_check_batch：trigger_type 二枚举、status 五枚举 CHECK。"""
    import sqlite3
    db.execute("INSERT INTO update_check_batch(batch_id, trigger_type, status)"
               " VALUES('upd_ct_01', 'manual', 'running')")
    db.execute("INSERT INTO update_check_batch(batch_id, trigger_type)"
               " VALUES('upd_ct_02', 'scheduled')")  # status 走缺省
    assert db.execute("SELECT status FROM update_check_batch WHERE batch_id='upd_ct_02'"
                      ).fetchone()[0] == "pending"
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO update_check_batch(batch_id, trigger_type)"
                   " VALUES('upd_ct_bad1', 'auto')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO update_check_batch(batch_id, trigger_type, status)"
                   " VALUES('upd_ct_bad2', 'manual', 'canceled')")


def test_update_event_change_type_enum(db):
    """update_change_event：change_type 恰好五枚举。"""
    import sqlite3
    sql = ("INSERT INTO update_change_event(change_id, batch_id, standard_no,"
           " change_type, source_channel) VALUES(?, 'upd_ev_01', 'GB 50016-2022', ?, 'official_gb')")
    db.execute("INSERT INTO update_check_batch(batch_id) VALUES('upd_ev_01')")
    for i, ct in enumerate(("new_version", "superseded",
                            "withdrawn", "not_found", "no_change")):
        db.execute(sql, (f"chg_ev_{i}", ct))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, ("chg_ev_bad", "renamed"))


def test_update_event_legal_status_and_nullable_doc(db):
    """current_legal_status 四枚举且可空；doc_id 可空（公告命中但库内无文档）。"""
    import sqlite3
    sql = ("INSERT INTO update_change_event(change_id, batch_id, standard_no,"
           " change_type, current_legal_status, source_channel)"
           " VALUES(?, 'upd_ls_01', 'GB/T 1234-2020', 'new_version', ?, 'govcn')")
    db.execute("INSERT INTO update_check_batch(batch_id) VALUES('upd_ls_01')")
    for i, st in enumerate(("effective", "upcoming", "superseded", "withdrawn")):
        db.execute(sql, (f"chg_ls_{i}", st))
    # 显式 NULL 与缺省两种写法都必须放行（公告命中但库内无文档 → doc_id 为 NULL）
    db.execute(sql, ("chg_ls_null", None))
    db.execute("INSERT INTO update_change_event(change_id, batch_id, standard_no,"
               " change_type, source_channel)"
               " VALUES('chg_ls_default', 'upd_ls_01', 'GB 9999-2019', 'not_found', 'web')")
    # 非空路径同样合法（库内命中文档时回填）
    db.execute("INSERT INTO update_change_event(change_id, batch_id, standard_no,"
               " doc_id, change_type, current_legal_status, source_channel)"
               " VALUES('chg_ls_hit', 'upd_ls_01', 'GB/T 1234-2020', 'doc_ls_hit',"
               " 'new_version', 'superseded', 'laws_db')")
    total = db.execute("SELECT count(*) FROM update_change_event"
                       " WHERE batch_id='upd_ls_01'").fetchone()[0]
    null_doc = db.execute("SELECT count(*) FROM update_change_event"
                          " WHERE batch_id='upd_ls_01' AND doc_id IS NULL").fetchone()[0]
    assert total == 7 and null_doc == 6
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, ("chg_ls_bad", "expired"))


def test_update_event_fk_cascade(db):
    """batch_id 外键：孤儿事件插入被拒、删批次级联删事件。"""
    import sqlite3
    ev = ("INSERT INTO update_change_event(change_id, batch_id, standard_no,"
          " change_type, source_channel)"
          " VALUES(?, 'upd_fk_missing', 'GB 50016-2022', 'superseded', 'laws_db')")
    with pytest.raises(sqlite3.IntegrityError):  # 批次不存在不得写入
        db.execute(ev, ("chg_fk_orphan",))
    db.execute("INSERT INTO update_check_batch(batch_id) VALUES('upd_fk_01')")
    db.execute(ev.replace("upd_fk_missing", "upd_fk_01"), ("chg_fk_01",))
    db.execute("DELETE FROM update_check_batch WHERE batch_id='upd_fk_01'")
    left = db.execute("SELECT count(*) FROM update_change_event"
                      " WHERE change_id='chg_fk_01'").fetchone()[0]
    assert left == 0


# ===== 批量导入批次表契约（阶段六·批次2，pipeline/06 §4；巡检侧最小版） =====


def test_bulk_import_batch_exists_and_columns(db):
    """31 号表存在性 + 巡检侧最小列集（tier/checkpoint_json 是编排器刚需）。"""
    from src.core.storage.sqlite_db import list_tables
    tables = set(list_tables())
    assert "bulk_import_batch" in tables, "缺少 bulk_import_batch 契约表"
    cols = {r["name"] for r in db.execute("PRAGMA table_info(bulk_import_batch)").fetchall()}
    required = {"batch_id", "batch_kind", "trigger_type", "status",
                "total", "checked", "red_count", "yellow_count",
                "green_count", "gray_count", "tier", "checkpoint_json",
                "started_at", "finished_at", "created_at"}
    missing = required - cols
    assert not missing, f"bulk_import_batch 缺列: {missing}"


def test_bulk_import_batch_ulid_pk_style(db):
    """主键为 ULID 风格 TEXT 主键，DDL 注释声明 bul_ 前缀。"""
    from pathlib import Path
    import src.core.storage.sqlite_db as sqlite_db_mod
    ddl = Path(sqlite_db_mod.__file__).with_name("schema.sql").read_text(encoding="utf-8")
    assert "-- ULID 前缀 bul_" in ddl, "bulk_import_batch 主键缺 ULID 前缀注释"
    col = {r["name"]: r for r in
           db.execute("PRAGMA table_info(bulk_import_batch)").fetchall()}["batch_id"]
    assert col["pk"] == 1 and col["type"] == "TEXT", "batch_id 须为 TEXT ULID 风格主键"


def test_bulk_import_batch_check_enums_and_defaults(db):
    """CHECK 枚举（batch_kind/trigger_type/status/tier）+ 默认值（status/计数/tier）。"""
    import sqlite3
    # 默认值路径：status=pending、五计数 0、tier=tier1、checkpoint_json 可空
    db.execute("INSERT INTO bulk_import_batch(batch_id, batch_kind, trigger_type)"
               " VALUES('bul_ct_01', 'inspect', 'manual')")
    row = db.execute("SELECT status, total, checked, red_count, yellow_count,"
                     " green_count, gray_count, tier, checkpoint_json"
                     " FROM bulk_import_batch WHERE batch_id='bul_ct_01'").fetchone()
    assert tuple(row) == ("pending", 0, 0, 0, 0, 0, 0, "tier1", None)
    # tier0 显式落值合法；bulk_ingest 枚举为批量导入预留
    db.execute("INSERT INTO bulk_import_batch(batch_id, batch_kind, trigger_type, tier)"
               " VALUES('bul_ct_02', 'bulk_ingest', 'scheduled', 'tier0')")
    # 四个 CHECK 枚举域逐一拒绝非法值
    bad = [("INSERT INTO bulk_import_batch(batch_id, batch_kind)"
            " VALUES('bul_bad1', 'crawl')"),
           ("INSERT INTO bulk_import_batch(batch_id, trigger_type)"
            " VALUES('bul_bad2', 'cron')"),
           ("INSERT INTO bulk_import_batch(batch_id, batch_kind, status)"
            " VALUES('bul_bad3', 'inspect', 'canceled')"),
           ("INSERT INTO bulk_import_batch(batch_id, batch_kind, tier)"
            " VALUES('bul_bad4', 'inspect', 'tier9')")]
    for sql in bad:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(sql)


# ===== 公告发现数据契约（契约增量见 pipeline/03「公告发现」节，三件套同步） =====

def test_announce_table_exists(db):
    """announcement_observed（32 号表）存在。"""
    from src.core.storage.sqlite_db import list_tables
    assert "announcement_observed" in set(list_tables())


def test_announce_observed_columns(db):
    """announcement_observed 契约：列集完备。"""
    cols = {r[1] for r in db.execute("PRAGMA table_info(announcement_observed)").fetchall()}
    required = {"observed_id", "source_id", "source_name", "title", "url",
                "url_hash", "standard_no", "published_date",
                "first_seen", "last_seen", "scan_id", "user_ack"}
    missing = required - cols
    assert not missing, f"announcement_observed 缺列: {missing}"


def test_announce_dedup_unique(db):
    """去重键 UNIQUE(source_id, url_hash)：重复 (source_id,url_hash) 写入被拒；
    同 URL 换源（source_id 不同）合法。"""
    import sqlite3
    base = ("INSERT INTO announcement_observed(observed_id, source_id, source_name,"
            " title, url, url_hash) VALUES (?,?,?,?,?,?)")
    db.execute(base, ("ann_ct_01", "src_a", "源A", "公告标题", "https://x/a.html",
                      "hash_aaa"))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(base, ("ann_ct_02", "src_a", "源A", "公告标题", "https://x/a.html",
                          "hash_aaa"))
    db.execute(base, ("ann_ct_03", "src_b", "源B", "公告标题", "https://x/a.html",
                      "hash_aaa"))  # 换源合法（按源隔离语义）


def test_announce_ulid_pk_style(db):
    """observed_id 须为 TEXT 主键且 DDL 带 ann_ 前缀注释（ULID 风格契约）。"""
    ddl = db.execute("SELECT sql FROM sqlite_master"
                     " WHERE type='table' AND name='announcement_observed'").fetchone()[0]
    assert "-- ULID 前缀 ann_" in ddl, "announcement_observed 主键缺 ULID 前缀注释"
    col = {r["name"]: r for r in
           db.execute("PRAGMA table_info(announcement_observed)").fetchall()}["observed_id"]
    assert col["pk"] == 1 and col["type"] == "TEXT"


# ===== 知识库多级目录数据契约（33~35 号表；契约增量见 pipeline/03-contract-delta.md 末节） =====

def test_folder_tables_exist(db):
    """folder / folder_member / doc_filing_state 三张表存在（方案 §3 定死的形状）。"""
    from src.core.storage.sqlite_db import list_tables
    tables = set(list_tables())
    for t in ("folder", "folder_member", "doc_filing_state"):
        assert t in tables, f"缺少 {t} 契约表"


def test_folder_columns(db):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(folder)").fetchall()}
    assert {"folder_id", "parent_id", "name", "sort", "created_at"} <= cols, cols


def test_folder_ulid_pk_style(db):
    """folder_id 须为 TEXT 主键且 DDL 带 fld_ 前缀注释（与 30/32 号表同款契约）。"""
    ddl = db.execute("SELECT sql FROM sqlite_master"
                     " WHERE type='table' AND name='folder'").fetchone()[0]
    assert "-- ULID 前缀 fld_" in ddl, "folder 主键缺 ULID 前缀注释"
    col = {r["name"]: r for r in
           db.execute("PRAGMA table_info(folder)").fetchall()}["folder_id"]
    assert col["pk"] == 1 and col["type"] == "TEXT"


def test_folder_member_columns_and_pk(db):
    info = db.execute("PRAGMA table_info(folder_member)").fetchall()
    cols = {r["name"] for r in info}
    assert {"folder_id", "item_kind", "item_id", "added_at"} <= cols, cols
    pk = {r["name"] for r in info if r["pk"]}
    assert pk == {"folder_id", "item_kind", "item_id"}, f"主键应为三列: {pk}"


def test_doc_filing_state_columns_and_stage_enum(db):
    cols = {r["name"] for r in db.execute("PRAGMA table_info(doc_filing_state)").fetchall()}
    required = {"doc_id", "stage", "confidence", "failure_kind", "suggested_folder_id",
                "suggest_new_path", "placed_folder_id", "placed_by", "placed_at",
                "last_error", "updated_at"}
    assert required <= cols, f"doc_filing_state 缺列: {required - cols}"
    # stage 五枚举（排队/识别中/待确认/已归位/识别失败）
    import sqlite3
    db.execute("INSERT INTO doc_filing_state(doc_id, stage) VALUES ('ct_fs_1','queued')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO doc_filing_state(doc_id, stage) VALUES ('ct_fs_2','bogus')")
    db.rollback()


def test_folder_member_kind_enum_and_pk_rejects_dup(db):
    """item_kind 只有 folder/file；同一 (folder,kind,item) 只能有一行（三列主键）。"""
    import sqlite3
    db.execute("INSERT INTO folder_member(folder_id, item_kind, item_id)"
               " VALUES ('ct_f1','file','ct_d1')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO folder_member(folder_id, item_kind, item_id)"
                   " VALUES ('ct_f1','file','ct_d1')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO folder_member(folder_id, item_kind, item_id)"
                   " VALUES ('ct_f1','bogus','ct_d1')")
    db.rollback()


def test_folder_same_name_same_level_rejected_by_indexes(db):
    """同名同层拒绝**必须**含根层：`parent_id IS NULL` 时表级 UNIQUE 无效（NULL 互不相等），
    靠部分唯一索引 idx_folder_root_name 兜住（方案 §二第 3 条 + §三「同名同层要拒」）。"""
    import sqlite3
    # 根层：第二条同名被拒
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_root_a',NULL,'契约国标')")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO folder(folder_id, parent_id, name)"
                   " VALUES ('ct_root_b',NULL,'契约国标')")
    db.rollback()
    # 异层同名**必须**允许
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_root_a',NULL,'契约国标')")
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_p2',NULL,'契约父2')")
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_c3','ct_p2','契约国标')")
    db.commit()
    assert db.execute(
        "SELECT COUNT(*) FROM folder WHERE name='契约国标'").fetchone()[0] == 2
    # 同层（parent_id 非空）同名拒绝
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_p1',NULL,'契约父')")
    db.execute("INSERT INTO folder(folder_id, parent_id, name)"
               " VALUES ('ct_c1','ct_p1','契约子')")
    db.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO folder(folder_id, parent_id, name)"
                   " VALUES ('ct_c2','ct_p1','契约子')")
    db.rollback()
