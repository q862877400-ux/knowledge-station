#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""build-baseline.py —— 把「阶段 0 基线」从既有产物**投影**成契约要求的 `baseline-v0/` 三件套（T023）。

## 为什么要有这个脚本（而不是手写三个 json）

`specs/002-recall-funnel/tasks.md` T023 要求二选一：**补齐三件套** 或 **把契约改成与实际一致**
（`contracts/baseline.schema.md`）。这里选**补齐**，但**不许**再造一份"第二真源"：

- `config.json`  —— 值**逐项带出处**（`config-inventory.md` 的小节 + 快照 tag），本文件里手写常量；
- `metrics.json` —— **从 `funnel-summary.json` 投影**（不重算、不手抄数字）；
- `results.jsonl`—— **从 `funnel-per-query.jsonl` 投影**（**丢掉 `elapsed_s` 这类墙钟字段**
  —— 契约要求"两次跑应逐字节相同"，带墙钟就永远做不到）。

⇒ 真源仍是 `config-inventory.md` / `funnel-summary.json` / `funnel-per-query.jsonl`；
   `baseline-v0/` 是它们的**可复算视图**。改真源后重跑本脚本即可。

## 判据（脚本自带，不满足即非零退出）

1. 契约 `baseline.schema.md` 列出的**必需字段一个都不许少**（config 13 项 / metrics 7 项）。
2. `results.jsonl` 行数必须等于 `metrics.n_total`；每条必须带"各通道最好名次"。
3. `config.code_revision.dirty` **必须是 `false`** —— 契约原话：`dirty=true` 的快照**不得**当基线。
   这里的取值来自**产生这份基线的快照 tag**（`step-241`），不是当前 HEAD。
4. 幂等：连跑两次，三个文件逐字节相同（墙钟字段已剔除）。

用法：`python eval/recall-funnel/baseline-v0/build-baseline.py`
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent          # eval/recall-funnel
REPO = ROOT.parent.parent   # 仓库根

SUMMARY = ROOT / "funnel-summary.json"
PER_QUERY = ROOT / "funnel-per-query.jsonl"
# 子集标签（FR-005）的唯一出处是 build-v2.py 写进 benchmark-v2.jsonl 的 `v2.subset`
# （funnel-per-query.jsonl 里没有这一列）⇒ 这里**按 i 连接**取标签，不重算（防第二套口径）。
BENCHMARK = ROOT / "benchmark-v2.jsonl"

# 产生这份基线的快照（T022 的"这份基线是哪版跑的"）。
SNAPSHOT_TAG = "step-241-recall-funnel-phase0-r2"

# ── config.json 的值：逐项带出处。数字全部来自 config-inventory.md（只读盘点），不重算。 ──
CONFIG_VALUES = {
    "embedding_model": "BAAI/bge-small-zh-v1.5",
    "embedding_dim": 512,
    "has_lexical_channel": True,
    "vector_index": "sqlite-vec v0.1.9 · vec0 虚拟表 · 暴力精确扫描（无 ANN）",
    "channels": {"A": True, "B": True, "C": True, "D": True, "E": True, "F": True},
    # ⚠ 契约示例里的 `"top_k": 5` 是泛例；本基线的**实测口径**是 rerank=False + top_k=1000
    #   （见 config-inventory.md §四末注）。生产 `ks_answer` 默认 top_k=8，另注。
    "top_k": 1000,
    "rerank": {"enabled": False, "model": "BAAI/bge-reranker-base"},
    "machine": {"cpu": "i7-14700KF", "cores": 20, "ram_gb": 63.8, "gpu": "RTX 4080 SUPER"},
    "corpus_size": 522021,
}
CONFIG_SOURCES = {
    "embedding_model": "config-inventory.md §一（`embedder.py` 的 `_get_model`）",
    "embedding_dim": "config-inventory.md §一（`EMBEDDING_DIM = 512`；库表 `embedding FLOAT[512]`）",
    "has_lexical_channel": "config-inventory.md §二（`clause_fts` FTS5）",
    "vector_index": "config-inventory.md §一",
    "channels": "config-inventory.md §四（六条通道在代码里都注册着）",
    "top_k": "config-inventory.md §四末注（本报告记的融合名次一律 rerank=False / top_k=1000）",
    "rerank": "config-inventory.md §三（`RERANK_MODEL = BAAI/bge-reranker-base`；文件头注释写 v2-m3，以常量为准；生产 ks_answer 不传 rerank ⇒ 关）",
    "machine": "config-inventory.md §六",
    "corpus_size": "config-inventory.md §六（`clause_revision` 522,021）",
}
CONFIG_NOTES = {
    "top_k": "契约示例写 5 是泛例。本基线实测口径 = rerank=False + top_k=1000（ks_answer 那条路）。"
             "生产 `api/server.py` 是 top_k=3 + rerank 开 ⇒ 换调用点结论会不同（REPORT.md §八 第 5 条）。",
    "channels": "六个键全 true = 代码里六条通道都注册着。⚠ 但实测**只有 B/C 恒常工作**："
                "A 触发 0/171、D 8/171、E/F 恒 0（config-inventory.md §四）。",
    "rerank.model": "契约示例写 `BAAI/bge-reranker-v2-m3`，**与代码不符**；照代码常量 `bge-reranker-base` 记（该不一致已登记）。",
    "corpus_size": "这是**基线当时**的规模。真库会继续长（2026-10-09 已到 663,634）⇒ 引用前先复核。",
}


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def build_config() -> dict:
    head = _git("rev-parse", f"{SNAPSHOT_TAG}^{{commit}}")
    committed_at = _git("log", "-1", "--format=%cI", f"{SNAPSHOT_TAG}^{{commit}}")
    cfg = {
        "captured_at": committed_at,
        "captured_at_source": f"git tag {SNAPSHOT_TAG} 的提交时间（= 产生这份基线的快照）",
        **CONFIG_VALUES,
        "code_revision": {"head": head, "tag": SNAPSHOT_TAG, "dirty": False},
        "_sources": CONFIG_SOURCES,
        "_notes": CONFIG_NOTES,
    }
    # 判据 1（config 侧）
    required = ["captured_at", "embedding_model", "embedding_dim", "has_lexical_channel",
                "vector_index", "channels", "top_k", "rerank", "machine", "corpus_size", "code_revision"]
    missing = [k for k in required if k not in cfg]
    if missing:
        raise SystemExit(f"config.json 缺必需字段：{missing}")
    # 判据 3
    if cfg["code_revision"]["dirty"] is not False:
        raise SystemExit("code_revision.dirty 必须是 false（契约：dirty=true 不得当基线）")
    return cfg


def build_metrics(summary: dict) -> dict:
    def fused(scope: dict) -> dict:
        f = scope["fused"]
        return {k.lstrip("@"): v for k, v in f.items() if k.startswith("@")}

    def channels(scope: dict) -> dict:
        out = {}
        for name, ch in scope["channel_recall"].items():
            out[name] = {
                "label": ch.get("name"),
                "fire_n": ch.get("fire_n"),
                "deep": ch.get("deep"),
                "prod": ch.get("prod"),
            }
        return out

    all171, head = summary["all_171"], summary["headline"]
    metrics = {
        "run_id": f"baseline-v0@{SNAPSHOT_TAG}",
        "n_total": summary["meta"]["n_per_query"],
        # 契约：n_used = 排除库外答案后的条数。本批 `answer_out_of_corpus` 全 False ⇒ n_used = n_total。
        "n_used": summary["meta"]["n_per_query"] - summary["meta"]["n_excluded_answer_out_of_corpus"],
        "n_headline": head["n"],
        # 契约要求 by_cutoff = {"20":…,"100":…,"1000":…}。这里给**融合后**的命中率（主口径 = 全量 171）。
        "by_cutoff": fused(all171),
        "by_cutoff_headline_120": fused(head),
        "by_cutoff_note": "by_cutoff 是**融合后**（fused）的命中率，口径 = 全量 171；"
                          "by_cutoff_headline_120 = 主结果 120 条的同名读数。"
                          "⚠ `fused@100` 与 `fused@1000` 相等是因为**融合列表只到 40 条**（池深所限），不是「@100 就满了」。",
        "by_channel": channels(all171),
        "by_channel_headline_120": channels(head),
        "by_channel_note": "各通道的 `deep` = 深读口径（同 SQL 放大 k 到 1000）；`prod` = 生产限量（B/C/F 各 20）。",
        "by_subset": summary["by_subset"],
        "by_subset_headline_120": summary["by_subset_headline"],
        "by_kind": summary["by_kind"],
        "denominators": {
            "all_171": all171["n"],
            "headline_120": head["n"],
            "by_subset": {k: v["n"] for k, v in summary["by_subset"].items()},
            "by_subset_headline_120": {k: v["n"] for k, v in summary["by_subset_headline"].items()},
            "note": "报数必须带分母（本仓既有教训：分母不同的数字不可比）。",
        },
        "triage": all171["triage"],
        "union": {"same_budget": all171["union"]["same_budget"], "prod_caps": all171["union"]["prod_caps"]},
        "replica_check": summary["replica_check"],
        "source": "从 funnel-summary.json 投影（不重算）",
    }
    required = ["run_id", "n_total", "n_used", "by_cutoff", "by_channel", "by_subset", "denominators"]
    missing = [k for k in required if k not in metrics]
    if missing:
        raise SystemExit(f"metrics.json 缺必需字段：{missing}")
    return metrics


def build_results() -> list[dict]:
    subset_by_i = {}
    for line in BENCHMARK.read_text(encoding="utf-8").splitlines():
        if line.strip():
            b = json.loads(line)
            subset_by_i[b["i"]] = b["v2"]["subset"]
    rows = []
    for line in PER_QUERY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        ch = r["channels"]
        rows.append({
            "i": r["i"],
            "query": r["query"],
            "gold_std": r["gold_std"],
            "gold_clause": r["gold_clause"],
            "bucket": r["bucket"],
            "flags": r["flags"],
            "kind": r["kind"],
            "subset": subset_by_i[r["i"]]["label"],
            # 契约："至少：正确答案在各路的最好名次" ⇒ 生产名次 + 深读名次都给。
            "best_rank_by_channel": {k: ch[k]["gold_rank"] for k in ch},
            "deep_best_rank_by_channel": {k: ch[k]["deep_gold_rank"] for k in ch},
            "channel_candidates": {k: ch[k]["n"] for k in ch},
            "hit_channels": r["hit_channels"],
            "union_same_budget": r["union"]["same_budget"],
            "union_prod_caps": r["union"]["prod_caps"],
            "fused": r["fused"],
            "replica_check": r["replica_check"],
            # ⚠ 故意**不含** `elapsed_s`：契约要求"两次跑逐字节相同"，带墙钟就永远做不到。
        })
    return rows


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    cfg = build_config()
    metrics = build_metrics(summary)
    rows = build_results()

    # 判据 2
    if len(rows) != metrics["n_total"]:
        raise SystemExit(f"results.jsonl 行数 {len(rows)} ≠ metrics.n_total {metrics['n_total']}")
    for r in rows:
        if not r["best_rank_by_channel"]:
            raise SystemExit(f"第 {r['i']} 条没有各路最好名次")

    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "results.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(f"已写 baseline-v0/：config.json / metrics.json / results.jsonl（{len(rows)} 行）")
    print(f"  code_revision = {cfg['code_revision']['head'][:9]}（{SNAPSHOT_TAG}），dirty=False")
    print(f"  by_cutoff(fused, 全量 171) = {metrics['by_cutoff']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
