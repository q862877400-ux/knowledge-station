"""漏斗结果汇总：把 `funnel-per-query.jsonl` 折成一张能直接看的表。

**三张表 + 一份分诊**（都分"全部 171 条"与"主结果 120 条"两种口径）：
 1. 每一路自己把 gold 召回到第几名（前 20 = 生产写死的上限；前 100/前 1000 = 探针深读）；
 2. 六路**并集**的 recall@20/@100/@1000 —— **同预算口径**（每路取前 d 条）
    与**生产上限口径**（A/D/E 不限量、B/C/F 各 20）**两个都出，名字分开**；
 3. 六路**融合后**（生产实际排序）的第几名，以及 rerank 之后还进不进前 8；
 4. **分诊**：每条到底丢在哪一步（前 1000 名里没有 / 被截断在 20 名之外 / 融合丢 / 没进用户看的 8 条）。

⚠ 并集的两个口径**不许混用**（2026-10-06 独立复核打回：原版把 A/D/E 也按 d 截断却仍叫"生产口径"，
于是同一份数据在报告里出现 103 与 104 两个"六路全未命中"）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\summarize.py
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PER = HERE / "funnel-per-query.jsonl"
OUT = HERE / "funnel-summary.json"

CHANNELS = ("exact", "fts", "vec", "modality", "legal_element", "behavior_scope")
CN_NAME = {"exact": "A 条款号精确", "fts": "B 全文 FTS5", "vec": "C 向量",
           "modality": "D 模态", "legal_element": "E 法理要素", "behavior_scope": "F 行为客体"}
DEPTHS = (20, 100, 1000)


def _pct(hit: int, n: int) -> float | None:
    return round(hit / n, 4) if n else None


def main() -> int:
    rows = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r["i"])

    # ⚠ 桶与标记以 **benchmark-v2.jsonl 为准**，不取逐条记录里那份快照 ——
    #   漏斗是边跑边写的，跑的过程中若重跑过 build-v2，逐条记录里的标记会过期。
    v2_path = HERE / "benchmark-v2.jsonl"
    if v2_path.exists():
        v2 = {json.loads(l)["i"]: json.loads(l) for l in
              v2_path.read_text(encoding="utf-8").splitlines() if l.strip()}
        for r in rows:
            meta = (v2.get(r["i"]) or {}).get("v2")
            if meta:
                r["bucket"] = meta["bucket"]
                r["flags"] = meta["flags"]

    def tables(subset: list[dict]) -> dict:
        n = len(subset)
        chan = {}
        for c in CHANNELS:
            fired = [r for r in subset if r["channels"][c]["fires"]]
            chan[c] = {
                "name": CN_NAME[c],
                "fire_n": len(fired),
                "prod": {f"@{d}": _pct(sum(1 for r in subset
                                         if (r["channels"][c]["gold_rank"] or 10**9) <= d), n)
                         for d in DEPTHS},
                "prod_within_fired": {f"@{d}": _pct(sum(1 for r in fired
                                                      if (r["channels"][c]["gold_rank"] or 10**9) <= d),
                                                     len(fired)) for d in DEPTHS},
                "deep": {f"@{d}": _pct(sum(1 for r in subset
                                           if (r["channels"][c]["deep_gold_rank"] or 10**9) <= d), n)
                         for d in DEPTHS},
                "n_candidates_median": statistics.median(
                    [r["channels"][c]["n"] for r in subset]) if subset else None,
            }
        union = {
            "same_budget": {f"@{d}": _pct(sum(1 for r in subset
                                            if r["union"]["same_budget"][f"@{d}"]), n)
                            for d in DEPTHS},
            "prod_caps": {"hit": _pct(sum(1 for r in subset if r["union"]["prod_caps"]["hit"]), n),
                          "pool_median": statistics.median(
                              [r["union"]["prod_caps"]["pool"] for r in subset]) if subset else None},
        }
        fused = {f"@{d}": _pct(sum(1 for r in subset if r["fused"][f"hit@{d}"]), n) for d in DEPTHS}
        rer = [r for r in subset if r.get("fused_rerank8") and r["fused_rerank8"].get("hit") is not None]
        fused_rerank8 = _pct(sum(1 for r in rer if r["fused_rerank8"]["hit"]), len(rer))

        # 独家 / 共同命中（按深读 1000 口径）
        excl = Counter()
        co2 = 0
        allmiss = 0
        for r in subset:
            hc = r["hit_channels"]
            if not hc:
                allmiss += 1
            elif len(hc) == 1:
                excl[hc[0]] += 1
            else:
                co2 += 1

        # 分诊：丢在哪一步（口径 = 每路前 d 条的并集）
        triage = Counter()
        for r in subset:
            deep1000 = r["union"]["same_budget"]["@1000"]
            same20 = r["union"]["same_budget"]["@20"]
            fused20 = r["fused"]["hit@20"]
            rank8 = r["fused"]["gold_rank"] is not None and r["fused"]["gold_rank"] <= 8
            if not deep1000:
                triage["L1_六路深读1000都没召回"] += 1
            elif not same20:
                triage["L2_要读到20条以外才够得着"] += 1
            elif not fused20:
                triage["L3_并集里有_融合后掉了"] += 1
            elif not rank8:
                triage["L4_融合后在前20但没进用户看的8条"] += 1
            else:
                triage["L0_进得了用户看的8条"] += 1

        return {
            "n": n,
            "channel_recall": chan,
            "union": union,
            "fused": fused,
            "fused_rerank_top8": fused_rerank8,
            "contribution": {
                "exclusive_hits": {CN_NAME[c]: excl.get(c, 0) for c in CHANNELS},
                "co_hit_2plus": co2,
                "no_channel_hit": allmiss,
            },
            "triage": dict(triage),
            "fts_pool": {
                "n": len([r for r in subset if r.get("fts_pool") is not None]),
                "median": statistics.median([r["fts_pool"] for r in subset
                                             if r.get("fts_pool") is not None]) if any(
                    r.get("fts_pool") is not None for r in subset) else None,
                "max": max([r.get("fts_pool") or 0 for r in subset]) if subset else None,
            },
        }

    _EXCLUDE = {"gold_multi_def", "gold_dup_text"}
    headline = [r for r in rows if r["bucket"] == "keep" and not (_EXCLUDE & set(r["flags"]))]
    by_kind = {k: tables([r for r in rows if r["kind"] == k]) for k in ("定义", "要求")}
    by_kind_headline = {k: tables([r for r in headline if r["kind"] == k])
                        for k in ("定义", "要求")}

    checks = [r for r in rows if r.get("replica_check") != "ok"]
    summary = {
        "meta": {
            "source": str(PER),
            "n_per_query": len(rows),
            "channel_definition": "六路 = A 条款号精确 / B FTS5 / C 向量 / D 模态 / E 法理要素 / F 行为客体",
            "prod_caps": {"fts": 20, "vec": 20, "behavior_scope": 20, "exact": None,
                          "modality": None, "legal_element": None},
            "note": "same_budget = 每一路都只取前 d 条再取并集（报告主口径）；"
                    "prod_caps = 照 perform_hybrid_search 的真实限量（A/D/E 不限量、B/C/F 各 20）。"
                    "B/C 在 d>20 时用探针深读列表（同 SQL 只把 k 放大），不是生产行为",
        },
        "all_171": tables(rows),
        "headline": tables(headline),
        "by_kind": by_kind,
        "by_kind_headline": by_kind_headline,
        "replica_check": {
            "n_checked": len(rows), "n_mismatch": len(checks),
            "note": "本脚本的通道副本 vs 生产 perform_hybrid_search(单通道) 的逐条比对",
            "samples": checks[:5],
        },
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"all_171": summary["all_171"], "headline": summary["headline"],
                      "replica_check": summary["replica_check"]},
                     ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}（全部 {len(rows)} 条 / 主结果 {len(headline)} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
