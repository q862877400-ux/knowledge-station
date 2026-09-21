"""`scripts/apply-folder-filing.py`（对真库落库那一步）的用例。

全部在**小 fixture 库**上跑（`KS_DATA_DIR` 已被 conftest 换成临时目录，且本文件的库是
`tmp_path` 下的独立文件）——**绝不碰真库**。覆盖业主点名的每一条：

- 不加 `--apply` 时**一个字节都不写**（比大小 + mtime，还比三张新表的行数）；
- 三个顶层「标准/法律法规/公司制度」+「待分类」都建对（含手定的 `sort`）；
- 标准树**跳过重复的那一层**（「国家标准·行业标准·团体标准」不许出现在「标准」下面），
  第二层直接挂「标准」；
- **379 篇无分类 `queued` + 2 篇 `catalog_hidden=1` `failed`**（`failure_kind` 是中文，
  且**真的去数过条款**才敢写"正文条款为零"）；
- 读回自证的数字与库里的实际数字一致；
- **幂等**：跑两次目录数/成员数不变；
- 缺表时按 schema.sql 建那三张表，且**既有表/列一个都不动**；
- **备份失败 ⇒ 中止、不写库**；
- 预演不再备份、不建目录。

⚠ 为什么这些用例必须存在：这是**对真数据、不可逆写入**的一步（AGENTS.md「必验」第 ②类）。
"""
from __future__ import annotations

import importlib.util
import json
import socket
import sqlite3
from pathlib import Path

import pytest

from src.core.knowledge.doc_catalog import classify_document

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "apply-folder-filing.py"
_spec = importlib.util.spec_from_file_location("ks_apply_folder_filing", _SCRIPT)
applymod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(applymod)

#: 与真库实测同形的数字：379 篇无分类（372 其他标准 + 7 未定级）、2 篇解析失败被隐藏
_N_OTHER_STANDARD = 372
_N_UNDEFINED_LAW = 7
_N_NO_CLASS = _N_OTHER_STANDARD + _N_UNDEFINED_LAW          # 379
_N_HIDDEN = 2
_N_FILED = 3                                                # P16 ×2 + A00 ×1

_DOC_SQL = (
    "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
    " current_revision_id, domain_tags, file_path, file_hash, legal_hierarchy,"
    " doc_type, catalog_hidden) VALUES (?,?,?,?,'r1',?,?,?,?,?,?)")


def _mk(doc_id: str, std: str, name: str, tags, *, hierarchy=None,
        doc_type="standard", hidden=0) -> dict:
    return {"doc_id": doc_id, "standard_no": std, "standard_name": name,
            "domain_tags": json.dumps(tags), "legal_hierarchy": hierarchy,
            "doc_type": doc_type, "catalog_hidden": hidden}


def _fixture_docs() -> list[dict]:
    """3 篇能归位的 + 379 篇无分类 + 2 篇解析失败（与真库同形的小复制）。"""
    out = [
        _mk("t_std_p1", "GB 50016-2014", "建筑设计防火规范", ["CCS:P16 工程防火"]),
        _mk("t_std_p2", "GB 50017-2017", "钢结构设计标准", ["CCS:P16 工程防火"]),
        _mk("t_std_a1", "GB/T 50001-2017", "房屋建筑制图统一标准",
            ["CCS:A00 标准化管理与一般规定"]),
    ]
    for i in range(_N_OTHER_STANDARD):
        out.append(_mk(f"t_nc_{i:03d}", f"GB/T {90000 + i}-2020", f"无分类标准{i}", []))
    for i in range(_N_UNDEFINED_LAW):
        out.append(_mk(f"t_law_{i}", f"某未定级法规通知{i}", f"某未定级法规{i}", [],
                       hierarchy="查无此层级", doc_type="法律法规"))
    out.append(_mk("t_hid_1", "GB/T 12668.8-2017", "机械电气设备 第8部分", [], hidden=1))
    out.append(_mk("t_hid_2", "GB 9706.222-2022", "医用电气设备 第2-22部分", [], hidden=1))
    return out


def _make_db(path: Path, *, drop_target_tables: bool = False,
             hidden_clauses: int = 0, extra_root: str | None = None) -> Path:
    """建一个小 fixture 库（生产同一套 schema）。"""
    from src.core.storage.sqlite_db import (close_thread_connection, get_db_connection,
                                            init_schema)
    init_schema(path)
    conn = get_db_connection(path)
    # ⚠ `catalog_hidden` **不在 schema.sql 里**（它是 clause_repo 的增量列，生产由
    #   `ensure_additive_columns()` 补上）。这里照它的 DDL 补一列，形状与真库一致。
    conn.execute("ALTER TABLE doc_meta ADD COLUMN catalog_hidden INTEGER NOT NULL DEFAULT 0")
    if drop_target_tables:                       # 测"缺表时自己建表"
        for t in ("folder_member", "folder", "doc_filing_state"):
            conn.execute(f"DROP TABLE IF EXISTS {t}")
    for d in _fixture_docs():
        conn.execute(_DOC_SQL, (d["doc_id"], d["standard_no"], d["standard_name"],
                                d["doc_id"], d["domain_tags"], "a.pdf",
                                f"h-{d['doc_id']}", d["legal_hierarchy"], d["doc_type"],
                                d["catalog_hidden"]))
    for i in range(hidden_clauses):              # 给"解析失败"那篇塞几条正文条款
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_type)"
            " VALUES (?,?,?,?,?,?,?,?,'normal')",
            (f"cr_{i}", "r1", "t_hid_1", f"k{i}", f"{i + 1}", "正文", 1, 1))
    if extra_root:
        conn.execute("INSERT INTO folder(folder_id, parent_id, name) VALUES (?,NULL,?)",
                     ("fld_old", extra_root))
        conn.commit()
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    close_thread_connection()                    # 关连接 ⇒ -wal 落盘、mtime 定住
    return path


@pytest.fixture()
def fdb(_isolate_data_dir, tmp_path) -> Path:
    return _make_db(tmp_path / "knowledge.db")


def _sql(db: Path, sql: str, args=()) -> list[dict]:
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, args)]
    finally:
        conn.close()


def _one(db: Path, sql: str, args=()):
    return _sql(db, sql, args)[0]


def _folder_id(db: Path, name: str) -> str:
    row = _one(db, "SELECT folder_id FROM folder WHERE parent_id IS NULL AND name=?", (name,))
    return row["folder_id"]


def _expected_l2_names() -> list[str]:
    """两张卡片的第二层名字 —— **与计划同源**（classify_document），不手抄。"""
    pairs = [("GB 50016-2014", ["CCS:P16 工程防火"]),
             ("GB/T 50001-2017", ["CCS:A00 标准化管理与一般规定"])]
    return sorted({classify_document({"standard_no": s, "domain_tags": t,
                                      "doc_type": "standard"})["level2"] for s, t in pairs})


def _run(db: Path, tmp_path: Path, *extra: str) -> int:
    return applymod.main(["--source", str(db), "--backup-dir", str(tmp_path / "backups"),
                          "--out-dir", str(tmp_path / "out"), *extra])


# ─────────────────────────── 默认只预演：一个字都不写 ───────────────────────────

def test_dry_run_writes_nothing(fdb, tmp_path):
    before = (fdb.stat().st_size, fdb.stat().st_mtime_ns)
    assert _run(fdb, tmp_path) == 0
    assert (fdb.stat().st_size, fdb.stat().st_mtime_ns) == before
    # 三张表还在（init_schema 建的），但**一行都没有**
    for t in applymod.TARGET_TABLES:
        assert _one(fdb, f"SELECT COUNT(*) AS n FROM {t}")["n"] == 0
    # 不备份、不落报告
    assert not (tmp_path / "backups").exists()
    assert not (tmp_path / "out").exists()


def test_dry_run_prints_what_would_happen(fdb, tmp_path, capsys):
    assert _run(fdb, tmp_path) == 0
    out = capsys.readouterr().out
    assert "预演" in out and "一个字节都不写" in out
    assert "跳过重复的那一层" in out
    assert "标准(sort=10)" in out and "待分类(sort=90)" in out
    assert "queued 379" in out and "failed 2" in out
    assert "回退办法" in out                       # 回退命令必须打印出来


# ─────────────────────────── 真写：形状、顶层、跳层 ───────────────────────────

def test_apply_builds_tops_and_skips_the_redundant_level(fdb, tmp_path):
    assert _run(fdb, tmp_path, "--apply") == 0
    tops = _sql(fdb, "SELECT name, sort FROM folder WHERE parent_id IS NULL"
                     " ORDER BY sort")
    assert [(t["name"], t["sort"]) for t in tops] == list(applymod.PREBUILT_TOPS)
    # 「标准」的直接下级 = 计划的第二层；**没有**重复的那一层
    kids = [r["name"] for r in _sql(
        fdb, "SELECT f.name FROM folder f JOIN folder_member m"
             " ON m.item_id=f.folder_id AND m.item_kind='folder'"
             " WHERE m.folder_id=? ORDER BY f.name", (_folder_id(fdb, "标准"),))]
    assert kids == _expected_l2_names()
    assert applymod.PLAN_STD_LEVEL1 not in kids
    # 顶层不许出现那个名字（既不在「标准」下，也不在根层）
    assert _sql(fdb, "SELECT 1 FROM folder WHERE name=?", (applymod.PLAN_STD_LEVEL1,)) == []
    # 「法律法规」「公司制度」保持空的；「待分类」里 379+2 篇
    for name in ("法律法规", "公司制度"):
        assert _one(fdb, "SELECT COUNT(*) AS n FROM folder_member WHERE folder_id=?",
                    (_folder_id(fdb, name),))["n"] == 0
    assert _one(fdb, "SELECT COUNT(*) AS n FROM folder_member WHERE folder_id=?"
                     " AND item_kind='file'", (_folder_id(fdb, "待分类"),))["n"] == \
        _N_NO_CLASS + _N_HIDDEN


def test_states_and_members_are_exactly_the_plan(fdb, tmp_path):
    assert _run(fdb, tmp_path, "--apply") == 0
    st = {r["stage"]: r["n"] for r in _sql(
        fdb, "SELECT stage, COUNT(*) AS n FROM doc_filing_state GROUP BY stage")}
    assert st == {"filed": _N_FILED, "queued": _N_NO_CLASS, "failed": _N_HIDDEN}
    assert _one(fdb, "SELECT COUNT(*) AS n FROM folder_member WHERE item_kind='file'")["n"] \
        == _N_FILED + _N_NO_CLASS + _N_HIDDEN
    # 归位的那几篇要记"谁在什么时候放进了哪个目录"
    row = _one(fdb, "SELECT * FROM doc_filing_state WHERE doc_id='t_std_p1'")
    assert row["stage"] == "filed" and row["placed_folder_id"] and row["placed_by"] \
        == "apply-folder-filing" and row["placed_at"]


def test_hidden_docs_go_to_pending_as_failed(fdb, tmp_path):
    assert _run(fdb, tmp_path, "--apply") == 0
    pend = _folder_id(fdb, "待分类")
    rows = {r["item_id"]: r for r in _sql(
        fdb, "SELECT m.item_id, s.stage, s.failure_kind FROM folder_member m"
             " LEFT JOIN doc_filing_state s ON s.doc_id=m.item_id"
             " WHERE m.folder_id=? AND m.item_kind='file'", (pend,))}
    assert rows["t_hid_1"]["stage"] == "failed"
    assert rows["t_hid_2"]["stage"] == "failed"
    assert rows["t_hid_1"]["failure_kind"] == applymod.FAILURE_KIND_ZERO_CLAUSES
    assert "解析失败" in rows["t_hid_2"]["failure_kind"]
    assert rows["t_nc_000"]["stage"] == "queued"
    assert rows["t_law_0"]["stage"] == "queued"
    # ⚠⚠ **2026-09-21（KB-FOLDER-PLAN 第 4 步）口径变更，就地把断言改成判「构成」**
    #   （原文保留在下面，别删）：原来是 `listed["total"] == _N_NO_CLASS`（379）——
    #   那时**列表接口**按 `catalog_hidden=0` 过滤，那 2 篇解析失败的真标准**在列表里看不到**
    #   （方案 §十 登记的缺陷）。第 4 步按 §十七③「看不到就修不了」把它改成
    #   `可见 OR stage='failed'` ⇒ 待分类 = **381**（379 queued + 2 failed），那 2 篇能看见、
    #   能被「重来一次」修。**判据不写成一个孤零零的 381**（那等于把口径藏进一个数字里），
    #   而是逐项判构成 + 判"被隐藏的那两篇确实在列表里"。
    from src.core.knowledge import folder_store as fs
    listed = fs.list_pending_filing(limit=5000, db_path=fdb)
    assert listed["total"] == _N_NO_CLASS + _N_HIDDEN          # 379 + 2 = 381
    assert len(listed["items"]) == _N_NO_CLASS + _N_HIDDEN
    by_stage: dict[str, int] = {}
    for it in listed["items"]:
        by_stage[str(it["stage"])] = by_stage.get(str(it["stage"]), 0) + 1
    assert by_stage == {"queued": _N_NO_CLASS, "failed": _N_HIDDEN}, by_stage
    # 「识别失败」的那两篇**就在列表里**（它们 `catalog_hidden=1`，过去正是被这一条挡掉的）
    hidden_in_list = {it["doc_id"] for it in listed["items"] if it["catalog_hidden"] == 1}
    assert hidden_in_list == {"t_hid_1", "t_hid_2"}, hidden_in_list
    assert set(rows) == {f"t_nc_{i:03d}" for i in range(_N_OTHER_STANDARD)} \
        | {f"t_law_{i}" for i in range(_N_UNDEFINED_LAW)} | {"t_hid_1", "t_hid_2"}


def test_hidden_doc_with_real_clauses_gets_an_honest_failure_kind(_isolate_data_dir,
                                                                 tmp_path):
    """库里**有**正文条款还写着"正文条款为零"就是编 —— 必须换成如实的话。"""
    db = _make_db(tmp_path / "knowledge.db", hidden_clauses=3)
    assert _run(db, tmp_path, "--apply") == 0
    kind = _one(db, "SELECT failure_kind FROM doc_filing_state WHERE doc_id='t_hid_1'"
                    )["failure_kind"]
    assert kind != applymod.FAILURE_KIND_ZERO_CLAUSES
    assert "待核" in kind and "3" in kind
    # 另一篇没条款的仍然是那句标准话术
    assert _one(db, "SELECT failure_kind FROM doc_filing_state WHERE doc_id='t_hid_2'"
                    )["failure_kind"] == applymod.FAILURE_KIND_ZERO_CLAUSES


# ─────────────────────────── 幂等 ───────────────────────────

def test_reused_tops_get_the_hand_set_order(fdb, tmp_path):
    """早先以 sort=0 建出来的顶层目录，复用后 sort 要对齐到业主手定的
    10/20/30/90 —— 否则顺序会变成拼音序（「待分类」跑到第二位）。"""
    conn = sqlite3.connect(str(fdb))
    for i, (name, _) in enumerate(applymod.PREBUILT_TOPS):
        conn.execute("INSERT INTO folder(folder_id, parent_id, name, sort)"
                     " VALUES (?,NULL,?,0)", (f"fld_pre{i}", name))
    conn.commit()
    conn.close()
    assert _run(fdb, tmp_path, "--apply") == 0
    got = [(r["name"], r["sort"]) for r in _sql(
        fdb, "SELECT name, sort FROM folder WHERE parent_id IS NULL ORDER BY sort, name")]
    assert got == list(applymod.PREBUILT_TOPS)
    assert _one(fdb, "SELECT COUNT(*) AS n FROM folder WHERE parent_id IS NULL")["n"] == 4


def test_apply_twice_changes_no_counts(fdb, tmp_path):
    assert _run(fdb, tmp_path, "--apply") == 0
    snap = {t: _one(fdb, f"SELECT COUNT(*) AS n FROM {t}")["n"]
            for t in applymod.TARGET_TABLES}
    rows1 = sorted((r["folder_id"], r["parent_id"], r["name"]) for r in
                   _sql(fdb, "SELECT folder_id, parent_id, name FROM folder"))
    assert _run(fdb, tmp_path, "--apply") == 0                 # 第二次
    assert {t: _one(fdb, f"SELECT COUNT(*) AS n FROM {t}")["n"]
            for t in applymod.TARGET_TABLES} == snap
    rows2 = sorted((r["folder_id"], r["parent_id"], r["name"]) for r in
                   _sql(fdb, "SELECT folder_id, parent_id, name FROM folder"))
    assert rows1 == rows2                                       # 连 id 都没换
    # 顶层还是四个、不重名
    assert [r["name"] for r in _sql(
        fdb, "SELECT name FROM folder WHERE parent_id IS NULL ORDER BY sort, name")] == \
        [n for n, _ in applymod.PREBUILT_TOPS]


# ─────────────────────────── 建表：只许新增 ───────────────────────────

def test_missing_tables_are_created_and_nothing_else_is_touched(_isolate_data_dir,
                                                                tmp_path):
    db = _make_db(tmp_path / "knowledge.db", drop_target_tables=True)
    for t in applymod.TARGET_TABLES:
        assert _sql(db, "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (t,)) == []
    before = {r["name"]: r["sql"] for r in
              _sql(db, "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")}
    rc = _run(db, tmp_path, "--apply")
    assert rc == 0
    after = {r["name"]: r["sql"] for r in
             _sql(db, "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL")}
    # 既有对象一个都没改
    assert {k: v for k, v in after.items() if k in before} == before
    # 三张表都在了
    for t in applymod.TARGET_TABLES:
        assert _one(db, "SELECT COUNT(*) AS n FROM sqlite_master WHERE name=?", (t,))["n"] == 1


def test_ddl_comes_from_schema_sql():
    """建表语句必须是**从 schema.sql 现取的**那三张表的（不手抄一份）。"""
    stmts = applymod.target_ddl()
    assert len(stmts) >= 5                          # 3 张表 + 至少 2 条索引
    for t in applymod.TARGET_TABLES:
        assert any(s.startswith(f"CREATE TABLE IF NOT EXISTS {t}") for s in stmts)
    assert all("IF NOT EXISTS" in s for s in stmts)
    # 一条都不许碰到别的表
    for s in stmts:
        assert not any(bad in s for bad in ("doc_meta", "clause_revision", "user_bookmark"))


# ─────────────────────────── 备份 ───────────────────────────

def test_backup_is_taken_and_verified(fdb, tmp_path):
    assert _run(fdb, tmp_path, "--apply") == 0
    files = list((tmp_path / "backups").glob("knowledge-pre-folders-*.db"))
    assert len(files) == 1
    # 备份是**写库之前**那一份：文档数一样、页数>0，而三张新表还是空的
    a = sqlite3.connect(str(fdb))
    b = sqlite3.connect(str(files[0]))
    try:
        assert a.execute("SELECT COUNT(*) FROM doc_meta").fetchone() == \
            b.execute("SELECT COUNT(*) FROM doc_meta").fetchone()
        assert b.execute("PRAGMA page_count").fetchone()[0] > 0
        assert b.execute("SELECT COUNT(*) FROM folder").fetchone()[0] == 0
        assert b.execute("SELECT COUNT(*) FROM doc_filing_state").fetchone()[0] == 0
        assert a.execute("SELECT COUNT(*) FROM folder").fetchone()[0] > 0
    finally:
        a.close()
        b.close()


def test_backup_failure_aborts_before_writing(fdb, tmp_path):
    """备份目录不可用 ⇒ 退出码 2，**库一个字节都没动、一行都没写**。"""
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("x", encoding="utf-8")
    before = (fdb.stat().st_size, fdb.stat().st_mtime_ns)
    rc = applymod.main(["--source", str(fdb), "--apply", "--backup-dir", str(blocker),
                        "--out-dir", str(tmp_path / "out")])
    assert rc == 2
    assert (fdb.stat().st_size, fdb.stat().st_mtime_ns) == before
    assert _one(fdb, "SELECT COUNT(*) AS n FROM folder")["n"] == 0
    assert _one(fdb, "SELECT COUNT(*) AS n FROM doc_filing_state")["n"] == 0


# ─────────────── 对账：库被事先动过 ⇒ 中止不写（第 2 步修准的第 0 条）───────────────
#
# 背景（2026-09-21 独立复核在 verify-freeze-kb-filed 上实测）：原先那句
# "既有表/列指纹一个都没变"只比"本次建表前后"，而三条建表语句全是 IF NOT EXISTS
# ⇒ 分支永不响。实测：删掉一个既有索引、或给既有表加一列，再 --apply ⇒
# **exit 0 照写**（还照做备份、照覆盖 6417 条状态行）。
# 下面两条就是那次实测的复现，修准后必须**退出非 0 且零写入**。

def _state(db: Path) -> dict:
    return applymod.db_state(db)


def test_apply_aborts_when_an_existing_index_is_missing(fdb, tmp_path, capsys):
    """① 先删掉一个既有索引 ⇒ ``--apply`` 必须非 0 且**零写入**。"""
    conn = sqlite3.connect(str(fdb))
    conn.execute("DROP INDEX IF EXISTS idx_alias_lookup")
    conn.commit()
    conn.close()
    before = _state(fdb)

    rc = _run(fdb, tmp_path, "--apply")

    assert rc == 2
    after = _state(fdb)
    assert applymod._db_state_diff(before, after) == {}       # .db/-wal/行数/对象 全同
    assert _one(fdb, "SELECT COUNT(*) AS n FROM folder")["n"] == 0
    assert _one(fdb, "SELECT COUNT(*) AS n FROM doc_filing_state")["n"] == 0
    assert not (tmp_path / "backups").exists()                # 连备份都没建
    out = capsys.readouterr()
    assert "idx_alias_lookup" in out.err and "中止" in out.err


def test_apply_aborts_when_an_existing_table_gained_a_column(fdb, tmp_path, capsys):
    """② 给既有表**加**一列 ⇒ **不中止**（只登记）。

    为什么加列不算"库被人动过"：生产的 ``create_app`` 每次启动都调
    ``clause_repo.ensure_additive_columns()`` —— **合法地**给既有表加列
    （``catalog_hidden`` 就是这么来的）。拿它当中止条件会把正常库判死。
    ⇒ 加列只在 ``extra_columns`` 里登记一行，"库被删过东西"（下表那条缺列用例）
    才中止。
    """
    conn = sqlite3.connect(str(fdb))
    conn.execute("ALTER TABLE doc_meta ADD COLUMN zz_probe INTEGER")
    conn.commit()
    conn.close()
    drift = applymod.schema_drift(fdb)
    assert drift["ok"] is True
    assert "doc_meta.zz_probe" in drift["extra_columns"]
    before = _state(fdb)
    assert _run(fdb, tmp_path, "--apply") == 0                 # 照常写
    assert _state(fdb)["rows"]["folder"] > before["rows"]["folder"]
    assert "只登记、不中止" in capsys.readouterr().out


def test_apply_aborts_when_a_declared_column_is_missing(fdb, tmp_path, capsys):
    """② 库里少了 ``schema.sql`` 声明的列 ⇒ **中止**。

    ⚠ 为什么不用 ``ALTER TABLE … DROP COLUMN`` 造：本机 SQLite 不支持（用例会 skip，
    于是这条保护**根本没被试过**）。改成给 ``schema.sql`` **加一条声明**
    （``doc_meta.zz_missing``）—— 对账拿的就是"声明 ⇄ 实际"，多一条声明与少一列
    是同一个缺口的两面，而且与 SQLite 版本无关。
    """
    schema = tmp_path / "schema-probe.sql"
    src = applymod.DEFAULT_SCHEMA.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS doc_meta (" in src
    schema.write_text(src.replace(
        "CREATE TABLE IF NOT EXISTS doc_meta (",
        "CREATE TABLE IF NOT EXISTS doc_meta (\n    zz_missing TEXT,"), encoding="utf-8")

    drift = applymod.schema_drift(fdb, schema)
    assert drift["ok"] is False and "doc_meta.zz_missing" in drift["missing_columns"]

    before = _state(fdb)
    import pytest as _pytest
    with _pytest.raises(applymod.Abort) as ei:
        applymod.ensure_target_tables(fdb, schema)
    assert "对不上" in str(ei.value)
    assert applymod._db_state_diff(before, _state(fdb)) == {}   # 零写入
    assert not (tmp_path / "backups").exists()


def test_dry_run_prints_zero_write_proof_and_three_size_numbers(fdb, tmp_path, capsys):
    """预演要**打印三个数**（.db / -wal / 合计）与"零写入证据"（第 2 步的措辞修）。"""
    assert _run(fdb, tmp_path) == 0
    out = capsys.readouterr().out
    assert "零写入证据" in out and "连一行都没写" in out
    assert "既有表行数" in out and "schema 对象" in out
    assert "对账（库 vs schema.sql）" in out


def test_schema_drift_reports_extras_but_does_not_fail_on_them(fdb):
    """``schema_drift`` 的四个清单各就各位：多列只登记；缺索引/缺表/缺列才 ok=False。"""
    drift = applymod.schema_drift(fdb)
    assert drift["ok"] is True
    assert drift["missing_tables"] == [] and drift["missing_indexes"] == []
    assert drift["missing_columns"] == []
    assert isinstance(drift["extra_columns"], list)
    # 本步那三张表**不参与缺表检查**（它们本来就可能还不存在，是要动手建的东西）
    assert not (set(drift["missing_tables"]) & set(applymod.TARGET_TABLES))
    # 删一个索引 ⇒ 只有那一项报
    conn = sqlite3.connect(str(fdb))
    conn.execute("DROP INDEX IF EXISTS idx_alias_lookup")
    conn.commit()
    conn.close()
    bad = applymod.schema_drift(fdb)
    assert bad["ok"] is False and bad["missing_indexes"] == ["idx_alias_lookup"]
    assert bad["missing_tables"] == [] and bad["missing_columns"] == []


def test_declared_objects_splits_sql_despite_comments_and_semicolons():
    """``declared_objects`` 必须真的解析出列。

    2026-09-21 实测踩到两个坑（都在 ``_strip_sql_comments`` 的 docstring 里）：
    ① 行尾 ``--`` 注释会把 ``page_breaks TEXT,  -- …PDF页…`` 读成一个叫 ``PDF页`` 的列；
    ② 字符串字面量里的 ``;``（FTS 的 ``tokenize``）会把 ``CREATE TABLE`` 切成碎片，
       于是脚本报"找不到这三张表的建表语句"。
    ⇒ 这条用例把两件事都钉住。
    """
    d = applymod.declared_objects()
    assert "folder" in d["tables"] and "doc_meta" in d["tables"]
    assert "idx_folder_root_name" in d["indexes"]
    for t, cols in d["tables"].items():
        assert cols, t
        for col in cols:
            assert col.isascii() and col.replace("_", "").isalnum(), (t, col)
    assert "page_breaks" in d["tables"]["clause_revision"]
    assert len(d["tables"]) >= 30 and len(d["indexes"]) >= 30
    # 三张表的建表语句必须能现取出来（②那个坑一旦复发这里当场红）
    stmts = applymod.target_ddl()
    for t in applymod.TARGET_TABLES:
        assert any(s.startswith(f"CREATE TABLE IF NOT EXISTS {t}") for s in stmts)


def test_refuses_when_the_unskipped_tree_is_already_there(_isolate_data_dir, tmp_path):
    """顶层已经有「国家标准·行业标准·团体标准」⇒ 拒绝，免得建出两棵并存的树。"""
    db = _make_db(tmp_path / "knowledge.db", extra_root=applymod.PLAN_STD_LEVEL1)
    rc = _run(db, tmp_path, "--apply")
    assert rc == 2
    assert _one(db, "SELECT COUNT(*) AS n FROM folder")["n"] == 1      # 只有那棵旧树
    assert not (tmp_path / "backups").exists()                          # 连备份都没做
    assert _one(db, "SELECT COUNT(*) AS n FROM doc_filing_state")["n"] == 0


# ─────────────────────────── 读回自证 / 报告 ───────────────────────────

def test_skipped_level_and_top_names_come_from_one_owner():
    """「跳过哪一段 / 真顶层叫什么」只有**一个**所有者（复核 2026-09-21 的①）。

    以前脚本自己写 ``PLAN_STD_LEVEL1`` / ``STANDARD_TOP`` 两个字面量，接口侧（建议去向）
    另有一份猜法 ⇒ 两边口径一旦漂移，``suggest_folder_for_doc`` 就对真树永远命中不了
    （复核实测：真库 6036 篇已归位文件精确命中 0）。这条钉住：脚本取的就是所有者那份值，
    而且那条规则（分类口径 L1 → 真顶层名）本身也在所有者里。
    """
    from src.core.knowledge import folder_filing_plan as fp
    assert applymod.PLAN_STD_LEVEL1 == fp.SKIPPED_PLAN_TOP
    assert applymod.STANDARD_TOP == fp.STANDARD_TOP_NAME
    assert applymod.STANDARD_TOP == fp.folder_store.STANDARD_TOP_NAME
    # 规则本体：被跳过的那一段换成真顶层名（段数因此少一级），其余原样
    assert fp.tree_path_of((fp.SKIPPED_PLAN_TOP, "A 综合")) == (fp.STANDARD_TOP_NAME, "A 综合")
    assert fp.tree_path_of(("法律法规", "行政法规")) == ("法律法规", "行政法规")
    # 脚本的顶层名字清单也不许自己抄一份
    assert tuple(n for n, _ in applymod.PREBUILT_TOPS) == applymod.fs.PREBUILT_TOP_NAMES


def test_read_back_matches_the_database(fdb, tmp_path):
    """读回自证的数字必须与**直接查库**的结果一致（不是自说自话）。"""
    from src.core.knowledge import folder_filing_plan as fp
    from src.core.storage.sqlite_db import get_db_connection

    assert _run(fdb, tmp_path, "--apply", "--report", str(tmp_path / "r.json")) == 0
    docs = [dict(r) for r in _sql(
        fdb, "SELECT doc_id, standard_no, standard_name, legal_hierarchy, doc_type,"
             " domain_tags, catalog_hidden FROM doc_meta")]
    plan = fp.plan_filing(docs)
    conn = get_db_connection(fdb)
    existing, _ = applymod._existing_folders(conn)
    payload = applymod.build_payload(plan, existing, {str(d["doc_id"]): d for d in docs},
                                     applymod._clause_counts(
                                         conn, list(plan["hidden_docs"])),
                                     "apply-folder-filing")
    v = applymod.read_back(fdb, plan=plan, payload=payload,
                           existing_total=len(set(existing.values())), sample=20, seed=7)
    assert v["mismatch"] == {}
    assert v["depth_matches_plan"] is True
    assert v["folders_total"] == _one(fdb, "SELECT COUNT(*) AS n FROM folder")["n"]
    assert v["member_rows_total"] == _one(
        fdb, "SELECT COUNT(*) AS n FROM folder_member")["n"]
    assert v["state_rows_total"] == _one(
        fdb, "SELECT COUNT(*) AS n FROM doc_filing_state")["n"]
    assert v["folders_by_depth"] == {1: 4, 2: 2, 3: 2, 4: 2}
    assert v["pending_docs"] == _N_NO_CLASS + _N_HIDDEN
    # ⚠⚠ **2026-09-21（KB-FOLDER-PLAN 第 4 步）口径变更，就地改成判「构成」**（原文保留：
    #   原来是 `v["pending_list_visible"] == _N_NO_CLASS`（379）——「列表接口按
    #   `catalog_hidden=0` 过滤」。第 4 步按 §十七③ 改成 `可见 OR stage='failed'`
    #   ⇒ 列表里能看到的就是**全部**待分类（381 = 379 queued + 2 failed），
    #   那 2 篇解析失败的真标准因此有了一条回头路（能在「待分类」里点「重来一次」）。
    #   ⇒ 判据改成三件事一起判：总数 = 待分类总数、**逐状态构成**、以及差额恰为 0 的原因。
    assert v["pending_list_visible"] == v["pending_docs"] == _N_NO_CLASS + _N_HIDDEN
    assert v["pending_by_stage"] == {"queued": _N_NO_CLASS, "failed": _N_HIDDEN}, \
        v["pending_by_stage"]
    assert len(v["spot_check"]) == min(20, v["folders_total"])   # 随机抽 20 个目录
    assert all({"path", "files", "files_total"} <= set(s) for s in v["spot_check"])
    assert v["standard_has_redundant_level"] is False
    rep = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert rep["by_depth"] == {"1": 4, "2": 2, "3": 2, "4": 2}
    assert rep["nodes_total"] == 10 and rep["nodes_reused"] == 0
    assert len(rep["failed_docs"]) == _N_HIDDEN
    assert rep["verify"]["mismatch"] == {}


def test_engine_running_prints_a_warning_but_does_not_block(fdb, tmp_path, monkeypatch,
                                                            capsys):
    """引擎在跑 ⇒ 打印醒目警告，但**不阻塞**（预演仍然跑完、仍然一个字不写）。"""
    data_dir = tmp_path / "datadir"
    data_dir.mkdir()
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    try:
        (data_dir / "engine.session.json").write_text(
            json.dumps({"port": port, "token": "t", "pid": 1234}), encoding="utf-8")
        monkeypatch.setenv("KS_DATA_DIR", str(data_dir))
        before = (fdb.stat().st_size, fdb.stat().st_mtime_ns)
        assert _run(fdb, tmp_path) == 0
        out = capsys.readouterr().out
        assert "引擎正在运行" in out and str(port) in out
        assert (fdb.stat().st_size, fdb.stat().st_mtime_ns) == before
    finally:
        srv.close()
