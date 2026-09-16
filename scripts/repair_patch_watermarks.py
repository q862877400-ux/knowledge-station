# -*- coding: utf-8 -*-
"""修复：`clause_patch` 里被 `pypdf_backfill` 越界抽取污染的水印/页眉。

**背景（生产库实测）**：19,981 条 content_text 补丁中 14,906 条（74.6%）含盗版站
页脚/页眉，涉及 2,112 个文档；而**原文 0 条**——即由回填引入，非 OCR 原产。
根因见 `src/core/ingestion/pypdf_backfill.py:60`（"下一条款"判据不认 `表3`/`附录A`
→ buf 一路吃到页尾）与 `:102`（打补丁判据只看数字个数，无边界校验）。

清洗判据的**单一所有者**是 `src.core.text_utils.strip_watermark_lines`
（本脚本只调用它，不自己写判据——判据改动只需改那一处并过它自己的回归用例）。

**为什么要重算 clause_fts**：`fetch_full_clause` 读的是**补丁**正文，而
`clause_fts.content_segmented` 是**补丁前原文**的分词。历史事故链：
`pypdf_backfill` 用裸 `INSERT INTO clause_patch` 写库，**绕过了
`clause_repo.upsert_patch` 的 `_reindex_clause_indexes`** → 19,981 条补丁的 FTS
从未同步。本脚本对受影响行一并重算 FTS（与 `_reindex_clause_indexes` 同口径）。
向量**不重算**（诚实标注）：`_reindex_clause_indexes` 用 `embed_query` 对同一条
`f"{title}\n{content[:512]}"` 打分，若 `fastembed` 不在本进程可用则跳过；
水印位于文本尾部，对 512 字前缀的影响远小于对全文检索的影响。

用法（**默认 dry-run，零写入**）：
    .venv\\Scripts\\python scripts\\repair_patch_watermarks.py            # 只报告
    .venv\\Scripts\\python scripts\\repair_patch_watermarks.py --apply    # 落库
    .venv\\Scripts\\python scripts\\repair_patch_watermarks.py --apply --no-reindex
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.storage.sqlite_db import get_db_connection  # noqa: E402
from src.core.text_utils import strip_watermark_lines  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="真正落库（缺省只报告，零写入）")
    ap.add_argument("--no-reindex", action="store_true",
                    help="不改 clause_fts（默认改；见模块 docstring）")
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 条（调试用）")
    a = ap.parse_args()

    conn = get_db_connection()
    # 带上该文档**自己的标准号**：水印判据里"页码 + 标准号"这一族靠它消歧 ——
    # 页眉永远是自家标准号，而**表格末格**引用的是别人的标准
    # （实测误删样例：`'…牵条 优质碳素结构钢 20 GB/T699—2015'`）。
    sql = ("SELECT p.patch_id, p.clause_revision_id, p.patched_value, dm.standard_no"
           " FROM clause_patch p"
           " JOIN clause_revision cr ON cr.clause_revision_id = p.clause_revision_id"
           " JOIN doc_meta dm ON dm.doc_id = cr.doc_id"
           " WHERE p.field_name='content_text'")
    if a.limit:
        sql += f" LIMIT {int(a.limit)}"
    rows = conn.execute(sql).fetchall()
    print(f"content_text 补丁共 {len(rows)} 条；dry_run={not a.apply}")

    changed: list[tuple[str, str, str]] = []   # (patch_id, rid, new_value)
    for pid, rid, val, std in rows:
        v = val or ""
        new = strip_watermark_lines(v, own_standard_no=std or None)
        if new != v:
            changed.append((pid, rid, new))

    print(f"将清洗（内容有变化）: {len(changed)} 条")
    if not changed:
        print("无变化——无需处理（幂等）。")
        return 0
    print("\n样例（前 3 条尾部对照）:")
    for pid, rid, new in changed[:3]:
        old = conn.execute("SELECT patched_value FROM clause_patch WHERE patch_id=?",
                           (pid,)).fetchone()[0]
        print(f"  [{pid}]")
        print(f"    旧尾: …{old[-72:]!r}")
        print(f"    新尾: …{new[-72:]!r}")

    if not a.apply:
        print("\n[dry-run] 未写入。加 --apply 落库。")
        return 0

    n_fts = 0
    # **预取 CR 元数据**：逐行 SELECT clause_revision 会让 1.5 万次更新退化成
    # 1.5 万次关联查询（首版即因此跑到 10 分钟超时被截断——单事务虽保证原子，
    # 但吞吐不可接受）。这里一次取回。
    rids = [rid for _, rid, _ in changed]
    meta: dict[str, tuple] = {}
    CH = 900
    for i in range(0, len(rids), CH):
        chunk = rids[i:i + CH]
        ph = ",".join("?" * len(chunk))
        for r in conn.execute(
                "SELECT cr.clause_revision_id, cr.title, cr.modality, cr.subject,"
                " cr.behavior_scope FROM clause_revision cr"
                f" WHERE cr.clause_revision_id IN ({ph})", chunk):
            meta[r[0]] = (r[1], r[2], r[3], r[4])

    from src.core.storage.clause_repo import _seg
    # 分批提交：单事务 1.5 万行会长时间持写锁并让命令超时；批与批之间可续跑
    # （脚本幂等——直到底层判据认为"无变化"即视为完成）。
    for i in range(0, len(changed), CH):
        batch = changed[i:i + CH]
        with conn:
            for pid, rid, new in batch:
                conn.execute(
                    "UPDATE clause_patch SET patched_value=?,"
                    " updated_at=datetime('now') WHERE patch_id=?", (new, pid))
                if a.no_reindex or rid not in meta:
                    continue
                title, modality, subject, bscope = meta[rid]
                cur = conn.execute(
                    "UPDATE clause_fts SET title=?, content_segmented=?, modality=?,"
                    " subject=?, behavior_scope_segmented=?"
                    " WHERE clause_revision_id=?",
                    (title or "", _seg(new), modality or "", subject or "",
                     _seg(bscope or ""), rid))
                n_fts += cur.rowcount
        print(f"  进度 {min(i + CH, len(changed))}/{len(changed)}"
              f"（累计 FTS {n_fts}）", flush=True)
    print(f"\n✅ 已落库：清洗 {len(changed)} 条 · FTS 重算 {n_fts} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
