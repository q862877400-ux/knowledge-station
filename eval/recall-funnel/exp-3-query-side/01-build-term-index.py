"""E3 · 步骤 1：构建/加载**术语索引**（术语桥的离线产物）。

术语索引 = 全库"术语和定义"条款里抽出的 `TermEntry`（中文名/英文名/定义正文）**及其向量**。
它**离线构建、在线只查**（模块文档：全库 42,181 条实测 531 s；在线每条约 1.2 ms）。

⚠ **它扫的是全库，不来自考卷** —— 这是 E3 防作弊判据的结构性前提之一
（另一条：`TermIndex.select(query,k)` 的输入只有 query，签名里没有 gold）。

只读真库；产物落 `var/tmp/term-index-full.json`（与既有测量台**同一个缓存路径**，复用不另立）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3-query-side\\01-build-term-index.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / "var" / "tmp" / "term-index-full.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def main() -> int:
    from src.core.retrieval.term_bridge import TermIndex
    from src.core.storage.sqlite_db import load_vec_extension

    if CACHE.exists():
        idx = TermIndex.load(CACHE)
        print(f"[term] 复用缓存 {CACHE}：{len(idx)} 个术语")
        return 0

    print(f"[term] 无缓存，开始构建（只读真库）：{DB}")
    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    t0 = time.perf_counter()
    idx = TermIndex.build(conn)
    print(f"[term] 构建完成：{len(idx)} 个术语，用时 {time.perf_counter()-t0:.0f}s")
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    idx.save(CACHE)
    print(f"[term] 已写 {CACHE}（{CACHE.stat().st_size/1e6:.1f} MB）")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
