"""E4 第二轮 · 判定：**按 `stop-loss.json` 里跑前写死的阈值机械算**，不靠看着数字感觉。

输入：`stop-loss.json`（阈值）/ `latency.json`（A 臂）/ `prefix-ab-result.json`（B 臂）
输出：`verdict.json`（含每条判据的取值、阈值、落档、以及仪器对照是否通过）

⚠ 本脚本**只做分类**，不改任何读数；阈值**从冻结文件 `stop-loss.json` 的判据键文本里抽边界**
（脚本里不另写一份数字，防两处漂移 —— 抽不到就抛错，宁可炸也不静默用错阈值）。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4b-embedding-round2\\12-verdict.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "verdict.json"


def _num_of_key(key: str) -> float:
    """从判据键（如 `<= 100 ms` / `>= 10pt`）里抽出数字边界。"""
    m = re.search(r"\d+(?:\.\d+)?", key)
    if m is None:
        raise SystemExit(f"[12-verdict] 阈值键里没有数字，无法抽边界：{key!r}")
    return float(m.group())


def _boundary(rule: dict, prefix: str) -> float:
    """在一条 decision_rule 里找以 `prefix` 开头的档，抽它的数字边界。找不到即抛错。"""
    for k in rule:
        if k.strip().startswith(prefix):
            return _num_of_key(k)
    raise SystemExit(f"[12-verdict] stop-loss.json 的判据里找不到以 {prefix!r} 开头的档：{list(rule)}")


def main() -> int:
    sl = json.loads((HERE / "stop-loss.json").read_text(encoding="utf-8"))
    lat = json.loads((HERE / "latency.json").read_text(encoding="utf-8"))
    ab = json.loads((HERE / "prefix-ab-result.json").read_text(encoding="utf-8"))
    real_path = HERE / "latency-real-db-scan.json"
    real = json.loads(real_path.read_text(encoding="utf-8")) if real_path.exists() else None

    # ── 阈值：**只**从冻结的 stop-loss.json 的判据键文本里抽（不在脚本里另写一份） ──
    a_rule = sl["part_A_cost_and_latency"]["decision_rule"]
    gpu_ok_ms = _boundary(a_rule["单条查询延迟_warm_GPU"], "<=")   # `<= 100 ms`
    vram_ok_MiB = _boundary(a_rule["显存峰值"], "<=")               # `<= 4096 MiB`
    b_rule = sl["part_B_query_instruction_prefix"]["decision_rule"]
    b_lo = _boundary(b_rule, "<")    # `< 8pt`
    b_hi = _boundary(b_rule, ">=")   # `>= 10pt`

    # ── A 臂：成本/延迟/显存 ──
    # 参照物按冻结口径用"同跑内复测值"（10-latency.py 在**副本**上量的）；
    # 14-real-db-scan.py 另在**真库**上量了一次 —— 两个都报，不拿副本冒充生产。
    scan = lat["reference_knn_scan"]["median_ms"]
    gpu = lat["path_experiment_gpu_qwen3"]
    cpu = lat["path_incumbent_cpu_bge_small"]
    gpu_p50 = gpu["warm"]["p50_ms"]
    vram = gpu["peak_mem_reserved_MiB"]
    if gpu_p50 <= gpu_ok_ms:
        a_bucket = "可上线：相对现有扫描可忽略"
    elif gpu_p50 <= scan:
        a_bucket = "灰区：与现有扫描同量级"
    else:
        a_bucket = "成本翻倍以上 ⇒ 不能单独上线"
    a_vram = "与本地大模型共存无压力" if vram <= vram_ok_MiB else "与本地大模型抢显存 ⇒ 决策点"

    # ── B 臂：指令前缀 ──
    h = ab["summary"]["headline_120"]
    a = ab["summary"]["all_171"]
    delta_head = h["delta_pp"]["rank@1000"]
    delta_all = a["delta_pp"]["rank@1000"]
    if delta_head < b_lo:
        b_bucket = "不加前缀（这条路放弃）"
    elif delta_head < b_hi:
        b_bucket = "灰区：不能据此改生产"
    else:
        b_bucket = "前缀有可分辨收益 ⇒ 进生产评估"

    ic = ab["instrument_control"]
    instruments_ok = (ic["round1_selfcheck_mismatch_items"] == 0 and ic["fts_mismatch_items"] == 0)

    verdict = {
        "experiment": "E4 第二轮：成本/延迟/显存 + 查询侧指令前缀",
        "stop_loss_sha256_note": "阈值取自 stop-loss.json（跑前落盘，哈希见 stop-loss-freeze.txt）",
        "part_A_cost_latency": {
            "reference_knn_scan_ms": scan,
            "incumbent_cpu_warm_p50_ms": cpu["warm"]["p50_ms"],
            "qwen3_gpu_warm_p50_ms": gpu_p50,
            "qwen3_gpu_warm_p90_ms": gpu["warm"]["p90_ms"],
            "qwen3_gpu_cold_start_ms": gpu["cold_start_ms"],
            "qwen3_peak_vram_reserved_MiB": vram,
            "embed_share_of_vector_path_pct": round(gpu_p50 / scan * 100, 2),
            "decision": a_bucket,
            "vram_decision": a_vram,
            "extra_qwen3_on_cpu": lat.get("extra_qwen3_on_cpu", {}).get("warm", {}).get("p50_ms"),
            "extra_note": "附加抽样，不在冻结口径内",
            "reference_on_real_db": None if real is None else {
                "rows": real["real_db"]["rows"],
                "scan_median_ms": real["real_db"]["median_ms"],
                "embed_share_pct": round(gpu_p50 / real["real_db"]["median_ms"] * 100, 2),
                "note": "真库比第一轮的副本**多了 141,656 条**（663,634 vs 521,978）⇒ "
                        "生产上真正的扫描参照是这一个，不是副本那个",
            },
            "recorded_reference_606ms": None if real is None else real["recorded_reference"],
        },
        "part_B_instruction_prefix": {
            "primary_endpoint": "Vector @1000（主结果 120 条口径）",
            "headline120_noprefix": h["noprefix"]["rank@1000"],
            "headline120_prefix": h["prefix"]["rank@1000"],
            "headline120_delta_pp": delta_head,
            "all171_noprefix": a["noprefix"]["rank@1000"],
            "all171_prefix": a["prefix"]["rank@1000"],
            "all171_delta_pp": delta_all,
            "flip_headline": h["flip_rank@1000"],
            "flip_all": a["flip_rank@1000"],
            "decision": b_bucket,
            "threshold_rule": sl["part_B_query_instruction_prefix"]["decision_rule"],
            "cluster_ci": json.loads((HERE / "prefix-cluster-ci.json").read_text(encoding="utf-8"))
            if (HERE / "prefix-cluster-ci.json").exists() else None,
        },
        "instrument_controls": {
            "round1_selfcheck_mismatch_items": ic["round1_selfcheck_mismatch_items"],
            "fts_mismatch_items": ic["fts_mismatch_items"],
            "passed": instruments_ok,
            "meaning": "任一非 0 ⇒ 先查仪器；**不许**把 B 臂读数读成『前缀有效/无效』",
        },
        "what_this_does_not_answer": sl["honesty_boundary"],
    }
    OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0 if instruments_ok else 2


if __name__ == "__main__":
    sys.exit(main())
