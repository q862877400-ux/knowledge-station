"""真实提问召回测试（D1）—— 用**官方答复点名的真实问题**考我们的检索。

## 为什么做这个
我们一直用 120 道**自己造**的题打转。而手上躺着 **35,696 条真实公众提问**（官方答复）。
本脚本把它们里**能判分**的部分做成考题，直接在**生产检索路径**上跑。

## 两档考题（严格程度不同，必须分开报）
 · **文件级**：官方答复精确点名了一份文件、且那份文件在我们库里 ⇒
   判「返回结果里有没有**这份文件**的条文」。**样本量最大。**
 · **条文级**：答复里**只出现一个条号** ⇒ `问题 → (文件, 那一条)` **唯一确定** ⇒
   判「返回结果里有没有**那一条**」。**最严，样本量小。**

## 冻结口径（先写死，跑完不许改）
 · **考题** = `tools/gov-qa/recon/real-a-items.json`（从 35,696 条里筛出的「精确点名且在库」）；
 · **判分**：
   - 文件级 = 返回的任一条文所属 `standard_no` **等于** gold 文件的 `standard_no`；
   - 条文级 = 返回的任一条文 `clause_revision_id` **等于** gold 条文 id；
 · **查询用提问原文**（不改写、不加料）—— 这正是"用户真的这么问"；
 · **生产口径** = `search_with_details(top_k=8, rerank=False)`（`ks_answer` 的默认）；
 · **同时报诊断深度** `@8 / @20 / @100`（100 是诊断探针，不是生产）；
 · **只读**（`mode=ro`）；**不改任何生产代码**。

## 报什么
两档各自：`@8 / @20 / @100` 命中率 + 逐条明细（含**未命中的样本**，供人读）。

用法：
  .venv\\Scripts\\python.exe tools\\gov-qa\\run-real-recall.py --limit 200   # 小样本验通
  .venv\\Scripts\\python.exe tools\\gov-qa\\run-real-recall.py               # 全量
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
ITEMS = HERE / "recon" / "real-a-items.json"
OUT = HERE / "recon" / "real-recall.json"
OUT_Q = HERE / "recon" / "real-recall-per-query.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--depth", type=int, default=100, help="诊断深度（生产是 8）")
    args = ap.parse_args()

    from src.core.storage.sqlite_db import load_vec_extension
    from src.core.retrieval.hybrid_engine import search_with_details
    from src.core.retrieval import hybrid_engine as he
    from src.core.text_utils import standard_key

    conn = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    conn.row_factory = sqlite3.Row      # ★ 生产 search_with_details 依赖它返回带属性的对象
    he._conn = lambda: conn          # 生产函数跑在只读连接上
    print(f"[D1] 库 = {DB}（mode=ro）", flush=True)

    items = json.loads(ITEMS.read_text(encoding="utf-8"))
    if args.limit:
        items = items[:args.limit]
    print(f"[D1] 真实考题 = {len(items)} 条（文件级）", flush=True)

    # 文件级 gold：standard_no → 该文件在库里的 doc_id 集合
    docs_of = {}
    for did, no in conn.execute("SELECT doc_id, standard_no FROM doc_meta"):
        docs_of.setdefault(no, set()).add(did)
    # 条文级 gold：把 (standard_no, 条号) 解析成 clause_revision_id
    std_of_key = {}
    for no, in conn.execute("SELECT standard_no FROM doc_meta"):
        std_of_key[standard_key(no)] = no

    per = []
    t0 = time.perf_counter()
    for n, it in enumerate(items, 1):
        q = it["q"]
        gold_docs = set()
        for no in it["docs"]:
            gold_docs |= docs_of.get(no, set())
        if not gold_docs:
            continue
        # 条文级 gold（仅有唯一条号时）
        gold_cr = None
        cls = it.get("clauses") or []
        if len(cls) == 1:
            for no in it["docs"]:
                r = conn.execute(
                    "SELECT cr.clause_revision_id FROM clause_revision cr"
                    " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
                    " WHERE dm.standard_no=? AND cr.clause_number=?", (no, cls[0])).fetchone()
                if r:
                    gold_cr = r[0]
                    break
        try:
            out = search_with_details(q, top_k=args.depth, rerank=False,
                                      channels=["exact", "fts", "vec", "modality"])
            res = out.get("results") or []
        except Exception as e:  # noqa: BLE001
            per.append({"i": n, "err": f"{type(e).__name__}: {e}"[:120], "q": q[:60]})
            continue
        ids = [r["clause_revision_id"] if isinstance(r, dict) else r.clause_revision_id for r in res]
        # 把返回的条文映射到 doc
        dmap = {}
        for cid in ids:
            row = conn.execute("SELECT doc_id FROM clause_revision WHERE clause_revision_id=?", (cid,)).fetchone()
            if row:
                dmap[cid] = row[0]
        def hit_doc(k: int) -> bool:
            return any(dmap.get(c) in gold_docs for c in ids[:k])
        def hit_cr(k: int) -> bool | None:
            return None if gold_cr is None else (gold_cr in ids[:k])
        per.append({"i": n, "src": it.get("src"), "q": q[:80],
                    "gold_docs": sorted(it["docs"]), "gold_clause": cls[0] if len(cls) == 1 else None,
                    "n_ret": len(ids),
                    "doc@8": hit_doc(8), "doc@20": hit_doc(20), "doc@100": hit_doc(100),
                    "cr@8": hit_cr(8), "cr@20": hit_cr(20), "cr@100": hit_cr(100)})
        if n % 50 == 0 or n == len(items):
            print(f"  [{n}/{len(items)}] {time.perf_counter()-t0:.0f}s", flush=True)

    good = [r for r in per if "err" not in r]
    crs = [r for r in good if r.get("cr@8") is not None]
    agg = {
        "n_items": len(items), "n_ok": len(good), "n_err": len(per) - len(good),
        "file_level": {f"@{k}": round(sum(1 for r in good if r[f"doc@{k}"]) / max(1, len(good)) * 100, 2)
                       for k in (8, 20, 100)},
        "clause_level": {f"@{k}": round(sum(1 for r in crs if r[f"cr@{k}"]) / max(1, len(crs)) * 100, 2)
                         for k in (8, 20, 100)},
        "n_clause_level": len(crs), "depth": args.depth,
    }
    print("\n[D1] ==== 真实提问召回 ====")
    print(f"  考题 {agg['n_items']} 条｜成功 {agg['n_ok']}")
    print(f"  ★ 文件级（{agg['n_ok']} 条）：" + "  ".join(f"{k}={v}%" for k, v in agg["file_level"].items()))
    print(f"  ★ 条文级（{agg['n_clause_level']} 条）：" + "  ".join(f"{k}={v}%" for k, v in agg["clause_level"].items()))
    OUT.write_text(json.dumps({"agg": agg, "per_query": per}, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_Q.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in per), encoding="utf-8")
    print(f"\n[D1] 已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
