"""从生产库切一个**小而全**的种子库，供门禁/开发用。

## 为什么需要它（这是仓库当前最大的结构性缺口）

`var/data/` 72 GB 不受版本控制 ⇒ 新克隆的仓是空库 ⇒ **所有依赖真实语料的判据
在门禁里结构上做不到**（实测：3,076 条用例里跑在真库上的是 0 条）。
后果：`resolve_clause` 的跨标准误命中（9 部受害标准）这类缺陷能活到今天。

## 这个脚本做什么

按「**每部标准至少留一条条款 + 覆盖各效力状态 + 覆盖各文档类型**」挑样本，
切成一个约 30~80 MB 的 sqlite，写进 `tests/fixtures/seed/`，随仓走。

## 保留什么

- `doc_meta`：抽样文档（默认 120 部，含全部 withdrawn/reference + 各 standard_type）
- `clause_revision`：这些文档的**全部**条款（不截断，否则条款号语义会断）
- `source_span`：这些条款的位置片段（可点链接要用）
- `folder` / `folder_member` / `doc_filing_state`：目录结构（检索可见性判据要用）
- `clause_fts`：FTS 索引（要重建，不能直接拷影子表）
- `alias_store` / `app_config` / `legal_*`：小表整拷

## 不保留什么

- `clause_vec`（向量要重算，且它依赖模型）、`material_*`（材料平面另算）、
  `event_log` / `operation_log` / `debug_dump`（运行日志）、`announcement_*` / `update_*`（巡检台账）

用法：
    python scripts/make-seed-db.py                    # 写到 tests/fixtures/seed/
    python scripts/make-seed-db.py --docs 200         # 抽更多文档
    python scripts/make-seed-db.py --out <path>
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DB = ROOT / "var" / "data" / "database" / "knowledge.db"
DEFAULT_OUT = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"

#: 整表照搬的小表（行数少、语义独立、判据会用到）
COPY_WHOLE = [
    "alias_store", "app_config", "legal_obligation", "obligation_list",
    "internal_policy", "review_point", "review_task", "gap_analysis",
    "snapshot_meta", "user_bookmark_folder",
]

#: 依赖抽样文档的表 → 过滤列（**各表列名不同，实测过**，别假设都叫 doc_id）
BY_DOC = {
    "doc_filing_state": "doc_id",
    "doc_ccs_state": "doc_id",
    "doc_page_geometry": "doc_id",
    "folder_member": "item_id",          # 多态列：item_kind 区分 doc / clause
    "evidence_edge": "source_clause_id",  # 条款级，按 clause 过滤
}
BY_CLAUSE = {"clause_patch": "clause_revision_id"}


#: **必须进种子库的标准**（判据：它们能暴露已知缺陷，不是"随便抽"）
#:
#: 这 12 部是 `resolve_clause` 年份兜底跨标准误命中（wiki §四 #2）的**完整现场**：
#: 前 9 部是"受害标准"（查一个不存在的条款号会被兜底串到别家），
#: 后 3 部是"被误命中的别家标准"。**少了任何一部，那条缺陷就没法在门禁里复现。**
MUST_INCLUDE = [
    "GBZ 188-2025", "GBZ 24-2025", "GBZ 215-2025", "GBZ 336-2025", "GBZ 337-2025",
    "GBZ 15-2024", "GBZ 37-2024", "GB/T 144-2024", "GB/T 150.4-2024",
    "GB 6675.2-2025", "GB/T 13537-2024", "GB 16556-2025",
    # 年份宽容的**正向**样本（改兜底时不能把它改坏）
    "GB 3608-2025", "GB 30871-2022",
]


def pick_docs(conn: sqlite3.Connection, limit: int) -> list[str]:
    """挑样本文档：**先保证缺陷可复现，再保证类型覆盖，最后才按大小补**。

    判据（不是随便抽）：
    0. `MUST_INCLUDE` 里的标准**必须有** —— 否则已知缺陷在门禁里复现不了；
    1. 每个 `legal_status` 至少留 1 部（`withdrawn` 只有 4 部，全留）；
    2. 每个 `standard_type` 至少留 2 部；
    3. 剩下的名额给**条款数少**的文档 —— 种子库要小、要能进版本控制，
       大文档只会让产物膨胀而不增加判据覆盖。
    """
    picked: list[str] = []
    seen: set[str] = set()

    def add(rows):
        for (doc_id,) in rows:
            if doc_id not in seen:
                seen.add(doc_id)
                picked.append(doc_id)

    # ⓿ 已知缺陷的现场（缺一部就复现不了）
    missing = []
    for no in MUST_INCLUDE:
        r = conn.execute("SELECT doc_id FROM doc_meta WHERE standard_no=?", (no,)).fetchone()
        if r:
            add([(r[0],)])
        else:
            missing.append(no)
    if missing:
        print(f"   ⚠ 这些必含标准在源库里没有：{missing}")

    # ① 效力状态全覆盖
    for status, in conn.execute("SELECT DISTINCT legal_status FROM doc_meta").fetchall():
        add(conn.execute(
            "SELECT doc_id FROM doc_meta WHERE legal_status IS ? LIMIT 5", (status,)))
    # ② 文档类型覆盖
    for st, in conn.execute("SELECT DISTINCT standard_type FROM doc_meta").fetchall():
        add(conn.execute(
            "SELECT doc_id FROM doc_meta WHERE standard_type IS ? LIMIT 3", (st,)))
    # ③ 按条款数**从小到大**补齐（种子库要小）
    add(conn.execute(
        "SELECT dm.doc_id FROM doc_meta dm"
        " LEFT JOIN (SELECT doc_id, COUNT(*) n FROM clause_revision GROUP BY doc_id) c"
        "   ON c.doc_id = dm.doc_id"
        " ORDER BY COALESCE(c.n, 0) ASC LIMIT ?", (limit,)))
    return picked[:max(limit, len(picked))]


def copy_table(src: sqlite3.Connection, dst: sqlite3.Connection, table: str,
               where: str = "", params: tuple = ()) -> int:
    cols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
    if not cols:
        print(f"   ⚠ 源库没有表 {table}，跳过")
        return 0
    sql = f'SELECT {",".join(f"[{c}]" for c in cols)} FROM "{table}"' + (f" WHERE {where}" if where else "")
    rows = src.execute(sql, params).fetchall()
    if not rows:
        return 0
    ph = ",".join("?" * len(cols))
    dst.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({",".join(f"[{c}]" for c in cols)}) VALUES ({ph})',
        rows)
    return len(rows)


def copy_by_temp_table(src: sqlite3.Connection, dst: sqlite3.Connection, table: str,
                       key_col: str, keys: list[str]) -> int:
    """按一列 keys 过滤拷贝 —— 用**临时表 join**，不用 `IN (?,?,…)`。

    ⚠ 为什么不能用 `IN`：SQLite 默认变量上限 32,766（`SQLITE_MAX_VARIABLE_NUMBER`），
    而抽样 135 部文档就有 **75,337 条条款** ⇒ `too many SQL variables`。
    临时表没有这个限制，而且快得多（一次 join 而不是拼接巨型 SQL）。
    """
    cols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")')]
    if not cols:
        print(f"   ⚠ 源库没有表 {table}，跳过")
        return 0
    dst.execute("DROP TABLE IF EXISTS _seed_keys")
    dst.execute("CREATE TEMP TABLE _seed_keys(k TEXT PRIMARY KEY)")
    dst.executemany("INSERT OR IGNORE INTO _seed_keys(k) VALUES (?)", [(k,) for k in keys])
    dst.commit()
    # 把 key 写成一张**临时 sqlite 库文件**，再用 ATTACH 在源库侧 join。
    # ⚠ 不用 `PRAGMA temp_store_directory`：该 pragma 已废弃且常返回 None（本脚本踩过）。
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="ks_seed_keys_")
    tmp_path = Path(tmpdir) / "_seed_keys.db"
    kc = sqlite3.connect(tmp_path)
    kc.execute("CREATE TABLE k(k TEXT PRIMARY KEY)")
    kc.executemany("INSERT OR IGNORE INTO k VALUES (?)", [(x,) for x in keys])
    kc.commit()
    kc.close()
    src.execute("ATTACH DATABASE ? AS seedkeys", (str(tmp_path),))
    try:
        sel = ", ".join(f's."{c}"' for c in cols)
        sql = (f'SELECT {sel} FROM "{table}" s'
               f' JOIN seedkeys.k k ON k.k = s."{key_col}"')
        rows = src.execute(sql).fetchall()
    finally:
        src.execute("DETACH DATABASE seedkeys")
        try:
            tmp_path.unlink()
        except OSError:
            pass
    if not rows:
        return 0
    ph = ",".join("?" * len(cols))
    dst.executemany(
        f'INSERT OR REPLACE INTO "{table}" ({",".join(f"[{c}]" for c in cols)}) VALUES ({ph})',
        rows)
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", type=int, default=120)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    if not SRC_DB.exists():
        print(f"源库不存在：{SRC_DB}", file=sys.stderr)
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    src = sqlite3.connect(f"file:{SRC_DB}?mode=ro", uri=True)
    # 用源库的 schema 建空壳（保证列/索引/约束一致）。
    # ⚠ 必须**逐条** execute：`sqlite_master.sql` 里的 DDL **不带结尾分号**，
    #   直接 `executescript` 会在第二条 CREATE 处报 `near "CREATE": syntax error`
    #   （本脚本第一版就这么挂的）。
    ddl = [r[0] for r in src.execute(
        "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL"
        " AND name NOT LIKE 'sqlite_%'"
        # FTS/vec 的影子表**不建**：它们由 `CREATE VIRTUAL TABLE` 自动生成，
        # 手建会和虚拟表冲突。
        " AND name NOT IN ('clause_fts_data','clause_fts_idx','clause_fts_content',"
        "'clause_fts_docsize','clause_fts_config')")]
    dst = sqlite3.connect(out)
    for stmt in ddl:
        try:
            dst.execute(stmt)
        except sqlite3.OperationalError as exc:
            print(f"   ⚠ 建表跳过（{exc}）：{stmt[:70]}...")
    dst.commit()

    docs = pick_docs(src, args.docs)
    print(f"抽样文档 {len(docs)} 部")
    ph = ",".join("?" * len(docs))

    print("\n=== 按文档抽样 ===")
    print(f"   doc_meta（抽样文档）        {copy_by_temp_table(src, dst, 'doc_meta', 'doc_id', docs):>9,}")
    print(f"   folder（整拷，树必须完整）  {copy_table(src, dst, 'folder'):>9,}")
    for t, col in BY_DOC.items():
        if t == "evidence_edge":
            continue  # 条款级，下面按 clause 过滤
        if t == "folder_member":
            where = f"item_kind='doc' AND item_id IN ({ph})"
            n = copy_table(src, dst, t, where, tuple(docs))
        else:
            n = copy_table(src, dst, t, f"{col} IN ({ph})", tuple(docs))
        print(f"   {t:26} {n:>9,}")

    print("\n=== 按条款抽样 ===")
    clause_ids = [r[0] for r in src.execute(
        f"SELECT clause_revision_id FROM clause_revision WHERE doc_id IN ({ph})",
        tuple(docs))]
    print(f"   条款数 {len(clause_ids):,}")
    for t in ["clause_revision", "source_span"]:
        n = copy_by_temp_table(src, dst, t, "clause_revision_id", clause_ids)
        print(f"   {t:26} {n:>9,}")
    for t, col in BY_CLAUSE.items():
        n = copy_by_temp_table(src, dst, t, col, clause_ids)
        print(f"   {t:26} {n:>9,}")
    n = copy_by_temp_table(src, dst, "evidence_edge", "source_clause_id", clause_ids)
    print(f"   {'evidence_edge':26} {n:>9,}")
    # user_annotation 按 clause_key 挂
    keys = [r[0] for r in dst.execute("SELECT clause_key FROM clause_revision").fetchall()]
    if keys:
        n = copy_by_temp_table(src, dst, "user_annotation", "clause_key", keys)
        print(f"   {'user_annotation':26} {n:>9,}")

    print("\n=== 整表照搬（小表）===")
    for t in COPY_WHOLE:
        n = copy_table(src, dst, t)
        print(f"   {t:26} {n:>9,}")

    print("\n=== 重建 FTS（不能拷影子表，也不能靠 rebuild）===")
    # ⚠ `clause_fts` 是**独立 FTS5 表**（不带 `content=` 选项）⇒ `INSERT INTO x(x) VALUES('rebuild')`
    #   会**返回 0 行**且不报错（本脚本第一版就这么静默失败了）。
    #   必须照 `clause_repo.py:327` 那处写入的同一口径显式插：
    #   `content_segmented` / `behavior_scope_segmented` 都要**先分词**（jieba）。
    # 必须先把仓根放进 sys.path（脚本从 scripts/ 跑，`src` 不在搜索路径上）
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from src.core.text_utils import segment_for_fts  # noqa: PLC0415

    rows = dst.execute(
        "SELECT clause_revision_id, clause_number, "
        "  (SELECT standard_no FROM doc_meta WHERE doc_meta.doc_id = clause_revision.doc_id), "
        "  COALESCE(title,''), COALESCE(content_text,''), COALESCE(modality,''), "
        "  COALESCE(subject,''), COALESCE(behavior_scope,'') "
        "FROM clause_revision").fetchall()
    dst.executemany(
        "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no, title,"
        " content_segmented, modality, subject, behavior_scope_segmented)"
        " VALUES (?,?,?,?,?,?,?,?)",
        [(r[0], r[1], r[2] or "", r[3], segment_for_fts(r[4]), r[5], r[6],
          segment_for_fts(r[7])) for r in rows])
    n = dst.execute("SELECT COUNT(*) FROM clause_fts").fetchone()[0]
    print(f"   clause_fts                {n:>9,}  （应与 clause_revision 同数）")

    dst.commit()
    dst.execute("VACUUM")
    dst.commit()

    print("\n=== 校验 ===")
    for t in ("doc_meta", "clause_revision", "source_span", "folder"):
        n = dst.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"   {t:26} {n:>9,}")
    size = out.stat().st_size / 1e6
    print(f"\n产物：{out}   {size:.1f} MB")
    dst.close()
    src.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
