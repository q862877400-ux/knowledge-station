"""全量重跑对照（可复算的产物）：同样的输入跑两遍，逐条通道名次必须一模一样。

**为什么要单独留一份**：报告头部断言"全量重跑对照 0 处差异"，但 `determinism.json` 只记了
12 条抽样 —— 独立复核指出这条断言**没有产物可核**。本脚本把它变成可复算的：
基线取**已提交的旧记录**（`git show bd7516a:eval/recall-funnel/funnel-per-query.jsonl`，
那次跑在 `funnel.py` 的并集口径修好之前，**通道名次不受口径影响**），
与工作区当前的 `funnel-per-query.jsonl` 逐字段比。

⚠ 基线是一次**旧实现**跑出来的，所以"并集/命中通道"字段本来就该不同（那正是被修的部分）；
本脚本把"名次类字段"与"口径类字段"**分开报**。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\rerun-consistency.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "rerun-consistency.json"
BASE_REV = "bd7516a"
CH = ("exact", "fts", "vec", "modality", "legal_element", "behavior_scope")
#: 名次类字段：跨两次运行必须完全一致（口径改动不该动它们）
RANK_FIELDS = ("n", "gold_rank", "deep_n", "deep_gold_rank", "fires")
#: 口径类字段：本次修的就是它们（并集与命中通道），**允许**不同
CALIBER_FIELDS = ("union", "hit_channels", "hit_in_deep_union")


def main() -> int:
    rel = "eval/recall-funnel/funnel-per-query.jsonl"
    blob = subprocess.run(["git", "show", f"{BASE_REV}:{rel}"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", check=True).stdout
    old = {json.loads(l)["i"]: json.loads(l) for l in blob.splitlines() if l.strip()}
    new = {json.loads(l)["i"]: json.loads(l)
           for l in (HERE / "funnel-per-query.jsonl").read_text(encoding="utf-8").splitlines()
           if l.strip()}

    rank_diffs, other_diffs, caliber_diffs = [], [], []
    for i in sorted(set(old) & set(new)):
        a, b = old[i], new[i]
        for c in CH:
            for f in RANK_FIELDS:
                if a["channels"][c][f] != b["channels"][c][f]:
                    rank_diffs.append({"i": i, "channel": c, "field": f,
                                       "old": a["channels"][c][f], "new": b["channels"][c][f]})
        if a.get("fts_pool") != b.get("fts_pool"):
            other_diffs.append({"i": i, "field": "fts_pool",
                                "old": a.get("fts_pool"), "new": b.get("fts_pool")})
        if (a.get("fused") or {}).get("gold_rank") != (b.get("fused") or {}).get("gold_rank"):
            other_diffs.append({"i": i, "field": "fused.gold_rank",
                                "old": a["fused"]["gold_rank"], "new": b["fused"]["gold_rank"]})
        if (a.get("fused_rerank8") or {}).get("hit") != (b.get("fused_rerank8") or {}).get("hit"):
            other_diffs.append({"i": i, "field": "fused_rerank8.hit",
                                "old": a["fused_rerank8"], "new": b["fused_rerank8"]})
        if a.get("hit_channels") != b.get("hit_channels"):
            caliber_diffs.append({"i": i, "old": a["hit_channels"], "new": b["hit_channels"]})

    result = {
        "meta": {
            "base": f"{BASE_REV}:{rel}（并集口径修好之前的跑，由 git show 取回，可复算）",
            "current": str(HERE / "funnel-per-query.jsonl"),
            "what": "同样输入跑两遍，逐条比每路候选数与 gold 名次",
            "why": "报告头部断言'全量重跑对照 0 处差异'，独立复核指出没有产物可核",
        },
        "n_compared": len(set(old) & set(new)),
        "rank_field_diffs": {"n": len(rank_diffs), "samples": rank_diffs[:5]},
        "other_field_diffs": {"n": len(other_diffs), "samples": other_diffs[:5]},
        "caliber_field_diffs": {
            "n": len(caliber_diffs),
            "note": "口径类字段（命中通道）**本来就该不同**——那次是旧实现跑的；实测只翻了这几条",
            "samples": caliber_diffs[:5],
        },
        "verdict": ("名次类字段跨两跑完全一致" if not rank_diffs and not other_diffs
                    else "⚠ 名次类字段出现差异：结果不可复现，必须先查环境"),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if not rank_diffs and not other_diffs else 1


if __name__ == "__main__":
    sys.exit(main())
