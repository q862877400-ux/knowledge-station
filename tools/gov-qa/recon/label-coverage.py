"""标签覆盖率体检 + 闸门 —— 服务 GOAL.md 的 M3（把内容的标签分好）。

## 背景

用户要求「把内容的标签分好，比如谁是咨询、谁是提建议、谁是反馈问题」。
但 2026-10-10 基线：**全库 352,813 条里 64.5% 没有类型标签**（`extra.msg_type` 为空）。

原因有两类，处置不同：
1. **源本身带类型字段**，只是适配器没提取 ⇒ 改适配器 + 重采（或就地回填）
2. **源本身不带类型** ⇒ 需要**按内容推断**（关键词规则）

## 用法

```bash
cd "D:/AI/work space/zcode"
P=.venv/Scripts/python.exe

$P tools/gov-qa/recon/label-coverage.py              # 看覆盖率 + 分布
$P tools/gov-qa/recon/label-coverage.py --by-source  # 按来源看谁最缺
$P tools/gov-qa/recon/label-coverage.py --gate 90    # 闸门：低于 90% 则 exit 2
$P tools/gov-qa/recon/label-coverage.py --samples 5  # 看无标签记录的样本
```

**只读，不改任何数据。**
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"

#: 从这些 extra 字段里找「消息类型」。
#: ⚠ `msg_type_norm` 优先 —— 它由 `label-classify.py` 写入（站方标签归一化 + 模型预测），
#:   是**干净的 9 分类**；原始 `msg_type` 是脏的（混了话题如「省直公积金」、部门如「办公室」）。
TYPE_KEYS = ("msg_type_norm", "msg_type", "type", "objective_type", "rqstType",
             "type_dictText", "letterType")


def read_all():
    for p in glob.glob(str(DATA / "*.jsonl")):
        with open(p, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if not line.strip() or not line.lstrip().startswith("{"):
                    continue
                try:
                    yield json.loads(line)
                except Exception:                                       # noqa: BLE001
                    continue


def msg_type(rec: dict):
    ex = rec.get("extra") or {}
    if not isinstance(ex, dict):
        return None
    for k in TYPE_KEYS:
        v = ex.get(k)
        if v not in (None, "", [], {}):
            return str(v).strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="标签覆盖率体检")
    ap.add_argument("--gate", type=int, default=0, help="覆盖率闸门（%%）；低于则 exit 2")
    ap.add_argument("--by-source", action="store_true", help="按来源列出缺标签最多的")
    ap.add_argument("--samples", type=int, default=0, help="打印 N 条无标签样本")
    args = ap.parse_args()

    tot = 0
    labeled = 0
    dist = Counter()
    per_src = defaultdict(lambda: [0, 0])      # source -> [total, labeled]
    unlabeled_samples = []

    for r in read_all():
        tot += 1
        s = str(r.get("source") or "?")
        t = msg_type(r)
        per_src[s][0] += 1
        if t:
            labeled += 1
            dist[t] += 1
            per_src[s][1] += 1
        elif len(unlabeled_samples) < max(args.samples, 0):
            unlabeled_samples.append((s, (r.get("question") or "")[:60]))

    if not tot:
        print("无数据")
        return 0

    rate = labeled / tot * 100
    print(f"总记录 {tot:,}  |  有标签 {labeled:,}  |  **覆盖率 {rate:.1f}%**")
    print(f"闸门要求 {args.gate}%  ⇒  {'✅ 通过' if rate >= args.gate else '❌ 未达标'}\n")

    print("=== 标签分布 top20 ===")
    for k, v in dist.most_common(20):
        print(f"  {k:22s} {v:8,d}  {v / tot * 100:5.2f}%")

    if args.by_source:
        print("\n=== 缺标签最多的来源 top25 ===")
        rows = [(s, a, b) for s, (a, b) in per_src.items() if a - b > 0]
        rows.sort(key=lambda r: -(r[1] - r[2]))
        for s, a, b in rows[:25]:
            print(f"  {s:26s} {a:8,d} 条，有标签 {b:7,d}（缺 {a - b:7,d}，{(a - b) / a * 100:5.1f}%）")

    if unlabeled_samples:
        print(f"\n=== 无标签样本（看能不能靠关键词补）===")
        for s, q in unlabeled_samples:
            print(f"  [{s}] {q}")

    if args.gate and rate < args.gate:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
