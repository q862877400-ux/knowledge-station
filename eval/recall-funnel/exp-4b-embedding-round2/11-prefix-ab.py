"""E4 第二轮 · B 臂：**查询侧指令前缀 A/B**（唯一变量 = 查询串上有没有 Qwen3 官方 instruct 前缀）。

第一轮（`../exp-4-embedding-shadow/`）把"查询侧不动"解释成"两臂都不加指令前缀"，
并把 Qwen3 官方推荐的 `instruct: …\\nquery: …` **留作第二刀**（README §六 明写"未测，别当已测"）。
本脚本就是那一刀。

**唯一变量**：送进**嵌入模型**的查询串前缀。条文侧**一字不动**、两臂都 KNN 同一张
`clause_vec_qwen`（第一轮算好的 512 维影子表）。
 · 无前缀臂：`{query}`
 · 前缀臂：  `Instruct: Given a web search query, retrieve relevant passages that answer the query\\nQuery: {query}`

⚠ **前缀只进嵌入，不进 FTS/exact/modality** —— 它是模型指令，不是检索文本。
   本脚本把前缀变量**只**传给 `qwen_vec()`；其余五路的 `q` 是原始串（下面 `fixed_five()` 里可见）。

**仪器对照（硬性）**：无前缀臂必须**同跑内复现**第一轮的 `ctx` 臂逐条 `rank@1000`
（`../exp-4-embedding-shadow/ab-per-query.jsonl`）。对不上 ⇒ 先查仪器，**不许**把它读成"前缀有效"。

只读：真库不碰；`exp.db` 只读（`mode=ro`）；不写任何向量。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4b-embedding-round2\\11-prefix-ab.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
R1 = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow"
EXP = R1 / "exp.db"
OUT = HERE / "prefix-ab-result.json"
OUT_PER = HERE / "prefix-ab-per-query.jsonl"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 512
K = 1000
#: Qwen3-Embedding 官方检索指令（英文默认），**逐字照抄**；自造中文版即第二个变量 ⇒ 不做。
INSTRUCT = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


def main() -> int:
    import funnel as F
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    from src.core.retrieval import embedder
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    n_q = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    print(f"[e4b] clause_vec_qwen={n_q}（应 521978）", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()

    def qwen_vec(text: str):
        enc = tok([text], padding=True, truncation=True, max_length=512,
                  return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model(**enc)
        v = Fn.normalize(out.last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
        return v[0].float().cpu().numpy().tolist()

    def knn(qv, k: int):
        return [r[0] for r in conn.execute(
            "SELECT clause_revision_id FROM clause_vec_qwen"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), k))]

    def fixed_five(q: str, mf):
        """五路**只用原始串**（前缀是模型指令，绝不进这里）。"""
        return F.channel_exact(conn, q), F.channel_fts(conn, q, K), F.channel_fts(conn, q, 20), \
            F.channel_modality(conn, mf)

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}
    r1 = {json.loads(l)["i"]: json.loads(l)
          for l in (R1 / "ab-per-query.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

    rows = []
    t0 = time.perf_counter()
    for n, it in enumerate(v2, 1):
        q = it["query"]
        gold = it["v2"]["gold_cr_id"]
        exact, fts1000, fts20, modality = fixed_five(q, extract_modality_from_query(q))
        vecs = {"noprefix": knn(qwen_vec(q), K),
                "prefix": knn(qwen_vec(INSTRUCT + q), K)}
        rec = {"i": it["i"],
               "headline": bool(it["v2"]["bucket"] == "keep"
                                and not ({"gold_multi_def", "gold_dup_text"} & set(it["v2"]["flags"]))),
               "kind": it["kind"], "tier": v3[it["i"]]["v3"]["req_tier"]}
        for arm, vec in vecs.items():
            a = {"vec_n": len(vec)}
            for d in (20, 100, 1000):
                union_d = set(exact[:d]) | set(fts1000[:d]) | set(modality[:d]) | set(vec[:d])
                a[f"rank@{d}"] = F.rank_of(gold, vec[:d])
                a[f"union_same@{d}"] = gold in union_d
                a[f"fts@{d}"] = gold in set(fts1000[:d])
            a["union_prod"] = gold in (set(exact) | set(fts20) | set(modality) | set(vec[:20]))
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[e4b] {n}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def rate(sub, arm, key):
        return round(sum(1 for r in sub if r[arm][key]) / len(sub), 4) if sub else None

    def blk(sub):
        s = {"n": len(sub), "n_clusters": len({v3[r["i"]]["v2"]["gold_cr_id"] for r in sub})}
        for arm in ("noprefix", "prefix"):
            s[arm] = {k: rate(sub, arm, k) for k in
                      ("rank@20", "rank@100", "rank@1000", "union_same@20", "union_same@100",
                       "union_same@1000", "union_prod", "fts@1000")}
        s["delta_pp"] = {k: round((s["prefix"][k] - s["noprefix"][k]) * 100, 2) for k in s["noprefix"]}
        s["flip_rank@1000"] = {
            "in": sum(1 for r in sub if not r["noprefix"]["rank@1000"] and r["prefix"]["rank@1000"]),
            "out": sum(1 for r in sub if r["noprefix"]["rank@1000"] and not r["prefix"]["rank@1000"]),
        }
        return s

    head = [r for r in rows if r["headline"]]
    summary = {"all_171": blk(rows), "headline_120": blk(head)}

    # ── 仪器对照 1：无前缀臂逐条复现第一轮的 ctx 臂 ──
    mism = [r["i"] for r in rows
            if r["i"] in r1 and r["noprefix"]["rank@1000"] != r1[r["i"]]["ctx"]["rank@1000"]]
    # ── 仪器对照 2：FTS 两臂必须完全相同（查询串没变）──
    fts_mism = sum(1 for r in rows if r["noprefix"]["fts@1000"] != r["prefix"]["fts@1000"])

    result = {
        "experiment": "E4 第二轮 · B 臂：查询侧指令前缀 A/B（Qwen3-Embedding-0.6B, 512d）",
        "single_variable": "查询串上是否加 Qwen3 官方 instruct 前缀；条文侧一字不动",
        "instruct_string": INSTRUCT + "{query}",
        "prefix_scope": "前缀**只**进 qwen_vec()；FTS/exact/modality 用原始串（见脚本 fixed_five）",
        "primary_endpoint": "Vector @1000（主结果 120 条口径）",
        "summary": summary,
        "instrument_control": {
            "round1_selfcheck_mismatch_items": len(mism),
            "round1_selfcheck_mismatch_i": mism[:20],
            "meaning_1": "无前缀臂必须逐条复现第一轮 ctx 臂的 rank@1000；非 0 ⇒ 先查仪器，"
                         "**不许**把它读成『前缀有效』",
            "fts_mismatch_items": fts_mism,
            "meaning_2": "FTS 两臂必须完全相同（前缀不进 FTS）；非 0 ⇒ 前缀泄漏了",
        },
        "baseline_selfcheck": {"round1_headline_vec@1000": 0.6833, "round1_all_vec@1000": 0.6667},
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_PER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}\n已写 {OUT_PER}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
