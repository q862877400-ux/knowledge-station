"""E1 复核补算 ②：**拆分诊断** —— 金标所在文档被找到了吗？找到后金标在文档内排第几？

外部评估 2026-10-06 点名要做的第一件"近乎免费"的事。它比"最近邻同篇率"更直接：
 · **文档级命中**：金标所在的那篇文档，有没有出现在前 N 条结果里？
 · **文档内名次**：在文档被命中的前提下，金标条文在该文档的候选里排第几？
若实验臂是「**文档级命中上升、文档内名次变差**」⇒「前缀让向量被文档身份主导」这个解释成立。

（它同时提醒：这仍是**观测**，不是干预。）

两臂都用**已存在的向量**，只重跑精确 KNN，不改任何东西。口径：全量 171 与主结果 120 都给。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\12-split-diagnostic.py
"""
from __future__ import annotations

import array
import json
import statistics as st
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
OUT = HERE / "split-diagnostic.json"
TOPK = 1000
DEPTHS = (20, 100, 1000)


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    db_conn = __import__("sqlite3").connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(db_conn)

    v2 = {json.loads(l)["i"]: json.loads(l)
          for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    ids = sorted(v2)
    doc_of = dict(db_conn.execute("SELECT clause_revision_id, doc_id FROM clause_revision"))

    def knn(table: str, qv, k: int):
        return [r[0] for r in db_conn.execute(
            f"SELECT clause_revision_id FROM {table}"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), k))]

    rows = []
    t0 = time.perf_counter()
    for n, i in enumerate(ids, 1):
        q = v2[i]["query"]
        gold_id = v2[i]["v2"]["gold_cr_id"]
        gold_doc = v2[i]["v2"]["gold_doc_id"]
        qv = embedder.embed_query(q)
        rec = {"i": i, "headline": bool(v2[i]["v2"]["bucket"] == "keep"
                                       and not ({"gold_multi_def", "gold_dup_text"} & set(v2[i]["v2"]["flags"])))}
        for arm, tbl in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            cand = knn(tbl, qv, TOPK)
            docs = [doc_of.get(c) for c in cand]
            a = {}
            for d in DEPTHS:
                a[f"doc_hit@{d}"] = gold_doc in docs[:d]
                a[f"gold_hit@{d}"] = gold_id in cand[:d]
            # 文档内名次：金标文档的候选里，金标排第几（1 = 该文档最佳）
            pos = [p for p, c in enumerate(cand, 1) if doc_of.get(c) == gold_doc]
            a["doc_present@1000"] = bool(pos)
            a["doc_best_rank"] = pos[0] if pos else None
            gp = next((p for p, c in enumerate(cand, 1) if c == gold_id), None)
            a["gold_rank"] = gp
            a["within_doc_pos"] = (pos.index(gp) + 1) if (gp and gp in pos) else None
            a["n_from_gold_doc_in_top1000"] = len(pos)
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[split] {n}/{len(ids)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def summarize(subset, arm):
        out = {"n": len(subset)}
        for d in DEPTHS:
            out[f"doc_hit@{d}"] = round(sum(1 for r in subset if r[arm][f"doc_hit@{d}"]) / len(subset), 4)
            out[f"gold_hit@{d}"] = round(sum(1 for r in subset if r[arm][f"gold_hit@{d}"]) / len(subset), 4)
        present = [r for r in subset if r[arm]["doc_present@1000"]]
        out["n_doc_present@1000"] = len(present)
        if present:
            out["doc_best_rank_median"] = st.median([r[arm]["doc_best_rank"] for r in present])
            wd = [r[arm]["within_doc_pos"] for r in present if r[arm]["within_doc_pos"]]
            out["within_doc_pos_median"] = st.median(wd) if wd else None
            out["within_doc_pos_mean"] = round(st.mean(wd), 2) if wd else None
            out["gold_in_top1000_given_doc_present"] = round(
                sum(1 for r in present if r[arm]["gold_rank"]) / len(present), 4)
        return out

    result = {"why": "外部评估点名要做的拆分诊断：文档级命中 vs 文档内名次",
              "k": TOPK, "observation_only": "这是观测，不是干预实验"}
    for name, pred in (("all_171", lambda r: True), ("headline_120", lambda r: r["headline"])):
        sub = [r for r in rows if pred(r)]
        b, c = summarize(sub, "base"), summarize(sub, "ctx")
        result[name] = {"base": b, "ctx": c, "delta": {
            k: (round(c[k] - b[k], 4) if isinstance(b.get(k), float) else None)
            for k in b if k in c and isinstance(b.get(k), (int, float))}}
    # 判读
    h = result["headline_120"]
    dh = h["delta"].get("doc_hit@20")
    wd_b, wd_c = h["base"].get("within_doc_pos_median"), h["ctx"].get("within_doc_pos_median")
    result["verdict"] = (
        "**前缀主导成立**：文档级命中上升、而文档内名次变差"
        if (dh is not None and dh > 0 and wd_b and wd_c and wd_c > wd_b) else
        "**前缀主导未获支持**：没有出现「文档级命中升、文档内名次降」的组合 —— 如实报，不圆")
    result["numbers_for_the_verdict"] = {
        "headline doc_hit@20 base→ctx": [h["base"]["doc_hit@20"], h["ctx"]["doc_hit@20"]],
        "headline within_doc_pos_median base→ctx": [wd_b, wd_c],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
