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

# ⚠⚠ **标签口径的唯一出处是 `common.LABEL_KEYS` / `common.has_label()`**（spec 005 T105）。
#   2026-10-10 之前这里另有一份 `TYPE_KEYS`，与 `health.py` 的实现**各算各的**：
#   本脚本回落到原始脏 `msg_type` ⇒ 报 100.0%；`health.py` 只认 `msg_type_norm` ⇒ 报 99.2%。
#   同一份数据、同一个指标、两个数字，而闸门判据④用的是宽的那个。
#   ⇒ 现在只保留一份定义，本脚本按历史口径（允许回落）调用。
sys.path.insert(0, str(ROOT))
from common import LABEL_KEYS as TYPE_KEYS, has_label  # noqa: E402


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
    # ⚠ 关键：**强制 UTF-8 输出**。
    #   Stop hook 的执行环境里 stdout 编码不是 UTF-8（实测追踪日志里中文变 `�ܼ¼`），
    #   而本脚本要打印中文（「总记录」「有标签」）⇒ 抛 UnicodeEncodeError ⇒ rc=1
    #   ⇒ 闸门判据④ 假红（覆盖率其实是 100%）。
    #   2026-10-10 排查了很久才定位到这一层。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                                   # noqa: BLE001
        pass

    ap = argparse.ArgumentParser(description="标签覆盖率体检")
    ap.add_argument("--gate", type=int, default=0, help="覆盖率闸门（%%）；低于则 exit 2")
    ap.add_argument("--by-source", action="store_true", help="按来源列出缺标签最多的")
    ap.add_argument("--samples", type=int, default=0, help="打印 N 条无标签样本")
    ap.add_argument("--quiet", action="store_true",
                    help="只输出一行纯 ASCII 的 COVERAGE=<pct>（给闸门用，避免中文编码问题）")
    args = ap.parse_args()

    tot = 0
    labeled = 0
    strict_labeled = 0          # 只认 msg_type_norm 的干净口径
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
            # 干净口径：**只认 `msg_type_norm`**（与 health.py 同源）
            if has_label(r, strict=True):
                strict_labeled += 1
        elif len(unlabeled_samples) < max(args.samples, 0):
            unlabeled_samples.append((s, (r.get("question") or "")[:60]))

    if not tot:
        print("无数据")
        return 0

    rate = labeled / tot * 100
    strict_rate = strict_labeled / tot * 100

    if args.quiet:
        # 给闸门用：**纯 ASCII 一行**，彻底规避中文编码问题。
        # ⚠ 同时打 STRICT_COVERAGE —— 闸门判据④用宽口径（历史行为），
        #   但**干净口径的数字必须一起打出来**，否则又变成"只有一个数、看不出宽窄"。
        print(f"COVERAGE={rate:.1f}")
        print(f"STRICT_COVERAGE={strict_rate:.1f}")
        return 2 if (args.gate and rate < args.gate) else 0

    print(f"总记录 {tot:,}  |  有标签 {labeled:,}  |  **覆盖率 {rate:.1f}%**")
    print(f"  其中**干净标签**（`msg_type_norm`）{strict_labeled:,} = {strict_rate:.1f}%")
    print(f"  差 {labeled - strict_labeled:,} 条只有原始脏 `msg_type`（混话题/部门）")
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
