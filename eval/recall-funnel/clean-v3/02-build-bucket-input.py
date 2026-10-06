"""清洗 v3 · 步骤 2：构造**失败题四桶盲分**的输入。

人群：六路同预算并集 @1000 **完全没命中**的那 104 条里抽的 50 条
（= `eval/recall-funnel/failure-samples.jsonl`，phase-0 的产物；
这正是外部评估说的"60% 前 1000 都没找到"的那一群）。

⚠ **盲**：输出只给 `id / 问法 / 金标标准号 / 金标条款号 / 金标条文原文`。
**不给** `channels` / `fused` / `votes` / `confidence` / 任何名次或分臂信息 ——
分桶判的是"这条题本身的问题出在哪"，不是"检索哪里错了"。

口径与理由见 `RULES-FROZEN.md` §五。规则冻结凭证见 `rules-hash.txt`。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\02-build-bucket-input.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "eval" / "recall-funnel" / "failure-samples.jsonl"
OUT = HERE / "bucket-input.jsonl"
RULES = HERE / "RULES-FROZEN.md"

KEEP = ("i", "query", "gold_std", "gold_clause", "gold_text")


def main() -> int:
    if not RULES.exists():
        print("⛔ 规则没冻结，不许产生标注输入")
        return 1
    digest = hashlib.sha256(RULES.read_bytes()).hexdigest()
    recorded = (HERE / "rules-hash.txt").read_text(encoding="utf-8")
    if digest not in recorded:
        print("⛔ 规则文件与冻结凭证不一致（被改过？）—— 停止")
        return 1
    print(f"[bucket] 规则校验通过，sha256 = {digest[:16]}…")

    rows = [json.loads(l) for l in SRC.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for r in rows:
        out.append({"id": f"f{r['i']}", **{k: r.get(k) for k in KEEP if k != "i"}})
    with OUT.open("w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[bucket] 已写 {OUT.name}：{len(out)} 行；每行键 = {sorted(out[0])}")
    print("[bucket] 已剔除：channels / fused / fused_rerank8 / votes / confidence / modality_filter / fts_pool")
    return 0


if __name__ == "__main__":
    sys.exit(main())
