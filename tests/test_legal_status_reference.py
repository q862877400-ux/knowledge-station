"""效力档新增值 `reference`（**参考资料·仅参考**）的**库结构迁移**测试（开发史 §10.192）。

背景（业主 2026-09-24 原话）："**征求意见稿也要入库**，只是效力层级是参考资料，不是强制执行的
那种"。要落这个档，`doc_meta.legal_status` 的枚举 CHECK 必须从四值扩到五值——而 SQLite
**改不了 CHECK**，只能按官方 12 步重建表。本文件钉住那次重建的**全部风险面**：

1. 迁移动机成立：迁移**前**写 `reference` 必须被 CHECK 拒（不然这文件是空转）；
2. 迁移**后**能写；
3. **数据一行不少**；
4. **索引/触发器跟着回来**（旧表 DROP 时它们一起没了）；
5. **外键级联还是通的**（`clause_revision … REFERENCES doc_meta(doc_id) ON DELETE CASCADE`）——
   这条是重建方案的核心风险：先 `ALTER TABLE doc_meta RENAME` 的写法会让子表外键被 SQLite
   一起改指到旧名上，级联当场断掉。**必须靠真删一行来证，不能只看 DDL 文本**；
6. **幂等**：再跑一次返回 0、不重建、数据还在。

⚠ 本文件**不动** `update_change_event.current_legal_status`（它仍是四值）：那个字段的取值来自
渠道探测结果（`channels/base.py` 的 `LEGAL_STATUSES`），库里没有任何通路会写 `reference`
——没有生产者的枚举值不该先塞进 CHECK。见 `sqlite_db._LEGAL_STATUS_TABLES` 的注释。
"""
from __future__ import annotations

import sqlite3

import pytest

from src.core.storage import sqlite_db

_REFERENCE_VALUE = "'withdrawn', 'reference'"


def _legacy_ddl() -> str:
    """真 `schema.sql` **只把 doc_meta 的枚举退回四值**——其余一字不改。

    这样测的就是"真库降级成迁移前那一版"的样子，而不是我手抄的一个近似结构。
    """
    schema = (sqlite_db._SCHEMA_PATH).read_text(encoding="utf-8")
    assert sqlite_db.LEGAL_STATUS_REFERENCE in schema, "schema.sql 里没有 reference 档？"
    legacy = schema.replace(
        "legal_status TEXT CHECK(legal_status IN ('effective', 'upcoming', 'superseded',"
        " 'withdrawn', 'reference'))",
        "legal_status TEXT CHECK(legal_status IN ('effective', 'upcoming', 'superseded',"
        " 'withdrawn'))")
    # 防"替换没命中、legacy 其实还是新库"的假绿（那样第 1 条断言会红得莫名其妙）
    assert legacy != schema, "降级替换没命中：schema.sql 的 doc_meta CHECK 写法变了？"
    assert "reference" not in legacy.split("CREATE TABLE IF NOT EXISTS doc_meta")[1].split(");")[0]
    return legacy


def _mk_doc(conn, doc_id: str, standard_no: str, status: str = "effective") -> None:
    conn.execute(
        "INSERT INTO doc_meta(doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, legal_status, domain_tags, file_path, file_hash)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (doc_id, standard_no, standard_no, standard_no[:24], f"rev_{doc_id}",
         status, '["法律"]', "law-text://test", f"hash_{doc_id}"))


def test_ref_migration_rebuilds_doc_meta(tmp_path):
    """四值 ⇒ 五值：迁移前写不进、迁移后写得进；数据/索引/触发器/外键级联全都保住；幂等。"""
    db_file = tmp_path / "legacy-four-status.db"
    conn = sqlite_db.get_db_connection(db_file)
    sqlite_db.load_vec_extension(conn)
    conn.executescript(_legacy_ddl())
    conn.commit()

    # ① 迁移动机：这一版 CHECK 必须**真的**把 reference 拒掉
    _mk_doc(conn, "doc_keep_1", "GB 1111-2020")
    with pytest.raises(sqlite3.IntegrityError):
        _mk_doc(conn, "doc_ref_before", "征求意见稿·迁移前", status="reference")
    # 子表一行（级联验证用）+ 一个显式索引（DROP TABLE 会带走它）
    conn.execute(
        "INSERT INTO clause_revision(clause_revision_id, doc_revision_id, doc_id, clause_key,"
        " clause_number, content_text, page_start, page_end)"
        " VALUES('clrev_keep_1','rev_doc_keep_1','doc_keep_1','doc_keep_1#1','1','第一条 测试',1,1)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_test_short ON doc_meta(short_code)")
    conn.commit()
    n_before = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    assert n_before == 1

    # ② 迁移（生产入口就是 init_schema）
    sqlite_db.init_schema(db_file)
    done = sqlite_db._ensure_legal_status_reference(conn)
    assert done == 0, f"init_schema 已经迁过了，再调必须是 0（实测 {done}）"

    # ③ 数据一行不少 + 新值写得进
    assert conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0] == n_before
    _mk_doc(conn, "doc_ref_after", "征求意见稿·迁移后", status="reference")
    assert conn.execute("SELECT legal_status FROM doc_meta WHERE doc_id='doc_ref_after'"
                       ).fetchone()[0] == "reference"

    # ④ 索引跟着回来（显式索引 + 库里原有的那几个）
    idx = {r[1] for r in conn.execute("PRAGMA index_list(doc_meta)").fetchall()}
    assert "idx_ref_test_short" in idx, f"显式索引没跟着回来：{sorted(idx)}"
    assert {"idx_doc_short_code", "idx_doc_hierarchy"} <= idx, f"原有索引丢了：{sorted(idx)}"

    # ⑤ 外键**级联**是通的（真删一行来证，不看 DDL 文本）
    fks = conn.execute("PRAGMA foreign_key_list(clause_revision)").fetchall()
    assert any(r[2] == "doc_meta" and r[6] == "CASCADE" for r in fks), \
        f"clause_revision 的外键没指向 doc_meta/CASCADE：{[tuple(r) for r in fks]}"
    conn.execute("DELETE FROM doc_meta WHERE doc_id='doc_keep_1'")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id='doc_keep_1'"
                       ).fetchone()[0] == 0, "删了文档，条款没被级联删掉 ⇒ 重建把外键弄断了"
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    # ⑥ 幂等：整套再跑一遍，仍是 0、数据还在
    sqlite_db.init_schema(db_file)
    assert sqlite_db._ensure_legal_status_reference(conn) == 0
    assert conn.execute("SELECT COUNT(*) FROM doc_meta WHERE doc_id='doc_ref_after'"
                       ).fetchone()[0] == 1
    sqlite_db.close_all_connections()


def test_ref_migration_leaves_other_enum_alone(db):
    """**不动** `update_change_event.current_legal_status`（四值）—— 它没有生产者要写 reference。

    这条是"**不许顺手把别的契约放松**"的判据：将来谁想给它加 reference，必须同时带来
    写它的那条通路，否则这个用例会红。
    """
    sql = db.execute("SELECT sql FROM sqlite_master WHERE type='table'"
                     " AND name='update_change_event'").fetchone()
    assert sql is not None
    assert sqlite_db.LEGAL_STATUS_REFERENCE not in sql[0], \
        "update_change_event 的枚举被顺手放宽了（没有生产者会写这个值）"
    assert "reference" not in sqlite_db._LEGAL_STATUS_TABLES
