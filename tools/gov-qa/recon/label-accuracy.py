"""标签真实准确率 —— spec 004 的 US3（FR-014 / SC-007）。

## 为什么必须「人工核对」

现有标签的来源是：**站方原始标签归一化（11.5 万条）+ 模型预测（24 万条，自评 78.9%）**。
**模型自评的准确率不可信** —— 它是 held-out 测试集上的数字，
而测试集来自「站方标签」那部分，模型标的那 24 万条根本没有真值。

⇒ 要回答「标签能不能信」，**只能人工抽检**。

## 宪法 III 的要求

> 「未做的 MUST 写『明确未做』」

所以本工具**强制留痕**：没核对过就输出「明确未做」，
**不许拿模型自评数充数**。

## 用法（两步，中间必须人工）

```bash
# 第一步：分层抽样并导出可核对表单
$P tools/gov-qa/recon/label-accuracy.py --sample 200 --export /tmp/label-check.csv
# 人工打开 CSV，把 label_ok 列填 1（对）/ 0（错）

# 第二步：算真实准确率
$P tools/gov-qa/recon/label-accuracy.py --score /tmp/label-check.csv
```
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common import ascii_kv, human, iter_records                 # noqa: E402

DATA = ROOT / "data"

TYPE_KEYS = ("msg_type_norm", "msg_type", "type", "objective_type",
             "rqstType", "type_dictText", "letterType")

#: SC-007 的阈值
TARGET_ACCURACY = 80.0


def _label(rec) -> str:
    ex = rec.get("extra") or {}
    if not isinstance(ex, dict):
        return ""
    for k in TYPE_KEYS:
        v = ex.get(k)
        if v not in (None, "", [], {}):
            return str(v).strip()
    return ""


def _source(rec) -> str:
    return str(rec.get("source") or "?")


def cmd_sample(args) -> int:
    """分层抽样：按 (标签, 标签来源) 分层，保证每层都有样本。"""
    buckets: dict[tuple, list] = defaultdict(list)
    for rec in iter_records(str(DATA / "*.jsonl")):
        lab = _label(rec)
        if not lab:
            continue
        ex = rec.get("extra") or {}
        src = str(ex.get("msg_type_source") or "?") if isinstance(ex, dict) else "?"
        buckets[(lab, src)].append(rec)

    if not buckets:
        human("无带标签记录")
        return 1

    rnd = random.Random(20261010)
    total_layers = len(buckets)
    per_layer = max(1, args.sample // total_layers)

    rows = []
    for (lab, src), recs in sorted(buckets.items()):
        rnd.shuffle(recs)
        for rec in recs[:per_layer]:
            rows.append({
                "source": _source(rec),
                "id": str(rec.get("id") or ""),
                "label": lab,
                "label_source": src,
                "question": (rec.get("question") or "")[:200].replace("\n", " "),
                "label_ok": "",              # ← 人工填 1 / 0
                "note": "",                  # ← 人工可填备注
            })

    rows = rows[:args.sample]
    out = Path(args.export)
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    human(f"已导出 {len(rows)} 条到 {out}")
    human(f"分层：{total_layers} 层（标签 × 标签来源），每层 {per_layer} 条")
    human("")
    human("下一步（**必须人工**）：打开 CSV，把 label_ok 列填 1（对）或 0（错），然后：")
    human(f"  {sys.executable} {__file__} --score {out}")
    human("")
    human("⚠ 宪法 III 要求：未核对时**不许**拿模型自评数充数。")
    return 0


def cmd_score(args) -> int:
    """读人工核对结果，算真实准确率。"""
    p = Path(args.score)
    if not p.exists():
        human(f"❌ 找不到文件：{p}")
        return 1

    rows = []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            v = str(r.get("label_ok") or "").strip()
            if v in ("1", "0"):
                rows.append(r)

    if not rows:
        # **宪法 III**：未核对 ⇒ 明确说未做，不给数字
        human("⚠️  **明确未做**：CSV 里没有任何已核对的 `label_ok`（1/0）。")
        human("    无法给出真实准确率。")
        human("")
        human("    （不许用模型自评的 78.9% 充数 —— 那是 held-out 测试集上的数字，")
        human("      而模型实际标注的 24 万条没有真值。）")
        return 1

    ok = sum(1 for r in rows if str(r.get("label_ok")).strip() == "1")
    acc = ok / len(rows) * 100

    if args.quiet:
        ascii_kv({"SAMPLED": len(rows), "CORRECT": ok,
                  "ACCURACY": round(acc, 1), "TARGET": TARGET_ACCURACY,
                  "PASS": acc >= TARGET_ACCURACY})
        return 0 if acc >= TARGET_ACCURACY else 1

    human(f"人工核对样本：{len(rows)} 条｜判对 {ok} 条")
    human(f"**真实准确率：{acc:.1f}%**（目标 ≥{TARGET_ACCURACY:.0f}%）"
          f"  {'✅ 通过' if acc >= TARGET_ACCURACY else '❌ 未达标'}")

    # 按标签分层的准确率
    per: dict[str, list] = defaultdict(list)
    for r in rows:
        per[str(r.get("label") or "?")].append(str(r.get("label_ok")).strip() == "1")
    human("")
    human("按标签：")
    for lab, oks in sorted(per.items(), key=lambda kv: -len(kv[1])):
        a = sum(oks) / len(oks) * 100
        human(f"  {lab:8s} {len(oks):4d} 条  准确率 {a:5.1f}%")

    # 按标签来源分层 —— 这才是关键：模型标的那部分准不准
    persrc: dict[str, list] = defaultdict(list)
    for r in rows:
        persrc[str(r.get("label_source") or "?")].append(
            str(r.get("label_ok")).strip() == "1")
    human("")
    human("按标签来源（**关键** —— 模型标的那部分准不准）：")
    for src, oks in sorted(persrc.items(), key=lambda kv: -len(kv[1])):
        a = sum(oks) / len(oks) * 100
        human(f"  {src:14s} {len(oks):4d} 条  准确率 {a:5.1f}%")

    return 0 if acc >= TARGET_ACCURACY else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="标签真实准确率（spec 004 US3）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", type=int, help="抽样条数")
    g.add_argument("--score", help="读人工核对后的 CSV 算准确率")
    ap.add_argument("--export", default="label-check.csv", help="配合 --sample：导出路径")
    ap.add_argument("--quiet", action="store_true", help="纯 ASCII")
    args = ap.parse_args()

    if args.sample:
        return cmd_sample(args)
    return cmd_score(args)


if __name__ == "__main__":
    sys.exit(main())
