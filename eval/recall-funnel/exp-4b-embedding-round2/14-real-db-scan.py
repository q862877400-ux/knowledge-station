"""E4 第二轮 · 参照物复测：现有向量路「扫描」耗时 —— **在真库上**量一次。

为什么要单独量：`stop-loss.json` 把 A 臂的参照物写成"现有向量路扫描耗时，以本轮同跑内复测值为准"。
`10-latency.py` 量的是 `../exp-4-embedding-shadow/exp.db`（**第一轮的副本，521,978 行**），
而**真库已经长大了** ⇒ 拿副本的耗时当生产参照是错的。本脚本在**真库**（只读 `mode=ro`）上按同法复测。

同时报两个数，把差异归因说清：
 · 真库 vs 副本 → **行数不同**（真库 663,634 / 副本 521,978）⇒ 可解释；
 · 副本 812.3 ms vs `NEXT-DEV-PLAN §四第1条` 记的 **606.0 ms（52 万行）** → **同一行数、不同耗时**，
   ⚠ **本脚本归因不了**（当时的量测口径/工具未记录）⇒ 如实并列，**不猜**。
   （同批 `10-latency.py` 另量得副本中位 819.7 ms —— 与 812.3 同量级，见 README §二。）

只读；不写任何向量、不碰真库。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4b-embedding-round2\\14-real-db-scan.py
"""
from __future__ import annotations

import array
import json
import os
import sqlite3
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
COPY = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"
OUT = HERE / "latency-real-db-scan.json"
K = 1000
REPEAT = 5


def scan(conn, qv) -> float:
    t = time.perf_counter()
    list(conn.execute("SELECT clause_revision_id FROM clause_vec"
                      " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                      (array.array("f", qv).tobytes(), K)))
    return (time.perf_counter() - t) * 1000


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    qv = embedder.embed_query("退潮后在海泥里插竹竿吊养生蚝，这种做法属于哪种行当？")
    out: dict = {"k": K, "repeat": REPEAT,
                 "query": "考卷第 1 条（只用来取一个查询向量；扫描耗时与查询向量无关）"}
    for name, path in (("real_db", DB), ("round1_copy", COPY)):
        st = path.stat()
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        load_vec_extension(conn)
        n = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
        ms = [scan(conn, qv) for _ in range(REPEAT)]
        out[name] = {"file_MB": round(st.st_size / 2**20, 1), "rows": n,
                     "all_ms": [round(x, 1) for x in ms],
                     "median_ms": round(statistics.median(ms), 1),
                     "first_ms": round(ms[0], 1)}
        conn.close()
        print(f"[e4b] {name}: {out[name]['file_MB']} MB / {n} 行 / 中位 "
              f"{out[name]['median_ms']} ms（首跑 {out[name]['first_ms']} ms）", flush=True)

    copy_ms = out["round1_copy"]["median_ms"]
    out["recorded_reference"] = {
        "ms": 606.0, "rows": 521978,
        "source": "docs/NEXT-DEV-PLAN-2026-09-28.md §四第 1 条（『本轮静机复测 606.0 ms（52 万行）』）",
        "attribution": f"⚠ **归因不了**：副本同是 521,978 行却量到 {copy_ms} ms（本脚本同批实测；"
                       f"`10-latency.py` 同批另量得 819.7 ms），比计划记的 606.0 ms 高约 "
                       f"{round((copy_ms / 606.0 - 1) * 100)}%。当时的量测口径/工具没有记录 ⇒ "
                       f"两个数并列，**不猜**。",
    }
    out["why_two_numbers"] = (f"真库 663,634 行 / 副本 521,978 行 ⇒ **行数不同**（库长大了 141,656 条），"
                              f"这是可解释的差；606 vs {copy_ms} 那一段不可解释。")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
