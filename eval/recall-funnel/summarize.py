"""漏斗结果汇总：把 `funnel-per-query.jsonl` 折成一张能直接看的表。

**三张表 + 一份分诊**（都分"全部 171 条"与"主结果 120 条"两种口径）：
 1. 每一路自己把 gold 召回到第几名（B/C 的前 20 = 生产写死的上限；前 100/前 1000 = 探针深读）；
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

#: FR-005 的四个难度子集（互斥分区，优先级见 `build-v2.py` 的 `main()`；标签由构建器算好，
#: 本脚本**只读不重算** —— 免得同一件事出现第二套口径）。
SUBSETS = ("短条款", "字面零重合", "带标准号", "普通")


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
                # FR-005 子集标签 + FR-006 库外标记（2026-10-09 T016/T017）
                r["subset_label"] = (meta.get("subset") or {}).get("label")
                r["subset_markers"] = meta.get("subset") or {}
                r["answer_out_of_corpus"] = bool(meta.get("answer_out_of_corpus"))

    # FR-006：**答案不在库内的题必须能被排除**（本批 0 条 —— 机制在，换考卷时才用得上）。
    # ⚠ 排除发生在**所有表之前**：分母是"库内题"，否则库外题会把召回率算低。
    ooc = [r for r in rows if r.get("answer_out_of_corpus")]
    rows = [r for r in rows if not r.get("answer_out_of_corpus")]

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
    # FR-005/FR-009：按四个难度子集分别给命中率（每个数都带分母 = `tables()` 的 `n`）。
    # 标签由 `build-v2.py` 算好，这里只分组 —— 免得同一件事出现第二套口径。
    by_subset = {k: tables([r for r in rows if r.get("subset_label") == k]) for k in SUBSETS}
    by_subset_headline = {k: tables([r for r in headline if r.get("subset_label") == k])
                          for k in SUBSETS}

    # ── 子集口径的敏感性（2026-10-09 T016）─────────────────────────────────
    # "字面零重合"在本仓有**两个都站得住的口径**（字符级 53% 那档 / 词级 77% 那档）。
    # 本批把**字符级**定为标签口径（与 spec.md 边界条同源），词级数并列在此供对照。
    # ⚠ 两个数**不是同一件事**，见 eval/recall-funnel/README.md §五。
    lex_path = HERE / "lexical-overlap.json"
    lex_zero_token = None
    if lex_path.exists():
        per = json.loads(lex_path.read_text(encoding="utf-8")).get("per_query") or []
        ids = {r["i"] for r in rows}
        lex_zero_token = sum(1 for p in per if p["i"] in ids and p.get("zero_overlap"))

    def _part_alt(rs: list[dict]) -> dict:
        """换个优先级（带标准号 → 字面零重合 → 短条款）时各桶会变成多少；从标记重算，不改标签。"""
        out = {k: 0 for k in SUBSETS}
        for r in rs:
            m = r.get("subset_markers") or {}
            if m.get("has_standard_no_verified"):
                out["带标准号"] += 1
            elif m.get("zero_overlap_char"):
                out["字面零重合"] += 1
            elif m.get("short_clause"):
                out["短条款"] += 1
            else:
                out["普通"] += 1
        return out

    checks = [r for r in rows if r.get("replica_check") != "ok"]
    summary = {
        "meta": {
            "source": str(PER),
            "n_per_query": len(rows),
            "n_excluded_answer_out_of_corpus": len(ooc),
            "channel_definition": "六路 = A 条款号精确 / B FTS5 / C 向量 / D 模态 / E 法理要素 / F 行为客体",
            "subset_definition": "四个难度子集 = 短条款 / 字面零重合 / 带标准号 / 普通（FR-005）；"
                                 "标签在 build-v2.py 里算，口径与出处见 eval/recall-funnel/README.md §五。"
                                 "⚠ `by_subset` 四个桶是**互斥分区**（优先级 短条款→字面零重合→带标准号→普通）。",
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
        "by_subset": by_subset,
        "by_subset_headline": by_subset_headline,
        "by_subset_sensitivity": {
            "zero_overlap_char_level": sum(1 for r in rows
                                           if (r.get("subset_markers") or {}).get("zero_overlap_char")),
            "zero_overlap_token_level": lex_zero_token,
            "partition_alt_priority": _part_alt(rows),
            "note": "char_level = 提问与 gold 条文无 ≥2 字公共子串（与 53.0% 那档同口径，**本批标签口径**）；"
                    "token_level = 与通道 B 同款分词下无共同词（77.2% 那档）。"
                    "partition_alt_priority = 若把优先级换成「带标准号→字面零重合→短条款」，四个桶各多少条。",
        },
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
