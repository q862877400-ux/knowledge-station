# -*- coding: utf-8 -*-
"""存量 content_text 三件套回填（2026-08-30 用户指令：按 triple-path 标准补齐 backfill 路）。

规则与 ingest 路完全一致（形态收敛、幂等可重放）：
    pua_bond_dash_html（PUA 键横线 → —，等长）
    sup_unit_exponents_text（cm-1 → cm⁻¹ Unicode 上标）
    space_clause_numbers_text（段首条款编号补空格）

同步维护（一致性铁律）：
  - clause_revision.content_hash     = sha256(new_text)（快照可验证红线 v2 #2）
  - clause_fts.content_segmented     = _seg(new_text)（jieba 分词，检索不断链）
  - clause_vec 不动：变化是标点/空格级，768 维向量漂移可忽略（DECISIONS 2026-08-30）
  - clause_patch（用户编辑权威数据）不动

用法：
  python scripts/backfill_text_trio.py            # dry-run：统计 + 抽样预览
  python scripts/backfill_text_trio.py --apply    # 实际写库（500 行/批事务）
"""
from __future__ import annotations

import sqlite3
import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

DB = Path(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
BATCH = 500

from src.core.text_utils import (  # noqa: E402
    pua_bond_dash_html, space_clause_numbers_text, sup_unit_exponents_text)
from src.core.storage.clause_repo import _seg, content_hash  # noqa: E402


def trio(text: str) -> str:
    """入库三件套（与 pipeline.py 落库前清洗完全同一顺序与实现）。"""
    return space_clause_numbers_text(
        sup_unit_exponents_text(pua_bond_dash_html(text)))


def main() -> None:
    apply = "--apply" in sys.argv
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row

    # FTS5 虚拟表 UPDATE 仅支持 rowid 定位（非 rowid 列 WHERE 的 UPDATE
    # binding 形态受限）——先载入 clause_revision_id → fts rowid 映射
    fts_rid = {cid: rid for rid, cid in
               conn.execute("SELECT rowid, clause_revision_id FROM clause_fts")}

    stats = {"scanned": 0, "changed": 0, "pua": 0, "sup": 0, "gap": 0}
    samples: list[tuple[str, str, str]] = []  # (clause_number, before, after)
    cur = conn.execute(
        "SELECT clause_revision_id, clause_number, content_text FROM clause_revision"
        " ORDER BY clause_revision_id")

    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        updates = []
        for r in rows:
            t = r["content_text"] or ""
            stats["scanned"] += 1
            # 分类计数（在单步应用前，反映每条规则的真实命中量）
            if "\ue5c6" in t:
                stats["pua"] += 1
            new = trio(t)
            if new == t:
                continue
            stats["changed"] += 1
            updates.append((new, content_hash(new), _seg(new),
                            r["clause_revision_id"]))
            if len(samples) < 6:
                samples.append((r["clause_number"], t[:60], new[:60]))
        if apply and updates:
            with conn:
                conn.executemany(
                    "UPDATE clause_revision SET content_text=?, content_hash=?"
                    " WHERE clause_revision_id=?",
                    [(u[0], u[1], u[3]) for u in updates])
                conn.executemany(
                    "UPDATE clause_fts SET content_segmented=? WHERE rowid=?",
                    [(u[2], fts_rid[u[3]]) for u in updates
                     if u[3] in fts_rid])

    conn.close()
    print(f"mode={'APPLY' if apply else 'DRY-RUN'} scanned={stats['scanned']} "
          f"changed={stats['changed']} (pua_rows={stats['pua']})")
    for no, b, a in samples:
        print(f"  [{no}]\n    - {b}\n    + {a}")


if __name__ == "__main__":
    main()
