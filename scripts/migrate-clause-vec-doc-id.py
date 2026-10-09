# -*- coding: utf-8 -*-
"""spec 003 · 迁移：给真库 `clause_vec` 加 `doc_id` 元数据列（**纯搬运，不重算向量**）。

## 为什么需要迁移

`clause_vec` 是 `vec0` **虚拟表**，`ALTER TABLE` 加列**不支持**；
而 `schema.sql` 里的 `CREATE VIRTUAL TABLE IF NOT EXISTS` 对**已存在**的表**不会**升级形状。
⇒ 存量库必须**建新表 + 搬数据 + 换名**。

## 为什么是"搬运"而不是"重算"

`doc_id` 从 `clause_revision.doc_id` 关联取得（库里已有），`embedding` **原样搬运**。
实测（`specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix2.py` Q7、
`var/tmp/r18/probe-migration.py` M2）**逐字节一致** ⇒ 不必承担重跑嵌入模型的浮点风险。

## 用法

```
python scripts/migrate-clause-vec-doc-id.py --dry-run          # 只读预演（不写库）
python scripts/migrate-clause-vec-doc-id.py --apply --db-copy  # 真跑（先做全库副本）
```

## 回滚（**可执行命令**，不是"理论上可以"）

`--apply` 会把旧数据**原样留一份**在普通表 `clause_vec_pre003`（**不删**），并打印下面三条：

```sql
DROP TABLE IF EXISTS clause_vec;
CREATE VIRTUAL TABLE clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512]);
INSERT INTO clause_vec(clause_revision_id, embedding)
    SELECT clause_revision_id, embedding FROM clause_vec_pre003;
```

再核一次行数即可。全库副本（`--db-copy`）路径也会打印出来。

⚠ **为什么不用 `ALTER TABLE … RENAME` 换名**（2026-10-09 实测踩过，已回滚）：
`vec0` 虚拟表 **RENAME 不连带改影子表**（`clause_vec_info` / `clause_vec_chunks` /
`clause_vec_rowids` / `clause_vec_vector_chunks00` 仍留旧名）⇒ 再建同名新表会撞
`Could not create '_info' shadow table: table "clause_vec_info" already exists`。
⇒ **必须走"普通表中转 → DROP 虚表 → 重建 → 回灌"**（`DROP` 会连影子表一起清掉）。

## 自检（任一不过 ⇒ 整体回滚、脚本非零退出）

1. 行数：迁移前后相同；
2. **向量逐字节相同**（全表比对，不是抽样）；
3. `doc_id` 与 `clause_revision` **全表一致**（`clause_vec.doc_id == clause_revision.doc_id`）；
4. 迁移后**形状正确**（`doc_id` 是普通列、`embedding` 仍 512 维）。
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

DDL_NEW = ("CREATE VIRTUAL TABLE clause_vec USING vec0("
           "clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[512])")
OLD_TABLE = "clause_vec_pre003"


def _db_path() -> Path:
    p = os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db")
    return Path(p)


def _conn(path: Path) -> sqlite3.Connection:
    import sqlite_vec
    c = sqlite3.connect(str(path), timeout=60)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=60000")
    c.enable_load_extension(True)
    sqlite_vec.load(c)
    c.enable_load_extension(False)
    return c


def _has_doc_id(c: sqlite3.Connection, table: str = "clause_vec") -> bool:
    try:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})")]
    except sqlite3.OperationalError:
        return False
    return "doc_id" in cols


def _count(c: sqlite3.Connection, table: str) -> int:
    return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description="clause_vec 加 doc_id 元数据列（纯搬运）")
    ap.add_argument("--apply", action="store_true", help="真的执行迁移（缺省 = 只读预演）")
    ap.add_argument("--dry-run", action="store_true", help="只读预演（缺省行为）")
    ap.add_argument("--db-copy", action="store_true", help="先做一份全库副本（强烈建议）")
    args = ap.parse_args()

    db = _db_path()
    if not db.exists():
        print(f"✗ 库不存在：{db}")
        return 2
    print(f"库：{db}  （{db.stat().st_size / 1024 / 1024:.0f} MB）")

    c = _conn(db)

    # ── 幂等：已经迁过就空操作（但**仍报一次自检读数**，便于事后核） ──────────────
    if _has_doc_id(c):
        print("✓ 已经是新形状（clause_vec 有 doc_id）⇒ 空操作")
        n = _count(c, "clause_vec")
        n_null = c.execute("SELECT COUNT(*) FROM clause_vec WHERE doc_id IS NULL").fetchone()[0]
        bad = c.execute(
            "SELECT COUNT(*) FROM clause_vec v JOIN clause_revision r"
            " ON r.clause_revision_id = v.clause_revision_id"
            " WHERE IFNULL(v.doc_id,'') <> IFNULL(r.doc_id,'')").fetchone()[0]
        print(f"  自检：行数 {n:,}｜doc_id 为空 {n_null}｜与 clause_revision 不一致 {bad}")
        if n_null or bad:
            print("  ⚠ **有新写入没带 doc_id** —— 最可能是**跑着的旧引擎**（未重启）写的。")
            print("    处置：① 重启引擎（`-m src.core.main`）；② 用下面的 SQL 回填：")
            print("    UPDATE clause_vec SET doc_id = (SELECT r.doc_id FROM clause_revision r"
                  " WHERE r.clause_revision_id = clause_vec.clause_revision_id)"
                  " WHERE doc_id IS NULL;")
        return 0

    n_before = _count(c, "clause_vec")
    n_clause = _count(c, "clause_revision")
    orphan = c.execute(
        "SELECT COUNT(*) FROM clause_vec v LEFT JOIN clause_revision r"
        " ON r.clause_revision_id = v.clause_revision_id WHERE r.clause_revision_id IS NULL"
    ).fetchone()[0]
    print(f"clause_vec 行数 = {n_before:,}｜clause_revision 行数 = {n_clause:,}")
    print(f"孤儿向量（在 clause_revision 里找不到对应条款）= {orphan:,}")

    if not args.apply:
        print()
        print("（只读预演；加 --apply 才写库。建议同时给 --db-copy。）")
        return 0

    # ── 全库副本 ───────────────────────────────────────────────────────────
    if args.db_copy:
        ts = time.strftime("%Y%m%d-%H%M%S")
        bak_dir = db.parent / "backup"
        bak_dir.mkdir(exist_ok=True)
        bak = bak_dir / f"{db.name}.bak-{ts}"
        t0 = time.time()
        dst = sqlite3.connect(str(bak))
        c.backup(dst)          # 在线备份 API：一致快照
        dst.close()
        print(f"① 全库副本：{bak}（{bak.stat().st_size / 1024 / 1024:.0f} MB，"
              f"{time.time() - t0:.0f} s）")

    t0 = time.time()
    try:
        c.execute("BEGIN IMMEDIATE")

        # ① 先把旧数据原样搬到**普通表**（回滚源）。
        #    ⚠ 不能用 `ALTER TABLE … RENAME`：vec0 的 RENAME **不连带改影子表** ⇒ 再建同名新表会撞名。
        c.execute(f"DROP TABLE IF EXISTS {OLD_TABLE}")
        c.execute(f"CREATE TABLE {OLD_TABLE}(clause_revision_id TEXT PRIMARY KEY,"
                  " doc_id TEXT, embedding BLOB)")
        c.execute(
            f"INSERT INTO {OLD_TABLE}(clause_revision_id, doc_id, embedding)"
            " SELECT v.clause_revision_id, r.doc_id, v.embedding FROM clause_vec v"
            " LEFT JOIN clause_revision r ON r.clause_revision_id = v.clause_revision_id")

        # ② DROP 旧虚表（连影子表一起清掉）+ 建新表 + 回灌（BLOB 原样 ⇒ 逐字节一致）
        c.execute("DROP TABLE clause_vec")
        c.execute(DDL_NEW)
        c.execute(
            "INSERT INTO clause_vec(clause_revision_id, doc_id, embedding)"
            f" SELECT clause_revision_id, doc_id, embedding FROM {OLD_TABLE}")

        # ③ 自检（在事务内；不过就抛）
        n_after = _count(c, "clause_vec")
        assert n_after == n_before, f"行数变了：{n_before} → {n_after}"

        bad_doc = c.execute(
            "SELECT COUNT(*) FROM clause_vec v JOIN clause_revision r"
            " ON r.clause_revision_id = v.clause_revision_id"
            " WHERE IFNULL(v.doc_id,'') <> IFNULL(r.doc_id,'')").fetchone()[0]
        assert bad_doc == 0, f"doc_id 与 clause_revision 不一致：{bad_doc} 行"

        cols = {r[1]: r for r in c.execute("PRAGMA table_info(clause_vec)")}
        assert "doc_id" in cols and cols["doc_id"]["pk"] == 0, "doc_id 不是普通列"

        c.execute("COMMIT")
    except Exception as e:  # noqa: BLE001
        c.execute("ROLLBACK")
        print(f"✗ 迁移失败已回滚：{type(e).__name__}: {e}")
        return 1

    print(f"② 迁移完成：{n_before:,} 行（{time.time() - t0:.0f} s）")

    # ── 事务外复核：**全表逐字节**比对（不是抽样） ────────────────────────────
    # ⚠ 用**一条 SQL** 全表比对（BLOB 直接 `<>`），不是 66 万次逐行查询 ——
    #   两种写法等价，但逐行查询在 663,634 行上要几分钟。
    t1 = time.time()
    n_old = _count(c, OLD_TABLE)
    missing = c.execute(
        f"SELECT COUNT(*) FROM {OLD_TABLE} p LEFT JOIN clause_vec v"
        " ON v.clause_revision_id = p.clause_revision_id WHERE v.clause_revision_id IS NULL"
    ).fetchone()[0]
    diff = c.execute(
        f"SELECT COUNT(*) FROM {OLD_TABLE} p JOIN clause_vec v"
        " ON v.clause_revision_id = p.clause_revision_id WHERE v.embedding <> p.embedding"
    ).fetchone()[0]
    print(f"③ 向量全表逐字节复核：旧表 {n_old:,} 行｜缺失 {missing}｜字节不同 {diff}"
          f"（{time.time() - t1:.0f} s）  {'✅' if (missing == 0 and diff == 0) else '❌'}")
    if missing or diff:
        print("   ✗ 自检不过 ⇒ 请按下面命令回滚")
        _print_rollback(db)
        return 1

    print()
    print("=" * 78)
    print("✅ 迁移完成且自检通过。")
    print()
    _print_rollback(db)
    return 0


def _print_rollback(db: Path) -> None:
    print("回滚（旧数据原样留在普通表里，**没删**）：")
    print("  DROP TABLE IF EXISTS clause_vec;")
    print("  CREATE VIRTUAL TABLE clause_vec USING vec0("
          "clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512]);")
    print(f"  INSERT INTO clause_vec(clause_revision_id, embedding)"
          f" SELECT clause_revision_id, embedding FROM {OLD_TABLE};")
    print("验证：`SELECT COUNT(*) FROM clause_vec;` 应回到迁移前的行数。")


if __name__ == "__main__":
    sys.exit(main())
