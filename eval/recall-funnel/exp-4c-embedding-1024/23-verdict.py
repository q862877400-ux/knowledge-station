"""E4c · 步骤 4：判定 —— **按 `stop-loss.json` 里跑前写死的阈值机械算**，不靠看着数字感觉。

输入：`stop-loss.json`（阈值）/ `ab-1024-result.json`（两臂）/ `ab-1024-cluster-ci.json`（簇级 CI）
输出：`verdict.json`

⚠ 阈值**只**从冻结文件 `stop-loss.json` 的判据键文本里抽边界（脚本里**不另写一份数字**，
抽不到即抛错 —— 防两处漂移；这是 E4b 复核 F1 的教训）。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4c-embedding-1024\\23-verdict.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "verdict.json"


def _nums(text: str) -> list[float]:
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def main() -> int:
    sl = json.loads((HERE / "stop-loss.json").read_text(encoding="utf-8"))
    ab = json.loads((HERE / "ab-1024-result.json").read_text(encoding="utf-8"))
    ci = json.loads((HERE / "ab-1024-cluster-ci.json").read_text(encoding="utf-8"))

    rule = sl["decision_rule"]

    def pick(prefix: str) -> dict:
        for k, v in rule.items():
            if k.strip().startswith(prefix):
                return v
        raise SystemExit(f"[23-verdict] stop-loss.json 判据里找不到以 {prefix!r} 开头的档：{list(rule)}")

    abandon = pick("放弃升维")
    gray = pick("灰区")
    advance = pick("升维有可分辨收益")
    abandon_lt = _nums(abandon["net_gain_pp"])[0]          # `< 4` → 4
    gray_lo, gray_hi = _nums(gray["net_gain_pp"])           # `4 ~ 8` → [4, 8]
    advance_ge = _nums(advance["net_gain_pp"])[0]           # `>= 8 …` → 8
    if not (abandon_lt == gray_lo and gray_hi == advance_ge):
        raise SystemExit(f"[23-verdict] stop-loss.json 三档边界不自洽："
                         f"放弃<{abandon_lt} / 灰区{gray_lo}~{gray_hi} / 收益>={advance_ge}")

    h = ab["summary"]["headline_120"]
    a = ab["summary"]["all_171"]
    delta_head = h["delta_pp"]["rank@1000"]
    delta_all = a["delta_pp"]["rank@1000"]
    ci_head = ci["headline_120"]
    ci_lo = ci_head["ci95_pp"][0]

    if delta_head < abandon_lt:
        bucket = "放弃升维（低于半条分辨率线）"
    elif delta_head < advance_ge:
        bucket = "灰区：有正向迹象但低于分辨率线 ⇒ 记录，不推进"
    elif ci_lo > 0:
        bucket = "升维有可分辨收益 ⇒ 进生产评估"
    else:
        bucket = "达到分辨率线但簇级 CI 下界 <= 0 ⇒ 不能据此推进"

    ic = ab["instrument_control"]
    set_ex = ic["vec_set_bidirectional_except"]
    instruments_ok = (ic["round1_selfcheck_mismatch_items"] == 0
                      and ic["fts_mismatch_items"] == 0
                      and set_ex["only_512"] == 0 and set_ex["only_1024"] == 0)

    cost = ab["cost_knn_scan_ms"]
    ratio = round(cost["d1024"]["p50"] / cost["d512"]["p50"], 3) if cost["d512"]["p50"] else None

    verdict = {
        "experiment": "E4c：Qwen3-Embedding-0.6B 升维（512 → 1024 维，同模型、无前缀）",
        "stop_loss_sha256_note": "阈值取自 stop-loss.json（跑前落盘，哈希见 stop-loss-freeze.txt）",
        "thresholds_parsed_from_stop_loss": {
            "abandon_lt_pp": abandon_lt, "gray_pp": [gray_lo, gray_hi], "advance_ge_pp": advance_ge},
        "primary_endpoint": "Vector @1000（主结果 120 条口径）",
        "result": {
            "headline120_d512": h["d512"]["rank@1000"],
            "headline120_d1024": h["d1024"]["rank@1000"],
            "headline120_delta_pp": delta_head,
            "all171_d512": a["d512"]["rank@1000"],
            "all171_d1024": a["d1024"]["rank@1000"],
            "all171_delta_pp": delta_all,
            "flip_headline": h["flip_rank@1000"],
            "flip_all": a["flip_rank@1000"],
            "cluster_ci_headline": ci_head,
            "cluster_ci_all": ci["all_171"],
            "secondary_deltas_headline_pp": {
                k: h["delta_pp"][k] for k in ("rank@20", "rank@100", "rank@1000",
                                              "union_same@20", "union_same@100",
                                              "union_same@1000", "union_prod")},
        },
        "cost": {
            "knn_scan_ms_d512_p50": cost["d512"]["p50"],
            "knn_scan_ms_d1024_p50": cost["d1024"]["p50"],
            "ratio_d1024_over_d512": ratio,
            "corpus_rows": cost["corpus_rows"],
            "meaning": "同一 521,978 行语料 KNN @1000 实测延迟 ⇒ 升维的代价（向量体积 ×2）",
        },
        "decision": bucket,
        "threshold_rule": rule,
        "instrument_controls": {
            "round1_selfcheck_mismatch_items": ic["round1_selfcheck_mismatch_items"],
            "fts_mismatch_items": ic["fts_mismatch_items"],
            "vec_set_bidirectional_except": set_ex,
            "passed": instruments_ok,
            "meaning": "任一非 0 ⇒ 先查仪器；**不许**把读数读成『升维有效/无效』",
        },
        "what_this_does_not_answer": [
            "未换模型（BGE-M3 未做）",
            "未加查询指令前缀（那是 exp-4b 的变量；本轮两臂都不加）",
            "语料冻结在 exp-4 副本的 521,978 条（不是真库当前 663,634 条）",
            "未在法规语料上量副作用；未接生产链",
        ],
    }
    OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0 if instruments_ok else 2


if __name__ == "__main__":
    sys.exit(main())
